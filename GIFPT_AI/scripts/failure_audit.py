"""failure_audit.py — production failure summary for the weekly review.

Pulls recent rows from the Spring backend's `analysis_jobs` MySQL table,
classifies failures into pipeline stages by parsing `errorMessage`, groups
by slug/domain, and writes both a JSON dump and a markdown summary the user
reads in their weekly 5-minute routine.

Usage:
    python -m scripts.failure_audit                          # last 7 days, mysql
    python -m scripts.failure_audit --days 14                # custom window
    python -m scripts.failure_audit --source json dump.json  # offline mode

Env vars (mysql mode):
    GIFPT_MYSQL_HOST     default 127.0.0.1
    GIFPT_MYSQL_PORT     default 3306
    GIFPT_MYSQL_USER     default root
    GIFPT_MYSQL_PASSWORD required
    GIFPT_MYSQL_DB       default gifpt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"


# ── Stage classification ──────────────────────────────────────────────────────
# Order matters: first match wins. Patterns are case-insensitive.
STAGE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ir_validation", re.compile(r"\b(ir validation|validate_pseudocode_ir|validate_anim_ir|IRValidationError)\b", re.I)),
    ("codegen",       re.compile(r"\b(codegen|static issues|validate_manim_code_basic|unknown_helper|class_name)\b", re.I)),
    ("render_timeout",re.compile(r"\b(timed out|TimeoutExpired|render timed out)\b", re.I)),
    ("render",        re.compile(r"\b(ManimRenderError|NameError|AttributeError|ImportError|MemoryError|manim)\b", re.I)),
    ("qa",            re.compile(r"\b(vision[_ ]?qa|QA score|qa_result)\b", re.I)),
    ("callback",      re.compile(r"\b(callback|HTTP \d{3}|connection refused|read timeout)\b", re.I)),
]

STAGE_LABELS = {
    "ir_validation":  "IR validation",
    "codegen":        "Codegen",
    "render":         "Render",
    "render_timeout": "Render (timeout)",
    "qa":             "Vision QA",
    "callback":       "Callback",
    "unknown":        "Unknown",
}


def classify_stage(error_message: str | None) -> str:
    if not error_message:
        return "unknown"
    for stage, pat in STAGE_PATTERNS:
        if pat.search(error_message):
            return stage
    return "unknown"


# Slug → coarse domain. Order matters for substring matching.
DOMAIN_KEYWORDS: list[tuple[str, str]] = [
    ("sorting",        "sort"),
    ("graph",          "graph"),
    ("graph",          "bfs"),
    ("graph",          "dfs"),
    ("graph",          "dijkstra"),
    ("graph",          "kruskal"),
    ("graph",          "prim"),
    ("tree",           "tree"),
    ("tree",           "heap"),
    ("dp",             "dp"),
    ("dp",             "knapsack"),
    ("dp",             "fibonacci"),
    ("cnn",            "conv"),
    ("cnn",            "cnn"),
    ("transformer",    "attention"),
    ("transformer",    "transformer"),
    ("hash",           "hash"),
    ("cache",          "cache"),
    ("cache",          "lru"),
    ("search",         "search"),
    ("search",         "binary"),
]


def slug_to_domain(slug: str | None) -> str:
    if not slug:
        return "unknown"
    s = slug.lower()
    for domain, kw in DOMAIN_KEYWORDS:
        if kw in s:
            return domain
    return "other"


# ── Data sources ──────────────────────────────────────────────────────────────

def fetch_from_mysql(days: int) -> list[dict[str, Any]]:
    try:
        import pymysql  # type: ignore
    except ImportError:
        sys.stderr.write(
            "[failure_audit] pymysql not installed. Run:\n"
            "    pip install pymysql\n"
            "Or use offline mode:\n"
            "    python -m scripts.failure_audit --source json /path/to/dump.json\n"
        )
        sys.exit(2)

    password = os.environ.get("GIFPT_MYSQL_PASSWORD")
    if not password:
        sys.stderr.write(
            "[failure_audit] GIFPT_MYSQL_PASSWORD env var is required for mysql mode.\n"
            "(See GIFPT_BE/src/main/resources/application-local.yml for the local password.)\n"
        )
        sys.exit(2)

    conn = pymysql.connect(
        host=os.environ.get("GIFPT_MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("GIFPT_MYSQL_PORT", "3306")),
        user=os.environ.get("GIFPT_MYSQL_USER", "root"),
        password=password,
        database=os.environ.get("GIFPT_MYSQL_DB", "gifpt"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, algorithm_slug, status,
                       error_message, started_at, finished_at, created_at
                FROM analysis_jobs
                WHERE created_at >= %s
                ORDER BY created_at DESC
                """,
                (cutoff,),
            )
            return list(cur.fetchall())
    finally:
        conn.close()


def fetch_from_json(path: Path) -> list[dict[str, Any]]:
    """Read a JSON dump produced by e.g. `mysql ... --batch -e "..." > dump.json`.

    Expected shape: a JSON array of records with at least `algorithm_slug`,
    `status`, `error_message`, `created_at`.
    """
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise ValueError(f"{path} is not a JSON array")
    return raw


# ── Aggregation ───────────────────────────────────────────────────────────────

