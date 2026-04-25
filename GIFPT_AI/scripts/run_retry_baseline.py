"""run_retry_baseline.py — drive a controlled batch through the self-healing
pipeline to produce Before/After trace data for the LangGraph refactor.

Each prompt is fed to `render_video_from_instructions`, which is the hand-rolled
state machine we plan to replace. With `GIFPT_DUMP_TRACES=1` (set automatically
by this script), every job writes a JSON trace to RESULT_DIR/traces/, capturing
per-attempt retry counts, error types, and QA scores.

After the batch finishes, `analyze_traces.summarize_job + render_markdown` is
invoked programmatically to produce a markdown report you can paste into the
blog as the v1 baseline.

Usage:
    # Built-in 15-prompt set (11 domains from v1 baseline)
    python -m scripts.run_retry_baseline

    # Custom prompt file (one prompt per line, blank lines skipped)
    python -m scripts.run_retry_baseline --prompts-file my_prompts.txt

    # Smoke test (no LLM, no render — just validate prompt loading + setup)
    python -m scripts.run_retry_baseline --dry-run

    # Subset for a cheap pilot run
    python -m scripts.run_retry_baseline --limit 3 --label "v1 pilot (n=3)"

Prerequisites for a real run:
    - OPENAI_API_KEY exported (used by codegen + vision_qa)
    - manim + ffmpeg available (for actual rendering)
    - GIFPT_RESULT_DIR writable (default /tmp/gifpt_results)
    - Estimated cost: ~$0.10–$0.30 per prompt
    - Estimated time: ~1–3 minutes per prompt (render-bound)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

GIFPT_AI_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GIFPT_AI_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GIFPT_AI.settings")

REPORTS_DIR = GIFPT_AI_ROOT / "reports"


# 15 prompts covering the 11 domains observed in docs/v1-baseline-report.md.
# Each is concise (matches real user input length) and asks for a 20–30s scene.
DEFAULT_PROMPTS: list[tuple[str, str]] = [
    ("sorting/bubble",
     "Visualize bubble sort on the array [5,3,8,1,4]. Show every comparison and swap step by step."),
    ("sorting/quick",
     "Visualize quicksort on [7,2,1,8,6,3,5,4]. Highlight the pivot and show partitioning."),
    ("sorting/merge",
     "Visualize merge sort on [38,27,43,3,9,82,10]. Show the divide and merge phases clearly."),
    ("graph/bfs",
     "Visualize BFS traversal on a graph with 6 nodes. Highlight the queue and visited set at each step."),
    ("graph/dfs",
     "Visualize DFS traversal on a small tree. Show the call stack and pre-order visit order."),
    ("graph/dijkstra",
     "Visualize Dijkstra's shortest path algorithm on a 5-node weighted graph. Show distance updates."),
    ("transformer/self_attention",
     "Visualize one layer of self-attention on 3 input tokens. Show Q, K, V matrices and softmax output."),
    ("cnn/convolution",
     "Visualize a 3x3 convolution sliding over a 5x5 input image. Show the dot product at each position."),
    ("cache/lru",
     "Visualize an LRU cache with capacity 3 receiving the access sequence A, B, C, A, D, B."),
    ("hash_table/insert",
     "Visualize hash table insertion with linear probing on a table of size 7. Insert keys 12, 25, 19, 5."),
    ("dp/fibonacci",
     "Visualize bottom-up dynamic programming computing fibonacci(7). Show the dp table filling in."),
    ("tree/inorder",
     "Visualize in-order traversal of a binary search tree with 7 nodes. Highlight each node as visited."),
    ("linked_list/reverse",
     "Visualize reversing a singly linked list with 5 nodes. Show pointer reassignments step by step."),
    ("stack/parentheses",
     "Visualize using a stack to check balanced parentheses in the string '(()(()))'. Show push/pop."),
    ("math/sieve",
     "Visualize the Sieve of Eratosthenes finding primes up to 30. Show numbers being crossed out."),
]


def load_prompts(path: Path | None, limit: int | None) -> list[tuple[str, str]]:
    if path is None:
        prompts = list(DEFAULT_PROMPTS)
    else:
        prompts = []
        for i, line in enumerate(path.read_text().splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            prompts.append((f"line_{i}", line))
        if not prompts:
            sys.stderr.write(f"[run_retry_baseline] no prompts loaded from {path}\n")
            sys.exit(2)
    if limit is not None:
        prompts = prompts[:limit]
    return prompts


def run_one(tag: str, prompt: str) -> dict:
    """Run a single prompt through the self-healing pipeline.

    Returns a small status dict for the per-prompt log line. The full per-attempt
    detail lands in RESULT_DIR/traces/{job_id}.json via the trace dump in
    render_video_from_instructions itself.
    """
    started = time.monotonic()
    try:
        from studio.video_render import render_video_from_instructions
    except Exception as e:
        return {"tag": tag, "status": "import_failed", "error": str(e), "seconds": 0}

    try:
        video_path = render_video_from_instructions(prompt)
        return {
            "tag": tag,
            "status": "ok",
            "video_path": video_path,
            "seconds": round(time.monotonic() - started, 1),
        }
    except Exception as e:
        return {
            "tag": tag,
            "status": "exception",
            "error": f"{type(e).__name__}: {str(e)[:200]}",
            "seconds": round(time.monotonic() - started, 1),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts-file", type=Path, default=None,
                        help="One prompt per line. Blank lines and # comments skipped.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only run the first N prompts.")
    parser.add_argument("--dry-run", action="store_true",
                        help="List prompts and exit. No LLM calls, no render.")
    parser.add_argument("--label", default=None,
                        help="Label for the analyze_traces report (default auto from N + timestamp).")
    parser.add_argument("--report-out", type=Path, default=None,
                        help="Markdown report path (default: reports/retry_baseline_{ts}.md).")
    parser.add_argument("--no-report", action="store_true",
                        help="Skip the analyze_traces report at the end.")
    args = parser.parse_args()

    prompts = load_prompts(args.prompts_file, args.limit)

    if args.dry_run:
        print(f"[dry-run] would run {len(prompts)} prompt(s):")
        for tag, prompt in prompts:
            preview = (prompt[:80] + "…") if len(prompt) > 80 else prompt
            print(f"  - [{tag}] {preview}")
        print("\nNo LLM calls or renders performed. Re-run without --dry-run to execute.")
        return 0

    # Activate trace dump for the patched render_video_from_instructions
    os.environ["GIFPT_DUMP_TRACES"] = "1"
    result_dir = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))
    traces_dir = result_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    print(f"[run_retry_baseline] N={len(prompts)} traces -> {traces_dir}")
    print(f"[run_retry_baseline] estimated: ~{len(prompts) * 0.2:.1f} USD, ~{len(prompts) * 2}min")

    started_at = time.monotonic()
    results = []
    for i, (tag, prompt) in enumerate(prompts, start=1):
        print(f"[run_retry_baseline] {i}/{len(prompts)} {tag} ...", flush=True)
        try:
            r = run_one(tag, prompt)
        except KeyboardInterrupt:
            print("\n[run_retry_baseline] interrupted — partial traces preserved", file=sys.stderr)
            break
        except Exception:
            traceback.print_exc()
            r = {"tag": tag, "status": "driver_exception", "seconds": 0}
        print(f"[run_retry_baseline]   -> {r['status']} ({r['seconds']}s)")
        results.append(r)

    elapsed = time.monotonic() - started_at
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n[run_retry_baseline] done in {elapsed:.1f}s — {ok}/{len(results)} OK")

    if args.no_report:
        return 0

    # Auto-generate analyze report on the freshly dumped traces
    from scripts.analyze_traces import load_traces, summarize_job, render_markdown

    traces = load_traces(traces_dir)
    summaries = [summarize_job(t) for t in traces]
    label = args.label or f"v1 baseline (n={len(summaries)}, batch run)"
    md = render_markdown(summaries, label)

    if args.report_out is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        args.report_out = REPORTS_DIR / f"retry_baseline_{ts}.md"

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(md, encoding="utf-8")
    print(f"[run_retry_baseline] report -> {args.report_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
