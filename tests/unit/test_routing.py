"""Routing.

Each row of the appendix B3 table is a test. A change to one of these is a change to how
every task in every repository is routed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pytest

from wizrelay import routing

POLICY: dict[str, Any] = json.loads(
    (
        Path(__file__).resolve().parent.parent.parent / "plugin" / "config" / "routing-policy.json"
    ).read_text(encoding="utf-8")
)


def task(
    signals: dict[str, str],
    *,
    role_signals: Optional[dict[str, dict[str, str]]] = None,
    overrides: Optional[dict[str, Any]] = None,
    allow: Optional[list[str]] = None,
    roles: Optional[list[str]] = None,
) -> dict[str, Any]:
    roles = roles or ["backend"]
    allow = allow or ["app/quota/**"]
    return {
        "id": "CU-86c1abcd",
        "title": "Tenant quota",
        "roles": roles,
        "scope": {role: {"allow": list(allow), "deny": []} for role in roles},
        "routing": {
            "signals": signals,
            "role_signals": role_signals or {},
            "overrides": overrides or {},
        },
    }


def launch(decision: routing.RoutingDecision) -> str:
    return routing.launch_command(decision.phases, include_name=False)


def test_b3_row1_medium_high_low() -> None:
    decision = routing.compute(
        task=task({"complexity": "medium", "risk": "high", "ambiguity": "low"}),
        profile={},
        policy=POLICY,
        role="backend",
    )
    assert decision.score == 6
    assert decision.tier == "T2-standard"
    assert launch(decision) == "claude --model opusplan --effort high"


def test_b3_row2_critical_paths_and_low_test_maturity() -> None:
    decision = routing.compute(
        task=task({"complexity": "medium", "risk": "high", "ambiguity": "low"}),
        profile={"test_maturity": "low", "critical_paths": ["app/quota/**"]},
        policy=POLICY,
        role="backend",
    )
    assert decision.score == 8
    assert decision.tier == "T3-critical"
    assert launch(decision) == "claude --model opus --effort high"
    assert sorted(decision.modifiers) == ["test_maturity_low", "touches_critical_paths"]


def test_b3_row3_role_signals_lower_the_tier() -> None:
    decision = routing.compute(
        task=task(
            {"complexity": "medium", "risk": "high", "ambiguity": "low"},
            role_signals={"frontend": {"complexity": "low", "risk": "low", "ambiguity": "low"}},
            roles=["backend", "frontend"],
            allow=["src/features/quota/**"],
        ),
        profile={},
        policy=POLICY,
        role="frontend",
    )
    assert decision.score == 3
    assert decision.tier == "T1-routine"
    assert launch(decision) == "claude --model sonnet --effort medium"


def test_b3_row4_high_everything_with_a_large_codebase() -> None:
    decision = routing.compute(
        task=task({"complexity": "high", "risk": "high", "ambiguity": "high"}),
        profile={"codebase_size": "large"},
        policy=POLICY,
        role="backend",
    )
    assert decision.score == 10
    assert decision.tier == "T4-high-risk"
    assert launch(decision) == "claude --model opus --effort high --advisor opus"


def test_b3_row5_mechanical_bypasses_the_score_and_honours_overrides() -> None:
    decision = routing.compute(
        task=task(
            {"complexity": "low", "risk": "low", "ambiguity": "low", "kind": "mechanical"},
            overrides={
                "*": {"verify": {"model": "opus", "effort": "max"}},
                "backend": {"implement": {"advisor": "opus"}},
            },
        ),
        profile={},
        policy=POLICY,
        role="backend",
    )
    assert decision.tier == "T0-mechanical"
    # Haiku cannot carry an advisor, so the override is dropped from the launch command.
    assert launch(decision) == "claude --model haiku --effort medium"
    assert decision.phases["implement"].advisor == "opus"
    assert (decision.phases["verify"].model, decision.phases["verify"].effort) == (
        "opus",
        "max",
    )


def test_b3_row6_an_advisor_weaker_than_the_main_model_is_dropped() -> None:
    assert routing.accepts_advisor("opus", "sonnet") is False
    assert routing.accepts_advisor("sonnet", "opus") is True
    assert routing.accepts_advisor("opus", "opus") is True
    assert routing.accepts_advisor("haiku", "opus") is False
    assert routing.accepts_advisor("sonnet", None) is False


def test_signals_default_to_medium() -> None:
    decision = routing.compute(task=task({}), profile={}, policy=POLICY, role="backend")
    assert decision.score == 6
    assert decision.signals == {
        "complexity": "medium",
        "risk": "medium",
        "ambiguity": "medium",
    }


def test_a_score_above_every_ceiling_lands_on_the_strongest_tier() -> None:
    policy = {
        "schema_version": 1,
        "modifiers": {},
        "tiers": [
            {
                "name": "only",
                "max_score": 1,
                "phases": {phase: {"model": "sonnet", "effort": "low"} for phase in routing.PHASES},
            }
        ],
    }
    decision = routing.compute(
        task=task({"complexity": "high", "risk": "high", "ambiguity": "high"}),
        profile={},
        policy=policy,
        role="backend",
    )
    assert decision.tier == "only"


def test_a_policy_with_no_tiers_is_an_error() -> None:
    with pytest.raises(ValueError):
        routing.compute(
            task=task({}), profile={}, policy={"schema_version": 1, "tiers": []}, role=None
        )


@pytest.mark.parametrize(
    ("model", "family"),
    [
        ("opus", "opus"),
        ("sonnet", "sonnet"),
        ("haiku", "haiku"),
        ("fable", "fable"),
        # opusplan plans with Opus and executes with Sonnet, so for "is this a
        # downgrade?" it counts as Sonnet.
        ("opusplan", "sonnet"),
        ("claude-opus-5-5", "opus"),
        ("default", None),
        ("inherit", None),
        ("", None),
        ("gpt-4", None),
    ],
)
def test_model_family(model: str, family) -> None:
    assert routing.model_family(model) == family


@pytest.mark.parametrize(
    ("from_model", "to_model", "expected"),
    [
        ("opus", "sonnet", True),
        ("opus", "haiku", True),
        ("sonnet", "opus", False),
        ("opus", "opus", False),
        ("opusplan", "sonnet", False),
        ("opus", "default", False),
        ("default", "haiku", False),
        ("opus", "something-else", False),
    ],
)
def test_is_downgrade(from_model: str, to_model: str, expected: bool) -> None:
    assert routing.is_downgrade(from_model, to_model) is expected


def test_below_implement_tier_is_silent_without_a_session_model() -> None:
    phases = {"implement": routing.PhaseSetting("opus", "high")}
    assert routing.below_implement_tier(None, phases) is False
    assert routing.below_implement_tier("sonnet", phases) is True
    assert routing.below_implement_tier("opus", phases) is False


def test_session_name_is_safe_for_both_shells() -> None:
    name = routing.safe_session_name("CU-1", 'Tenant\'ın "kota"sı $x `y`')
    for character in "\"'`$\\":
        assert character not in name


def test_session_name_truncates_at_a_word_boundary() -> None:
    name = routing.safe_session_name("CU-1", "alpha beta gamma delta epsilon", limit=20)
    assert len(name) <= 20
    assert not name.endswith(" ")
    assert name.startswith("CU-1 ")


def test_launch_command_includes_the_name_by_default() -> None:
    phases = {
        "plan": routing.PhaseSetting("opus", "high"),
        "implement": routing.PhaseSetting("sonnet", "high"),
    }
    command = routing.launch_command(phases, task_id="CU-1", title="Quota")
    assert command == "claude --model opusplan --effort high --name 'CU-1 Quota'"
