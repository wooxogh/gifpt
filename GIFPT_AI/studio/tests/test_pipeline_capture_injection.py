"""Week 5 D1 — tests for the `GIFPT_INTENT_INJECT` env flag resolver.

Only covers the parser (`_resolve_injection_stages`). The full
`run_pipeline_capture` orchestration is tested indirectly by the
live LangSmith run; mocking every LLM stage here would reinvent
pipeline_capture for the test.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

for mod in ("openai", "dotenv"):
    sys.modules.setdefault(mod, MagicMock())

from studio.evaluators.pipeline_capture import _resolve_injection_stages  # noqa: E402


def _with_env(value: str | None):
    """Context-manager-ish: set/clear env var for a single assertion."""
    prev = os.environ.get("GIFPT_INTENT_INJECT")
    if value is None:
        os.environ.pop("GIFPT_INTENT_INJECT", None)
    else:
        os.environ["GIFPT_INTENT_INJECT"] = value
    return prev


def _restore(prev: str | None):
    if prev is None:
        os.environ.pop("GIFPT_INTENT_INJECT", None)
    else:
        os.environ["GIFPT_INTENT_INJECT"] = prev


def test_unset_returns_empty_set():
    prev = _with_env(None)
    try:
        assert _resolve_injection_stages() == frozenset()
    finally:
        _restore(prev)


def test_off_returns_empty_set():
    prev = _with_env("off")
    try:
        assert _resolve_injection_stages() == frozenset()
    finally:
        _restore(prev)


def test_none_literal_returns_empty_set():
    prev = _with_env("none")
    try:
        assert _resolve_injection_stages() == frozenset()
    finally:
        _restore(prev)


def test_pseudo_ir_only():
    prev = _with_env("pseudo_ir")
    try:
        assert _resolve_injection_stages() == frozenset({"pseudo_ir"})
    finally:
        _restore(prev)


def test_all_literal_expands_to_three_stages():
    prev = _with_env("all")
    try:
        assert _resolve_injection_stages() == frozenset(
            {"pseudo_ir", "anim_ir", "codegen"}
        )
    finally:
        _restore(prev)


def test_comma_separated_multi_stage():
    prev = _with_env("pseudo_ir,anim_ir")
    try:
        assert _resolve_injection_stages() == frozenset({"pseudo_ir", "anim_ir"})
    finally:
        _restore(prev)


def test_unknown_tokens_dropped_silently():
    """A typo must not silently enable an unintended stage — unknown
    tokens drop, known tokens survive."""
    prev = _with_env("pseudo_ir,typo,codegen")
    try:
        assert _resolve_injection_stages() == frozenset({"pseudo_ir", "codegen"})
    finally:
        _restore(prev)


def test_whitespace_and_case_tolerant():
    prev = _with_env("  Pseudo_IR , codegen ")
    try:
        assert _resolve_injection_stages() == frozenset({"pseudo_ir", "codegen"})
    finally:
        _restore(prev)
