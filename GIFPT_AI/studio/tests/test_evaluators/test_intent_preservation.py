"""Tests for the 5th evaluator: canonical intent preservation."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from studio.evaluators.intent_preservation import intent_preservation  # noqa: E402


def _loss_record(lost_ent=None, lost_op=None, pres_ent=0, pres_op=0) -> dict:
    lost_ent = lost_ent or []
    lost_op = lost_op or []
    total = len(lost_ent) + len(lost_op) + pres_ent + pres_op
    rate = 1.0 if total == 0 else 1.0 - (len(lost_ent) + len(lost_op)) / total
    return {
        "stage": "x",
        "lost_entities": lost_ent,
        "lost_operations": lost_op,
        "preserved_entities": pres_ent,
        "preserved_operations": pres_op,
        "preservation_rate": rate,
    }


# ---------- all preserved ----------


def test_all_preserved_scores_one():
    intent = {
        "entities": ["input matrix", "kernel"],
        "operations": ["slide kernel right"],
    }
    intent_loss = {
        "pseudo_ir": _loss_record(pres_ent=2, pres_op=1),
        "anim_ir": _loss_record(pres_ent=2, pres_op=1),
        "codegen": _loss_record(pres_ent=2, pres_op=1),
    }
    result = intent_preservation(intent, intent_loss)
    assert result.edge == "intent_preservation"
    assert result.score == 1
    assert result.missing == []
    assert result.extra["stages_checked"] == 3
    assert result.extra["overall_rate"] == 1.0
    assert result.extra["per_stage_rate"]["pseudo_ir"] == 1.0


def test_partial_loss_scores_zero_and_records_where():
    intent = {
        "entities": ["input matrix", "output grid"],
        "operations": ["slide kernel right"],
    }
    intent_loss = {
        "pseudo_ir": _loss_record(
            lost_ent=["output grid"], pres_ent=1, pres_op=1
        ),
        "anim_ir": _loss_record(
            lost_ent=["output grid"], pres_ent=1, pres_op=1
        ),
        "codegen": _loss_record(pres_ent=2, pres_op=1),
    }
    result = intent_preservation(intent, intent_loss)
    assert result.score == 0
    assert any(
        "pseudo_ir:entity:output grid" == m for m in result.missing
    )
    assert any("anim_ir:entity:output grid" == m for m in result.missing)
    assert result.extra["per_stage_lost"]["pseudo_ir"] == ["entity:output grid"]
    assert result.extra["per_stage_lost"]["codegen"] == []
    # overall_rate averages over stages that ran
    assert 0 < result.extra["overall_rate"] < 1


def test_user_to_pseudo_edge_loss_is_visible():
    """The new signal IntentTracker adds: user_text → pseudo_ir loss.
    The 4 pairwise evaluators cannot see this — pseudo_ir is their starting
    point. This test pins the behavior."""
    intent = {
        "entities": ["hash bucket"],
        "operations": [],
    }
    # pseudo_ir already dropped "hash bucket". Downstream stages faithfully
    # propagate the already-diminished pseudo_ir (no further loss).
    intent_loss = {
        "pseudo_ir": _loss_record(lost_ent=["hash bucket"]),
        "anim_ir": _loss_record(lost_ent=["hash bucket"]),
        "codegen": _loss_record(lost_ent=["hash bucket"]),
    }
    result = intent_preservation(intent, intent_loss)
    assert result.score == 0
    # The loss is recorded at every stage because it's a persistent gap.
    assert "pseudo_ir:entity:hash bucket" in result.missing
    assert "anim_ir:entity:hash bucket" in result.missing
    assert "codegen:entity:hash bucket" in result.missing


# ---------- extract failure ----------


def test_extract_failure_scores_zero_with_reason():
    result = intent_preservation(
        intent=None,
        intent_loss={},
        stage_errors={"intent_extract": "TimeoutError: upstream slow"},
    )
    assert result.score == 0
    assert result.extra["reason"] == "extract_failed"
    assert any("intent_extract" in m for m in result.missing)


# ---------- empty intent ----------


def test_empty_intent_is_neutral_pass():
    """No canonical intent → no signal. Return preserved (don't punish)."""
    result = intent_preservation({"entities": [], "operations": []}, {})
    assert result.score == 1
    assert result.extra["reason"] == "empty_intent"
    assert result.extra["stages_checked"] == 0


def test_none_intent_is_neutral_pass():
    result = intent_preservation(None, None)
    assert result.score == 1


# ---------- upstream crash ----------


def test_upstream_crash_no_stages_reached():
    """Intent was extracted but no stage got far enough to be checked."""
    intent = {"entities": ["x"], "operations": []}
    intent_loss = {}  # empty — pseudo_ir stage crashed before check ran
    result = intent_preservation(intent, intent_loss)
    assert result.score == 0
    assert result.extra["reason"] == "upstream_crash"
    assert result.extra["stages_checked"] == 0


def test_partial_stages_only_pseudo_reached():
    """pseudo_ir ran and was clean, but anim_ir/codegen never ran (crash)."""
    intent = {"entities": ["stack"], "operations": []}
    intent_loss = {"pseudo_ir": _loss_record(pres_ent=1)}
    result = intent_preservation(intent, intent_loss)
    # Only stages that actually ran are counted.
    assert result.extra["stages_checked"] == 1
    assert result.score == 1
    assert result.extra["overall_rate"] == 1.0


# ---------- feedback shape ----------


def test_as_feedback_shape_is_langsmith_compatible():
    intent = {"entities": ["a"], "operations": []}
    intent_loss = {"pseudo_ir": _loss_record(pres_ent=1)}
    result = intent_preservation(intent, intent_loss)
    fb = result.as_feedback()
    assert fb["key"] == "intent_preservation_preservation"  # base formatter
    assert fb["score"] == 1.0
    assert fb["value"]["edge"] == "intent_preservation"
    assert "missing" in fb["value"]
