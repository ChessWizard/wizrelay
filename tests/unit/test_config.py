"""Layered configuration."""

from __future__ import annotations

from wizrelay import config


def test_deep_merge_recurses_into_objects() -> None:
    assert config.deep_merge(
        {"hub": {"repo": "r", "branch": "main"}}, {"hub": {"path": "~/h"}}
    ) == {"hub": {"repo": "r", "branch": "main", "path": "~/h"}}


def test_deep_merge_replaces_arrays() -> None:
    # A list of paths is one decision, not something to accumulate across layers.
    assert config.deep_merge({"paths": ["a", "b"]}, {"paths": ["c"]}) == {"paths": ["c"]}


def test_deep_merge_does_not_mutate_its_inputs() -> None:
    base = {"hub": {"repo": "r"}}
    config.deep_merge(base, {"hub": {"path": "p"}})
    assert base == {"hub": {"repo": "r"}}


def test_strip_comments_is_recursive() -> None:
    assert config.strip_comments({"_c": 1, "a": {"_d": 2, "b": [{"_e": 3, "f": 4}]}}) == {
        "a": {"b": [{"f": 4}]}
    }


def test_layer_order_is_defaults_hub_shared_local() -> None:
    effective = config.layer_config(
        hub_marker={
            "schema_version": 1,
            "name": "h",
            "language": "tr",
            "tracker": {"type": "clickup", "id_prefix": "CU-"},
            "default_branch": "develop",
        },
        shared={"schema_version": 1, "role": "backend", "language": "en"},
        local={"hub": {"path": "~/code/hub"}},
    )
    # The project overrides the hub.
    assert effective["language"] == "en"
    # The hub supplies what the project does not state.
    assert effective["tracker"] == {"type": "clickup", "id_prefix": "CU-"}
    # The local layer merges into the hub's branch rather than replacing the block.
    assert effective["hub"] == {"branch": "develop", "path": "~/code/hub"}
    # Library defaults survive where nothing else sets them.
    assert effective["prompt_anchor"] is True
    assert effective["fetch_ttl_minutes"] == 10


def test_layer_config_strips_comments_from_every_layer() -> None:
    effective = config.layer_config(
        shared={"schema_version": 1, "_why": "a note", "role": "backend"},
        local={"_who": "me", "language": "tr"},
    )
    assert "_why" not in effective
    assert "_who" not in effective
    assert effective["role"] == "backend"


def test_unknown_keys_are_reported_not_rejected() -> None:
    assert config.unknown_keys({"schema_version": 1, "rolle": "backend"}) == ["rolle"]
    assert config.unknown_keys({"schema_version": 1, "_note": "x"}) == []


def test_effective_signals_defaults_to_medium() -> None:
    assert config.effective_signals({}, None) == {
        "complexity": "medium",
        "risk": "medium",
        "ambiguity": "medium",
    }


def test_role_signals_override_task_signals() -> None:
    assert (
        config.effective_signals(
            {"signals": {"risk": "high"}, "role_signals": {"frontend": {"risk": "low"}}},
            "frontend",
        )["risk"]
        == "low"
    )


def test_role_signals_for_another_role_are_ignored() -> None:
    assert (
        config.effective_signals(
            {"signals": {"risk": "high"}, "role_signals": {"frontend": {"risk": "low"}}},
            "backend",
        )["risk"]
        == "high"
    )


def test_merge_overrides_applies_wildcard_then_role() -> None:
    merged = config.merge_overrides(
        {
            "*": {"verify": {"model": "opus", "effort": "max"}},
            "backend": {"verify": {"effort": "high"}, "implement": {"advisor": "opus"}},
        },
        "backend",
    )
    # The role's value wins over the wildcard's, and the wildcard's other keys survive.
    assert merged["verify"] == {"model": "opus", "effort": "high"}
    assert merged["implement"] == {"advisor": "opus"}


def test_get_path_does_not_raise_on_a_missing_level() -> None:
    assert config.get_path({"a": {"b": 1}}, "a.b") == 1
    assert config.get_path({"a": {}}, "a.b.c", "fallback") == "fallback"
    assert config.get_path({}, "a", None) is None


def test_commands_drops_empty_values() -> None:
    assert config.commands({"commands": {"test": "pytest", "lint": "  ", "build": None}}) == {
        "test": "pytest"
    }


def test_paths_of_always_returns_a_list_of_strings() -> None:
    assert config.paths_of({"critical_paths": ["a", "", None, "b"]}, "critical_paths") == [
        "a",
        "b",
    ]
    assert config.paths_of({"critical_paths": "a/**"}, "critical_paths") == []
    assert config.paths_of({}, "critical_paths") == []
