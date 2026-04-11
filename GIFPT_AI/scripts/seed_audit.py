"""seed_audit.py — re-render every seed example and run vision QA on it.

Catches drift in `seed_examples.jsonl`: an example that no longer renders, or
whose visual quality has dropped, will poison every few-shot prompt that uses it.
This script gives the user one markdown summary they can scan in 1 minute.

Usage:
    python -m scripts.seed_audit                    # full run (slow + costs $)
    python -m scripts.seed_audit --dry-run          # validate JSONL only, no render
    python -m scripts.seed_audit --no-qa            # render, skip vision QA
    python -m scripts.seed_audit --tag bubble_sort  # run a single example

Note:
    - Each render takes ~30–60s (manim) and each QA call hits OpenAI vision (~$0.01-0.05).
    - Full run on 13 examples ≈ 10–15 min, ~$0.50. Run weekly or on-demand.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make `studio` importable from this script.
GIFPT_AI_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GIFPT_AI_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GIFPT_AI.settings")

REPORTS_DIR = GIFPT_AI_ROOT / "reports"
SEED_FILE = GIFPT_AI_ROOT / "studio" / "ai" / "examples" / "seed_examples.jsonl"

QA_THRESHOLD = 5.0


def load_seeds(path: Path) -> list[dict[str, Any]]:
    out = []
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[seed_audit] line {i}: invalid JSON ({e})\n")
    return out


def validate_schema(seed: dict[str, Any]) -> list[str]:
    """Return a list of schema problems for one seed example (empty = ok)."""
    issues: list[str] = []
    required = ["tag", "algorithm", "domain", "description", "code"]
    for k in required:
        v = seed.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            issues.append(f"missing required field '{k}'")
    if "code" in seed and isinstance(seed["code"], str):
        if "from manim import" not in seed["code"]:
            issues.append("code does not import manim")
        if "class AlgorithmScene" not in seed["code"]:
            issues.append("code does not define AlgorithmScene")
    return issues


def run_one(seed: dict[str, Any], do_render: bool, do_qa: bool) -> dict[str, Any]:
    """Render + QA a single seed example. Returns a result dict."""
    result: dict[str, Any] = {
        "tag": seed.get("tag"),
        "domain": seed.get("domain"),
        "schema_issues": validate_schema(seed),
        "render_ok": None,
        "render_duration_s": None,
        "render_error": None,
        "qa_score": None,
        "qa_passed": None,
        "qa_issues": [],
        "qa_summary": None,
    }

    if not do_render:
        return result

    if result["schema_issues"]:
        result["render_ok"] = False
        result["render_error"] = "schema invalid; skipped render"
        return result

    # Lazy imports so --dry-run works without manim/openai installed.
    try:
        from studio.video_render import run_manim_code, ManimRenderError
    except Exception as e:
        result["render_ok"] = False
        result["render_error"] = f"import failed: {e}"
        return result

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"seed_audit_{seed['tag']}_") as tmp:
        try:
            video_path = run_manim_code(seed["code"], Path(tmp), f"{seed['tag']}.mp4")
            result["render_ok"] = True
            result["render_duration_s"] = round(time.monotonic() - started, 1)
        except ManimRenderError as e:
            result["render_ok"] = False
            result["render_duration_s"] = round(time.monotonic() - started, 1)
            result["render_error"] = f"{e.error_type}: {e.stderr_snippet[-300:]}"
            return result
        except Exception as e:
            result["render_ok"] = False
            result["render_duration_s"] = round(time.monotonic() - started, 1)
            result["render_error"] = f"{type(e).__name__}: {e}"
            return result

        if not do_qa:
            return result

        try:
            from studio.ai.qa import vision_qa
            qa = vision_qa(
                video_path=video_path,
                algorithm_description=seed["description"],
                threshold=QA_THRESHOLD,
                domain=seed.get("domain"),
            )
            result["qa_score"] = qa.get("score")
            result["qa_passed"] = qa.get("passed")
            result["qa_issues"] = qa.get("issues", [])
            result["qa_summary"] = qa.get("summary")
        except Exception as e:
            result["qa_passed"] = False
            result["qa_summary"] = f"QA call failed: {type(e).__name__}: {e}"

    return result


def render_markdown(results: list[dict[str, Any]], mode: str) -> str:
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    total = len(results)
    schema_bad = [r for r in results if r["schema_issues"]]
    rendered = [r for r in results if r["render_ok"] is True]
    render_failed = [r for r in results if r["render_ok"] is False]
    qa_run = [r for r in results if r["qa_score"] is not None]
    qa_passed = [r for r in qa_run if r["qa_passed"]]
    qa_failed = [r for r in qa_run if r["qa_passed"] is False]

    lines: list[str] = []
    lines.append(f"# Seed Examples Audit — {today}")
    lines.append("")
    lines.append(f"**Mode:** {mode}  ")
    lines.append(f"**Examples:** {total}  ")
    lines.append(f"**Schema OK:** {total - len(schema_bad)}/{total}  ")
    if mode != "dry-run":
        lines.append(f"**Render OK:** {len(rendered)}/{total}  ")
    if qa_run:
        lines.append(f"**QA pass (≥{QA_THRESHOLD}):** {len(qa_passed)}/{len(qa_run)}")
    lines.append("")

    # Per-example table
    lines.append("## Per example")
    lines.append("")
    lines.append("| Tag | Domain | Schema | Render | QA score | QA pass | Time |")
    lines.append("|---|---|:---:|:---:|---:|:---:|---:|")
    for r in results:
        schema = "OK" if not r["schema_issues"] else f"!{len(r['schema_issues'])}"
        render = {True: "OK", False: "FAIL", None: "—"}[r["render_ok"]]
        qa_score = f"{r['qa_score']:.1f}" if isinstance(r["qa_score"], (int, float)) and r["qa_score"] >= 0 else "—"
        qa_pass = {True: "OK", False: "FAIL", None: "—"}[r["qa_passed"]]
        dur = f"{r['render_duration_s']}s" if r["render_duration_s"] is not None else "—"
        lines.append(f"| `{r['tag']}` | {r['domain']} | {schema} | {render} | {qa_score} | {qa_pass} | {dur} |")
    lines.append("")

    # Failure detail
    problem = [r for r in results if r["schema_issues"] or r["render_ok"] is False or r["qa_passed"] is False]
    if problem:
        lines.append("## Failures detail")
        lines.append("")
        for r in problem:
            lines.append(f"### `{r['tag']}` ({r['domain']})")
            if r["schema_issues"]:
                lines.append("**Schema issues:**")
                for s in r["schema_issues"]:
                    lines.append(f"- {s}")
            if r["render_ok"] is False:
                lines.append(f"**Render failed:** `{r['render_error']}`")
            if r["qa_passed"] is False and r["qa_score"] is not None:
                lines.append(f"**QA score:** {r['qa_score']} (below {QA_THRESHOLD})")
                if r["qa_summary"]:
                    lines.append(f"**Summary:** {r['qa_summary']}")
                if r["qa_issues"]:
                    lines.append("**Issues:**")
                    for issue in r["qa_issues"][:5]:
                        lines.append(f"- {issue}")
            lines.append("")
    else:
        lines.append("## Failures detail")
        lines.append("")
        lines.append("_No failures._")
        lines.append("")

    lines.append("## Action items (fill in during weekly review)")
    lines.append("")
    lines.append("- [ ] ")
    lines.append("- [ ] ")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Schema check only, no render")
    parser.add_argument("--no-qa", action="store_true", help="Render, skip vision QA")
    parser.add_argument("--tag", help="Run a single example by tag")
    parser.add_argument("--seed-file", default=str(SEED_FILE))
    parser.add_argument("--out-dir", default=str(REPORTS_DIR))
    args = parser.parse_args()

    seeds = load_seeds(Path(args.seed_file))
    if args.tag:
        seeds = [s for s in seeds if s.get("tag") == args.tag]
        if not seeds:
            sys.stderr.write(f"[seed_audit] no seed with tag '{args.tag}'\n")
            return 2

    do_render = not args.dry_run
    do_qa = do_render and not args.no_qa
    mode = "dry-run" if args.dry_run else ("render-only" if args.no_qa else "full")

    print(f"[seed_audit] mode={mode}, examples={len(seeds)}")
    results: list[dict[str, Any]] = []
    for i, seed in enumerate(seeds, start=1):
        print(f"[seed_audit] {i}/{len(seeds)} {seed.get('tag')}")
        try:
            results.append(run_one(seed, do_render, do_qa))
        except Exception:
            traceback.print_exc()
            results.append({
                "tag": seed.get("tag"),
                "domain": seed.get("domain"),
                "schema_issues": [],
                "render_ok": False,
                "render_error": "unhandled exception (see stderr)",
                "qa_score": None,
                "qa_passed": None,
                "qa_issues": [],
                "qa_summary": None,
                "render_duration_s": None,
            })

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().astimezone().strftime("%Y-%m-%d")

    json_path = out_dir / f"seed_audit_{today}.json"
    md_path = out_dir / f"seed_audit_{today}.md"

    json_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "results": results,
    }, indent=2, default=str))
    md_path.write_text(render_markdown(results, mode))

    print(f"[seed_audit] wrote {json_path}")
    print(f"[seed_audit] wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
