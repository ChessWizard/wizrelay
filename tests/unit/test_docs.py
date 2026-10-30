"""The bilingual documentation set.

The product documentation is one guide published twice, once per language, with one file
per section. That shape gives a reader short pages and a working previous/next trail, and
it gives the repository 44 files whose links all have to agree with each other. Written by
hand, some of those links are wrong on the first day and more of them rot with every
reordering, so `scripts/docs_nav.py` writes them from a single section list and this file
asserts the properties that generator cannot enforce on its own:

* the two languages carry the same sections, under the same file names
* every navigation block matches what the generator would write right now
* every relative link resolves to a file that exists
* a translation never silently drops a section, a command or a cross-reference

The last one is what makes a second language maintainable. English and Turkish prose will
never be comparable token for token, but a page's *structure* is: the same number of
headings, the same number of code blocks, and the same set of link targets. When a
translation falls behind, one of those three stops matching long before anyone notices the
missing paragraph.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
DOCS = REPO / "docs"


def _load_generator():
    """Import `scripts/docs_nav.py` by path.

    It is a script rather than a module of the package — it is not shipped in the plugin
    and must not be importable from the runtime — so there is no import path to it.
    """
    path = REPO / "scripts" / "docs_nav.py"
    spec = importlib.util.spec_from_file_location("docs_nav", path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NAV = _load_generator()
SECTIONS = NAV.SECTIONS
LANGUAGES = NAV.LANGUAGES

#: A markdown link to something inside the repository: not http(s), not mailto, not a
#: bare fragment.
INTERNAL_LINK = re.compile(r"\]\((?!https?:|mailto:|#)([^)\s]+)\)")

#: Every markdown file a reader of the documentation can reach.
PAGES = (
    [REPO / "README.md", REPO / "README.tr.md", DOCS / "README.md"]
    + [DOCS / language / f"{section.slug}.md" for language in LANGUAGES for section in SECTIONS]
    + [DOCS / language / "README.md" for language in LANGUAGES]
)


#: Every markdown file in the repository. The link check runs over all of them, not only the
#: product documentation, because a removed page breaks links from CONTRIBUTING.md and an
#: ADR just as readily — and those are the links nobody re-reads.
ALL_MARKDOWN = sorted(
    path
    for path in REPO.rglob("*.md")
    if ".git" not in path.parts and "node_modules" not in path.parts
)


def _ids(paths) -> list:
    return [str(path.relative_to(REPO)) for path in paths]


# --------------------------------------------------------------------------- parity


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_language_has_exactly_the_sections_the_generator_lists(language: str) -> None:
    """No section file without an entry, and no entry without a file.

    A file nobody lists has no navigation and no place in the index, so a reader only ever
    arrives at it from a search engine. An entry with no file is a dead link in the index.
    """
    on_disk = {path.stem for path in (DOCS / language).glob("*.md") if path.name != "README.md"}
    listed = {section.slug for section in SECTIONS}
    assert on_disk == listed, (
        f"docs/{language}: unlisted file(s) {sorted(on_disk - listed)}, "
        f"missing file(s) {sorted(listed - on_disk)}"
    )


@pytest.mark.parametrize("slug", [section.slug for section in SECTIONS])
def test_both_languages_carry_the_same_structure(slug: str) -> None:
    """Same headings, same code blocks, same links — the prose differs, the shape does not.

    This is the test that catches a stale translation. A new subsection, a new command or a
    new cross-reference added to one language and not the other changes one of these three
    counts, and nothing else in the suite would notice.
    """
    english = (DOCS / "en" / f"{slug}.md").read_text(encoding="utf-8")
    turkish = (DOCS / "tr" / f"{slug}.md").read_text(encoding="utf-8")

    for level in (2, 3):
        pattern = re.compile(rf"^#{{{level}}} ", re.MULTILINE)
        assert len(pattern.findall(english)) == len(pattern.findall(turkish)), (
            f"{slug}: the two languages have a different number of level-{level} headings"
        )

    assert english.count("\n```") == turkish.count("\n```"), (
        f"{slug}: the two languages show a different number of code blocks"
    )

    def targets(text: str) -> set:
        found = set(INTERNAL_LINK.findall(text))
        # The link to the other language is the one link that differs by design.
        return {target for target in found if not target.startswith(("../en/", "../tr/"))}

    assert targets(english) == targets(turkish), (
        f"{slug}: link targets differ — "
        f"en only {sorted(targets(english) - targets(turkish))}, "
        f"tr only {sorted(targets(turkish) - targets(english))}"
    )


@pytest.mark.parametrize("slug", [section.slug for section in SECTIONS])
def test_each_page_links_to_its_own_counterpart(slug: str) -> None:
    """The language switch stays on the same section.

    Pointing at the other language's index, or at a neighbouring section, is the kind of
    mistake that is invisible in review and infuriating to a reader mid-page.
    """
    for language in LANGUAGES:
        other = "tr" if language == "en" else "en"
        text = (DOCS / language / f"{slug}.md").read_text(encoding="utf-8")
        assert f"(../{other}/{slug}.md)" in text, (
            f"docs/{language}/{slug}.md does not link to docs/{other}/{slug}.md"
        )


def test_the_two_indexes_link_to_each_other() -> None:
    assert "(../tr/README.md)" in (DOCS / "en" / "README.md").read_text(encoding="utf-8")
    assert "(../en/README.md)" in (DOCS / "tr" / "README.md").read_text(encoding="utf-8")


def test_the_root_readmes_link_to_each_other() -> None:
    assert "README.tr.md" in (REPO / "README.md").read_text(encoding="utf-8")
    assert "README.md" in (REPO / "README.tr.md").read_text(encoding="utf-8")


# ----------------------------------------------------------------- generated output


@pytest.mark.parametrize("path", ALL_MARKDOWN, ids=_ids(ALL_MARKDOWN))
def test_every_relative_link_resolves(path: Path) -> None:
    """A link to a file that is not there.

    This is the single most common documentation defect and the cheapest one to test for.
    A directory link (`../testing/`) is accepted as a directory.
    """
    text = path.read_text(encoding="utf-8")
    for target in sorted(set(INTERNAL_LINK.findall(text))):
        resolved = (path.parent / target.split("#", 1)[0]).resolve()
        assert resolved.exists(), f"{path.relative_to(REPO)} → {target} does not exist"


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_navigation_is_what_the_generator_would_write(language: str) -> None:
    """`python3 scripts/docs_nav.py` has been run since the last edit.

    Stale navigation and wrong navigation are the same thing: the previous/next trail and
    the breadcrumb come from the section list, so a file that disagrees with the generator
    is sending readers somewhere the list does not.
    """
    for index, section in enumerate(SECTIONS):
        path = DOCS / language / f"{section.slug}.md"
        expected = NAV.render_file(path, index, language)
        assert path.read_text(encoding="utf-8") == expected, (
            f"docs/{language}/{section.slug}.md has stale navigation. "
            "Run `python3 scripts/docs_nav.py`."
        )

    index_path = DOCS / language / "README.md"
    assert index_path.read_text(encoding="utf-8") == NAV.render_index(
        language, NAV.load_descriptions()
    ), f"docs/{language}/README.md is stale. Run `python3 scripts/docs_nav.py`."


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_page_summarises_itself(language: str) -> None:
    """The index describes each page in that page's own words, so each page must have them.

    `summary_of` reads the paragraph directly under the heading. Without one the index gets
    an empty cell, which is how this was caught the first time.
    """
    for section in SECTIONS:
        path = DOCS / language / f"{section.slug}.md"
        assert NAV.summary_of(path), (
            f"docs/{language}/{section.slug}.md has no summary paragraph under its heading"
        )


# ------------------------------------------------------------------------ hygiene


@pytest.mark.parametrize("path", PAGES, ids=_ids(PAGES))
def test_no_page_links_out_of_the_repository(path: Path) -> None:
    """No `/Users/...`, no `C:\\...`, no link that only works on one machine."""
    text = path.read_text(encoding="utf-8")
    for target in sorted(set(INTERNAL_LINK.findall(text))):
        assert not target.startswith("/"), (
            f"{path.relative_to(REPO)} → {target} is an absolute path"
        )
        resolved = (path.parent / target.split("#", 1)[0]).resolve()
        assert REPO in resolved.parents or resolved == REPO, (
            f"{path.relative_to(REPO)} → {target} points outside the repository"
        )


@pytest.mark.parametrize("path", PAGES, ids=_ids(PAGES))
def test_no_page_has_an_unclosed_code_fence(path: Path) -> None:
    """An odd number of fences swallows the rest of the page in every renderer."""
    fences = [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("```")
    ]
    assert len(fences) % 2 == 0, (
        f"{path.relative_to(REPO)} has {len(fences)} code fences, so one is unclosed"
    )
