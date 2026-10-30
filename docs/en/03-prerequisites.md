<!-- nav:top -->
[Documentation](README.md) › **3. Prerequisites** &nbsp;·&nbsp; [Türkçe](../tr/03-prerequisites.md)
<!-- /nav:top -->

# Prerequisites

What each person needs before anything is installed, and how to check it.

## The list

| Requirement | Who needs it | How to check |
|---|---|---|
| Claude Code ≥ v2.1.295 | Everybody | `claude --version` · upgrade with `claude update` |
| Python ≥ 3.9, with `python3` on `PATH` | Everybody | `python3 --version` |
| git | Everybody | `git --version` |
| Access to the hub repository | Researcher: write · Developer: read | `git ls-remote <hub-url>` |
| A tracker account and MCP authorisation | The researcher, and any developer who will post questions or reports | `/mcp` in Claude Code shows it connected |
| Model access | Everybody | Opus and Sonnet both appear in the `/model` picker |

## Things worth knowing before you start

### Which Claude

The plugin is for **Claude Code**: the terminal, the VS Code and JetBrains extensions, or
the desktop app's Code tab. It does not work in the claude.ai chat interface, and it is not
installable on claude.ai or in Cowork — the plugin ships a `bin/` directory, which those
surfaces refuse, and the hooks that do the enforcing do not exist there.

### `python3` is not optional

The hooks run as `python3 <script>`. Without a resolvable `python3`, **the hooks do not run
at all** — and that means scope protection is silently absent while every command still
appears to work.

`wizrelay doctor` reports this as an **error**, not a warning, for exactly that reason. See
[16. Troubleshooting](16-troubleshooting.md) if it fires.

### Windows

Install Git for Windows, so Git Bash is available, and make sure `python3` resolves there.
A PowerShell-only environment is best-effort in v1: the plugin's commands work, but the
hooks do not, because a hook in exec form needs a real executable and a shell script is not
one on Windows.

### Models and billing

- **Fable** is optional and on some plans is billed from usage credit. The default routing
  policy never selects it; a researcher can choose it explicitly with an override.
- **Advisor** is experimental and works only on the Anthropic API. If you run Claude Code
  on Amazon Bedrock, Google Cloud's Agent Platform or Microsoft Foundry, drop the
  `--advisor` part from any launch command the plugin suggests.

### Trust the folder

Claude Code asks you to trust a folder the first time you open it. **Project settings and
the plugin suggestion only take effect after that**, so a repository that looks like it is
not connected often just has an unanswered trust prompt.

## A five-minute check

Run these before you set anything up. All four should succeed:

```bash
claude --version          # ≥ 2.1.295
python3 --version         # ≥ 3.9
git --version
git ls-remote <hub-url>   # your hub, once it exists
```

And inside a Claude Code session:

```
/mcp        # your tracker, connected
/model      # Opus and Sonnet both listed
```

## Next

[4. Install the plugin](04-install-plugin.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 2. What it does and does not do](02-scope.md) | [Contents](README.md) | [4. Install the plugin →](04-install-plugin.md) |
<!-- /nav:bottom -->
