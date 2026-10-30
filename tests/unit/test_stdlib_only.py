"""The runtime imports only the standard library.

A single third-party import in `plugin/lib/wizrelay/` breaks the plugin for anyone whose
Python does not happen to have that package, and nothing installs dependencies for a
plugin: Claude Code copies the directory and runs it.
"""

from __future__ import annotations

import ast
import sys
import sysconfig
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent.parent / "plugin" / "lib" / "wizrelay"


def _absolute_imports(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            found.add(node.module)
    return found


def _stdlib_names() -> set[str]:
    """The top-level module names the standard library provides.

    `sys.stdlib_module_names` arrived in 3.10 and the floor here is 3.9, so on 3.9 the set
    is derived instead: the interpreter's built-ins, plus every top-level module and
    package that lives in the standard library directory. Both branches run in CI, because
    the matrix covers 3.9 as well as 3.12 and 3.13.
    """
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return set(names)

    found = set(sys.builtin_module_names)
    for key in ("stdlib", "platstdlib"):
        root = sysconfig.get_paths().get(key)
        if not root:
            continue
        directory = Path(root)
        if not directory.is_dir():
            continue
        for entry in directory.iterdir():
            if entry.suffix == ".py":
                found.add(entry.stem)
            elif entry.is_dir() and (entry / "__init__.py").exists():
                found.add(entry.name)
        # Extension modules are not importable as files: `_socket`, `math` and friends.
        dynload = directory / "lib-dynload"
        if dynload.is_dir():
            found.update(entry.name.split(".")[0] for entry in dynload.iterdir())
    return found


def test_no_third_party_import_in_the_runtime() -> None:
    stdlib = _stdlib_names()
    offenders: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for imported in _absolute_imports(ast.parse(path.read_text(encoding="utf-8"))):
            top = imported.split(".")[0]
            if top and top not in stdlib and top != "wizrelay":
                offenders.append(f"{path.relative_to(PACKAGE)} imports {imported}")
    assert not offenders, "the runtime must be stdlib-only: " + "; ".join(offenders)


def test_the_derived_stdlib_set_covers_what_the_runtime_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the 3.9 branch on every version, so it cannot rot unnoticed.

    Only 3.9 takes it in CI. Without this test a mistake in the fallback would surface as
    a red 3.9 job months later, and only on that one row of the matrix.
    """
    monkeypatch.delattr(sys, "stdlib_module_names", raising=False)
    derived = _stdlib_names()

    imported: set[str] = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        for name in _absolute_imports(ast.parse(path.read_text(encoding="utf-8"))):
            imported.add(name.split(".")[0])
    imported.discard("wizrelay")

    assert imported, "the runtime imports nothing, which cannot be right"
    missing = sorted(name for name in imported if name not in derived)
    assert not missing, f"the derived set would wrongly flag: {missing}"


def test_the_distribution_declares_no_runtime_dependencies() -> None:
    pyproject = (PACKAGE.parent.parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject, "pyproject.toml must declare no runtime dependencies"


def test_the_launcher_needs_no_installed_package() -> None:
    launcher = PACKAGE.parent.parent / "bin" / "wizrelay.py"
    assert "sys.path.insert" in launcher.read_text(encoding="utf-8")


def test_every_runtime_module_postpones_annotation_evaluation() -> None:
    """`from __future__ import annotations` is what makes modern annotations 3.9-safe.

    With it, `dict[str, int]` and `X | Y` inside an annotation are strings at runtime and
    never evaluated, so they work on 3.9. Without it, either one raises on import.
    """
    missing: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "from __future__ import annotations" not in text:
            missing.append(str(path.relative_to(PACKAGE)))
    assert not missing, f"missing the future import: {missing}"


def test_no_python_310_only_syntax_in_the_runtime() -> None:
    """The floor is Python 3.9, and mypy can no longer target it.

    Two constructs the future import does **not** rescue:

    * a `match` statement, which is a syntax error on 3.9
    * a PEP 604 union in a position that is evaluated, such as a type alias or a `cast`
    """
    offenders: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if type(node).__name__ == "Match":
                offenders.append(f"{path.relative_to(PACKAGE)}: match statement")
            # A module-level or class-level assignment whose value is a `X | Y` expression
            # is a type alias, and it is evaluated at import time.
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if isinstance(value, ast.BinOp) and isinstance(value.op, ast.BitOr):
                    if isinstance(value.left, (ast.Name, ast.Subscript, ast.Attribute)):
                        offenders.append(
                            f"{path.relative_to(PACKAGE)}:{node.lineno}: "
                            "a PEP 604 union in an evaluated position"
                        )
    assert not offenders, "3.10-only syntax in the runtime: " + "; ".join(offenders)
