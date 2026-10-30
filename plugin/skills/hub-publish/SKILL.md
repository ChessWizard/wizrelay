---
name: hub-publish
description: Publish a validated research package: bump the version, commit, and announce it on the tracker.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
argument-hint: "<task reference>"
---

Publish a package so developers can pull it.

**Push only with the user's explicit approval**, and post the tracker comment only with
their explicit approval. These are the two outward-facing actions in this workflow, and
both are visible to the whole team.

**Never edit a published package in place.** A developer's lock file records the hashes of
what they pulled; changing a published file makes their copy look corrupted. Edit, then
publish a new version.

## 1. Prepare

```
wizrelay hub publish-prep $ARGUMENTS --summary "<one line for the changelog>"
```

It refuses to run while validation errors remain — that is deliberate, not an obstacle.
If it refuses, run `/wizrelay:hub-validate` and fix what it lists.

On success it has bumped `version`, set `status` to `published`, written `updated_at`, and
appended a changelog entry.

The summary becomes the changelog line a developer reads in `/wizrelay:sync`. Write it as
what changed and why, not "updates".

## 2. Commit

Show the user the exact command, including which paths it covers:

```
git add tasks/<folder> && git commit -m "publish <task id> v<N>: <summary>"
```

Let them run it, or ask before running it yourself.

## 3. Push or open a pull request

Ask which the team uses. If the hub's default branch is protected — and it should be — a
pull request is the path. Say so rather than attempting a push that will be rejected.

## 4. Announce on the tracker

```
wizrelay hub comment <task id>
```

Show the user the output. It contains, per role: the acceptance criteria, the pull command
in a code block, and a deep link for each role whose `repos` entry names a repository.

Both the pull command and the deep link are in code blocks on purpose: GitHub strips
`claude-cli://` links, so a Markdown link would render as bare text with the URL removed.

**Only on an explicit yes**, post it with the tracker's MCP tools. First line:

```
[WIZRELAY-PUBLISH] <task id> — research v<N> published
```

## 5. Report

Tell the user the version published, which roles can now pull, and the command each
developer runs: `/wizrelay:pull <task id>`.

Answer in the language set in `wizrelay-hub.json`.
