"""Upload seed_examples.jsonl to a LangSmith Dataset.

Usage (from GIFPT_AI/):
    python -m scripts.upload_goldset
    python -m scripts.upload_goldset --name gifpt-goldset-v0 --dry-run

Requires these env vars (see LangSmith project settings):
    LANGSMITH_API_KEY
    LANGSMITH_TRACING=true        (enables the client)
    LANGSMITH_ENDPOINT            (defaults to https://api.smith.langchain.com)

The dataset is keyed by `tag`; re-running replaces existing examples rather
than duplicating them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parents[1] / "studio" / "ai" / "examples" / "seed_examples.jsonl"
DEFAULT_NAME = "gifpt-goldset-v0"
DEFAULT_DESCRIPTION = (
    "GIFPT Phase 0 goldset — 16 hand-picked algorithm animation requests. "
    "Each example pairs a natural-language description (input) with a reference "
    "Manim implementation and its hand-assigned quality score (output). Used as "
    "the baseline dataset for Phase 1 experiment A (prompt tweak) and Phase 2 "
    "experiment B (v1 vs v2)."
)


def load_seed_examples(path: Path) -> list[dict]:
    examples = []
    with path.open() as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {i}: {exc}")
    return examples


def example_to_dataset_pair(ex: dict) -> tuple[dict, dict, dict]:
    """Return (inputs, outputs, metadata) for LangSmith."""
    inputs = {
        "description": ex.get("description", ""),
        "algorithm": ex.get("algorithm", ""),
    }
    outputs = {
        "reference_code": ex.get("code", ""),
        "quality_score": ex.get("quality_score", 0),
    }
    metadata = {
        "tag": ex.get("tag", ""),
        "domain": ex.get("domain", ""),
        "pattern_type": ex.get("pattern_type", ""),
    }
    return inputs, outputs, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default=DEFAULT_NAME, help="LangSmith dataset name")
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    parser.add_argument("--seed-path", default=str(SEED_PATH))
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate only, do not upload")
    args = parser.parse_args()

    seed_path = Path(args.seed_path)
    if not seed_path.exists():
        print(f"Seed file not found: {seed_path}", file=sys.stderr)
        return 1

    examples = load_seed_examples(seed_path)
    print(f"Loaded {len(examples)} seed examples from {seed_path}")

    if args.dry_run:
        for ex in examples:
            inputs, outputs, metadata = example_to_dataset_pair(ex)
            print(f"  - {metadata['tag']:<25s} domain={metadata['domain']:<20s} score={outputs['quality_score']}")
        print("\nDry run complete. No upload performed.")
        return 0

    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY not set. Export it or pass --dry-run.", file=sys.stderr)
        return 1

    try:
        from langsmith import Client
    except ImportError:
        print("langsmith package not installed. Run: pip install langsmith", file=sys.stderr)
        return 1

    client = Client()

    existing = list(client.list_datasets(dataset_name=args.name))
    if existing:
        dataset = existing[0]
        print(f"Reusing existing dataset: {dataset.name} (id={dataset.id})")
        existing_examples = {
            ex.metadata.get("tag"): ex
            for ex in client.list_examples(dataset_id=dataset.id)
            if ex.metadata and ex.metadata.get("tag")
        }
    else:
        dataset = client.create_dataset(
            dataset_name=args.name,
            description=args.description,
        )
        print(f"Created dataset: {dataset.name} (id={dataset.id})")
        existing_examples = {}

    created = updated = 0
    for ex in examples:
        inputs, outputs, metadata = example_to_dataset_pair(ex)
        tag = metadata["tag"]
        if tag in existing_examples:
            client.update_example(
                example_id=existing_examples[tag].id,
                inputs=inputs,
                outputs=outputs,
                metadata=metadata,
            )
            updated += 1
        else:
            client.create_example(
                inputs=inputs,
                outputs=outputs,
                metadata=metadata,
                dataset_id=dataset.id,
            )
            created += 1

    print(f"\nUpload complete. created={created}, updated={updated}, total={created + updated}")
    print(f"Dataset URL: https://smith.langchain.com/o/-/datasets/{dataset.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