def summarize(rows: list[dict[str, Any]], days: int) -> dict[str, Any]:
    total = len(rows)
    by_status = Counter(r.get("status", "UNKNOWN") for r in rows)
    failed = [r for r in rows if r.get("status") == "FAILED"]

    by_stage: Counter = Counter()
    by_domain_total: Counter = Counter()
    by_domain_failed: Counter = Counter()
    by_slug_failed: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for r in rows:
        domain = slug_to_domain(r.get("algorithm_slug"))
        by_domain_total[domain] += 1

    for r in failed:
        stage = classify_stage(r.get("error_message"))
        by_stage[stage] += 1
        domain = slug_to_domain(r.get("algorithm_slug"))
        by_domain_failed[domain] += 1
        slug = r.get("algorithm_slug") or "(custom prompt)"
        by_slug_failed[slug].append(r)

    return {
        "window_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "by_status": dict(by_status),
        "by_stage": dict(by_stage),
        "by_domain": {
            d: {
                "total": by_domain_total[d],
                "failed": by_domain_failed.get(d, 0),
                "fail_rate": (by_domain_failed.get(d, 0) / by_domain_total[d]) if by_domain_total[d] else 0.0,
            }
            for d in by_domain_total
        },
        "top_failing_slugs": sorted(
            (
                {
                    "slug": slug,
                    "count": len(items),
                    "samples": [
                        {
                            "created_at": _iso(item.get("created_at")),
                            "error": _trunc(item.get("error_message"), 200),
                        }
                        for item in items[:3]
                    ],
                }
                for slug, items in by_slug_failed.items()
            ),
            key=lambda x: x["count"],
            reverse=True,
        )[:10],
    }


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _trunc(s: Any, n: int) -> str:
    if s is None:
        return ""
    s = str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# ── Markdown rendering ────────────────────────────────────────────────────────

def render_markdown(summary: dict[str, Any]) -> str:
    total = summary["total"]
    by_status = summary["by_status"]
    success = by_status.get("SUCCESS", 0)
    failed = by_status.get("FAILED", 0)
    pass_rate = (success / total * 100) if total else 0.0
    fail_rate = (failed / total * 100) if total else 0.0

    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    window = summary["window_days"]

    lines: list[str] = []
    lines.append(f"# Failure Audit — {today}")
    lines.append("")
    lines.append(f"**Window:** last {window} days  ")
    lines.append(f"**Total jobs:** {total}  ")
    lines.append(f"**Success:** {success} ({pass_rate:.1f}%)  ")
    lines.append(f"**Failed:** {failed} ({fail_rate:.1f}%)")
    lines.append("")

    if total == 0:
        lines.append("_No jobs in window. Nothing to report._")
        return "\n".join(lines) + "\n"

    # By stage
    lines.append("## Failures by stage")
    lines.append("")
    if not summary["by_stage"]:
        lines.append("_No failures._")
    else:
        lines.append("| Stage | Count | Share of failures |")
        lines.append("|---|---:|---:|")
        for stage, count in sorted(summary["by_stage"].items(), key=lambda x: -x[1]):
            share = (count / failed * 100) if failed else 0
            lines.append(f"| {STAGE_LABELS.get(stage, stage)} | {count} | {share:.0f}% |")
    lines.append("")

    # By domain
    lines.append("## Failures by domain")
    lines.append("")
    lines.append("| Domain | Total | Failed | Fail rate | Flag |")
    lines.append("|---|---:|---:|---:|:---:|")
    for domain, stats in sorted(summary["by_domain"].items(), key=lambda x: -x[1]["fail_rate"]):
        flag = "**!**" if stats["fail_rate"] >= 0.30 and stats["total"] >= 3 else ""
        lines.append(
            f"| {domain} | {stats['total']} | {stats['failed']} | "
            f"{stats['fail_rate']*100:.0f}% | {flag} |"
        )
    lines.append("")
    lines.append("_Flagged: fail rate ≥ 30% with at least 3 jobs in the window._")
    lines.append("")

    # Top failing slugs
    lines.append("## Top failing slugs")
    lines.append("")
    if not summary["top_failing_slugs"]:
        lines.append("_No repeated failures._")
    else:
        for entry in summary["top_failing_slugs"]:
            lines.append(f"### `{entry['slug']}` — {entry['count']} failure(s)")
            for s in entry["samples"]:
                lines.append(f"- {s['created_at']} — `{s['error']}`")
            lines.append("")

    # Action items the user fills in during review
    lines.append("## Action items (fill in during weekly review)")
    lines.append("")
    lines.append("- [ ] ")
    lines.append("- [ ] ")
    lines.append("- [ ] ")
    lines.append("")

    return "\n".join(lines) + "\n"


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Look-back window in days (default: 7)")
    parser.add_argument(
        "--source",
        nargs=2,
        metavar=("MODE", "PATH"),
        help="Use 'json /path/to/dump.json' to read from a JSON dump instead of MySQL",
    )
    parser.add_argument(
        "--out-dir",
        default=str(REPORTS_DIR),
        help=f"Where to write reports (default: {REPORTS_DIR})",
    )
    args = parser.parse_args()

    if args.source:
        mode, path = args.source
        if mode != "json":
            sys.stderr.write(f"unknown source mode: {mode}\n")
            return 2
        rows = fetch_from_json(Path(path))
    else:
        rows = fetch_from_mysql(args.days)

    summary = summarize(rows, args.days)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().astimezone().strftime("%Y-%m-%d")

    json_path = out_dir / f"failure_audit_{today}.json"
    md_path = out_dir / f"failure_audit_{today}.md"

    json_path.write_text(json.dumps(summary, indent=2, default=str))
    md_path.write_text(render_markdown(summary))

    print(f"[failure_audit] wrote {json_path}")
    print(f"[failure_audit] wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
