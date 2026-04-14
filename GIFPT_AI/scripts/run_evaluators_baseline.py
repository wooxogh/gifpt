"""Run the 4 edge-preservation evaluators against the LangSmith goldset.

Usage (from GIFPT_AI/):
    # Offline smoke test — no LangSmith, no LLM calls, fixture inputs only
    python -m scripts.run_evaluators_baseline --offline

    # Dry run: resolve the dataset but skip the LLM pipeline (uses reference_code)
    python -m scripts.run_evaluators_baseline --dry-run

    # Full baseline: runs the v1 pipeline on every example, logs to LangSmith
    python -m scripts.run_evaluators_baseline --experiment-prefix v1_baseline
    python -m scripts.run_evaluators_baseline --limit 2 --no-render

    # Experiment A: condensed pedagogical rules variant
    # NOTE: pass a BASE prefix without the variant suffix — this script
    # auto-appends `_{prompt_variant}` so the example below produces
    # `v1_exp_a_condensed`, not `v1_exp_a_condensed_condensed`.
    python -m scripts.run_evaluators_baseline \
        --prompt-variant condensed \
        --experiment-prefix v1_exp_a

Flags:
    --dataset, -d       LangSmith dataset name (default: gifpt-goldset-v0)
    --experiment-prefix Base experiment label attached to the run. The prompt
                        variant is appended automatically (e.g. `v1_baseline`
                        with variant `full` → `v1_baseline_full`). Pass a base
                        prefix WITHOUT the variant suffix.
    --limit N           Only run the first N examples (cheap smoke runs)
    --no-render         Skip Manim render + QA (measures 2 LLM edges only)
    --dry-run           Use the goldset's reference_code instead of calling LLM
    --offline           Run 1 synthetic fixture case without touching LangSmith
    --prompt-variant    `full` (default) or `condensed`. Sets GIFPT_PROMPT_VARIANT
                        before the pipeline runs so codegen picks up the matching
                        PEDAGOGICAL_RULES block. Experiment A compares the two.

The 4 evaluators (pseudo_anim, anim_codegen, codegen_render, render_qa) are
registered as LangSmith feedback producers, giving the "16 case × 4 evaluator"
matrix that Week 2 DoW calls for.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve()
_GIFPT_AI = _HERE.parents[1]
if str(_GIFPT_AI) not in sys.path:
    sys.path.insert(0, str(_GIFPT_AI))

# Load GIFPT_AI/.env so OPENAI_API_KEY / LANGSMITH_API_KEY are available
# when this script runs from the shell, matching how llm_codegen.py reads
# its OpenAI key at import time.
try:
    from dotenv import load_dotenv
    load_dotenv(_GIFPT_AI / ".env")
except ImportError:
    pass


def _run_offline() -> int:
    """Minimal smoke test: run all 4 evaluators on a hand-built fixture capture
    and print the scores. Zero LLM cost, zero LangSmith dependency.

    Stubs optional third-party deps (openai, dotenv, langsmith) so this
    runs in a bare Python environment. If they're already installed,
    setdefault is a no-op and the real modules are used.
    """
    from unittest.mock import MagicMock
    for mod in ("openai", "dotenv", "langsmith"):
        sys.modules.setdefault(mod, MagicMock())

    from studio.evaluators.langsmith_adapter import (
        anim_codegen_evaluator,
        codegen_render_evaluator,
        intent_preservation_evaluator,
        pseudo_anim_evaluator,
        render_qa_evaluator,
    )

    class FakeRun:
        def __init__(self, outputs: dict):
            self.outputs = outputs

    fixture_capture = {
        "intent": {
            "entities": ["array", "pointer"],
            "operations": ["swap array elements"],
        },
        "intent_loss": {
            "pseudo_ir": {
                "stage": "pseudo_ir",
                "lost_entities": [],
                "lost_operations": [],
                "preserved_entities": 2,
                "preserved_operations": 1,
                "preservation_rate": 1.0,
            },
            "anim_ir": {
                "stage": "anim_ir",
                "lost_entities": [],
                "lost_operations": [],
                "preserved_entities": 2,
                "preserved_operations": 1,
                "preservation_rate": 1.0,
            },
            "codegen": {
                "stage": "codegen",
                "lost_entities": [],
                "lost_operations": [],
                "preserved_entities": 2,
                "preserved_operations": 1,
                "preservation_rate": 1.0,
            },
        },
        "stage_errors": {},
        "pseudo_ir": {
            "metadata": {"title": "Bubble Sort"},
            "entities": [
                {"id": "array", "type": "array"},
                {"id": "pointer", "type": "pointer"},
            ],
            "operations": [
                {"step": 1, "subject": "array", "action": "create"},
                {"step": 2, "subject": "pointer", "action": "move", "target": "array"},
                {"step": 3, "subject": "array", "action": "swap"},
            ],
        },
        "anim_ir": {
            "metadata": {"domain": "sorting", "title": "Bubble Sort"},
            "layout": [
                {"id": "array", "shape": "array", "position": [0, 0]},
                {"id": "pointer", "shape": "Arrow", "position": [0, -1]},
            ],
            "actions": [
                {"step": 1, "target": "array", "animation": "fade_in"},
                {"step": 2, "target": "pointer", "animation": "move"},
                {"step": 3, "target": "array", "animation": "swap"},
            ],
        },
        "manim_code": (
            "from manim import *\n\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        array = Text('array')\n"
            "        pointer = Text('pointer')\n"
            "        self.play(FadeIn(array), FadeIn(pointer))\n"
            "        self.wait(1)\n"
        ),
        "render_result": {
            "success": True,
            "duration_s": 12.5,
            "error_type": None,
            "video_path": "/tmp/offline_fixture.mp4",
        },
        "qa_result": {
            "score": 7.0,
            "threshold": 5.0,
            "passed": True,
            "domain_checks": {
                "elements_visible": True,
                "comparison_shown": True,
                "sorted_progression": True,
                "state_highlighting": True,
            },
            "issues": [],
        },
    }

    run = FakeRun(fixture_capture)
    feedbacks = [
        pseudo_anim_evaluator(run),
        anim_codegen_evaluator(run),
        codegen_render_evaluator(run),
        render_qa_evaluator(run),
        intent_preservation_evaluator(run),
    ]
    print("Offline evaluator smoke test — 1 fixture case × 5 evaluators:\n")
    for fb in feedbacks:
        verdict = "PASS" if fb["score"] == 1.0 else "FAIL"
        print(f"  [{verdict}] {fb['key']:<30s} {fb['comment']}")
    print("\nAll 5 evaluators wired correctly." if all(f["score"] == 1.0 for f in feedbacks)
          else "\nAt least one evaluator flagged an issue — inspect feedback above.")
    return 0


def _run_dry(dataset_name: str, limit: int | None) -> int:
    """Resolve dataset via LangSmith but skip the LLM pipeline.

    Synthesizes a capture dict from each example's `reference_code`
    so the evaluators receive plausible (stub) inputs and LangSmith
    never sees a real pipeline run.
    """
    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY not set. Use --offline for zero-dependency smoke test.", file=sys.stderr)
        return 1

    try:
        from langsmith import Client
    except ImportError:
        print("langsmith not installed. pip install -r requirements.txt", file=sys.stderr)
        return 1

    client = Client()
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    if not datasets:
        print(f"Dataset '{dataset_name}' not found. Run upload_goldset.py first.", file=sys.stderr)
        return 1
    dataset = datasets[0]
    print(f"Dataset: {dataset.name} (id={dataset.id})")

    examples = list(client.list_examples(dataset_id=dataset.id))
    if limit:
        examples = examples[:limit]
    print(f"Evaluating {len(examples)} examples (dry-run, no pipeline execution)\n")

    from studio.evaluators.langsmith_adapter import (
        anim_codegen_evaluator,
        codegen_render_evaluator,
        pseudo_anim_evaluator,
        render_qa_evaluator,
    )

    class StubRun:
        def __init__(self, outputs: dict):
            self.outputs = outputs

    totals = {"pseudo_anim": 0, "anim_codegen": 0, "codegen_render": 0, "render_qa": 0}
    for ex in examples:
        tag = (ex.metadata or {}).get("tag", "?")
        ref_code = (ex.outputs or {}).get("reference_code", "") if ex.outputs else ""
        stub = {
            "pseudo_ir": {
                "metadata": {"title": tag},
                "entities": [{"id": "entity_stub", "type": "placeholder"}],
                "operations": [
                    {"step": 1, "subject": "entity_stub", "action": "create"},
                    {"step": 2, "subject": "entity_stub", "action": "update"},
                ],
            },
            "anim_ir": {
                "metadata": {"domain": (ex.metadata or {}).get("domain", "")},
                "layout": [{"id": "entity_stub", "shape": "Circle", "position": [0, 0]}],
                "actions": [
                    {"step": 1, "target": "entity_stub", "animation": "fade_in"},
                    {"step": 2, "target": "entity_stub", "animation": "move"},
                ],
            },
            "manim_code": ref_code,
            "render_result": {
                "success": True,
                "duration_s": 0.0,
                "error_type": None,
                "video_path": f"/dry-run/{tag}.mp4",
            },
            "qa_result": {
                "score": 6.0,
                "threshold": 5.0,
                "passed": True,
                "domain_checks": {},
                "issues": [],
            },
        }
        run = StubRun(stub)
        results = {
            "pseudo_anim": pseudo_anim_evaluator(run),
            "anim_codegen": anim_codegen_evaluator(run),
            "codegen_render": codegen_render_evaluator(run),
            "render_qa": render_qa_evaluator(run),
        }
        row_scores = {k: int(v["score"]) for k, v in results.items()}
        for k, v in row_scores.items():
            totals[k] += v
        print(f"  {tag:<30s} " + "  ".join(f"{k}={row_scores[k]}" for k in totals))

    print("\nTotals (dry-run, reference_code as stub):")
    for k in totals:
        print(f"  {k:<20s} {totals[k]}/{len(examples)}")
    print("\nDry run complete. Use without --dry-run to execute the real pipeline.")
    return 0


def _run_live(
    dataset_name: str,
    experiment_prefix: str,
    limit: int | None,
    render: bool,
    run_qa: bool,
) -> int:
    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY not set. Export it before running live.", file=sys.stderr)
        return 1
    try:
        from langsmith import Client
        from langsmith.evaluation import evaluate
    except ImportError:
        print("langsmith not installed. pip install -r requirements.txt", file=sys.stderr)
        return 1

    from studio.evaluators.langsmith_adapter import ALL_EVALUATORS, build_target_fn

    client = Client()
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    if not datasets:
        print(f"Dataset '{dataset_name}' not found.", file=sys.stderr)
        return 1

    target = build_target_fn(render=render, run_qa=run_qa)

    print(f"Running {experiment_prefix} against '{dataset_name}'"
          + (f" (limit={limit})" if limit else "")
          + f" [render={render}, qa={run_qa}]")

    # When `limit` is set, fetch examples explicitly and pass the sliced
    # list as `data`. The `max_examples` kwarg on `evaluate()` is not
    # supported on every LangSmith SDK version and raises ValueError on
    # newer ones, so we avoid it entirely.
    if limit:
        datasets = list(client.list_datasets(dataset_name=dataset_name))
        if not datasets:
            print(f"Dataset '{dataset_name}' not found.", file=sys.stderr)
            return 1
        examples = list(client.list_examples(dataset_id=datasets[0].id))[:limit]
        data_arg: Any = examples
        print(f"Sliced dataset to first {len(examples)} example(s)")
    else:
        data_arg = dataset_name

    eval_kwargs: dict = {
        "data": data_arg,
        "evaluators": list(ALL_EVALUATORS),
        "experiment_prefix": experiment_prefix,
    }

    results = evaluate(target, **eval_kwargs)

    print("\nLangSmith evaluation run submitted.")
    try:
        url = getattr(results, "url", None) or getattr(results, "experiment_url", None)
        if url:
            print(f"View results: {url}")
    except Exception:
        pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", "-d", default="gifpt-goldset-v0")
    parser.add_argument("--experiment-prefix", default="v1_baseline")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-render", action="store_true", help="Skip Manim render + QA")
    parser.add_argument("--no-qa", action="store_true", help="Skip Vision QA step")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM pipeline, stub capture from reference_code")
    parser.add_argument("--offline", action="store_true", help="Run 1 synthetic fixture; zero deps")
    parser.add_argument(
        "--prompt-variant",
        choices=("full", "condensed"),
        default="full",
        help="PEDAGOGICAL_RULES variant for codegen system prompt (Experiment A)",
    )
    args = parser.parse_args()

    if args.offline:
        return _run_offline()

    if args.dry_run:
        return _run_dry(args.dataset, args.limit)

    # Propagate the prompt variant to the codegen module and tag the
    # experiment so FULL vs CONDENSED runs are distinguishable in the
    # LangSmith UI. Set BEFORE calling _run_live so the env var is in
    # place when the codegen module resolves it at call time.
    os.environ["GIFPT_PROMPT_VARIANT"] = args.prompt_variant
    experiment_prefix = f"{args.experiment_prefix}_{args.prompt_variant}"
    print(f"GIFPT_PROMPT_VARIANT={args.prompt_variant} -> experiment_prefix={experiment_prefix}")

    return _run_live(
        args.dataset,
        experiment_prefix,
        args.limit,
        render=not args.no_render,
        run_qa=not (args.no_qa or args.no_render),
    )


if __name__ == "__main__":
    raise SystemExit(main())
