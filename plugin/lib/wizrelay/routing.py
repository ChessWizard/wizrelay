"""Model and effort routing.

The question this answers: for *this* task in *this* repository, which model and effort
level should each phase use, and what is the exact command to start the session with?

The answer is policy-driven rather than hard-coded, so a team can replace it by committing
`policies/routing-policy.json` to their hub. The default policy is appendix C, shipped at
`plugin/config/routing-policy.json`.

The algorithm, verbatim from §8.2::

    signals = task.routing.signals (+) task.routing.role_signals[role]
    base    = sum of level(complexity, risk, ambiguity)      low=1, medium=2, high=3
    mods    = policy weights for:
                profile.codebase_size == "large"
                profile.test_maturity == "low"
                intersection(scope[role].allow, profile.critical_paths)
                intersection(scope[role].allow, profile.legacy_paths)
    score   = base + sum(mods)
    tier    = mechanical when signals.kind == "mechanical",
              otherwise the first tier by ascending max_score with score <= max_score
    phases  = tier.phases (+) overrides["*"] (+) overrides[role]
    launch  = model:    plan=opus and implement=sonnet -> "opusplan", else implement.model
              --effort  implement.effort
              --advisor only when the main model accepts one and rank(advisor) >= rank(main)
              --name    "<ID> <title>"

This module is pure. It takes the task, the profile and the policy as dictionaries and
returns a `RoutingDecision`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from . import config as config_mod
from . import globs

__all__ = [
    "LEVEL_SCORE",
    "MODEL_RANK",
    "PHASES",
    "PhaseSetting",
    "RoutingDecision",
    "accepts_advisor",
    "compute",
    "launch_command",
    "model_family",
    "model_rank",
]

PHASES = ("plan", "implement", "verify", "ask")

LEVEL_SCORE = {"low": 1, "medium": 2, "high": 3}

#: Family ordering used for two guards: whether an advisor may be paired with a main model
#: and whether a model switch is a downgrade (§8.3 item 4).
#:
#: The official documentation states that an advisor "must be the same level as the main
#: model or higher" and that Haiku cannot be an advisor, but it does not publish a total
#: order across families. The order below is therefore a **project convention**, chosen so
#: that an uncertain pair is dropped rather than proposed. Fable sits above Sonnet because
#: it is selected for open-ended research work, and below Opus because Opus is the
#: strongest general model. Recorded here rather than in code comments elsewhere so there
#: is one place to change if Anthropic publishes an order.
MODEL_RANK = {"haiku": 1, "sonnet": 2, "fable": 3, "opus": 4}

#: Models that can carry an advisor at all. Haiku cannot.
ADVISOR_CAPABLE = frozenset({"sonnet", "opus", "fable"})

_UNSAFE_NAME = re.compile(r"[\"'`$\\\x00-\x1f]")


class PhaseSetting:
    """The model, effort and optional advisor for one phase."""

    __slots__ = ("advisor", "effort", "model")

    def __init__(self, model: str, effort: str, advisor: Optional[str] = None) -> None:
        self.model = model
        self.effort = effort
        self.advisor = advisor

    def as_dict(self) -> dict[str, str]:
        out = {"model": self.model, "effort": self.effort}
        if self.advisor:
            out["advisor"] = self.advisor
        return out

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PhaseSetting):
            return NotImplemented
        return self.as_dict() == other.as_dict()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.model}/{self.effort}{'+' + self.advisor if self.advisor else ''}>"


class RoutingDecision:
    """Everything routing produces, ready to render or store in the lock file."""

    __slots__ = ("launch", "modifiers", "phases", "score", "signals", "tier")

    def __init__(
        self,
        score: int,
        tier: str,
        phases: Mapping[str, PhaseSetting],
        signals: Mapping[str, str],
        modifiers: Sequence[str],
        launch: str,
    ) -> None:
        self.score = score
        self.tier = tier
        self.phases: dict[str, PhaseSetting] = dict(phases)
        self.signals: dict[str, str] = dict(signals)
        #: Names of the modifiers that fired, so `route` can explain the score.
        self.modifiers: list[str] = list(modifiers)
        self.launch = launch

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "score": self.score,
            "phases": {name: setting.as_dict() for name, setting in self.phases.items()},
            "launch": self.launch,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<RoutingDecision {self.tier} score={self.score}>"


def model_family(model: Optional[str]) -> Optional[str]:
    """Normalise a model name to the family used for ranking.

    `opusplan` plans with Opus and executes with Sonnet, so for the purpose of "is this a
    downgrade?" it counts as Sonnet — the model that does the work.
    `default`, `inherit` and anything unrecognised return None, which every caller reads
    as "make no decision".
    """
    if not model:
        return None
    name = model.strip().lower()
    if name in ("default", "inherit", ""):
        return None
    if name == "opusplan":
        return "sonnet"
    # Accept full model identifiers such as `claude-opus-5-5` as well as aliases.
    for family in ("haiku", "sonnet", "fable", "opus"):
        if family in name:
            return family
    return None


def model_rank(model: Optional[str]) -> Optional[int]:
    """Rank a model within MODEL_RANK, or None when it is not comparable."""
    family = model_family(model)
    return MODEL_RANK.get(family) if family else None


def accepts_advisor(main_model: str, advisor: Optional[str]) -> bool:
    """Whether this advisor may be proposed alongside this main model.

    Both conditions have to hold: the main model can carry an advisor at
    all, and the advisor is at least as strong as the main model.
    """
    if not advisor:
        return False
    main_family = model_family(main_model)
    advisor_family = model_family(advisor)
    if main_family is None or advisor_family is None:
        return False
    if main_family not in ADVISOR_CAPABLE:
        return False
    if advisor_family not in ADVISOR_CAPABLE:
        return False
    return MODEL_RANK[advisor_family] >= MODEL_RANK[main_family]


def _score_signals(signals: Mapping[str, str]) -> int:
    return sum(
        LEVEL_SCORE.get(str(signals.get(key, "medium")).lower(), 2)
        for key in ("complexity", "risk", "ambiguity")
    )


def _modifiers(
    policy: Mapping[str, Any],
    profile: Mapping[str, Any],
    allow: Sequence[str],
) -> list[tuple[str, int]]:
    """Evaluate each modifier, returning `(name, weight)` for the ones that fired."""
    weights = policy.get("modifiers") or {}
    fired: list[tuple[str, int]] = []

    def weight(name: str) -> int:
        value = weights.get(name, 0)
        return value if isinstance(value, int) else 0

    if str(profile.get("codebase_size", "")).lower() == "large":
        fired.append(("codebase_size_large", weight("codebase_size_large")))
    if str(profile.get("test_maturity", "")).lower() == "low":
        fired.append(("test_maturity_low", weight("test_maturity_low")))
    critical = config_mod.paths_of(profile, "critical_paths")
    if critical and globs.intersects(allow, critical):
        fired.append(("touches_critical_paths", weight("touches_critical_paths")))
    legacy = config_mod.paths_of(profile, "legacy_paths")
    if legacy and globs.intersects(allow, legacy):
        fired.append(("touches_legacy_paths", weight("touches_legacy_paths")))
    return [(name, w) for name, w in fired if w]


def _select_tier(policy: Mapping[str, Any], score: int, mechanical: bool) -> Mapping[str, Any]:
    if mechanical:
        tier = policy.get("mechanical")
        if isinstance(tier, dict):
            return tier
    tiers = [t for t in (policy.get("tiers") or []) if isinstance(t, dict)]
    if not tiers:
        raise ValueError("routing policy declares no tiers")
    ordered = sorted(tiers, key=lambda t: t.get("max_score", 0))
    for tier in ordered:
        if score <= tier.get("max_score", 0):
            return tier
    # Above every ceiling: the strongest tier applies.
    return ordered[-1]


def _phase_settings(
    tier: Mapping[str, Any], overrides: Mapping[str, Mapping[str, Any]]
) -> dict[str, PhaseSetting]:
    out: dict[str, PhaseSetting] = {}
    tier_phases = tier.get("phases") or {}
    for phase in PHASES:
        base = dict(tier_phases.get(phase) or {})
        base.update({k: v for k, v in (overrides.get(phase) or {}).items() if v})
        model = str(base.get("model") or "sonnet")
        effort = str(base.get("effort") or "medium")
        advisor = base.get("advisor")
        out[phase] = PhaseSetting(model, effort, str(advisor) if advisor else None)
    return out


def safe_session_name(task_id: str, title: str, *, limit: int = 60) -> str:
    """Build a `--name` value that is safe to paste into sh and into PowerShell.

    The two shells escape an embedded single quote differently (`'\\''` versus `''`), so
    rather than pick one, the characters that would need escaping are removed. The value is
    a human-readable session label, so losing a stray quote costs nothing.
    """
    cleaned = _UNSAFE_NAME.sub("", f"{task_id} {title}".strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > limit:
        # Cut at a word boundary: a label ending in "kotas" reads like a typo, and the
        # identifier at the front is the part that has to survive.
        cut = cleaned[: limit + 1]
        boundary = cut.rfind(" ")
        cleaned = (cut[:boundary] if boundary > len(task_id) else cleaned[:limit]).rstrip()
    return cleaned or task_id


def launch_command(
    phases: Mapping[str, PhaseSetting],
    *,
    task_id: str = "",
    title: str = "",
    include_name: bool = True,
) -> str:
    """Render the `claude ...` command that starts a session routed for this task.

    The model is `opusplan` exactly when the policy wants Opus to plan and Sonnet to
    implement, because that is what the alias means. Otherwise the implement model wins:
    it is the phase the session spends its time in.
    """
    plan = phases.get("plan")
    implement = phases.get("implement")
    if implement is None:
        return "claude"

    plan_family = model_family(plan.model) if plan else None
    implement_family = model_family(implement.model)
    if plan_family == "opus" and implement_family == "sonnet":
        model = "opusplan"
    else:
        model = implement.model

    parts = ["claude", "--model", model, "--effort", implement.effort]
    if accepts_advisor(model, implement.advisor):
        parts += ["--advisor", str(implement.advisor)]
    if include_name and (task_id or title):
        parts += ["--name", f"'{safe_session_name(task_id, title)}'"]
    return " ".join(parts)


def compute(
    *,
    task: Mapping[str, Any],
    profile: Optional[Mapping[str, Any]] = None,
    policy: Mapping[str, Any],
    role: Optional[str] = None,
) -> RoutingDecision:
    """Run the §8.2 algorithm and return the decision.

    `role` selects the scope whose globs are compared against the profile's critical and
    legacy paths, and the role-specific signal overrides. With no role, task-wide signals
    apply and no scope intersection is possible.
    """
    profile = profile or {}
    task_routing = task.get("routing") or {}
    if not isinstance(task_routing, Mapping):
        task_routing = {}

    signals = config_mod.effective_signals(task_routing, role)
    base = _score_signals(signals)

    scope = task.get("scope") or {}
    role_scope = scope.get(role) if role and isinstance(scope, Mapping) else None
    allow: Sequence[str] = []
    if isinstance(role_scope, Mapping):
        allow = [p for p in (role_scope.get("allow") or []) if isinstance(p, str)]

    fired = _modifiers(policy, profile, allow)
    score = base + sum(weight for _name, weight in fired)

    mechanical = str(signals.get("kind", "")).lower() == "mechanical"
    tier = _select_tier(policy, score, mechanical)

    overrides = config_mod.merge_overrides(task_routing.get("overrides") or {}, role)
    phases = _phase_settings(tier, overrides)

    launch = launch_command(
        phases,
        task_id=str(task.get("id") or ""),
        title=str(task.get("title") or ""),
    )

    return RoutingDecision(
        score=score,
        tier=str(tier.get("name") or "unknown"),
        phases=phases,
        signals=signals,
        modifiers=[name for name, _weight in fired],
        launch=launch,
    )


def is_downgrade(from_model: Optional[str], to_model: Optional[str]) -> bool:
    """True when switching from one model to another drops to a weaker family.

     Used by the `PreModelSwitch` hook. Returns False whenever either side is not
     comparable, so an unknown or `default` model never triggers a prompt
    .
    """
    left = model_rank(from_model)
    right = model_rank(to_model)
    if left is None or right is None:
        return False
    return right < left


def below_implement_tier(session_model: Optional[str], phases: Mapping[str, PhaseSetting]) -> bool:
    """True when the running session's model is weaker than the implement phase wants.

    `SessionStart` uses this to warn with the launch command. A
    session model Claude Code did not report returns False: silence beats a wrong warning.
    """
    implement = phases.get("implement")
    if implement is None:
        return False
    current = model_rank(session_model)
    wanted = model_rank(implement.model)
    if current is None or wanted is None:
        return False
    return current < wanted
