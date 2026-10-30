"""Shared plumbing for every hook handler."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "MAX_STDIN_BYTES",
    "emit",
    "emit_nothing",
    "read_event",
    "resolve_tool_path",
    "session_id_of",
]

#: Hook stdin is capped at 1 MB. A payload larger than that is not a payload this
#: project understands, and reading it would let an oversized transcript path exhaust
#: memory inside a hook.
MAX_STDIN_BYTES = 1024 * 1024


def read_event() -> Optional[dict[str, Any]]:
    """Read the event JSON from stdin.

    Returns None when the payload is absent, truncated, oversized or malformed. Every
    caller treats None as "make no decision": a broken stdin produces no decision at all,
    because acting on a payload we could not parse is worse than not acting.
    """
    try:
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    except (OSError, ValueError):
        return None
    if not raw or len(raw) > MAX_STDIN_BYTES:
        return None
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def emit(payload: Mapping[str, Any]) -> int:
    """Print the hook response and return 0.

    Hooks communicate through stdout JSON and always exit 0. An exit code is a second,
    coarser channel (exit 2 blocks on most events), and mixing the two makes behaviour
    depend on which one Claude Code reads first.
    """
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


def emit_nothing() -> int:
    """Produce no output at all.

    This is what invariant I5 requires in a directory with no marker file: not an empty
    JSON object, not a newline — nothing.
    """
    return 0


def session_id_of(event: Mapping[str, Any]) -> str:
    return str(event.get("session_id") or "")


def cwd_of(event: Mapping[str, Any]) -> Path:
    """The event's working directory, falling back to the process's own."""
    raw = event.get("cwd")
    if isinstance(raw, str) and raw.strip():
        try:
            return Path(raw).expanduser()
        except (OSError, ValueError):
            pass
    return Path.cwd()


#: Keys that carry a file path in the tool inputs this project matches on. Edit and Write
#: use `file_path`; NotebookEdit uses `notebook_path`. Several are checked rather than one,
#: because a future tool with a different key should degrade to "no decision" only if it
#: really carries no recognisable path.
_PATH_KEYS = ("file_path", "notebook_path", "path", "filePath")


def resolve_tool_path(event: Mapping[str, Any]) -> Optional[Path]:
    """Extract the target file from a tool event and resolve it against the event cwd.

    A relative path is resolved against the hook's `cwd`, which is what makes the
    subdirectory case work: a session started in `packages/api/`
    editing `src/x.ts` has to resolve to the repository-relative `packages/api/src/x.ts`.
    """
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, Mapping):
        return None
    for key in _PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            candidate = Path(os.path.expandvars(value)).expanduser()
            if not candidate.is_absolute():
                candidate = cwd_of(event) / candidate
            return candidate
    return None


def debug(message: str) -> None:
    """Write a diagnostic to stderr, and only when WIZRELAY_DEBUG=1.

    stdout belongs to the contract; anything else there would corrupt the response.
    """
    if os.environ.get("WIZRELAY_DEBUG") == "1":
        sys.stderr.write(f"[wizrelay] {message}\n")
