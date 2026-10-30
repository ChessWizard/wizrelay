# Security policy

## Supported versions

Security fixes land on the latest minor release. Older minors receive fixes only while
they are the newest release of a still-supported major version.

## Reporting a vulnerability

Report privately, never in a public issue:

1. **Preferred:** open a [GitHub private security advisory](https://github.com/ChessWizard/wizrelay/security/advisories/new).
2. **Alternative:** email `security@example.com` with `[wizrelay]` in the subject.

Please include the Claude Code version, the wizrelay version (`wizrelay doctor --json`),
the operating system, and the smallest set of steps that reproduces the problem.

Expect an acknowledgement within three working days and a fix or a mitigation plan within
fourteen days for a confirmed issue.

## Threat model

wizrelay is a **guardrail, not a jail**. The primary risk it
addresses is accidental scope drift, not a determined attacker with local shell access.

Known and accepted bypasses:

- Disabling the plugin or editing `.claude/settings.json`.
- Writing files from a subprocess (a Python or Node script) rather than through Claude's
  file tools. Claude Code's Read and Edit deny rules do not cover such a subprocess.
- Running Claude Code in `bypassPermissions` mode.

The layers that do not depend on the session behaving well are the CI gate
(`wizrelay audit` on the pull request) and managed settings deployed by an administrator.

## What is in scope

- A package file that escapes the target directory during `pull` (path traversal,
  symbolic links, absolute paths).
- A hub URL with embedded credentials being written to disk or logged.
- A hook that blocks a session permanently, or that fails open where the plan specifies
  fail-closed (`PreToolUse`).
- Secrets written to any file the plugin creates.
- Content from a tracker or a package being executed rather than treated as data.

## What is out of scope

- Operating-system sandboxing. Use Claude Code's own sandbox for that.
- A user with shell access choosing to edit protected files directly.
- Vulnerabilities in Claude Code itself. Report those to Anthropic.
