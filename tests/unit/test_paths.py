"""Persona detection, containment and cache identity."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from wizrelay import paths


def _dev(root: Path) -> Path:
    (root / paths.CONFIG_DIR_NAME).mkdir(parents=True, exist_ok=True)
    (root / paths.CONFIG_DIR_NAME / paths.DEV_CONFIG).write_text("{}", encoding="utf-8")
    return root


def test_developer_persona(tmp_path: Path) -> None:
    root = _dev(tmp_path / "repo")
    context = paths.detect(root)
    assert context.persona == paths.PERSONA_DEV
    assert context.root == root.resolve()
    assert context.is_dev and not context.is_hub and not context.is_silent


def test_developer_persona_is_found_from_a_subdirectory(tmp_path: Path) -> None:
    # Appendix B4 needs this: a session started in a subdirectory still resolves.
    root = _dev(tmp_path / "repo")
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert paths.detect(deep).root == root.resolve()


def test_hub_persona(tmp_path: Path) -> None:
    root = tmp_path / "hub"
    root.mkdir()
    (root / paths.HUB_MARKER).write_text("{}", encoding="utf-8")
    assert paths.detect(root).persona == paths.PERSONA_HUB


def test_no_marker_is_silent(tmp_path: Path) -> None:
    assert paths.detect(tmp_path).persona == paths.PERSONA_NONE
    assert paths.detect(tmp_path).is_silent


def test_developer_wins_when_both_markers_exist(tmp_path: Path) -> None:
    # A misconfiguration, and the developer persona is the one with protective hooks.
    root = _dev(tmp_path / "both")
    (root / paths.HUB_MARKER).write_text("{}", encoding="utf-8")
    assert paths.detect(root).persona == paths.PERSONA_DEV


def test_find_repo_root_handles_a_worktree_file(tmp_path: Path) -> None:
    root = tmp_path / "wt"
    root.mkdir()
    # In a git worktree, `.git` is a file rather than a directory.
    (root / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
    assert paths.find_repo_root(root) == root.resolve()


def test_find_repo_root_returns_none_outside_a_repository(tmp_path: Path) -> None:
    assert paths.find_repo_root(tmp_path) is None


def test_is_inside(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "a").mkdir(parents=True)
    assert paths.is_inside(root, root / "a") is True
    assert paths.is_inside(root, root) is True
    assert paths.is_inside(root, tmp_path) is False


@pytest.mark.skipif(sys.platform != "win32", reason="drive letters exist only on Windows")
def test_a_different_drive_reads_as_outside() -> None:  # pragma: no cover - Windows only
    assert paths.is_inside(Path("C:/repo"), Path("D:/other")) is False


@pytest.mark.skipif(sys.platform != "win32", reason="UNC paths exist only on Windows")
def test_a_unc_path_reads_as_outside() -> None:  # pragma: no cover - Windows only
    assert paths.is_inside(Path("C:/repo"), Path("//server/share/file")) is False


def test_rel_posix(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "a" / "b").mkdir(parents=True)
    assert paths.rel_posix(root, root / "a" / "b" / "x.py") == "a/b/x.py"
    assert paths.rel_posix(root, tmp_path / "outside.py") is None


def test_hub_identity_is_stable_across_url_spellings() -> None:
    identities = {
        paths.hub_identity(url)
        for url in (
            "git@github.com:acme/hub.git",
            "https://github.com/acme/hub.git",
            "https://github.com/acme/hub/",
            "https://github.com/acme/hub",
            "ssh://git@github.com/acme/hub.git",
        )
    }
    assert len(identities) == 1, "the same hub must resolve to one cache directory"


def test_hub_identity_differs_between_hubs() -> None:
    assert paths.hub_identity("git@github.com:acme/hub.git") != paths.hub_identity(
        "git@github.com:other/hub.git"
    )


def test_hub_identity_is_readable_and_hashed() -> None:
    identity = paths.hub_identity("git@github.com:acme/research-hub.git")
    assert identity.startswith("acme-research-hub-")
    assert len(identity.rsplit("-", 1)[1]) == 8


def test_hub_cache_dirs_never_collide() -> None:
    # Invariant I4: two hubs on one machine must not share a directory.
    first = paths.hub_cache_dir("git@github.com:acme/hub.git")
    second = paths.hub_cache_dir("git@github.com:other/hub.git")
    assert first != second
    assert first.parent == second.parent


@pytest.mark.parametrize(
    ("url", "embedded"),
    [
        ("https://user:token@github.com/a/b.git", True),
        ("http://u:p@example.com/x", True),
        ("git@github.com:a/b.git", False),
        ("https://github.com/a/b.git", False),
        ("ssh://git@host/a/b", False),
    ],
)
def test_embedded_credentials_detection(url: str, embedded: bool) -> None:
    assert paths.has_embedded_credentials(url) is embedded


def test_cache_root_honours_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WIZRELAY_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert paths.cache_root() == tmp_path / "xdg" / "wizrelay"


def test_data_root_prefers_the_plugin_data_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "pd"))
    assert paths.data_root() == tmp_path / "pd"
    assert paths.heartbeat_dir() == tmp_path / "pd" / "heartbeats"
