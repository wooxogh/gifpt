"""analyze_traces.py — summarize per-job retry distribution from render traces.

Reads JSON traces written by `render_video_from_instructions` when
`GIFPT_DUMP_TRACES=1` is set, and emits a markdown report you can paste into
the LangGraph refactor blog post as the **Before** baseline.

Usage:
    # Dump traces during your batch run (one-time):
    export GIFPT_DUMP_TRACES=1
    # ... run whatever batch hits render_video_from_instructions ...

    # Analyze:
    python -m scripts.analyze_traces
    python -m scripts.analyze_traces --traces-dir /tmp/gifpt_results/traces
    python -m scripts.analyze_traces --label "v1 baseline (n=23)" --out reports/retry_baseline.md

What it computes per job:
  - pipeline_attempts_used (1 or 2)
  - codegen attempts across all pipeline attempts (sum)
  - render-failed codegen attempts (sum)
  - total LLM calls (rough: pseudo + anim + codegen across pipelines)
  - final outcome (success / best_effort_returned / loop_exhausted / exception)
  - QA score on final attempt

What it computes across the corpus:
  - distribution histograms (codegen_attempts, total_llm_calls, pipeline_attempts)
  - mean / median / p90 / max
  - error_type frequency table
  - outcome breakdown
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_TRACES_DIR = Path(
    os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results")
) / "traces"


def load_traces(traces_dir: Path) -> list[dict[str, Any]]:
    if not traces_dir.exists():
        sys.stderr.write(f"[analyze_traces] no traces dir: {traces_dir}\n")
        sys.stderr.write("  Did you set GIFPT_DUMP_TRACES=1 and run a batch?\n")
        return []
    traces: list[dict[str, Any]] = []
    for p in sorted(traces_dir.glob("*.json")):
        try:
            traces.append(json.loads(p.read_text()))
        except Exception as e:
            sys.stderr.write(f"[analyze_traces] skipping {p.name}: {e}\n")
    return traces


def summarize_job(trace: dict[str, Any]) -> dict[str, Any]:
    attempts = trace.get("pipeline_attempts", []) or []
    cg_total = 0
    cg_render_failed = 0
    llm_calls = 0
    error_types: list[str] = []
    qa_score_final = None
    qa_passed_final = None

    for ap in attempts:
        llm_calls += int(ap.get("pseudo_ir_tries", 0))
        llm_calls += int(ap.get("anim_ir_tries", 0))
        cg_attempts = ap.get("codegen_attempts", []) or []
        cg_total += len(cg_attempts)
        llm_calls += len(cg_attempts)
        for cg in cg_attempts:
            if cg.get("outcome") == "render_failed":
                cg_render_failed += 1
                if cg.get("error_type"):
                    error_types.append(cg["error_type"])
        qa_score_final = ap.get("qa_score", qa_score_final)
        qa_passed_final = ap.get("qa_passed", qa_passed_final)

    return {
        "job_id": trace.get("job_id"),
        "pipeline_attempts_used": len(attempts),
        "codegen_attempts_total": cg_total,
        "codegen_render_failed": cg_render_failed,
        "total_llm_calls_rough": llm_calls,
        "final_outcome": trace.get("final_outcome", "unknown"),
        "qa_score_final": qa_score_final,
        "qa_passed_final": qa_passed_final,
        "error_types": error_types,
    }


def histogram(values: list[int]) -> str:
    if not values:
        return "_(no data)_"
    counter = collections.Counter(values)
    max_count = max(counter.values())
    lines = []
    for k in sorted(counter):
        bar = "█" * max(1, round(counter[k] / max_count * 30))
        lines.append(f"  {k}: {bar} ({counter[k]})")
    return "\n".join(lines)


def stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "p90": 0.0, "max": 0.0, "min": 0.0}
    s = sorted(values)
    p90_idx = max(0, min(len(s) - 1, int(round(len(s) * 0.9)) - 1))
    return {
        "mean": round(statistics.fmean(values), 2),
        "median": statistics.median(values),
        "p90": s[p90_idx],
        "max": max(values),
        "min": min(values),
    }


def render_markdown(summaries: list[dict[str, Any]], label: str) -> str:
    n = len(summaries)
    if n == 0:
        return f"# Render Trace Report — {label}\n\n_No traces found._\n"

    cg_attempts = [s["codegen_attempts_total"] for s in summaries]
    cg_failed = [s["codegen_render_failed"] for s in summaries]
    llm_calls = [s["total_llm_calls_rough"] for s in summaries]
    pipeline_attempts = [s["pipeline_attempts_used"] for s in summaries]

    outcomes = collections.Counter(s["final_outcome"] for s in summaries)
    error_types = collections.Counter()
    for s in summaries:
        error_types.update(s["error_types"])

    qa_scores = [s["qa_score_final"] for s in summaries if isinstance(s.get("qa_score_final"), (int, float))]
    qa_passed = sum(1 for s in summaries if s.get("qa_passed_final"))

    lines: list[str] = []
    lines.append(f"# Render Trace Report — {label}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}  ")
    lines.append(f"**Jobs analyzed:** {n}")
    lines.append("")

    lines.append("## TL;DR (블로그용 한 줄)")
    lines.append("")
    cg_s = stats(cg_attempts)
    llm_s = stats(llm_calls)
    pipe_s = stats(pipeline_attempts)
    lines.append(
        f"- 잡당 평균 codegen 시도 **{cg_s['mean']}회** (max {int(cg_s['max'])}), "
        f"평균 LLM 호출 **{llm_s['mean']}회** (max {int(llm_s['max'])}), "
        f"파이프라인 재시도 비율 **{sum(1 for v in pipeline_attempts if v >= 2) / n * 100:.0f}%**"
    )
    lines.append(f"- QA 통과율 **{qa_passed}/{n} ({qa_passed / n * 100:.1f}%)**, 평균 QA 점수 **{(statistics.fmean(qa_scores) if qa_scores else 0):.2f}**")
    lines.append("")

    lines.append("## 1. 분포 요약")
    lines.append("")
    lines.append("| 지표 | mean | median | p90 | max | min |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for name, s in [
        ("Codegen attempts / job", cg_s),
        ("Codegen render-failed / job", stats(cg_failed)),
        ("Total LLM calls / job", llm_s),
        ("Pipeline attempts / job", pipe_s),
    ]:
        lines.append(f"| {name} | {s['mean']} | {s['median']} | {s['p90']} | {int(s['max'])} | {int(s['min'])} |")
    lines.append("")

    lines.append("## 2. Histograms")
    lines.append("")
    lines.append("**Codegen attempts per job**")
    lines.append("```")
    lines.append(histogram(cg_attempts))
    lines.append("```")
    lines.append("")
    lines.append("**Total LLM calls per job (rough)**")
    lines.append("```")
    lines.append(histogram(llm_calls))
    lines.append("```")
    lines.append("")
    lines.append("**Pipeline attempts per job**")
    lines.append("```")
    lines.append(histogram(pipeline_attempts))
    lines.append("```")
    lines.append("")

    lines.append("## 3. Final outcomes")
    lines.append("")
    lines.append("| outcome | count | % |")
    lines.append("|---|---:|---:|")
    for outcome, count in outcomes.most_common():
        lines.append(f"| `{outcome}` | {count} | {count / n * 100:.1f}% |")
    lines.append("")

    if error_types:
        lines.append("## 4. Render error types (across all attempts)")
        lines.append("")
        lines.append("| error_type | occurrences |")
        lines.append("|---|---:|")
        for et, count in error_types.most_common():
            lines.append(f"| `{et}` | {count} |")
        lines.append("")

    lines.append("## 5. Per-job (sorted by codegen attempts desc)")
    lines.append("")
    lines.append("| job_id | pipeline | codegen | render_failed | llm_calls | qa_score | outcome |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for s in sorted(summaries, key=lambda x: x["codegen_attempts_total"], reverse=True):
        qa = f"{s['qa_score_final']:.1f}" if isinstance(s.get("qa_score_final"), (int, float)) else "—"
        lines.append(
            f"| `{s['job_id']}` | {s['pipeline_attempts_used']} | "
            f"{s['codegen_attempts_total']} | {s['codegen_render_failed']} | "
            f"{s['total_llm_calls_rough']} | {qa} | `{s['final_outcome']}` |"
        )
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces-dir", default=str(DEFAULT_TRACES_DIR),
                        help=f"Directory of trace JSONs (default: {DEFAULT_TRACES_DIR})")
    parser.add_argument("--label", default="v1 baseline",
                        help="Label printed in the report header (e.g. 'v1 baseline (n=23)')")
    parser.add_argument("--out", default=None,
                        help="Write markdown to this path (default: stdout)")
    parser.add_argument("--json", action="store_true",
                        help="Emit per-job JSON summary instead of markdown")
    args = parser.parse_args()

    traces = load_traces(Path(args.traces_dir))
    summaries = [summarize_job(t) for t in traces]

    if args.json:
        out = json.dumps(summaries, indent=2, default=str)
    else:
        out = render_markdown(summaries, args.label)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"[analyze_traces] wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
