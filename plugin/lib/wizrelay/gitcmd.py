"""A thin, safe wrapper around the `git` command line.

Not one of the original modules: `hubrepo.py` and `audit.py` both need git, and one
wrapper is better than two.

Every rule is enforced here rather than at each call site:

* ``shell=False`` always, with the command as a list. No string interpolation reaches a
  shell, so a branch name containing `;` is an argument, not a command.
* an explicit ``timeout`` on every call, because a hook that hangs is worse than a hook
  that fails — `SessionStart` has a 30-second budget and a git fetch against an
  unreachable host would eat all of it.
* ``--`` before any path or ref that could otherwise be read as an option. A branch
  literally named `--upload-pack=...` is the reason this is not optional.
* output decoded as UTF-8 with ``errors="replace"``, so a commit message in another
  encoding cannot raise inside a hook.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

__all__ = [
    "DEFAULT_TIMEOUT",
    "GitResult",
    "changed_paths",
    "current_branch",
    "head_commit",
    "is_repo",
    "merge_base_diff",
    "ref_exists",
    "run",
]

DEFAULT_TIMEOUT = 20.0
#: Network operations get their own budget: 4 seconds for the
#: SessionStart fetch; anything longer is skipped silently.
NETWORK_TIMEOUT = 4.0


class GitResult:
    """The outcome of one git invocation. Never raises on a non-zero exit."""

    __slots__ = ("args", "returncode", "stderr", "stdout", "timed_out")

    def __init__(
        self,
        args: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
        timed_out: bool = False,
    ) -> None:
        self.args = list(args)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<git {' '.join(self.args)} -> {self.returncode}>"


def run(
    args: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    timeout: float = DEFAULT_TIMEOUT,
    env: Optional[dict] = None,
) -> GitResult:
    """Run `git <args>` and return the result. A failure is data, not an exception."""
    command = ["git", *args]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed program, list form, no shell
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return GitResult(command, 124, "", f"timed out after {timeout}s", timed_out=True)
    except (OSError, ValueError) as exc:
        return GitResult(command, 127, "", str(exc))
    return GitResult(command, completed.returncode, completed.stdout, completed.stderr)


def is_repo(path: Path) -> bool:
    """Whether `path` is inside a git work tree."""
    return run(["rev-parse", "--is-inside-work-tree"], cwd=path).stdout.strip() == "true"


def head_commit(path: Path, *, short: bool = True) -> Optional[str]:
    """The current commit, or None in a repository with no commits yet."""
    result = run(["rev-parse", "--short=12" if short else "HEAD", "HEAD"], cwd=path)
    return result.stdout.strip() or None if result.ok else None


def current_branch(path: Path) -> Optional[str]:
    """The checked-out branch name, or None when HEAD is detached."""
    result = run(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=path)
    return result.stdout.strip() or None if result.ok else None


def ref_exists(path: Path, ref: str) -> bool:
    """Whether a ref resolves. Used before diffing against a base that may be absent."""
    return run(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=path).ok


def _split_nul(payload: str) -> list[str]:
    return [item for item in payload.split("\0") if item]


def changed_paths(path: Path) -> tuple[list[str], bool]:
    """Working-tree and index changes as repository-relative POSIX paths.

    Reads ``git status --porcelain=v1 -z -uall``:

    * ``-z`` makes the separator a NUL byte, so a filename containing a newline or a quote
      is reported literally instead of being C-quoted. Parsing quoted names correctly is
      far harder than consuming NUL-separated records.
    * ``-uall`` lists untracked files individually rather than collapsing them into their
      directory, which is what makes a new out-of-scope file visible.
    * a rename or copy record (``R`` or ``C``) occupies **two** entries: the destination
      first, then the source. Only the destination is reported, because that is the path
      that now exists.

    Returns `(paths, ok)`; `ok` is False when git could not be run at all.
    """
    result = run(["status", "--porcelain=v1", "-z", "-uall"], cwd=path)
    if not result.ok:
        return [], False

    entries = _split_nul(result.stdout)
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 3:
            continue
        status = entry[:2]
        name = entry[3:]
        if status[0] in ("R", "C") or status[1] in ("R", "C"):
            # The next entry is the source path of the rename; consume and ignore it.
            index += 1
        if name:
            paths.append(name.replace("\\", "/"))
    return sorted(set(paths)), True


def merge_base_diff(path: Path, base: str) -> tuple[list[str], bool]:
    """Paths changed between the merge base of `base` and HEAD, and HEAD.

    `base...HEAD` (three dots) is deliberate: it answers "what has this branch changed
    since it diverged", which is the question a pull-request gate asks. Two dots would
    also report everything that landed on the base branch meanwhile.

    Returns `(paths, ok)`; `ok` is False when the base ref does not resolve, which the
    caller turns into a notice rather than a failure.
    """
    if not ref_exists(path, base):
        return [], False
    result = run(
        ["diff", "--name-only", "-z", f"{base}...HEAD", "--"],
        cwd=path,
    )
    if not result.ok:
        return [], False
    return sorted({p.replace("\\", "/") for p in _split_nul(result.stdout)}), True


def clone(url: str, dest: Path, *, branch: Optional[str] = None, depth: int = 1) -> GitResult:
    """Clone a hub. Shallow by default: only the current content of the tasks is needed."""
    args = ["clone", "--quiet"]
    if depth:
        args += ["--depth", str(depth)]
    if branch:
        args += ["--branch", branch]
    args += ["--", url, str(dest)]
    return run(args, timeout=60.0)


def fetch(path: Path, *, branch: Optional[str] = None) -> GitResult:
    """Fetch the hub's current state within the network budget."""
    args = ["fetch", "--quiet", "--depth", "1", "origin"]
    if branch:
        args += ["--", branch]
    return run(args, cwd=path, timeout=NETWORK_TIMEOUT)


def reset_hard(path: Path, ref: str) -> GitResult:
    """Move a cache clone onto a fetched ref. Only ever used inside a cache directory."""
    return run(["reset", "--hard", "--quiet", "--", ref], cwd=path)


def tracked_files(path: Path, subdir: str = "") -> list[str]:
    """Paths git tracks, optionally limited to a subdirectory."""
    args = ["ls-files", "-z", "--"]
    if subdir:
        args.append(subdir)
    result = run(args, cwd=path)
    if not result.ok:
        return []
    return sorted(p.replace("\\", "/") for p in _split_nul(result.stdout))
