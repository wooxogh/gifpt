"""IntentTracker — canonical intent extraction from user text.

Week 4 Day 1: observability-only. Given a natural-language description,
extract a minimal canonical intent (entity list + operation list) that
downstream stages must preserve. The check/injection logic lives in
sibling modules and will be wired in Day 2+.

Design notes:
- Existing 4 edge evaluators are pairwise (pseudo→anim, anim→codegen, ...).
  They cannot see losses that happen BEFORE pseudo_ir is written. IntentTracker
  closes that gap by anchoring to the raw user text.
- Extraction uses `gpt-4o` to stay aligned with the pipeline stages (Week 3
  uniform-model principle: don't introduce a new model tier as a hidden
  independent variable).
- Output schema is deliberately minimal (two flat string lists). Rich
  hierarchical schemas tempt the LLM to invent structure the user didn't ask
  for; that's how intent extractors silently hallucinate.
"""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from studio.ai._tracing import traceable

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


MODEL_INTENT = "gpt-4o"


class IntentSchema(BaseModel):
    """Canonical intent extracted from a user description.

    `entities` are the visual objects the user expects to see on screen.
    `operations` are the visually observable actions the animation must show.
    Both are short user-facing phrases (not implementation details).
    """

    entities: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.entities and not self.operations


SYSTEM_PROMPT_INTENT = """You are an intent extractor for algorithm-animation requests.
Read a natural-language description and output a minimal canonical intent as JSON.

Output schema:
{
  "entities": list of short noun phrases naming the visual objects the user
              expects to see on screen (e.g. "input matrix", "query token",
              "pivot pointer", "hash bucket"). Keep them atomic and
              user-facing — not implementation details.
  "operations": list of short verb phrases naming the actions the animation
                must show (e.g. "slide kernel right", "highlight compared pair",
                "pop top of stack"). Each operation must be visually observable.
}

Rules:
- Only include items EXPLICITLY stated or unambiguously implied by the text.
- Do NOT invent operations the user did not ask for.
- Do NOT repeat the same concept under different phrasings.
- Keep phrases short (2–5 words) and consistent ("highlight X", not "make X yellow").
- Lowercase each phrase unless it's a proper noun or acronym.
- Output JSON only. No commentary.

Example input:
  "A 4x4 input grid with a 2x2 kernel; yellow highlight slides over the input
   window as the kernel convolves. Show each convolution output value as it's
   computed."

Example output:
{
  "entities": ["4x4 input grid", "2x2 kernel", "output grid"],
  "operations": ["slide kernel over input", "highlight current window",
                 "show output value per step"]
}
"""


def build_intent_prompt(user_text: str) -> str:
    return (
        f"Description:\n{user_text.strip()}\n\n"
        "Extract the canonical intent as JSON matching the schema."
    )


def _parse_intent_response(raw: str) -> IntentSchema:
    """Parse LLM JSON output into IntentSchema, tolerating minor shape drift."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"intent_extract: invalid JSON from LLM: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"intent_extract: expected dict, got {type(data).__name__}")

    entities = data.get("entities") or []
    operations = data.get("operations") or []
    if not isinstance(entities, list):
        entities = []
    if not isinstance(operations, list):
        operations = []

    entities = [str(e).strip() for e in entities if str(e).strip()]
    operations = [str(o).strip() for o in operations if str(o).strip()]

    try:
        return IntentSchema(entities=entities, operations=operations)
    except ValidationError as exc:
        raise ValueError(f"intent_extract: schema validation failed: {exc}") from exc


def _extract_usage(usage_obj: Any) -> dict | None:
    if not usage_obj:
        return None
    return {
        "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
        "completion_tokens": getattr(usage_obj, "completion_tokens", None),
        "total_tokens": getattr(usage_obj, "total_tokens", None),
    }


def extract_intent(user_text: str) -> IntentSchema:
    """Extract canonical intent from user text. Returns IntentSchema."""
    resp = client.chat.completions.create(
        model=MODEL_INTENT,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_INTENT},
            {"role": "user", "content": build_intent_prompt(user_text)},
        ],
    )
    raw = resp.choices[0].message.content
    return _parse_intent_response(raw)


@traceable(name="intent_extract", run_type="chain")
def extract_intent_with_usage(user_text: str) -> tuple[IntentSchema, dict | None]:
    """Variant that also returns token usage for cost bookkeeping."""
    resp = client.chat.completions.create(
        model=MODEL_INTENT,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_INTENT},
            {"role": "user", "content": build_intent_prompt(user_text)},
        ],
    )
    raw = resp.choices[0].message.content
    intent = _parse_intent_response(raw)
    usage = _extract_usage(getattr(resp, "usage", None))
    return intent, usage


# ----------------------------------------------------------------------
# Day 2: check_intent_loss — deterministic matcher over stage artifacts
# ----------------------------------------------------------------------

# English stopwords dropped before token matching. Deliberately small —
# we want loss detection to be conservative, so we only strip words that
# carry no discriminative signal.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "of", "in", "on", "at", "to", "for", "with",
        "and", "or", "is", "are", "be", "by", "from", "as", "that", "this",
        "it", "its", "into", "onto", "over", "under", "each", "per",
        "show", "shows", "showing", "display", "displays", "displaying",
    }
)

# Tokens shorter than this are ignored (too likely to false-match).
_MIN_TOKEN_LEN = 3


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords and short tokens."""
    if not text:
        return []
    buf: list[str] = []
    current: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                buf.append("".join(current))
                current = []
    if current:
        buf.append("".join(current))
    return [t for t in buf if len(t) >= _MIN_TOKEN_LEN and t not in _STOPWORDS]


