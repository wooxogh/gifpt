# studio/ai/example_library.py
import json
import re
import logging
from pathlib import Path
from typing import Optional

from studio.ai.patterns import PatternType

logger = logging.getLogger(__name__)

_JSONL_PATH = Path(__file__).parent / "examples" / "seed_examples.jsonl"


def normalize_slug(name: str) -> str:
    """Normalize an algorithm name to a safe cache key slug.

    Examples:
        "A*"            -> "a_star"
        "Floyd-Warshall"-> "floyd_warshall"
        "bubble sort"   -> "bubble_sort"
        "버블정렬"       -> ""  (non-ASCII stripped)
    """
    name = name.lower()
    name = name.replace("*", "_star").replace("+", "_plus")
    name = name.replace("-", "_").replace("/", "_").replace(" ", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:64]


class ExampleLibrary:
    """Loads Manim examples from a JSONL file and retrieves them by PatternType.

    Each line in the JSONL must have at minimum:
        tag, algorithm, pattern_type, domain, quality_score, code
    """

    def __init__(self, jsonl_path: Path = _JSONL_PATH):
        self._examples: list[dict] = []
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._examples.append(json.loads(line))
            logger.info(
                "ExampleLibrary loaded %d examples from %s",
                len(self._examples),
                jsonl_path,
            )
        except FileNotFoundError:
            logger.warning(
                "ExampleLibrary: JSONL not found at %s — library is empty", jsonl_path
            )

    def get_examples(
        self,
        pattern_type: Optional[PatternType] = None,
        top_k: int = 3,
        is_3d: bool = False,
    ) -> list[dict]:
        """Return top-k examples by quality_score for the given pattern_type.

        When is_3d=True, prefers 3D examples (ThreeDScene). Falls back to all
        examples sorted by quality_score when no examples match.
        """
        pool = list(self._examples)

        # Filter by 3D preference
        if is_3d:
            threed_pool = [e for e in pool if e.get("is_3d", False)]
            if threed_pool:
                pool = threed_pool

        if pattern_type is not None:
            pattern_val = pattern_type.value
            matching = [
                e for e in pool
                if e.get("pattern_type", "").lower() == pattern_val
            ]
        else:
            matching = list(pool)

        matching.sort(key=lambda e: e.get("quality_score", 0), reverse=True)

        if not matching:
            # Fallback: all examples (respecting 3D pref) ranked by quality
            fallback = pool if pool else self._examples
            all_sorted = sorted(
                fallback,
                key=lambda e: e.get("quality_score", 0),
                reverse=True,
            )
            return all_sorted[:top_k]

        return matching[:top_k]


# Module-level singleton — loaded once at import time.
_library: Optional["ExampleLibrary"] = None


def get_library() -> ExampleLibrary:
    global _library
    if _library is None:
        _library = ExampleLibrary()
    return _library
