"""What the runtime reads from the environment, and what it must never read.

The plugin's central privacy claim is that it reads no credential: no token, no key, no
password, no `.netrc`, no keychain, no credential helper. `PRIVACY.md` and the plugin's
`README.md` both state it, and a directory security scan asks for it to be demonstrated
rather than asserted — a scan can see that the code handles URLs containing `user:token@`
and cannot tell, on its own, that the handling is a *rejection*.

Prose cannot hold that claim. One `os.environ.get("GITHUB_TOKEN")` added in a hurry would
make both documents false and nothing would fail. So the claim is pinned here, from four
directions:

* the set of environment variables the runtime reads is exactly the documented set
* every one of those reads names its variable as a **literal**, so the set above is the
  whole set and cannot be widened at run time
* no variable read anywhere is credential-shaped
* the runtime imports no network client, so there is nowhere for a credential to go even
  if one were read

The fourth is the one that turns the first three into a guarantee rather than a promise:
`urllib.parse` builds the deep link in a tracker comment and is pure string work, but
`urllib.request`, `http.client` or a bare socket would be an outbound channel, and the
package is specified to have none (every outbound call is `git`, which authenticates with
the user's own git configuration exactly as it does when they run it themselves).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
PACKAGE = REPO / "plugin" / "lib" / "wizrelay"
LAUNCHER = REPO / "plugin" / "bin" / "wizrelay"

RUNTIME_VARIABLES = frozenset(
    {
        "WIZRELAY_CACHE_DIR",
        "WIZRELAY_DEBUG",
        "WIZRELAY_TRACKERS_DIR",
        "XDG_CACHE_HOME",
        "LOCALAPPDATA",
        "CLAUDE_PLUGIN_DATA",
        "CLAUDE_MODEL",
        "CLAUDE_CODE_SESSION_ID",
    }
)

LAUNCHER_VARIABLES = frozenset({"WIZRELAY_PYTHON"})

DOCUMENTED_VARIABLES = RUNTIME_VARIABLES | LAUNCHER_VARIABLES

CREDENTIAL_SHAPED = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "APIKEY",
    "API_KEY",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "NETRC",
    "KEYCHAIN",
    "SSH_",
    "GH_",
    "GITHUB_",
    "AUTH",
)

NETWORK_MODULES = (
    "urllib.request",
    "urllib.error",
    "http.client",
    "http.server",
    "socket",
    "ssl",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "xmlrpc",
    "webbrowser",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
)

_ENV_IN_DOCS = re.compile(r"`((?:WIZRELAY|CLAUDE)_[A-Z0-9_]+)`")


def _runtime_modules() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def _is_environ_read(node: ast.AST) -> bool:
    """Whether `node` is an `os.environ.get(...)` or `os.getenv(...)` call."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr == "getenv":
        return True
    if func.attr != "get":
        return False
    return isinstance(func.value, ast.Attribute) and func.value.attr == "environ"


def _environ_reads(tree: ast.Module) -> list[tuple[int, ast.AST]]:
    """Every environment read in a module, as `(line, first argument or None)`."""
    found: list[tuple[int, ast.AST]] = []
    for node in ast.walk(tree):
        if _is_environ_read(node):
            first = node.args[0] if node.args else None
            found.append((node.lineno, first))
        elif isinstance(node, ast.Subscript):
            value = node.value
            if isinstance(value, ast.Attribute) and value.attr == "environ":
                found.append((node.lineno, node.slice))
    return found


def _read_names() -> set:
    names: set = set()
    for path in _runtime_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for _line, argument in _environ_reads(tree):
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                names.add(argument.value)
    return names


def test_the_runtime_reads_only_the_documented_environment_variables() -> None:
    found = _read_names()
    assert found == set(RUNTIME_VARIABLES), (
        "the environment surface changed; update PRIVACY.md, plugin/README.md and "
        f"RUNTIME_VARIABLES together.\n  added: {sorted(found - RUNTIME_VARIABLES)}\n"
        f"  gone:  {sorted(set(RUNTIME_VARIABLES) - found)}"
    )


def test_every_environment_read_names_its_variable_as_a_literal() -> None:
    """A computed name would make the set above a sample rather than the whole surface."""
    offenders: list[str] = []
    for path in _runtime_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for line, argument in _environ_reads(tree):
            if argument is None:
                offenders.append(f"{path.relative_to(PACKAGE)}:{line}: no variable named")
            elif not (isinstance(argument, ast.Constant) and isinstance(argument.value, str)):
                offenders.append(
                    f"{path.relative_to(PACKAGE)}:{line}: the variable name is computed"
                )
    assert not offenders, "every environment read must name a literal: " + "; ".join(offenders)


