"""Tests for domain-aware Vision QA scoring.

Run from GIFPT_AI/: python3 -m pytest studio/tests/test_domain_qa.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Mock external packages before importing qa
sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

from studio.ai.qa import (  # noqa: E402
    compute_domain_adjusted_score,
    _build_domain_checks_prompt,
    DOMAIN_QA_CONFIG,
    DEFAULT_WEIGHTS,
)


# ── compute_domain_adjusted_score ────────────────────────────────────────────


class TestComputeScoreNoDomain:
    """When no domain is provided, uses default weights with no penalties."""

    def test_uniform_scores(self):
        base = {"correctness": 8, "clarity": 8, "completeness": 8, "readability": 8}
        score, penalties = compute_domain_adjusted_score(base, {}, None)
        assert score == 8.0
        assert penalties == []

    def test_varied_scores_weighted(self):
        base = {"correctness": 10, "clarity": 6, "completeness": 6, "readability": 4}
        score, penalties = compute_domain_adjusted_score(base, {}, None)
        # Expected: 10*0.35 + 6*0.25 + 6*0.25 + 4*0.15 = 3.5 + 1.5 + 1.5 + 0.6 = 7.1
        assert score == 7.1
        assert penalties == []

    def test_missing_criterion_defaults_to_5(self):
        base = {"correctness": 10}
        score, _ = compute_domain_adjusted_score(base, {}, None)
        # correctness=10, others=5.0 (default)
        # 10*0.35 + 5*0.25 + 5*0.25 + 5*0.15 = 3.5 + 1.25 + 1.25 + 0.75 = 6.75 → 6.8
        assert score == 6.8

    def test_clamping_scores(self):
        base = {"correctness": 15, "clarity": -2, "completeness": 5, "readability": 5}
        score, _ = compute_domain_adjusted_score(base, {}, None)
        # 10*0.35 + 1*0.25 + 5*0.25 + 5*0.15 = 3.5 + 0.25 + 1.25 + 0.75 = 5.75 → 5.8
        assert score == 5.8


class TestComputeScoreWithDomain:
    """Domain-specific weights and penalties."""

    def test_sorting_all_checks_pass(self):
        base = {"correctness": 7, "clarity": 7, "completeness": 7, "readability": 7}
        checks = {
            "elements_visible": True,
            "comparison_shown": True,
            "sorted_progression": True,
            "state_highlighting": True,
        }
        score, penalties = compute_domain_adjusted_score(base, checks, "sorting")
        assert score == 7.0
        assert penalties == []

    def test_sorting_critical_check_fails(self):
        base = {"correctness": 8, "clarity": 8, "completeness": 8, "readability": 8}
        checks = {
            "elements_visible": True,
            "comparison_shown": False,  # penalty 2.5
            "sorted_progression": True,
            "state_highlighting": True,
        }
        score, penalties = compute_domain_adjusted_score(base, checks, "sorting")
        assert score == 5.5  # 8.0 - 2.5
        assert len(penalties) == 1
        assert "comparison" in penalties[0].lower() or "FAILED" in penalties[0]

    def test_sorting_multiple_checks_fail(self):
        base = {"correctness": 7, "clarity": 7, "completeness": 7, "readability": 7}
        checks = {
            "elements_visible": False,  # penalty 2.0
            "comparison_shown": False,  # penalty 2.5
            "sorted_progression": True,
            "state_highlighting": False,  # penalty 1.0
        }
        score, penalties = compute_domain_adjusted_score(base, checks, "sorting")
        # 7.0 - 2.0 - 2.5 - 1.0 = 1.5
        assert score == 1.5
        assert len(penalties) == 3

    def test_score_floor_at_zero(self):
        """Score cannot go below 0."""
        base = {"correctness": 3, "clarity": 3, "completeness": 3, "readability": 3}
        checks = {
            "elements_visible": False,
            "comparison_shown": False,
            "sorted_progression": False,
            "state_highlighting": False,
        }
        score, _ = compute_domain_adjusted_score(base, checks, "sorting")
        assert score == 0.0

    def test_graph_domain_weights(self):
        base = {"correctness": 10, "clarity": 4, "completeness": 4, "readability": 4}
        checks = {"nodes_visible": True, "edges_drawn": True, "traversal_order": True, "frontier_shown": True}
        score, _ = compute_domain_adjusted_score(base, checks, "graph_traversal")
        # graph weights: correctness=0.35, clarity=0.25, completeness=0.25, readability=0.15
        # 10*0.35 + 4*0.25 + 4*0.25 + 4*0.15 = 3.5+1.0+1.0+0.6 = 6.1
        assert score == 6.1

    def test_unknown_domain_uses_defaults(self):
        base = {"correctness": 8, "clarity": 8, "completeness": 8, "readability": 8}
        score, penalties = compute_domain_adjusted_score(base, {}, "unknown_domain")
        assert score == 8.0
        assert penalties == []

    def test_missing_check_defaults_to_pass(self):
        """If a check key is missing from domain_checks, assume pass (don't penalize)."""
        base = {"correctness": 7, "clarity": 7, "completeness": 7, "readability": 7}
        checks = {"elements_visible": True}  # other keys missing
        score, penalties = compute_domain_adjusted_score(base, checks, "sorting")
        assert score == 7.0
        assert penalties == []


class TestComputeScoreAllDomains:
    """Ensure every configured domain works without errors."""

    def test_all_domains_pass_with_good_scores(self):
        base = {"correctness": 8, "clarity": 8, "completeness": 8, "readability": 8}
        for domain, config in DOMAIN_QA_CONFIG.items():
            checks = {c["key"]: True for c in config["required_checks"]}
            score, penalties = compute_domain_adjusted_score(base, checks, domain)
            assert score > 0, f"Domain {domain} scored 0 with all checks passing"
            assert penalties == [], f"Domain {domain} had penalties with all checks passing"


# ── _build_domain_checks_prompt ──────────────────────────────────────────────


class TestBuildDomainChecksPrompt:
    def test_known_domain(self):
        prompt = _build_domain_checks_prompt("sorting")
        assert "SORTING" in prompt
        assert "elements_visible" in prompt
        assert "comparison_shown" in prompt

    def test_unknown_domain_returns_empty(self):
        assert _build_domain_checks_prompt("nonexistent") == ""

    def test_all_domains_have_prompts(self):
        for domain in DOMAIN_QA_CONFIG:
            prompt = _build_domain_checks_prompt(domain)
            assert len(prompt) > 0, f"Domain {domain} has empty prompt"
            # Every check key should appear in the prompt
            for chk in DOMAIN_QA_CONFIG[domain]["required_checks"]:
                assert chk["key"] in prompt, f"Check {chk['key']} missing from {domain} prompt"
