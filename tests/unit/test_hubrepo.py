"""Hub resolution."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from wizrelay import hubrepo, paths
from wizrelay.errors import UsageError


def test_ttl_zero_means_fetch_every_time() -> None:
    # The prototype's `value or 10` turned a configured 0 into 10, silently disabling the
    # setting. An explicit None check is the fix, and this test is the guard.
    assert hubrepo.ttl_minutes({"fetch_ttl_minutes": 0}) == 0


def test_ttl_unset_uses_the_default() -> None:
    assert hubrepo.ttl_minutes({}) == hubrepo.DEFAULT_TTL_MINUTES


@pytest.mark.parametrize("value", ["ten", None, [], {}])
def test_ttl_junk_falls_back_to_the_default(value) -> None:
    assert hubrepo.ttl_minutes({"fetch_ttl_minutes": value}) == hubrepo.DEFAULT_TTL_MINUTES


def test_ttl_negative_is_clamped() -> None:
    assert hubrepo.ttl_minutes({"fetch_ttl_minutes": -5}) == 0


def test_a_local_hub_is_read_only(hub: Path) -> None:
    handle = hubrepo.resolve({"hub": {"path": str(hub)}}, allow_network=False)
    assert handle.source == "local"
    assert handle.read_only is True
    assert handle.available is True
    assert handle.tasks_dir == hub / "tasks"


def test_a_missing_local_hub_degrades_with_a_note(tmp_path: Path) -> None:
    handle = hubrepo.resolve({"hub": {"path": str(tmp_path / "absent")}}, allow_network=False)
    assert handle.available is False
    assert handle.notes


def test_a_directory_without_the_marker_is_noted(tmp_path: Path) -> None:
    directory = tmp_path / "not-a-hub"
    directory.mkdir()
    handle = hubrepo.resolve({"hub": {"path": str(directory)}}, allow_network=False)
    assert any(paths.HUB_MARKER in note for note in handle.notes)


def test_no_hub_configured() -> None:
    handle = hubrepo.resolve({}, allow_network=False)
    assert handle.source == "none"
    assert handle.available is False


def test_a_hook_never_clones() -> None:
    # Cloning is slow and can prompt for credentials, so a hook must not.
    handle = hubrepo.resolve(
        {"hub": {"repo": "git@example.invalid:a/b.git"}},
        allow_network=False,
        allow_clone=False,
    )
    assert handle.available is False
    assert any("not cached" in note for note in handle.notes)


def test_a_credential_url_is_rejected() -> None:
    with pytest.raises(UsageError) as excinfo:
        hubrepo.resolve({"hub": {"repo": "https://u:token@example.com/a/b.git"}})
    assert "credential" in str(excinfo.value).lower()


def test_a_home_relative_hub_path_is_expanded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `expanduser` reads HOME on POSIX and USERPROFILE on Windows, where HOME is never
    # consulted. Setting only one of them makes this test pass on three platforms and
    # resolve to the real home directory on the fourth.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    hub = tmp_path / "myhub"
    hub.mkdir()
    (hub / paths.HUB_MARKER).write_text("{}", encoding="utf-8")
    handle = hubrepo.resolve({"hub": {"path": "~/myhub"}}, allow_network=False)
    assert handle.path == hub


def test_read_marker(hub: Path) -> None:
    marker = hubrepo.read_marker(hub)
    assert marker["name"] == "test-hub"
    assert hubrepo.read_marker(hub / "tasks") == {}


def test_read_policy_returns_none_when_the_hub_has_none(hub: Path) -> None:
    assert hubrepo.read_policy(hub) is None
    assert hubrepo.read_policy(None) is None


def test_read_policy_reads_a_team_policy(hub: Path) -> None:
    policy_path = hub / "policies" / "routing-policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text('{"schema_version": 1, "tiers": []}', encoding="utf-8")
    assert hubrepo.read_policy(hub) == {"schema_version": 1, "tiers": []}


def test_freshness_stamp_respects_the_ttl(tmp_path: Path) -> None:
    cache = tmp_path / "cache" / "hubs" / "acme-hub-12345678"
    cache.mkdir(parents=True)
    assert hubrepo._is_fresh(cache, 10) is False
    hubrepo._touch_stamp(cache)
    assert hubrepo._is_fresh(cache, 10) is True
    # A TTL of 0 is never fresh, however recent the stamp.
    assert hubrepo._is_fresh(cache, 0) is False
    # An expired stamp is not fresh.
    stamp = hubrepo._stamp_path(cache)
    old = time.time() - 3600
    import os

    os.utime(stamp, (old, old))
    assert hubrepo._is_fresh(cache, 10) is False
