"""Tracker adapters."""

from __future__ import annotations

from typing import Any, Optional

import pytest

from wizrelay import trackers
from wizrelay.errors import UsageError


def cfg(**tracker: Any) -> dict[str, Any]:
    return {"tracker": tracker}


ALL_TYPES = ["clickup", "github", "jira", "linear", "azure-devops", "none"]


def test_every_adapter_in_the_plan_table_ships() -> None:
    assert set(trackers.available()) == set(ALL_TYPES)


@pytest.mark.parametrize(
    ("raw", "tracker_type", "config", "canonical"),
    [
        # ClickUp
        ("86c1abcd", "clickup", None, "CU-86c1abcd"),
        ("CU-86c1abcd", "clickup", None, "CU-86c1abcd"),
        ("https://app.clickup.com/t/86c1abcd", "clickup", None, "CU-86c1abcd"),
        # A team's own identifier prefix becomes the canonical prefix.
        ("123456", "clickup", cfg(id_prefix="TASK-"), "TASK-123456"),
        ("TASK-123456", "clickup", cfg(id_prefix="TASK-"), "TASK-123456"),
        # GitHub
        ("#123", "github", cfg(repo="acme/web"), "GH-123"),
        ("123", "github", cfg(repo="acme/web"), "GH-123"),
        ("GH-123", "github", cfg(repo="acme/web"), "GH-123"),
        ("acme/web#123", "github", None, "GH-123"),
        # Jira: already canonical, and case-insensitive on input.
        ("PROJ-123", "jira", cfg(base_url="https://a.atlassian.net"), "PROJ-123"),
        ("proj-123", "jira", cfg(base_url="https://a.atlassian.net"), "PROJ-123"),
        # Linear
        ("ENG-45", "linear", cfg(workspace="acme"), "ENG-45"),
        ("eng-45", "linear", cfg(workspace="acme"), "ENG-45"),
        # Azure DevOps
        ("AB#99", "azure-devops", cfg(base_url="https://dev.azure.com/a", project="P"), "AB-99"),
        ("99", "azure-devops", cfg(base_url="https://dev.azure.com/a", project="P"), "AB-99"),
        # none
        ("quota-limits", "none", None, "quota-limits"),
    ],
)
def test_identifier_normalisation(
    raw: str, tracker_type: str, config: Optional[dict[str, Any]], canonical: str
) -> None:
    assert trackers.normalize(raw, tracker_type, config=config)[0] == canonical


@pytest.mark.parametrize(
    ("tracker_type", "ref", "config", "url"),
    [
        ("clickup", "86c1abcd", None, "https://app.clickup.com/t/86c1abcd"),
        ("github", "123", cfg(repo="acme/web"), "https://github.com/acme/web/issues/123"),
        (
            "jira",
            "PROJ-1",
            cfg(base_url="https://acme.atlassian.net"),
            "https://acme.atlassian.net/browse/PROJ-1",
        ),
        ("linear", "ENG-1", cfg(workspace="acme"), "https://linear.app/acme/issue/ENG-1"),
        (
            "azure-devops",
            "99",
            cfg(base_url="https://dev.azure.com/acme", project="Core"),
            "https://dev.azure.com/acme/Core/_workitems/edit/99",
        ),
        ("none", "local-1", None, None),
    ],
)
def test_url_building(tracker_type: str, ref: str, config, url) -> None:
    assert trackers.build_url(ref, tracker_type, config=config) == url


@pytest.mark.parametrize(
    ("tracker_type", "ref"),
    [("github", "123"), ("jira", "PROJ-1"), ("linear", "ENG-1"), ("azure-devops", "9")],
)
def test_no_url_without_the_required_configuration(tracker_type: str, ref: str) -> None:
    # A wrong link in a tracker comment is worse than no link.
    assert trackers.build_url(ref, tracker_type, config=None) is None


@pytest.mark.parametrize("raw", ["", "!!bad!!", "this-is-far-too-long-to-be-a-clickup-id"])
def test_an_unusable_reference_is_a_usage_error(raw: str) -> None:
    with pytest.raises(UsageError):
        trackers.normalize(raw, "clickup")


def test_an_unknown_tracker_type_is_a_usage_error() -> None:
    with pytest.raises(UsageError):
        trackers.descriptor("trello")


def test_only_a_verified_mcp_endpoint_is_offered() -> None:
    """An unverified endpoint is never written into a configuration."""
    assert trackers.mcp_server_config("clickup") == {
        "clickup": {"type": "http", "url": "https://mcp.clickup.com/mcp"}
    }
    for tracker_type in ("github", "jira", "linear", "azure-devops", "none"):
        assert trackers.mcp_server_config(tracker_type) is None


def test_every_adapter_explains_its_mcp_status() -> None:
    for tracker_type in ALL_TYPES:
        note = trackers.mcp_note(tracker_type)
        if tracker_type == "none":
            assert note is None
        else:
            assert note


def test_every_adapter_ships_instructions() -> None:
    for tracker_type in ALL_TYPES:
        assert trackers.instructions_path(tracker_type) is not None, tracker_type


def test_levels_match_the_plan_table() -> None:
    assert trackers.level("clickup") == "full"
    assert trackers.level("github") == "full"
    assert trackers.level("none") == "full"
    for beta in ("jira", "linear", "azure-devops"):
        assert trackers.level(beta) == "beta"


def test_comment_tags() -> None:
    assert trackers.TAG_PUBLISH == "[WIZRELAY-PUBLISH]"
    assert trackers.TAG_QUESTION == "[WIZRELAY-Q]"
    assert trackers.TAG_ANSWER == "[WIZRELAY-A]"
    assert trackers.TAG_VERIFY == "[WIZRELAY-VERIFY]"


def test_task_folder_name_pattern() -> None:
    assert trackers.task_folder_name("CU-1", "quota") == "CU-1-quota"
    assert trackers.is_safe_folder_name("CU-1-quota") is True
    for unsafe in ("../escape", ".hidden", "with space", "-leading", "a" * 200):
        assert trackers.is_safe_folder_name(unsafe) is False


def test_task_folder_name_rejects_an_unusable_result() -> None:
    with pytest.raises(UsageError):
        trackers.task_folder_name("..", "x")


def test_descriptors_use_the_portable_named_group_syntax() -> None:
    # Descriptors are written `(?<name>...)` so the same expression can be reused by a
    # JSON Schema pattern; trackers.py translates it for Python's `re`.
    import json

    directory = trackers.catalogue_dir()
    assert directory is not None
    for path in directory.glob("*.json"):
        pattern = json.loads(path.read_text(encoding="utf-8")).get("ref_pattern") or ""
        assert "(?P<" not in pattern, f"{path.name} uses Python-only group syntax"