def _intent_phrase_tokens(phrase: str) -> list[str]:
    """Content tokens inside a single intent phrase, preserving order."""
    return _tokenize(phrase)


def _serialize_pseudo_ir(pseudo_ir: dict) -> str:
    """Flatten pseudo_ir into a single searchable text blob."""
    if not isinstance(pseudo_ir, dict):
        return ""
    parts: list[str] = []
    meta = pseudo_ir.get("metadata") or {}
    if isinstance(meta, dict):
        parts.append(str(meta.get("title") or ""))
    for ent in pseudo_ir.get("entities") or []:
        if not isinstance(ent, dict):
            continue
        parts.append(str(ent.get("id") or ""))
        parts.append(str(ent.get("type") or ""))
        attrs = ent.get("attributes") or {}
        if isinstance(attrs, dict):
            for k, v in attrs.items():
                parts.append(f"{k} {v}")
    for op in pseudo_ir.get("operations") or []:
        if not isinstance(op, dict):
            continue
        parts.append(str(op.get("subject") or ""))
        parts.append(str(op.get("action") or ""))
        parts.append(str(op.get("target") or ""))
        parts.append(str(op.get("description") or ""))
    return " ".join(parts)


def _serialize_anim_ir(anim_ir: dict) -> str:
    """Flatten anim_ir into a single searchable text blob."""
    if not isinstance(anim_ir, dict):
        return ""
    parts: list[str] = []
    meta = anim_ir.get("metadata") or {}
    if isinstance(meta, dict):
        parts.append(str(meta.get("title") or ""))
        parts.append(str(meta.get("domain") or ""))
    for item in anim_ir.get("layout") or []:
        if not isinstance(item, dict):
            continue
        parts.append(str(item.get("id") or ""))
        parts.append(str(item.get("shape") or ""))
        parts.append(str(item.get("label") or ""))
        parts.append(str(item.get("dimensions") or ""))
    for act in anim_ir.get("actions") or []:
        if not isinstance(act, dict):
            continue
        parts.append(str(act.get("target") or ""))
        parts.append(str(act.get("animation") or ""))
        parts.append(str(act.get("description") or ""))
    return " ".join(parts)


def _serialize_codegen(manim_code: str) -> str:
    """Codegen output is already a string; pass-through."""
    return manim_code or ""


_SERIALIZERS = {
    "pseudo_ir": _serialize_pseudo_ir,
    "anim_ir": _serialize_anim_ir,
    "codegen": _serialize_codegen,
}


def _phrase_preserved(phrase_tokens: list[str], stage_tokens_set: set[str]) -> bool:
    """An intent phrase is preserved in a stage iff ALL of its content
    tokens appear in the stage's token set.

    This is deliberately conservative: a single missing content token
    marks the phrase as lost. False positives (phrase flagged lost when
    the LLM used a synonym) are acceptable for Day 2 — Day 5 analysis
    will tell us whether we need a semantic matcher instead.

    Edge case: empty phrase_tokens (phrase was all stopwords or too
    short) is treated as preserved by default — we have no signal to
    judge it either way, and reporting loss with zero evidence would
    poison the loss rate.
    """
    if not phrase_tokens:
        return True
    return all(tok in stage_tokens_set for tok in phrase_tokens)


class IntentLoss(BaseModel):
    """Per-stage intent loss report."""

    stage: str
    lost_entities: list[str] = Field(default_factory=list)
    lost_operations: list[str] = Field(default_factory=list)
    preserved_entities: int = 0
    preserved_operations: int = 0

    @property
    def total_lost(self) -> int:
        return len(self.lost_entities) + len(self.lost_operations)

    @property
    def total_checked(self) -> int:
        return (
            len(self.lost_entities)
            + len(self.lost_operations)
            + self.preserved_entities
            + self.preserved_operations
        )

    @property
    def preservation_rate(self) -> float:
        total = self.total_checked
        if total == 0:
            return 1.0
        return 1.0 - (self.total_lost / total)


def check_intent_loss(
    intent: IntentSchema,
    artifact: Any,
    stage: str,
) -> IntentLoss:
    """Check how much of `intent` survived into a given pipeline stage.

    Args:
        intent: The canonical intent extracted from user text.
        artifact: The stage's output (dict for pseudo_ir/anim_ir, str for codegen).
        stage: One of "pseudo_ir", "anim_ir", "codegen".

    Returns:
        IntentLoss with lost_entities / lost_operations populated.
    """
    if stage not in _SERIALIZERS:
        raise ValueError(f"unknown stage '{stage}' (expected one of {list(_SERIALIZERS)})")

    serialize = _SERIALIZERS[stage]
    stage_text = serialize(artifact)
    stage_tokens = set(_tokenize(stage_text))

    lost_entities: list[str] = []
    preserved_entities = 0
    for phrase in intent.entities:
        phrase_tokens = _intent_phrase_tokens(phrase)
        if _phrase_preserved(phrase_tokens, stage_tokens):
            preserved_entities += 1
        else:
            lost_entities.append(phrase)

    lost_operations: list[str] = []
    preserved_operations = 0
    for phrase in intent.operations:
        phrase_tokens = _intent_phrase_tokens(phrase)
        if _phrase_preserved(phrase_tokens, stage_tokens):
            preserved_operations += 1
        else:
            lost_operations.append(phrase)

    return IntentLoss(
        stage=stage,
        lost_entities=lost_entities,
        lost_operations=lost_operations,
        preserved_entities=preserved_entities,
        preserved_operations=preserved_operations,
    )