def test_no_environment_variable_read_is_credential_shaped() -> None:
    offenders = sorted(
        name
        for name in _read_names() | set(LAUNCHER_VARIABLES)
        if any(marker in name.upper() for marker in CREDENTIAL_SHAPED)
    )
    assert not offenders, f"credential-shaped environment reads: {offenders}"


def test_the_runtime_imports_no_network_client() -> None:
    """Every outbound call is `git`. There is no second channel, by construction."""
    offenders: list[str] = []
    for path in _runtime_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                for blocked in NETWORK_MODULES:
                    if name == blocked or name.startswith(blocked + "."):
                        offenders.append(
                            f"{path.relative_to(PACKAGE)}:{node.lineno}: imports {name}"
                        )
    assert not offenders, "the runtime must have no network client: " + "; ".join(offenders)


def test_the_launcher_reads_only_its_own_interpreter_override() -> None:
    """`bin/wizrelay` selects the interpreter, so it reads the environment before Python.

    A variable the script assigns itself is a local, not an environment read, so those are
    subtracted. What remains is what the launcher takes from the caller's environment, and
    the documented override is the only thing it may take.
    """
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "WIZRELAY_PYTHON" in text, "the documented interpreter override is gone"

    assigned = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", text, re.MULTILINE))
    referenced = set(re.findall(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", text))
    from_environment = referenced - assigned

    unexpected = sorted(from_environment - DOCUMENTED_VARIABLES)
    assert not unexpected, f"the launcher reads undocumented variables: {unexpected}"


@pytest.mark.parametrize("relative", ["PRIVACY.md", "plugin/README.md"])
def test_the_documentation_lists_exactly_the_variables_that_are_read(relative: str) -> None:
    """Both documents make the claim, so both have to stay true as the code changes."""
    text = (REPO / relative).read_text(encoding="utf-8")

    prefixed = {name for name in _ENV_IN_DOCS.findall(text)}
    expected = {name for name in DOCUMENTED_VARIABLES if name.startswith(("WIZRELAY_", "CLAUDE_"))}
    assert prefixed == expected, (
        f"{relative} lists the wrong WIZRELAY_/CLAUDE_ variables.\n"
        f"  listed but not read: {sorted(prefixed - expected)}\n"
        f"  read but not listed: {sorted(expected - prefixed)}"
    )

    for name in ("XDG_CACHE_HOME", "LOCALAPPDATA"):
        assert f"`{name}`" in text, f"{relative} does not mention {name}"


CREDENTIAL_BEARING_MCP_KEYS = (
    "env",
    "headers",
    "headersHelper",
    "token",
    "apiKey",
    "api_key",
    "authorization",
)


def test_no_tracker_descriptor_declares_a_credential_bearing_field() -> None:
    """A tracker descriptor is the only place an MCP entry is described.

    `wizrelay init --tracker <type>` can write that entry into the project's `.mcp.json`,
    so a credential-bearing field here would become a credential-bearing field in the
    user's configuration. None of the six descriptors has one, and this keeps it that way.
    """
    offenders: list = []
    for path in sorted((REPO / "plugin" / "trackers").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        mcp = document.get("mcp") or {}
        for key in CREDENTIAL_BEARING_MCP_KEYS:
            if key in mcp:
                offenders.append(f"{path.name}: mcp.{key}")
    assert not offenders, f"a tracker descriptor would forward a credential: {offenders}"


def test_a_written_mcp_entry_can_carry_no_credential() -> None:
    """Whatever a descriptor says, only a fixed key list reaches `.mcp.json`.

    `trackers.mcp_server_config` copies `type`, `url`, `command`, `args` and `headers` and
    nothing else, so an `env` block added to a descriptor by mistake could not reach the
    user's configuration. This asserts the output rather than the copy list, so the
    guarantee survives a refactor of either.
    """
    from wizrelay import trackers

    for tracker_type in trackers.available():
        entry = trackers.mcp_server_config(tracker_type)
        if entry is None:
            continue
        for name, fields in entry.items():
            present = sorted(set(fields) & set(CREDENTIAL_BEARING_MCP_KEYS))
            assert not present, f"{tracker_type} would write {name} with {present}"


def test_the_runtime_never_reads_a_credential_file() -> None:
    """The names of the files a credential would live in, as a last backstop."""
    forbidden = (".netrc", "_netrc", ".git-credentials", "id_rsa", "id_ed25519")
    offenders: list[str] = []
    for path in _runtime_modules():
        text = path.read_text(encoding="utf-8")
        for name in forbidden:
            if name in text:
                offenders.append(f"{path.relative_to(PACKAGE)} mentions {name}")
    assert not offenders, "the runtime must not touch a credential file: " + "; ".join(offenders)
