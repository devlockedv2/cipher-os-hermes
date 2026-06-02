"""Path-scoping enforcement — prevents agents from accessing out-of-scope files."""

from pathlib import Path


class PathViolationError(Exception):
    """Raised when an agent attempts to access a path outside its allowed scope."""
    pass


def is_path_allowed(target: str, allowed_paths: list[str]) -> bool:
    """Check if target path is within any of the allowed paths (prefix match)."""
    target_resolved = str(Path(target).resolve())

    for allowed in allowed_paths:
        allowed_resolved = str(Path(allowed).resolve())
        if target_resolved.startswith(allowed_resolved):
            return True

    return False


def enforce_path(target: str, allowed_paths: list[str]) -> str:
    """Enforce path scoping. Returns resolved path or raises PathViolationError."""
    if not is_path_allowed(target, allowed_paths):
        raise PathViolationError(
            f"Access denied: '{target}' is outside allowed paths. "
            f"Allowed: {allowed_paths}"
        )
    return str(Path(target).resolve())
