"""Package discovery, classification and safe copying."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from wizrelay import package
from wizrelay.errors import UsageError, ValidationError


@pytest.mark.parametrize(
    ("relative", "kind"),
    [
        ("task.json", package.RESEARCHER),
        ("research.md", package.RESEARCHER),
        ("roles/backend.md", package.RESEARCHER),
        ("diagrams/flow.png", package.RESEARCHER),
        ("extra-analysis.md", package.RESEARCHER),
        ("plan.md", package.DEVELOPER),
        ("questions.md", package.DEVELOPER),
        ("verification.md", package.DEVELOPER),
        ("notes/scratch.md", package.DEVELOPER),
        ("notes/deep/thought.md", package.DEVELOPER),
        (".validation.md", package.PRIVATE),
        (".lock.json", package.PRIVATE),
        (".notes/private.md", package.PRIVATE),
        ("roles/.hidden.md", package.PRIVATE),
        ("", package.PRIVATE),
    ],
)
def test_classification(relative: str, kind: str) -> None:
    assert package.classify(relative) == kind


def test_a_developer_file_in_a_subdirectory_is_researcher_owned() -> None:
    # `plan.md` at the root is the developer's; `docs/plan.md` is part of the analysis.
    assert package.classify("docs/plan.md") == package.RESEARCHER


def _package(root: Path, name: str = "CU-1-x") -> Path:
    directory = root / "tasks" / name
    (directory / "roles").mkdir(parents=True)
    (directory / "task.json").write_text('{"id": "CU-1"}', encoding="utf-8")
    (directory / "research.md").write_text("r\n", encoding="utf-8")
    (directory / "roles" / "backend.md").write_text("b\n", encoding="utf-8")
    (directory / ".validation.md").write_text("private\n", encoding="utf-8")
    (directory / "plan.md").write_text("hub's own plan\n", encoding="utf-8")
    return directory


def test_find_package_by_canonical_id_raw_ref_and_folder(tmp_path: Path) -> None:
    """Appendix B2 #2."""
    _package(tmp_path, "CU-86c1abcd-quota")
    tasks = tmp_path / "tasks"
    for kwargs in (
        {"canonical_id": "CU-86c1abcd"},
        {"raw_ref": "86c1abcd"},
        {"folder": "CU-86c1abcd-quota"},
    ):
        assert package.find_package(tasks, **kwargs).name == "CU-86c1abcd-quota"


def test_find_package_rejects_an_ambiguous_reference(tmp_path: Path) -> None:
    _package(tmp_path, "CU-1-alpha")
    _package(tmp_path, "CU-1-beta")
    with pytest.raises(UsageError) as excinfo:
        package.find_package(tmp_path / "tasks", canonical_id="CU-1")
    assert "more than one" in str(excinfo.value)


def test_find_package_reports_an_empty_hub(tmp_path: Path) -> None:
    (tmp_path / "tasks").mkdir()
    with pytest.raises(UsageError):
        package.find_package(tmp_path / "tasks", canonical_id="CU-1")


def test_list_packages_skips_dotted_and_unsafe_names(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "CU-1-ok").mkdir()
    (tasks / ".hidden").mkdir()
    (tasks / "with space").mkdir()
    assert [p.name for p in package.list_packages(tasks)] == ["CU-1-ok"]


def test_plan_copy_skips_private_and_developer_files(tmp_path: Path) -> None:
    source = _package(tmp_path)
    plan = package.plan_copy(source)
    assert plan.ok
    assert sorted(plan.files) == ["research.md", "roles/backend.md", "task.json"]
    skipped = dict(plan.skipped)
    assert skipped[".validation.md"] == "private to the hub"
    assert skipped["plan.md"] == "developer-owned"


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges")
def test_a_symbolic_link_is_refused_by_name(tmp_path: Path) -> None:
    source = _package(tmp_path)
    (source / "link.md").symlink_to(source / "research.md")
    plan = package.plan_copy(source)
    assert plan.ok is False
    assert ("link.md", "symbolic link") in plan.refused


def test_an_oversized_file_is_refused_by_name(tmp_path: Path) -> None:
    source = _package(tmp_path)
    (source / "huge.bin").write_bytes(b"0" * (package.MAX_FILE_BYTES + 1))
    plan = package.plan_copy(source)
    assert plan.ok is False
    assert any(name == "huge.bin" for name, _reason in plan.refused)
    assert any("file limit" in reason for _name, reason in plan.refused)


def test_copy_refuses_rather_than_half_copying(tmp_path: Path) -> None:
    source = _package(tmp_path)
    (source / "huge.bin").write_bytes(b"0" * (package.MAX_FILE_BYTES + 1))
    destination = tmp_path / "dev" / "CU-1-x"
    with pytest.raises(ValidationError) as excinfo:
        package.copy_package(source, destination)
    assert "huge.bin" in str(excinfo.value)
    assert not (destination / "research.md").exists()


def test_copy_preserves_a_developer_file(tmp_path: Path) -> None:
    """Invariant I9."""
    source = _package(tmp_path)
    destination = tmp_path / "dev" / "CU-1-x"
    destination.mkdir(parents=True)
    (destination / "plan.md").write_text("MY plan\n", encoding="utf-8")

    package.copy_package(source, destination)
    assert (destination / "plan.md").read_text(encoding="utf-8") == "MY plan\n"
    assert not (destination / ".validation.md").exists()


