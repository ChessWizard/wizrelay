"""Lock files and integrity."""

from __future__ import annotations

import json
from pathlib import Path

from wizrelay import lock


def test_crlf_and_lf_hash_identically(tmp_path: Path) -> None:
    # Without this, a Windows checkout of the hub and a macOS checkout of the same commit
    # would disagree on every digest and `sync` would report the package as corrupted.
    crlf = tmp_path / "crlf.md"
    lf = tmp_path / "lf.md"
    crlf.write_bytes(b"line one\r\nline two\r\n")
    lf.write_bytes(b"line one\nline two\n")
    assert lock.digest_file(crlf) == lock.digest_file(lf)


def test_crlf_normalisation_survives_a_chunk_boundary() -> None:
    # A chunk ending in \r followed by one starting with \n is still one line ending.
    payload = b"a" * 65535
    assert lock.digest_bytes(payload + b"\r\nz") == lock.digest_bytes(payload + b"\nz")


def test_build_omits_absent_optional_fields() -> None:
    document = lock.build(
        task_id="CU-1", folder="CU-1-x", version=2, files={}, pulled_at="2026-10-30T00:00:00+00:00"
    )
    assert "hub_commit" not in document
    assert "role" not in document
    assert document["schema_version"] == 1


def test_build_sorts_files_and_keeps_key_order_stable() -> None:
    document = lock.build(
        task_id="CU-1",
        folder="CU-1-x",
        version=1,
        files={"z.md": "f" * 64, "a.md": "e" * 64},
        pulled_at="2026-10-30T00:00:00+00:00",
        role="backend",
    )
    assert list(document["files"]) == ["a.md", "z.md"]
    assert list(document)[:3] == ["schema_version", "task_id", "folder"]


def test_serialize_matches_the_project_json_style() -> None:
    text = lock.serialize({"a": "ş"})
    assert text.endswith("\n")
    assert "ş" in text  # ensure_ascii=False
    assert '  "a"' in text  # indent=2


def test_load_returns_none_for_a_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / ".lock.json"
    path.write_text("{not json", encoding="utf-8")
    assert lock.load(path) is None
    assert lock.load(tmp_path / "absent.json") is None


def test_verify_detects_changed_missing_and_unlocked(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "kept.md").write_text("same\n", encoding="utf-8")
    (package / "changed.md").write_text("new\n", encoding="utf-8")
    (package / "extra.md").write_text("surprise\n", encoding="utf-8")

    document = {
        "files": {
            "kept.md": lock.digest_bytes(b"same\n"),
            "changed.md": lock.digest_bytes(b"old\n"),
            "gone.md": lock.digest_bytes(b"x\n"),
        }
    }
    report = lock.verify(package, document, present=["kept.md", "changed.md", "extra.md"])
    assert report.changed == ["changed.md"]
    assert report.missing == ["gone.md"]
    assert report.unlocked == ["extra.md"]
    assert report.clean is False
    assert bool(report) is True


def test_a_clean_report_is_falsy(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "a.md").write_text("x\n", encoding="utf-8")
    report = lock.verify(package, {"files": {"a.md": lock.digest_bytes(b"x\n")}}, present=["a.md"])
    assert report.clean is True
    assert bool(report) is False


def test_verify_without_present_does_not_report_unlocked(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "a.md").write_text("x\n", encoding="utf-8")
    report = lock.verify(package, {"files": {"a.md": lock.digest_bytes(b"x\n")}})
    assert report.unlocked == []


def test_diff_versions() -> None:
    old = {"files": {"a.md": "1" * 64, "b.md": "2" * 64}}
    new = {"files": {"a.md": "1" * 64, "b.md": "3" * 64, "c.md": "4" * 64}}
    assert lock.diff_versions(old, new) == (["c.md"], ["b.md"], [])
    assert lock.diff_versions(None, new) == (["a.md", "b.md", "c.md"], [], [])


def test_lock_round_trips_through_json() -> None:
    document = lock.build(
        task_id="CU-1",
        folder="CU-1-x",
        version=1,
        files={"a.md": "0" * 64},
        pulled_at="2026-10-30T00:00:00+00:00",
    )
    assert json.loads(lock.serialize(document)) == document
