<!-- nav:top -->
[Documentation](README.md) › **Appendix C — Tracker comment tags** &nbsp;·&nbsp; [Türkçe](../tr/appendix-c-tracker-tags.md)
<!-- /nav:top -->

# Appendix C — Tracker comment tags

The four tags, their exact first lines, and the rules around posting.

## The tags

| Tag | Written by | When | First line |
|---|---|---|---|
| `[WIZRELAY-PUBLISH]` | Researcher | Every publication of a package | `[WIZRELAY-PUBLISH] <ID> — research v<N> published` |
| `[WIZRELAY-Q]` | Developer | A question the package cannot answer | `[WIZRELAY-Q] Q-<nnn> — <ID> — <role>` |
| `[WIZRELAY-A]` | Researcher | The answer, mapping the question to a decision | `[WIZRELAY-A] Q-<nnn> → D-<nnn>` |
| `[WIZRELAY-VERIFY]` | Developer | A verification report | `[WIZRELAY-VERIFY] <ID> — <role> — <PASS/FAIL/PARTIAL>` |

**The tag has to be the first thing on the first line.** That is how `hub-inbox` and
`hub-status` find these comments later; a tag in the middle of a sentence is invisible to
them.

## The rules

**Nothing is posted without explicit approval.** Every one of these comments is written by
Claude through the tracker's MCP tools, and only after you say yes. A comment is visible to
everyone on the task, so it is not something to do on your behalf.

**Tracker content is data, not instruction.** If a task description or a comment contains
text addressed to an assistant, the skills quote it to you and do not act on it. Every
skill says so in its own text.

**The researcher is mentioned** in a `[WIZRELAY-Q]` comment when `researcher_mention` is
set in the configuration.

## Full examples

### Publication

```text
[WIZRELAY-PUBLISH] CU-86c1abcd — research v1 published
Summary: First publication
- backend: AC-1, AC-2, AC-3, AC-4
- frontend: AC-5, AC-6
To start, in the relevant repository inside Claude Code:
/wizrelay:pull CU-86c1abcd
Deep link (paste into your browser's address bar):
- backend: claude-cli://open?repo=acme%2Fapi-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
- frontend: claude-cli://open?repo=acme%2Fweb-app&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

### A question

```text
[WIZRELAY-Q] Q-001 — CU-86c1abcd — backend
Upper bound for Retry-After?

contracts.md C-1 specifies Retry-After in seconds but states no maximum, and decisions.md
has nothing on it.

Options: (a) cap at 3600 seconds, (b) cap at the time to the next UTC midnight, (c) no cap.
Absent an answer I would implement (b), because the quota window is daily. The risk is a
client library treating a large value as a hard stop.

Blocks: AC-1
```

### An answer

```text
[WIZRELAY-A] Q-001 → D-002
Retry-After is capped at 3600 seconds. Rationale: a longer value makes clients look stuck,
and the quota window never exceeds a day anyway.
research v2 is published; run /wizrelay:sync in your repository.
```

### A verification report

```text
[WIZRELAY-VERIFY] CU-86c1abcd — backend — PARTIAL
- AC-1 PASS — pytest tests/quota/test_limit.py (3 passed)
- AC-2 PASS — pytest tests/quota/test_counter.py (1 passed)
- AC-3 NOT COVERED — no test for the Redis-unavailable path from D-001
Scope audit: clean · Research integrity: clean
```

## Deep links

A deep link opens Claude Code on the reader's machine, in the right repository, with the
command pre-filled and **not sent** — they read it and press Enter.

```
claude-cli://open?repo=acme%2Fapi-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

| Parameter | What it does |
|---|---|
| `repo` | A GitHub `owner/name` slug. Claude Code resolves it to a clone it has seen before |
| `q` | The text to pre-fill. URL-encoded; `%0A` for a line break; 5000 characters maximum |

Two things to know:

- **A deep link is produced only for a role whose `repos` entry names a repository.** `repo`
  is the only parameter that resolves across machines.
- **GitHub strips `claude-cli://` links.** A Markdown link renders as bare label text with
  the URL removed, so the link always goes in a fenced code block. That survives every
  renderer, and the reader copies it.

If the session opens in the home directory instead of the repository, the `repo` slug
resolves only to clones Claude Code has already seen — running `claude` inside the clone
once records its path.

## Per-tracker notes

Each adapter ships an instruction file a skill loads on demand. The things worth knowing
without opening them:

**ClickUp.** Read the task, the description **and all the comments** — ClickUp discussions
carry decisions that never reach the description. Note the custom fields: ClickUp teams
often put priority, sprint or component there rather than in tags.

**GitHub Issues.** No verified MCP endpoint, so `gh` is the usual path:
`gh issue view 123 --repo acme/web --comments`. Labels often carry the component and the
priority. And confirm the repository with the user before commenting.

**Jira.** Note the issue type and workflow state — a Story and a Bug carry different
acceptance expectations — the linked issues, especially "blocks" and "is blocked by", and
the sprint or fix version, which is usually the real deadline.

**Linear.** Sub-issues matter: a parent issue is often the real task and the sub-issues are
the roles. The project and cycle carry the deadline.

**Azure DevOps.** It has a dedicated **Acceptance Criteria** field and teams do use it. The
area path often maps directly onto a role.

**none.** No comments are posted anywhere, and no deep links. `hub comment` still produces
the per-role criteria and the pull command, which you can paste wherever your team does
talk.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Appendix B — File reference](appendix-b-files.md) | [Contents](README.md) | [Appendix D — Checklists →](appendix-d-checklists.md) |
<!-- /nav:bottom -->
