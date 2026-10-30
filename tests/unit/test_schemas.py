"""Schema validation.

Three things are asserted here, and the third is the one that matters most:

1. every valid fixture passes the stdlib validator
2. every invalid fixture fails it, with the offending **field path** in the message
3. the stdlib validator and the JSON Schema files in `schemas/` **agree** on every fixture

Two implementations of one contract drift silently unless something compares them. The
runtime cannot import `jsonschema`, so the comparison lives in the test
suite, where `jsonschema` is a development dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wizrelay import schemas

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "schemas"
SCHEMA_DIR = REPO_ROOT / "schemas"

EXPECTATIONS: dict[str, str] = json.loads(
    (FIXTURES / "expectations.json").read_text(encoding="utf-8")
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_name(path: Path) -> str:
    """`task.bad-status.json` and `task.json` both name the `task` schema."""
    return path.name.split(".")[0]


VALID_FILES = sorted((FIXTURES / "valid").glob("*.json"))
INVALID_FILES = sorted((FIXTURES / "invalid").glob("*.json"))


def _json_schema_errors(document: Any, name: str) -> list[str]:
    """Validate with `jsonschema`, returning one message per error with its path."""
    import jsonschema

    schema = _load(SCHEMA_DIR / f"{name}.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    out: list[str] = []
    for error in validator.iter_errors(document):
        path = ".".join(str(part) for part in error.absolute_path)
        out.append(f"{path or '<root>'}: {error.message}")
    return out


# --------------------------------------------------------------------------------------
# Coverage of the acceptance criterion itself
# --------------------------------------------------------------------------------------


def test_every_schema_has_a_valid_fixture() -> None:
    covered = {_schema_name(p) for p in VALID_FILES}
    assert covered == set(schemas.SCHEMAS), (
        f"missing valid fixtures for {sorted(set(schemas.SCHEMAS) - covered)}"
    )


def test_every_schema_has_at_least_five_invalid_fixtures() -> None:
    counts: dict[str, int] = {}
    for path in INVALID_FILES:
        counts[_schema_name(path)] = counts.get(_schema_name(path), 0) + 1
    thin = {name: counts.get(name, 0) for name in schemas.SCHEMAS if counts.get(name, 0) < 5}
    assert not thin, f"each schema needs at least five invalid fixtures; thin: {thin}"


def test_every_json_schema_file_has_a_runtime_counterpart() -> None:
    on_disk = {p.name.replace(".schema.json", "") for p in SCHEMA_DIR.glob("*.schema.json")}
    assert on_disk == set(schemas.SCHEMAS)


def test_every_invalid_fixture_has_an_expectation() -> None:
    names = {p.name for p in INVALID_FILES}
    assert names == set(EXPECTATIONS)


# --------------------------------------------------------------------------------------
# The stdlib validator
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", VALID_FILES, ids=lambda p: p.name)
def test_valid_fixture_passes_stdlib_validator(path: Path) -> None:
    assert schemas.validate(_load(path), _schema_name(path)) == []


@pytest.mark.parametrize("path", INVALID_FILES, ids=lambda p: p.name)
def test_invalid_fixture_fails_with_the_field_path(path: Path) -> None:
    issues = schemas.validate(_load(path), _schema_name(path))
    assert issues, f"{path.name} was expected to fail validation"
    expected = EXPECTATIONS[path.name]
    joined = "\n".join(issues)
    assert expected in joined, f"{path.name}: no issue names {expected!r}.\nIssues were:\n{joined}"


def test_validate_or_raise_carries_the_issues() -> None:
    with pytest.raises(schemas.SchemaError) as excinfo:
        schemas.validate_or_raise({"schema_version": 1}, "task")
    assert excinfo.value.issues
    assert excinfo.value.code == 1  # a validation failure, not a usage error


def test_unknown_schema_name_raises() -> None:
    with pytest.raises(KeyError):
        schemas.validate({}, "nope")


def test_comment_keys_are_ignored() -> None:
    document = _load(FIXTURES / "valid" / "config.json")
    document["_note"] = "a comment"
    assert schemas.validate(document, "config") == []


def test_a_boolean_is_not_an_integer() -> None:
    # `bool` subclasses `int` in Python; JSON does not agree, and neither does the schema.
    assert schemas.validate({"schema_version": True}, "config")


# --------------------------------------------------------------------------------------
# Equivalence: the two validators must agree
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", VALID_FILES + INVALID_FILES, ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_both_validators_agree(path: Path) -> None:
    name = _schema_name(path)
    document = _load(path)
    stdlib_ok = not schemas.validate(document, name)
    json_schema_ok = not _json_schema_errors(document, name)
    assert stdlib_ok == json_schema_ok, (
        f"{path.name}: stdlib says {'valid' if stdlib_ok else 'invalid'} but the JSON "
        f"Schema in schemas/{name}.schema.json says "
        f"{'valid' if json_schema_ok else 'invalid'}. The two implementations have drifted."
    )


def test_known_keys_exposes_top_level_properties() -> None:
    keys = set(schemas.known_keys("config"))
    assert {"hub", "role", "tracker", "language"} <= keys
