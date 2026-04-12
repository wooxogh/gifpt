"""LangSmith tracing helper with safe fallback.

When `langsmith` is not installed, `traceable` becomes a no-op decorator so the
pipeline keeps working in environments without the dependency (tests, minimal
installs). Import from this module instead of `langsmith` directly.
"""

try:
    from langsmith import traceable  # type: ignore
except ImportError:
    def traceable(*args, **kwargs):  # type: ignore[no-redef]
        def _decorate(fn):
            return fn
        if args and callable(args[0]) and not kwargs:
            return args[0]
        return _decorate
