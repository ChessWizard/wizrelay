"""Architecture invariants.

Three properties that are cheap to assert and expensive to lose
(the stdlib-only rule has its own file, `test_stdlib_only.py`):

* the core layer does no IO
* the layer graph points one way
* there are no circular imports
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent.parent / "plugin" / "lib" / "wizrelay"

#: `core` is pure; `services` may touch the filesystem and git; `entry`
#: holds the process entry points.
CORE = {
    "config",
    "errors",
    "globs",
    "i18n",
    "lock",
    "routing",
    "schemas",
    "textformats",
    "trackers",
}
SERVICES = {"audit", "context", "gitcmd", "hubrepo", "package", "paths", "templates"}
ENTRY = {"cli", "__main__"}

#: Modules the core may not import, because importing one means it can do IO.
IO_MODULES = {"subprocess", "socket", "urllib.request", "http.client", "shutil", "tempfile"}


def _modules() -> dict[str, ast.Module]:
    out: dict[str, ast.Module] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE)
        name = ".".join(relative.with_suffix("").parts)
        if name.endswith(".__init__"):
            name = name[: -len(".__init__")]
        out[name or "__init__"] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return out


MODULES = _modules()


def _absolute_imports(tree: ast.Module) -> set[str]:
    """Imports of modules outside this package.

    A relative import (`from . import x`, `from .hooks.common import y`) is our own code by
    definition, so it is excluded here and checked by the layer tests instead.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            found.add(node.module)
    return found


def _relative_imports(tree: ast.Module) -> set[str]:
    """Sibling modules this module imports, as bare module names.

    `from . import globs` yields `globs`; `from .hooks.common import x` yields
    `hooks.common`; `from . import SCHEMA_VERSION` yields nothing, because that is a value
    from the package `__init__`, not a module.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        if node.module:
            found.add(node.module)
            continue
        for alias in node.names:
            # `from . import globs` imports a module; `from . import SCHEMA_VERSION`
            # imports a constant. Only the former is a module name.
            if alias.name in MODULES:
                found.add(alias.name)
    return found


@pytest.mark.parametrize("name", sorted(CORE))
def test_core_modules_do_no_io(name: str) -> None:
    imported = _absolute_imports(MODULES[name])
    forbidden = {
        module
        for module in imported
        if module.split(".")[0] in {m.split(".")[0] for m in IO_MODULES}
    }
    # `pathlib` is allowed as a type: it appears in signatures. Importing `subprocess` or
    # opening a socket is what this test is about.
    assert not forbidden, f"{name} is a core module but imports {sorted(forbidden)}"


def test_core_does_not_import_a_service_or_an_entry_point() -> None:
    violations: list[str] = []
    for name in sorted(CORE):
        for imported in _relative_imports(MODULES[name]):
            top = imported.split(".")[0]
            if top in SERVICES or top in ENTRY:
                violations.append(f"{name} -> {imported}")
    assert not violations, "the layer graph points the wrong way: " + "; ".join(violations)


def test_services_do_not_import_an_entry_point() -> None:
    violations: list[str] = []
    for name in sorted(SERVICES):
        for imported in _relative_imports(MODULES[name]):
            if imported.split(".")[0] in ENTRY:
                violations.append(f"{name} -> {imported}")
    assert not violations, "; ".join(violations)


def test_every_module_is_assigned_to_a_layer() -> None:
    known = CORE | SERVICES | ENTRY
    actual = {name for name in MODULES if not name.startswith("hooks") and name not in {"__init__"}}
    assert actual == known, (
        f"unassigned: {sorted(actual - known)}; stale: {sorted(known - actual)}. "
        "Add the module to CORE, SERVICES or ENTRY."
    )


def test_no_circular_imports() -> None:
    """A real import, not a static analysis: a cycle raises on import."""
    import importlib

    for name in sorted(MODULES):
        module = f"wizrelay.{name}" if name != "__init__" else "wizrelay"
        importlib.import_module(module)


def test_no_forbidden_constructs() -> None:
    """No eval, exec, pickle, or shell=True."""
    offenders: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec"}:
                    offenders.append(f"{path.name}: {node.func.id}()")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = _absolute_imports(ast.Module(body=[node], type_ignores=[]))
                if any(n.split(".")[0] == "pickle" for n in names):
                    offenders.append(f"{path.name}: imports pickle")
            if isinstance(node, ast.keyword) and node.arg == "shell":
                if isinstance(node.value, ast.Constant) and node.value.value is True:
                    offenders.append(f"{path.name}: shell=True")
    assert not offenders, "; ".join(offenders)
