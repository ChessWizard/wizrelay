<!-- nav:top -->
**Documentation** &nbsp;·&nbsp; [Türkçe](../tr/README.md)
<!-- /nav:top -->

# wizrelay — documentation

One guide, one file per section. Every page links to the previous section, the
next section, this index, and its Turkish counterpart.

## Where to start

| Your role | Read in this order | Roughly |
|---|---|---|
| Setting it up for a team | [1](01-overview.md) → [2](02-scope.md) → [3](03-prerequisites.md) → [4](04-install-plugin.md) → [5](05-set-up-hub.md) → [6](06-connect-repository.md) → [13](13-team-and-enterprise.md) | 50 min |
| Researcher | [1](01-overview.md) → [7](07-researcher-workflow.md) → [9](09-question-loop.md) → [10](10-routing.md) → [11](11-scope-protection.md) | 40 min |
| Developer | [1](01-overview.md) → [6](06-connect-repository.md) → [8](08-developer-workflow.md) → [11](11-scope-protection.md) → [16](16-troubleshooting.md) | 30 min |
| Platform / DevOps | [12](12-ci-integration.md) → [13](13-team-and-enterprise.md) → [16](16-troubleshooting.md) | 20 min |
| Just want to see it work | [15](15-walkthrough.md) | 15 min |

## Understand

| # | Section | What it covers |
|---|---|---|
| 1 | [Overview](01-overview.md) | What wizrelay is, the problem it solves, and the three pieces it is made of |
| 2 | [What it does and does not do](02-scope.md) | The boundary of this tool: the goals it commits to, the things it deliberately leaves alone, and the guarantees it can and cannot make |
| 3 | [Prerequisites](03-prerequisites.md) | What each person needs before anything is installed, and how to check it |

## Set up

| # | Section | What it covers |
|---|---|---|
| 4 | [Install the plugin](04-install-plugin.md) | Installing `wizrelay`, checking that it worked, and confirming that scope protection is actually live in a session |
| 5 | [Set up the team hub](05-set-up-hub.md) | Creating the repository that holds your team's analysis, and the two settings that make it trustworthy |
| 6 | [Connect a repository](06-connect-repository.md) | Connecting a project repository to the hub, and getting its profile right — because routing reads that profile |

## Use

| # | Section | What it covers |
|---|---|---|
| 7 | [Researcher: prepare and publish](07-researcher-workflow.md) | Writing a task package, file by file, and the two gates it passes before developers can pull it |
| 8 | [Developer: implement a task](08-developer-workflow.md) | Pulling a package, planning against it, implementing with the checks live, and verifying with evidence |
| 9 | [The question and version loop](09-question-loop.md) | What the researcher does after a developer asks, and why the answer has to become a version rather than a reply |

## Mechanics

| # | Section | What it covers |
|---|---|---|
| 10 | [Model and effort routing](10-routing.md) | How a task's signals and a repository's profile become a model, an effort level and a launch command |
| 11 | [Scope protection](11-scope-protection.md) | The five layers, what each one actually stops, the glob syntax, and the bypasses that are documented rather than hidden |
| 12 | [CI integration](12-ci-integration.md) | The pull-request gate: the only layer that does not run inside the developer's own session |

## Operate

| # | Section | What it covers |
|---|---|---|
| 13 | [Team and enterprise administration](13-team-and-enterprise.md) | Rolling this out to a team, and the two layers a developer cannot turn off |
| 14 | [Customisation](14-customisation.md) | Every knob, where it lives, and which layer wins when two of them disagree |

## Example

| # | Section | What it covers |
|---|---|---|
| 15 | [Worked example: a task end to end](15-walkthrough.md) | One task, from a tracker entry to a merged pull request, with the real file contents and the real command output at every step |

## Reference

| # | Section | What it covers |
|---|---|---|
| 16 | [Troubleshooting](16-troubleshooting.md) | Symptom, cause, fix |
| 17 | [Frequently asked questions](17-faq.md) | The questions that come up in the first week |
| A | [Appendix A — Command reference](appendix-a-commands.md) | Every command, who uses it, and its CLI equivalent |
| B | [Appendix B — File reference](appendix-b-files.md) | Every file the system creates or reads, who owns it, and whether it is committed |
| C | [Appendix C — Tracker comment tags](appendix-c-tracker-tags.md) | The four tags, their exact first lines, and the rules around posting |
| D | [Appendix D — Checklists](appendix-d-checklists.md) | Copy these into an issue or a wiki page |
| E | [Appendix E — Glossary](appendix-e-glossary.md) | Every term this documentation uses as if you already knew it, and the pairs of terms that are easy to confuse for each other |

## For contributors

[CONTRIBUTING.md](../../CONTRIBUTING.md) has the setup, the standards and the
definition of done.
