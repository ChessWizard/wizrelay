"""The runtime imports only the standard library.

A single third-party import in `plugin/lib/wizrelay/` breaks the plugin for anyone whose
Python does not happen to have that package, and nothing installs dependencies for a
plugin: Claude Code copies the directory and runs it.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
import sysconfig
from pathlib import Path
from typing import Optional

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


def _under(path: str, root: Optional[str]) -> bool:
    """True when `path` sits inside `root`, comparing the way the platform does."""
    if not root:
        return False
    prefix = os.path.normcase(os.path.realpath(root)) + os.sep
    return os.path.normcase(os.path.realpath(path)).startswith(prefix)


def _is_stdlib(name: str) -> bool:
    """Whether a top-level module name belongs to the standard library.

    `sys.stdlib_module_names` arrived in 3.10 and the floor here is 3.9, so on 3.9 the
    answer is worked out from where the module actually resolves. Asking the import system
    rather than listing a directory is what makes this portable: on POSIX an extension
    module such as `unicodedata` lives in `lib-dynload` under the stdlib directory, while
    on Windows it lives in `DLLs`, which is a sibling of `Lib` and outside every path
    `sysconfig` reports. Both are under `sys.base_prefix`, and site-packages is ruled out
    first because on some layouts it sits inside the stdlib directory.
    """
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return name in names

    if name in sys.builtin_module_names:
        return True
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return False
    if spec is None:
        return False
    origin = spec.origin
    if origin in (None, "built-in", "frozen"):
        return True
    paths = sysconfig.get_paths()
    if any(_under(origin, paths.get(key)) for key in ("purelib", "platlib")):
        return False
    return any(_under(origin, root) for root in (sys.base_prefix, sys.prefix))


def test_no_third_party_import_in_the_runtime() -> None:
    offenders: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for imported in _absolute_imports(ast.parse(path.read_text(encoding="utf-8"))):
            top = imported.split(".")[0]
            if top and top != "wizrelay" and not _is_stdlib(top):
                offenders.append(f"{path.relative_to(PACKAGE)} imports {imported}")
    assert not offenders, "the runtime must be stdlib-only: " + "; ".join(offenders)


def _runtime_imports() -> set[str]:
    found: set[str] = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        for name in _absolute_imports(ast.parse(path.read_text(encoding="utf-8"))):
            found.add(name.split(".")[0])
    found.discard("wizrelay")
    return found


def test_the_fallback_classifies_every_runtime_import_as_stdlib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the 3.9 branch on every version, so it cannot rot unnoticed.

    Only 3.9 takes it in CI. Without this test a mistake in the fallback would surface as a
    red 3.9 job months later, on one row of the matrix and one operating system — which is
    exactly how the `lib-dynload` version of this check reached Windows before it was
    caught.
    """
    monkeypatch.delattr(sys, "stdlib_module_names", raising=False)
    imported = _runtime_imports()
    assert imported, "the runtime imports nothing, which cannot be right"
    wrong = sorted(name for name in imported if not _is_stdlib(name))
    assert not wrong, f"the fallback would wrongly flag: {wrong}"


def test_the_fallback_does_not_depend_on_the_stdlib_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Windows failure in one sentence, locked so it cannot come back.

    `unicodedata` is an extension module. On POSIX it sits in `lib-dynload` under the
    directory `sysconfig` calls `stdlib`; on Windows it sits in `DLLs`, outside every path
    `sysconfig` reports. A check that reads those paths therefore passes on three platforms
    and fails on the fourth. Blanking them here proves this one does not read them.
    """
    monkeypatch.delattr(sys, "stdlib_module_names", raising=False)
    real = sysconfig.get_paths()
    blanked = dict(real, stdlib="/nowhere/stdlib", platstdlib="/nowhere/platstdlib")
    monkeypatch.setattr(sysconfig, "get_paths", lambda *a, **k: blanked)

    assert _is_stdlib("unicodedata"), "an extension module must still count as stdlib"
    assert _is_stdlib("json"), "a pure-Python stdlib module must still count as stdlib"
    assert not _is_stdlib("pytest"), "site-packages must still be ruled out"


def test_the_fallback_still_rejects_a_third_party_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fallback that answers "stdlib" to everything would pass the test above silently."""
    monkeypatch.delattr(sys, "stdlib_module_names", raising=False)
    assert not _is_stdlib("pytest"), "an installed package must not count as stdlib"
    assert not _is_stdlib("a_package_that_does_not_exist_anywhere")


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
