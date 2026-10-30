"""Templates.

The `en` and `tr` sets have to be structurally identical: a Turkish team that gets an
English `PROTOCOL.md` because the translation is missing a file has silently lost the
rules the whole system depends on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wizrelay import templates
from wizrelay.i18n import LANGUAGES

ROOT = Path(__file__).resolve().parent.parent.parent / "plugin" / "templates"


def _relative_files(kind: str, language: str) -> set[str]:
    base = ROOT / kind / language
    return {path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file()}


@pytest.mark.parametrize("kind", ["dev", "hub"])
def test_the_language_sets_are_identical(kind: str) -> None:
    sets = {language: _relative_files(kind, language) for language in LANGUAGES}
    english = sets["en"]
    for language, files in sets.items():
        assert files == english, (
            f"{kind}/{language} differs from {kind}/en: "
            f"missing {sorted(english - files)}, extra {sorted(files - english)}"
        )


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_protocol_fits_in_sixty_lines(language: str) -> None:
    """Appendix D caps PROTOCOL.md at 60 lines; it is injected into every session."""
    text = templates.dev_template(language, "PROTOCOL.md")
    assert len(text.splitlines()) <= 60, f"{language} PROTOCOL.md is too long"


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_protocol_covers_every_required_rule(language: str) -> None:
    """Appendix D lists ten rules; each has a numbered heading."""
    text = templates.dev_template(language, "PROTOCOL.md")
    for number in range(1, 11):
        assert f"## {number}." in text, f"{language} PROTOCOL.md is missing rule {number}"


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_protocol_names_every_developer_command(language: str) -> None:
    text = templates.dev_template(language, "PROTOCOL.md")
    for command in ("pull", "plan", "ask", "verify", "sync", "status", "doctor"):
        assert f"/wizrelay:{command}" in text, f"{language}: /wizrelay:{command} is missing"


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_shipped_json_template_parses(language: str) -> None:
    for kind, name in (
        ("dev", "config.json"),
        ("dev", "profile.json"),
        ("hub", "wizrelay-hub.json"),
    ):
        reader = templates.dev_template if kind == "dev" else templates.hub_template
        text = reader(language, name)
        # A placeholder is a JSON string value, so the file stays parseable.
        json.loads(text)


def test_templates_carry_no_team_or_company_value() -> None:
    """Invariant I1: the plugin holds no content.

    The needles are the placeholder names the documentation and the examples use. A
    template that carries one of them is a template someone filled in with a concrete
    team's value and then shipped.
    """
    banned = (
        "acme",
        "api-service",
        "web-app",
        "deploy-infra",
        "example.com",
        "atlassian.net",
    )
    offenders = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for needle in banned:
            if needle in lowered:
                offenders.append(f"{path.relative_to(ROOT)}: {needle}")
    assert not offenders, "a template carries a concrete value: " + "; ".join(offenders)


def test_placeholders_are_the_documented_form() -> None:
    import re

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        # A single-brace `{like this}` would be read as a format placeholder by the
        # validator and would not be caught as an unfilled template value.
        for match in re.finditer(r"(?<!\{)\{(?!\{)([^{}]*)\}(?!\})", text):
            inner = match.group(1)
            # `{path}` is the documented substitution in a targeted test command.
            assert inner in ("path", ""), (
                f"{path.relative_to(ROOT)} has a single-brace placeholder {match.group(0)!r}"
            )


def test_render_leaves_unknown_placeholders_intact() -> None:
    rendered = templates.render("{{ROLE}} and {{something I do not know}}", {"ROLE": "backend"})
    assert rendered == "backend and {{something I do not know}}"


def test_find_placeholders_reports_one_based_lines() -> None:
    assert templates.find_placeholders("a\nb {{X}}\n") == [(2, "{{X}}")]


def test_write_if_absent_does_not_replace(tmp_path: Path) -> None:
    target = tmp_path / "plan.md"
    assert templates.write_if_absent(target, "first") is True
    assert templates.write_if_absent(target, "second") is False
    assert target.read_text(encoding="utf-8") == "first"


def test_write_if_changed_is_a_no_op_for_identical_content(tmp_path: Path) -> None:
    target = tmp_path / "PROTOCOL.md"
    assert templates.write_if_changed(target, "same") is True
    assert templates.write_if_changed(target, "same") is False
    assert templates.write_if_changed(target, "different") is True


def test_append_line_if_absent_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text("# Project\n\nRules.\n", encoding="utf-8")
    assert templates.append_line_if_absent(target, "@x", heading="## H") is True
    assert templates.append_line_if_absent(target, "@x", heading="## H") is False
    text = target.read_text(encoding="utf-8")
    assert text.count("@x") == 1
    assert text.count("## H") == 1
    assert "Rules." in text


def test_merge_gitignore_preserves_existing_entries(tmp_path: Path) -> None:
    target = tmp_path / ".gitignore"
    target.write_text("node_modules/\n", encoding="utf-8")
    assert templates.merge_gitignore(target, ["a", "b"]) is True
    assert templates.merge_gitignore(target, ["a"]) is False
    assert target.read_text(encoding="utf-8").splitlines() == ["node_modules/", "a", "b"]


def test_package_scaffold_adds_contracts_only_for_multiple_roles() -> None:
    single = templates.package_scaffold("en", ["backend"])
    multiple = templates.package_scaffold("en", ["backend", "frontend"])
    assert "contracts.md" not in single
    assert "contracts.md" in multiple
    assert "roles/backend.md" in single
    assert {"roles/backend.md", "roles/frontend.md"} <= set(multiple)


def test_package_scaffold_substitutes_the_role_name() -> None:
    scaffold = templates.package_scaffold("en", ["backend"])
    assert "backend" in scaffold["roles/backend.md"]
    assert "{{ROLE}}" not in scaffold["roles/backend.md"]


def test_an_unknown_template_name_is_a_usage_error() -> None:
    from wizrelay.errors import UsageError

    with pytest.raises(UsageError):
        templates.dev_template("en", "nope.md")