def test_copy_removes_a_file_deleted_in_the_hub(tmp_path: Path) -> None:
    """Appendix B2 #6."""
    source = _package(tmp_path)
    destination = tmp_path / "dev" / "CU-1-x"
    package.copy_package(source, destination)
    assert (destination / "roles" / "backend.md").exists()

    (source / "roles" / "backend.md").unlink()
    _digests, removed = package.copy_package(source, destination)
    assert removed == ["roles/backend.md"]
    assert not (destination / "roles" / "backend.md").exists()
    # The emptied directory is cleaned up too.
    assert not (destination / "roles").exists()


def test_copy_returns_digests_for_every_copied_file(tmp_path: Path) -> None:
    source = _package(tmp_path)
    destination = tmp_path / "dev" / "CU-1-x"
    digests, _removed = package.copy_package(source, destination)
    assert set(digests) == {"research.md", "roles/backend.md", "task.json"}
    assert all(len(value) == 64 for value in digests.values())


def test_read_task_names_the_file_on_a_syntax_error(tmp_path: Path) -> None:
    directory = tmp_path / "pkg"
    directory.mkdir()
    (directory / "task.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(ValidationError) as excinfo:
        package.read_task(directory)
    assert "task.json" in str(excinfo.value)


def test_read_task_explains_a_missing_file(tmp_path: Path) -> None:
    directory = tmp_path / "pkg"
    directory.mkdir()
    with pytest.raises(UsageError) as excinfo:
        package.read_task(directory)
    assert "hub new" in (excinfo.value.remedy or "")


def test_write_task_uses_the_project_json_style(tmp_path: Path) -> None:
    directory = tmp_path / "pkg"
    directory.mkdir()
    package.write_task(directory, {"title": "kotası"})
    text = (directory / "task.json").read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "kotası" in text


def test_a_new_task_document_is_deliberately_unpublishable(tmp_path: Path) -> None:
    document = package.new_task_document(
        canonical_id="CU-1", ref="1", title="T", roles=["backend"], tracker_type="clickup"
    )
    assert document["status"] == "draft"
    assert document["version"] == 0
    # A placeholder in the scope is what makes `hub validate` fail until a person fills
    # it in.
    assert "{{" in document["scope"]["backend"]["allow"][0]


def test_find_by_branch_strips_a_refs_prefix(tmp_path: Path) -> None:
    """Task 2.10."""
    _package(tmp_path, "CU-86c1abcd-quota")
    tasks = tmp_path / "tasks"
    for branch in (
        "feature/CU-86c1abcd-quota",
        "refs/heads/feature/CU-86c1abcd-x",
        "fix/cu-86c1abcd",
        "CU-86c1abcd",
    ):
        found = package.find_by_branch(tasks, branch)
        assert found is not None and found.name == "CU-86c1abcd-quota", branch


def test_find_by_branch_returns_none_for_an_unrelated_branch(tmp_path: Path) -> None:
    _package(tmp_path, "CU-86c1abcd-quota")
    assert package.find_by_branch(tmp_path / "tasks", "chore/bump-deps") is None
    assert package.find_by_branch(tmp_path / "tasks", "") is None


def test_resolve_active_prefers_the_pointer(tmp_path: Path) -> None:
    """Appendix B2 #8."""
    _package(tmp_path, "CU-1-alpha")
    _package(tmp_path, "CU-2-beta")
    tasks = tmp_path / "tasks"
    pointer = tmp_path / ".active-task"
    pointer.write_text("CU-2-beta\n", encoding="utf-8")

    found, source = package.resolve_active(tasks, pointer=pointer, branch="feature/CU-1-x")
    assert found is not None and found.name == "CU-2-beta"
    assert source == "pointer"


def test_resolve_active_falls_back_to_the_branch(tmp_path: Path) -> None:
    _package(tmp_path, "CU-1-alpha")
    tasks = tmp_path / "tasks"
    found, source = package.resolve_active(tasks, pointer=None, branch="feature/CU-1-alpha")
    assert found is not None and found.name == "CU-1-alpha"
    assert source == "branch"


def test_resolve_active_ignores_a_stale_pointer(tmp_path: Path) -> None:
    _package(tmp_path, "CU-1-alpha")
    tasks = tmp_path / "tasks"
    pointer = tmp_path / ".active-task"
    pointer.write_text("CU-9-gone\n", encoding="utf-8")
    found, source = package.resolve_active(tasks, pointer=pointer, branch="feature/CU-1-alpha")
    assert found is not None and found.name == "CU-1-alpha"
    assert source == "branch"


def test_resolve_active_reports_nothing_found(tmp_path: Path) -> None:
    (tmp_path / "tasks").mkdir()
    assert package.resolve_active(tmp_path / "tasks") == (None, "none")


def test_researcher_files_is_sorted_and_excludes_others(tmp_path: Path) -> None:
    directory = _package(tmp_path)
    assert package.researcher_files(directory) == [
        "research.md",
        "roles/backend.md",
        "task.json",
    ]


def test_scaffold_names(tmp_path: Path) -> None:
    folder, slug = package.scaffold_names("CU-1", "Tenant bazlı kota")
    assert folder == "CU-1-tenant-bazli-kota"
    assert slug == "tenant-bazli-kota"
