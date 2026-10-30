# Privacy

wizrelay is a Claude Code plugin that runs entirely on the machine it is installed on.

**There is no wizrelay service.** The plugin has no backend, no account, no analytics and no
telemetry. It ships no HTTP client: the only network calls it makes are `git clone` and
`git fetch` against the repository you configured. Nothing is sent to the plugin's author,
and no data is received, processed or retained by anyone on the plugin's behalf.

## What it reads on your machine

- `.wizrelay/` in the repository you connected: the configuration, the repository profile,
  the task package and your own working files.
- The repository's git state: the current branch, `git status`, and the diff against the
  base reference. It never reads commit authors, names or email addresses.
- These environment variables and no others: `WIZRELAY_CACHE_DIR`, `WIZRELAY_DEBUG`,
  `WIZRELAY_PYTHON`, `WIZRELAY_TRACKERS_DIR`, `XDG_CACHE_HOME`, `LOCALAPPDATA`,
  `CLAUDE_PLUGIN_DATA`, `CLAUDE_MODEL` and `CLAUDE_CODE_SESSION_ID`. It never reads a
  credential, a token or a password, and it has no code that could.

## What it writes on your machine

- `.wizrelay/` in your repository, and two lines in `.gitignore`.
- A cache of the hub clone under your own cache directory.
- A lock file recording the task identifier, its title and version, the hub commit and a
  SHA-256 of each package file. It holds no personal data.

## Where anything leaves your machine

Two destinations, both services **you** configure:

| Destination | What goes there | When |
|---|---|---|
| Your hub repository | Reads over `git clone` and `git fetch`; a `git push` when a researcher publishes | `pull`, `sync`, `hub-publish` |
| Your issue tracker | One of four comment types: a published package, a question, an answer, a verification report | Only on `ask`, `verify` and `hub-publish`, and only after you approve the exact text |

The plugin declares no MCP server of its own. Your tracker is reached through the connector
you connect or through your own CLI. `wizrelay init --tracker clickup` can add ClickUp's
published MCP endpoint to your project's `.mcp.json`; for every other tracker it writes no
endpoint at all.

## Personal data

The plugin reads no personal data of its own accord. Where a tracker task or a research
package happens to contain a person's name, that text reaches your Claude Code session like
any other task content and is stored in your team's own repository. None of it reaches the
plugin's author.

## Children

wizrelay is a tool for software developers and is not directed at anyone under 18.

## Questions

Open an issue on [the repository](https://github.com/ChessWizard/wizrelay), or follow
[SECURITY.md](SECURITY.md) for anything that should not be public.
