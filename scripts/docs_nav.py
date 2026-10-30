#!/usr/bin/env python3
"""Generate the navigation blocks and the index for the bilingual documentation set.

The documentation is one guide published twice, once per language, with one file per
section. That shape is good for readers and bad for hand-written links: 22 sections times
two languages is 44 files, each needing a previous link, a next link, an index link and a
link to its counterpart in the other language. Written by hand, some of those are wrong
from the first day and more of them rot with every reordering.

So the section list below is the single source of truth, and this script writes every
navigation block and both indexes from it. `--check` makes it a CI gate: it fails when a
file's navigation is stale, which is the same thing as saying the links are wrong.

Run it after adding, removing or renaming a section:

    python3 scripts/docs_nav.py           # rewrite the navigation and the indexes
    python3 scripts/docs_nav.py --check   # fail if anything is out of date
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

TOP_OPEN = "<!-- nav:top -->"
TOP_CLOSE = "<!-- /nav:top -->"
BOTTOM_OPEN = "<!-- nav:bottom -->"
BOTTOM_CLOSE = "<!-- /nav:bottom -->"


class Section(NamedTuple):
    slug: str
    en: str
    tr: str
    group_en: str
    group_tr: str


#: Every section, in reading order. Adding one here and creating the two files is the whole
#: procedure; the navigation, both indexes and the parity test follow from this list.
SECTIONS: tuple = (
    # Understanding it
    Section("01-overview", "Overview", "Genel bakış", "Understand", "Anlama"),
    Section(
        "02-scope", "What it does and does not do", "Ne yapar, ne yapmaz", "Understand", "Anlama"
    ),
    Section("03-prerequisites", "Prerequisites", "Ön koşullar", "Understand", "Anlama"),
    # Setting it up
    Section("04-install-plugin", "Install the plugin", "Plugin'i kurmak", "Set up", "Kurulum"),
    Section("05-set-up-hub", "Set up the team hub", "Ekip hub'ını kurmak", "Set up", "Kurulum"),
    Section(
        "06-connect-repository", "Connect a repository", "Bir repoyu bağlamak", "Set up", "Kurulum"
    ),
    # Using it
    Section(
        "07-researcher-workflow",
        "Researcher: prepare and publish",
        "Researcher: hazırlamak ve yayınlamak",
        "Use",
        "Kullanım",
    ),
    Section(
        "08-developer-workflow",
        "Developer: implement a task",
        "Developer: task'ı uygulamak",
        "Use",
        "Kullanım",
    ),
    Section(
        "09-question-loop",
        "The question and version loop",
        "Soru ve sürüm döngüsü",
        "Use",
        "Kullanım",
    ),
    # How it works
    Section(
        "10-routing",
        "Model and effort routing",
        "Model ve effort yönlendirmesi",
        "Mechanics",
        "Mekanizma",
    ),
    Section("11-scope-protection", "Scope protection", "Kapsam koruması", "Mechanics", "Mekanizma"),
    Section("12-ci-integration", "CI integration", "CI entegrasyonu", "Mechanics", "Mekanizma"),
    # Running it for a team
    Section(
        "13-team-and-enterprise",
        "Team and enterprise administration",
        "Ekip ve kurum yönetimi",
        "Operate",
        "İşletme",
    ),
    Section("14-customisation", "Customisation", "Özelleştirme", "Operate", "İşletme"),
    # Seeing it whole
    Section(
        "15-walkthrough",
        "Worked example: a task end to end",
        "Örnek: bir task baştan sona",
        "Example",
        "Örnek",
    ),
    # Getting unstuck
    Section("16-troubleshooting", "Troubleshooting", "Sorun giderme", "Reference", "Referans"),
    Section("17-faq", "Frequently asked questions", "Sık sorulan sorular", "Reference", "Referans"),
    Section(
        "appendix-a-commands",
        "Appendix A — Command reference",
        "Ek A — Komut referansı",
        "Reference",
        "Referans",
    ),
    Section(
        "appendix-b-files",
        "Appendix B — File reference",
        "Ek B — Dosya referansı",
        "Reference",
        "Referans",
    ),
    Section(
        "appendix-c-tracker-tags",
        "Appendix C — Tracker comment tags",
        "Ek C — Tracker yorum etiketleri",
        "Reference",
        "Referans",
    ),
    Section(
        "appendix-d-checklists",
        "Appendix D — Checklists",
        "Ek D — Kontrol listeleri",
        "Reference",
        "Referans",
    ),
    Section(
        "appendix-e-glossary", "Appendix E — Glossary", "Ek E — Sözlük", "Reference", "Referans"
    ),
)

LANGUAGES = ("en", "tr")

STRINGS = {
    "en": {
        "other": "Türkçe",
        "other_lang": "tr",
        "docs": "Documentation",
        "contents": "Contents",
        "previous": "Previous",
        "next": "Next",
        "index_title": "wizrelay — documentation",
        "index_intro": (
            "One guide, one file per section. Every page links to the previous section, the\n"
            "next section, this index, and its Turkish counterpart."
        ),
        "index_section_header": "| # | Section | What it covers |",
        "reading_title": "Where to start",
        "reading": (
            "| Your role | Read in this order | Roughly |\n"
            "|---|---|---|\n"
            "| Setting it up for a team | [1](01-overview.md) → [2](02-scope.md) → [3](03-prerequisites.md) → [4](04-install-plugin.md) → [5](05-set-up-hub.md) → [6](06-connect-repository.md) → [13](13-team-and-enterprise.md) | 50 min |\n"
            "| Researcher | [1](01-overview.md) → [7](07-researcher-workflow.md) → [9](09-question-loop.md) → [10](10-routing.md) → [11](11-scope-protection.md) | 40 min |\n"
            "| Developer | [1](01-overview.md) → [6](06-connect-repository.md) → [8](08-developer-workflow.md) → [11](11-scope-protection.md) → [16](16-troubleshooting.md) | 30 min |\n"
            "| Platform / DevOps | [12](12-ci-integration.md) → [13](13-team-and-enterprise.md) → [16](16-troubleshooting.md) | 20 min |\n"
            "| Just want to see it work | [15](15-walkthrough.md) | 15 min |"
        ),
        "contributor_title": "For contributors",
        "contributor": (
            "[CONTRIBUTING.md](../../CONTRIBUTING.md) has the setup, the standards and the\n"
            "definition of done."
        ),
    },
    "tr": {
        "other": "English",
        "other_lang": "en",
        "docs": "Dokümantasyon",
        "contents": "İçindekiler",
        "previous": "Önceki",
        "next": "Sonraki",
        "index_title": "wizrelay — dokümantasyon",
        "index_intro": (
            "Tek bir kılavuz, bölüm başına bir dosya. Her sayfa önceki bölüme, sonraki bölüme,\n"
            "bu dizine ve İngilizce karşılığına bağlanır."
        ),
        "index_section_header": "| # | Bölüm | Ne anlatır |",
        "reading_title": "Nereden başlamalı",
        "reading": (
            "| Rolün | Şu sırayla oku | Yaklaşık |\n"
            "|---|---|---|\n"
            "| Ekip için kuran kişi | [1](01-overview.md) → [2](02-scope.md) → [3](03-prerequisites.md) → [4](04-install-plugin.md) → [5](05-set-up-hub.md) → [6](06-connect-repository.md) → [13](13-team-and-enterprise.md) | 50 dk |\n"
            "| Researcher | [1](01-overview.md) → [7](07-researcher-workflow.md) → [9](09-question-loop.md) → [10](10-routing.md) → [11](11-scope-protection.md) | 40 dk |\n"
            "| Developer | [1](01-overview.md) → [6](06-connect-repository.md) → [8](08-developer-workflow.md) → [11](11-scope-protection.md) → [16](16-troubleshooting.md) | 30 dk |\n"
            "| Platform / DevOps | [12](12-ci-integration.md) → [13](13-team-and-enterprise.md) → [16](16-troubleshooting.md) | 20 dk |\n"
            "| Sadece çalıştığını görmek isteyen | [15](15-walkthrough.md) | 15 dk |"
        ),
        "contributor_title": "Katkıda bulunanlar için",
        "contributor": (
            "[CONTRIBUTING.md](../../CONTRIBUTING.md) kurulumu, standartları ve bitmişlik\n"
            "tanımını anlatıyor."
        ),
    },
}


def title_of(section: Section, language: str) -> str:
    return section.en if language == "en" else section.tr


def group_of(section: Section, language: str) -> str:
    return section.group_en if language == "en" else section.group_tr


def display_number(index: int, section: Section) -> str:
    """`5` for a numbered section, `A` for an appendix."""
    if section.slug.startswith("appendix-"):
        return section.slug.split("-")[1].upper()
    return section.slug.split("-")[0].lstrip("0") or "0"


def label(index: int, language: str) -> str:
    """How a section is named in a link: `9. The question loop`, or `Appendix A — …`.

    An appendix title already carries its letter, so numbering it again would read as
    "A. Appendix A". Numbered sections keep the number, because readers refer to them by it.
    """
    section = SECTIONS[index]
    title = title_of(section, language)
    if section.slug.startswith("appendix-"):
        return title
    return f"{display_number(index, section)}. {title}"


def nav_top(index: int, language: str) -> str:
    section = SECTIONS[index]
    strings = STRINGS[language]
    other = strings["other_lang"]
    return (
        f"{TOP_OPEN}\n"
        f"[{strings['docs']}](README.md) › "
        f"**{label(index, language)}** "
        f"&nbsp;·&nbsp; [{strings['other']}](../{other}/{section.slug}.md)\n"
        f"{TOP_CLOSE}"
    )


def nav_bottom(index: int, language: str) -> str:
    strings = STRINGS[language]
    previous = SECTIONS[index - 1] if index > 0 else None
    following = SECTIONS[index + 1] if index + 1 < len(SECTIONS) else None

    left = f"[← {label(index - 1, language)}]({previous.slug}.md)" if previous else "&nbsp;"
    right = f"[{label(index + 1, language)} →]({following.slug}.md)" if following else "&nbsp;"
    return (
        f"{BOTTOM_OPEN}\n"
        "---\n\n"
        f"| ← | ↑ | → |\n"
        f"|:---|:---:|---:|\n"
        f"| {left} | [{strings['contents']}](README.md) | {right} |\n"
        f"{BOTTOM_CLOSE}"
    )


def _replace_block(text: str, open_marker: str, close_marker: str, block: str) -> str:
    start = text.find(open_marker)
    if start == -1:
        return text
    end = text.find(close_marker, start)
    if end == -1:
        return text
    return text[:start] + block + text[end + len(close_marker) :]


def render_file(path: Path, index: int, language: str) -> str:
    text = path.read_text(encoding="utf-8")
    if TOP_OPEN not in text:
        # A new file: put the top block before the first heading.
        heading = text.find("# ")
        heading = 0 if heading == -1 else heading
        text = text[:heading] + nav_top(index, language) + "\n\n" + text[heading:]
    else:
        text = _replace_block(text, TOP_OPEN, TOP_CLOSE, nav_top(index, language))

    if BOTTOM_OPEN not in text:
        text = text.rstrip("\n") + "\n\n" + nav_bottom(index, language) + "\n"
    else:
        text = _replace_block(text, BOTTOM_OPEN, BOTTOM_CLOSE, nav_bottom(index, language))

    return text.rstrip("\n") + "\n"


def render_index(language: str, descriptions: dict) -> str:
    strings = STRINGS[language]
    other = strings["other_lang"]
    lines = [
        f"{TOP_OPEN}",
        f"**{strings['docs']}** &nbsp;·&nbsp; [{strings['other']}](../{other}/README.md)",
        f"{TOP_CLOSE}",
        "",
        f"# {strings['index_title']}",
        "",
        strings["index_intro"],
        "",
        f"## {strings['reading_title']}",
        "",
        strings["reading"],
        "",
    ]

    current_group = None
    for index, section in enumerate(SECTIONS):
        group = group_of(section, language)
        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f"## {group}")
            lines.append("")
            lines.append(strings["index_section_header"])
            lines.append("|---|---|---|")
            current_group = group
        description = descriptions.get(f"{language}/{section.slug}", "")
        lines.append(
            f"| {display_number(index, section)} "
            f"| [{title_of(section, language)}]({section.slug}.md) "
            f"| {description} |"
        )
    lines.append("")
    lines.append(f"## {strings['contributor_title']}")
    lines.append("")
    lines.append(strings["contributor"])
    return "\n".join(lines).rstrip("\n") + "\n"


#: What a summary paragraph cannot start with. Anything in this list means the page went
#: straight from its heading into content, which `--check` reports rather than guessing.
NOT_PROSE = ("<!--", "#", "|", ">", "```", "- ", "* ", "1. ", "[")

#: A sentence ends at `.`, `?` or `!` followed by a space and a capital. The lookbehind for a
#: digit keeps `v2.1.295` and `Python 3.9` from being read as two sentences.
SENTENCE_END = re.compile(r"(?<!\d)[.?!]\s+(?=[A-ZÇĞİÖŞÜ`*])")


def summary_of(path: Path) -> str:
    """The page's own summary: the paragraph directly under its heading, first sentence.

    Taking it from the page rather than from a table in this script means the index
    describes each section in that section's own words and cannot drift from it. Reading
    the whole paragraph rather than its first line matters because these files are hard
    wrapped — a one-line read would cut most summaries mid-clause.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    position = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if position is None:
        return ""

    paragraph: list = []
    for candidate in lines[position + 1 :]:
        stripped = candidate.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith(NOT_PROSE):
            break
        paragraph.append(stripped)

    text = " ".join(paragraph)
    split = SENTENCE_END.split(text, maxsplit=1)
    return split[0].rstrip(" .") if split else ""


