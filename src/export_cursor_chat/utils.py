import re
from pathlib import Path


def safe_filename(name: str) -> str:
    """Return a filesystem-safe base name.

    Replaces spaces and special characters with underscores and collapses repeats.
    Returns 'untitled' if the resulting name is empty.
    """
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return cleaned or "untitled"


def sanitize_filename(name: str) -> str:
    """Replace sensitive/invalid filename characters with underscores.

    On Windows, invalid characters include: <>:"/\|?* and control chars.
    We'll conservatively allow only [A-Za-z0-9._-] and replace others with _.
    Also trim trailing spaces/dots which are not allowed in Windows filenames.
    """
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    sanitized = sanitized.strip(" ")
    sanitized = sanitized.rstrip(" .")
    if not sanitized:
        sanitized = "untitled"
    return sanitized


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


