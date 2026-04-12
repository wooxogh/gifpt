"""Tests for render → qa edge preservation evaluator."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from studio.evaluators.render_qa_preservation import render_qa_preservation  # noqa: E402


FAKE_DOMAIN_CONFIG = {
    "sorting": {
        "threshold": 5.0,
        "required_checks": [
            {"key": "elements_visible", "penalty": 2.0},
            {"key": "comparison_shown", "penalty": 2.5},
            {"key": "sorted_progression", "penalty": 1.5},
        ],
    },
    "graph_traversal": {
        "threshold": 5.0,
        "required_checks": [
            {"key": "nodes_visible", "penalty": 2.5},
            {"key": "edges_drawn", "penalty": 2.0},
        ],
    },
}


def test_passing_qa_with_all_checks_scores_one():
    qa_result = {
        "score": 7.0,
        "threshold": 5.0,
        "passed": True,
        "domain_checks": {
            "elements_visible": True,
            "comparison_shown": True,
            "sorted_progression": True,
        },
        "issues": [],
    }
    result = render_qa_preservation(
        qa_result, domain="sorting", domain_qa_config=FAKE_DOMAIN_CONFIG
    )
    assert result.score == 1, f"expected pass, got missing={result.missing}"
    assert result.edge == "render_qa"
    assert result.extra["failed_checks"] == []


def test_failing_qa_score_fails():
    qa_result = {
        "score": 3.2,
        "threshold": 5.0,
        "passed": False,
        "domain_checks": {},
        "issues": ["too dark"],
    }
    result = render_qa_preservation(
        qa_result, domain=None, domain_qa_config=FAKE_DOMAIN_CONFIG
    )
    assert result.score == 0
    assert any(m.startswith("qa_score:") for m in result.missing)


def test_domain_check_failure_fails():
    qa_result = {
        "score": 6.8,
        "threshold": 5.0,
        "passed": True,
        "domain_checks": {
            "elements_visible": True,
            "comparison_shown": False,   # this is the bfs/sorting bleed
            "sorted_progression": True,
        },
        "issues": [],
    }
    result = render_qa_preservation(
        qa_result, domain="sorting", domain_qa_config=FAKE_DOMAIN_CONFIG
    )
    assert result.score == 0
    assert "comparison_shown" in result.extra["failed_checks"]
    assert "domain_check:sorting.comparison_shown" in result.missing


def test_missing_domain_check_is_flagged():
    qa_result = {
        "score": 6.0,
        "threshold": 5.0,
        "passed": True,
        "domain_checks": {"elements_visible": True},
        "issues": [],
    }
    result = render_qa_preservation(
        qa_result, domain="sorting", domain_qa_config=FAKE_DOMAIN_CONFIG
    )
    assert result.score == 0
    assert any("(missing)" in m for m in result.missing)


def test_non_dict_qa_result_fails():
    result = render_qa_preservation(None)  # type: ignore[arg-type]
    assert result.score == 0
    assert "qa_result:not_a_dict" in result.missing
