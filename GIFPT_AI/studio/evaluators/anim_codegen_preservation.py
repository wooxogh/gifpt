"""Edge evaluator: anim_ir → manim_code.

This is the edge where v1 bleeds the most (see docs/failure-taxonomy.md).
`post_process_manim_code` exists at 26 regex rules precisely because this
handoff loses information — the codegen LLM invents helpers not described
in the anim_ir, or uses color names the anim_ir never specified.

Score drops to 0 when any of:
    1. A layout item id has no textual trace in the code
    2. The code references a hallucinated helper from _UNKNOWN_HELPERS
    3. The code references a forbidden API from FORBIDDEN_NAMES
"""
from __future__ import annotations

import ast
from typing import Any

from studio.evaluators.base import EdgeEvalResult


def _collect_identifiers(code: str) -> tuple[set[str], set[str], list[str]]:
    """Return (names, attributes, string_constants) found in the code.

    Falls back to an empty partition if the code doesn't parse; the
    caller will still flag "syntax_error" via the missing list.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set(), set(), []

    names: set[str] = set()
    attrs: set[str] = set()
    strings: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            attrs.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)

    return names, attrs, strings


def _id_appears(layout_id: str, code: str, strings: list[str]) -> bool:
    """Heuristic: layout id is 'present' if it appears as a substring in any
    string literal or as a word in variable/Name usage.

    This is deliberately generous — the evaluator measures preservation of
    *intent*, not naming discipline. A Text("Input matrix") can satisfy the
    layout id 'input_matrix' even if the exact id string isn't used.
    """
    if not layout_id:
        return False
    needle = layout_id.lower()
    for s in strings:
        if needle in s.lower() or needle.replace("_", " ") in s.lower():
            return True
    # Fallback: case-insensitive substring search against raw code for
    # variable-name-style occurrences (e.g. `input_matrix = VGroup(...)`).
    return needle in code.lower()


def anim_codegen_preservation(
    anim_ir: dict,
    manim_code: str,
    *,
    unknown_helpers: set[str] | None = None,
    forbidden_names: set[str] | None = None,
) -> EdgeEvalResult:
    """Score the anim_ir → manim_code handoff.

    Args:
        anim_ir: Animation IR dict with `layout` and `actions` keys.
        manim_code: The Python source string emitted by codegen.
        unknown_helpers: Optional override. When None, imports the live
            `_UNKNOWN_HELPERS` list from `studio.ai.llm_codegen`.
        forbidden_names: Optional override for the AST-level forbidden set.
    """
    if unknown_helpers is None:
        try:
            from studio.ai.llm_codegen import _UNKNOWN_HELPERS
            unknown_helpers = set(_UNKNOWN_HELPERS)
        except Exception:
            unknown_helpers = set()

    if forbidden_names is None:
        try:
            from studio.video_render import FORBIDDEN_NAMES
            forbidden_names = set(FORBIDDEN_NAMES)
        except Exception:
            forbidden_names = set()

    missing: list[str] = []

    if not isinstance(manim_code, str) or not manim_code.strip():
        return EdgeEvalResult(
            edge="anim_codegen",
            score=0,
            missing=["manim_code:empty"],
            extra={"hallucinated": [], "forbidden_hits": []},
        )

    try:
        ast.parse(manim_code)
        parseable = True
    except SyntaxError as exc:
        parseable = False
        missing.append(f"syntax:{exc.msg}")

    names, attrs, strings = _collect_identifiers(manim_code)
    all_symbols = names | attrs

    # Layout id coverage
    layout_items = anim_ir.get("layout") if isinstance(anim_ir, dict) else None
    layout_ids: list[str] = []
    if isinstance(layout_items, list):
        for item in layout_items:
            if isinstance(item, dict):
                item_id = item.get("id")
                if isinstance(item_id, str) and item_id:
                    layout_ids.append(item_id)

    for layout_id in layout_ids:
        if not _id_appears(layout_id, manim_code, strings):
            missing.append(f"layout_id:{layout_id}")

    # Hallucinated helpers
    hallucinated = sorted(all_symbols & unknown_helpers)
    for helper in hallucinated:
        missing.append(f"hallucinated:{helper}")

    # Forbidden API references
    forbidden_hits = sorted(all_symbols & forbidden_names)
    # FORBIDDEN_NAMES already contains UNKNOWN_HELPERS in v1 — dedupe
    forbidden_only = [f for f in forbidden_hits if f not in hallucinated]
    for name in forbidden_only:
        missing.append(f"forbidden:{name}")

    extra = {
        "parseable": parseable,
        "layout_id_count": len(layout_ids),
        "hallucinated": hallucinated,
        "forbidden_hits": forbidden_only,
    }

    score = 1 if not missing else 0
    return EdgeEvalResult(edge="anim_codegen", score=score, missing=missing, extra=extra)
