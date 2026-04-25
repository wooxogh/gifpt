"""Shared types for the 4 edge-preservation evaluators.

Every evaluator returns an `EdgeEvalResult` so downstream aggregation
(run-diff, LangSmith feedback, CI reports) can iterate over a uniform
structure regardless of which edge produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EDGE_NAMES: tuple[str, ...] = (
    "pseudo_anim",
    "anim_codegen",
    "codegen_render",
    "render_qa",
    # 5th dimension added in Week 4 Day 3. Not a pairwise edge — it's a
    # transitive check that anchors user_text intent against every stage.
    # Kept in the same tuple so adapter/feedback code can iterate uniformly.
    "intent_preservation",
)


@dataclass
class EdgeEvalResult:
    edge: str
    score: int
    missing: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.edge not in EDGE_NAMES:
            raise ValueError(f"unknown edge '{self.edge}' (expected one of {EDGE_NAMES})")
        if self.score not in (0, 1):
            raise ValueError(f"score must be 0 or 1, got {self.score!r}")

    @property
    def passed(self) -> bool:
        return self.score == 1

    def as_feedback(self, key: str | None = None) -> dict[str, Any]:
        """Return a LangSmith feedback dict usable by `client.create_feedback`.

        Shape matches LangSmith's FeedbackCreate schema: {key, score, value, comment}.
        """
        feedback_key = key or f"{self.edge}_preservation"
        if self.passed:
            comment = f"OK — {self.edge} edge preserved"
        else:
            preview = ", ".join(self.missing[:3])
            more = f" (+{len(self.missing) - 3} more)" if len(self.missing) > 3 else ""
            comment = f"{len(self.missing)} missing on {self.edge}: {preview}{more}"

        return {
            "key": feedback_key,
            "score": float(self.score),
            "value": {
                "edge": self.edge,
                "missing": list(self.missing),
                **self.extra,
            },
            "comment": comment,
        }