def load_descriptions() -> dict:
    out: dict = {}
    for language in LANGUAGES:
        for section in SECTIONS:
            path = DOCS / language / f"{section.slug}.md"
            if path.is_file():
                out[f"{language}/{section.slug}"] = summary_of(path)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail instead of writing, for CI.")
    args = parser.parse_args()

    descriptions = load_descriptions()
    stale: list = []
    missing: list = []
    unsummarised = sorted(key for key, value in descriptions.items() if not value)
    written = 0

    for language in LANGUAGES:
        for index, section in enumerate(SECTIONS):
            path = DOCS / language / f"{section.slug}.md"
            if not path.is_file():
                missing.append(str(path.relative_to(REPO)))
                continue
            rendered = render_file(path, index, language)
            if rendered != path.read_text(encoding="utf-8"):
                if args.check:
                    stale.append(str(path.relative_to(REPO)))
                else:
                    path.write_text(rendered, encoding="utf-8")
                    written += 1

        index_path = DOCS / language / "README.md"
        rendered = render_index(language, descriptions)
        existing = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
        if rendered != existing:
            if args.check:
                stale.append(str(index_path.relative_to(REPO)))
            else:
                index_path.write_text(rendered, encoding="utf-8")
                written += 1

    for path in missing:
        print(f"missing: {path}")
    for path in stale:
        print(f"stale navigation: {path}")

    for key in unsummarised:
        print(f"no summary paragraph under the heading: docs/{key}.md")

    if missing:
        print(f"\n{len(missing)} section file(s) are missing.")
        return 1
    if unsummarised:
        print(f"\n{len(unsummarised)} page(s) have no summary, so the index has an empty cell.")
        return 1
    if stale:
        print(f"\n{len(stale)} file(s) are out of date. Run `python3 scripts/docs_nav.py`.")
        return 1
    print(
        f"navigation up to date ({written} file(s) written, "
        f"{len(SECTIONS)} sections × {len(LANGUAGES)} languages)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
