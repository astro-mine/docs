#!/usr/bin/env python3
"""Tests for the docs gate.

A check nobody has seen fail is a check nobody should trust, and this one
cannot be watched failing in CI until the organization has Actions minutes
again (astro-mine/.github#8). So every check is tested the same way: build a
tiny tree, introduce exactly one defect, assert the check reports it, then
assert the same tree without the defect is clean. The second half matters as
much as the first — a check that fires on everything is as useless as one that
fires on nothing.

Standard library only, like the thing it tests::

    python3 -m unittest discover -s scripts -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_docs as gate


def write(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


class TempTree(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def messages(self, failures) -> str:
        return "\n".join(f.render() for f in failures)


class TestLinks(TempTree):
    def test_a_broken_relative_link_fails(self) -> None:
        page = write(self.root, "a.md", "See [the other](b.md).\n")
        failures = gate.check_links([page])
        self.assertEqual(len(failures), 1, self.messages(failures))
        self.assertIn("b.md", failures[0].message)
        self.assertEqual(failures[0].line, 1)

    def test_a_link_that_resolves_passes(self) -> None:
        write(self.root, "b.md", "# B\n")
        page = write(self.root, "a.md", "See [the other](b.md).\n")
        self.assertEqual(gate.check_links([page]), [])

    def test_it_resolves_relative_to_the_linking_file_not_the_repo(self) -> None:
        """`../architecture/x.md` from `guide/` is the dominant form here."""
        write(self.root, "architecture/x.md", "# X\n")
        page = write(self.root, "guide/g.md", "[x](../architecture/x.md)\n")
        self.assertEqual(gate.check_links([page]), [])

    def test_external_and_mailto_links_are_not_touched(self) -> None:
        page = write(
            self.root,
            "a.md",
            "[gh](https://github.com/astro-mine) [m](mailto:x@example.com)\n",
        )
        self.assertEqual(gate.check_links([page]), [])

    def test_a_url_containing_parentheses_is_not_truncated(self) -> None:
        """The balance scan exists for this; a naive regex reports a false break."""
        page = write(
            self.root,
            "a.md",
            "[wiki](https://en.wikipedia.org/wiki/Regolith_(geology))\n",
        )
        self.assertEqual(gate.check_links([page]), [])

    def test_links_inside_a_fenced_block_are_ignored(self) -> None:
        page = write(self.root, "a.md", "```\n[nope](gone.md)\n```\n")
        self.assertEqual(gate.check_links([page]), [])

    def test_an_image_is_not_read_as_a_link(self) -> None:
        write(self.root, "d.png", "")
        page = write(self.root, "a.md", "![alt](d.png)\n")
        self.assertEqual(gate.check_links([page]), [])

    def test_a_link_title_is_not_part_of_the_target(self) -> None:
        write(self.root, "b.md", "# B\n")
        page = write(self.root, "a.md", '[b](b.md "the other one")\n')
        self.assertEqual(gate.check_links([page]), [])


class TestAnchors(TempTree):
    def test_a_missing_anchor_fails(self) -> None:
        write(self.root, "b.md", "# Heading One\n")
        page = write(self.root, "a.md", "[x](b.md#heading-two)\n")
        failures = gate.check_anchors([page])
        self.assertEqual(len(failures), 1, self.messages(failures))
        self.assertIn("heading-two", failures[0].message)

    def test_a_present_anchor_passes(self) -> None:
        write(self.root, "b.md", "# Heading One\n")
        page = write(self.root, "a.md", "[x](b.md#heading-one)\n")
        self.assertEqual(gate.check_anchors([page]), [])

    def test_an_in_page_fragment_is_checked_against_the_same_file(self) -> None:
        page = write(self.root, "a.md", "# Top\n\n[here](#top)\n[gone](#bottom)\n")
        failures = gate.check_anchors([page])
        self.assertEqual(len(failures), 1, self.messages(failures))
        self.assertIn("bottom", failures[0].message)
        self.assertIn("in this document", failures[0].message)

    def test_a_missing_file_is_left_to_the_link_check(self) -> None:
        """One defect, one finding: a broken link must not also report an anchor."""
        page = write(self.root, "a.md", "[x](nowhere.md#top)\n")
        self.assertEqual(gate.check_anchors([page]), [])
        self.assertEqual(len(gate.check_links([page])), 1)

    def test_an_explicit_html_anchor_resolves(self) -> None:
        write(self.root, "b.md", '<a id="roadmap-phases"></a>\n\n## Phases\n')
        page = write(self.root, "a.md", "[x](b.md#roadmap-phases)\n")
        self.assertEqual(gate.check_anchors([page]), [])

    def test_duplicate_headings_get_github_s_numeric_suffixes(self) -> None:
        write(self.root, "b.md", "## Notes\n\n## Notes\n\n## Notes\n")
        page = write(
            self.root, "a.md", "[1](b.md#notes) [2](b.md#notes-1) [3](b.md#notes-2)\n"
        )
        self.assertEqual(gate.check_anchors([page]), [])

    def test_a_heading_inside_a_fence_is_not_an_anchor(self) -> None:
        write(self.root, "b.md", "```\n# Not A Heading\n```\n")
        page = write(self.root, "a.md", "[x](b.md#not-a-heading)\n")
        self.assertEqual(len(gate.check_anchors([page])), 1)


class TestSlugify(unittest.TestCase):
    """GitHub's algorithm, spot-checked against headings this tree really uses."""

    CASES = {
        "3. The narrow waist: how everything integrates": (
            "3-the-narrow-waist-how-everything-integrates"
        ),
        "**Component vs. distribution**": "component-vs-distribution",
        "`astro_mine.core` — the waist": "astro_minecore--the-waist",
        "7.1 The four distributions": "71-the-four-distributions",
        "What it is": "what-it-is",
        "Plan + ContingentPlan": "plan--contingentplan",
    }

    def test_headings_slug_the_way_github_slugs_them(self) -> None:
        for heading, expected in self.CASES.items():
            with self.subTest(heading=heading):
                self.assertEqual(gate.slugify(heading), expected)


class TestStatus(TempTree):
    def test_calling_a_built_distribution_unbuilt_fails(self) -> None:
        page = write(self.root, "a.md", "The `astro-mine-api` is not yet stood up.\n")
        failures = gate.check_status([page])
        self.assertEqual(len(failures), 1, self.messages(failures))
        self.assertIn("astro-mine-api", failures[0].message)

    def test_calling_a_planned_component_unbuilt_is_fine(self) -> None:
        page = write(self.root, "a.md", "Ops is not yet built; it is Phase 2.\n")
        self.assertEqual(gate.check_status([page]), [])

    def test_the_table_is_what_makes_it_fail(self) -> None:
        """Flip the fact and the same sentence changes verdict — nothing else."""
        page = write(self.root, "a.md", "Ops does not exist yet.\n")
        self.assertEqual(gate.check_status([page]), [])
        original = dict(gate.SUBJECT_STATUS)
        gate.SUBJECT_STATUS["Ops"] = gate.BUILT
        self.addCleanup(lambda: gate.SUBJECT_STATUS.update(original))
        self.assertEqual(len(gate.check_status([page])), 1)

    def test_a_retired_claim_fails(self) -> None:
        page = write(
            self.root, "a.md", "The repositories are archived, not deleted.\n"
        )
        failures = gate.check_status([page])
        self.assertTrue(failures)
        self.assertIn("deleted, not archived", failures[0].message)

    def test_the_eighteen_repository_count_cannot_come_back(self) -> None:
        page = write(self.root, "a.md", "The eighteen component repositories.\n")
        self.assertTrue(gate.check_status([page]))

    def test_rfc_2119_is_not_mistaken_for_a_retired_proposal(self) -> None:
        """The tree cites it deliberately; flagging it would kill the check."""
        page = write(self.root, "a.md", "Read MUST in the RFC-2119 sense.\n")
        self.assertEqual(gate.check_status([page]), [])
        page = write(self.root, "b.md", "As decided in RFC-0006.\n")
        self.assertTrue(gate.check_status([page]))

    def test_verbatim_program_output_is_exempt(self) -> None:
        """Quoting what a command prints is correct; the fix belongs upstream."""
        page = write(
            self.root,
            "a.md",
            "It prints:\n\n```\nastro-mine-api ... is not stood up yet\n```\n",
        )
        self.assertEqual(gate.check_status([page]), [])

    def test_a_subject_inside_a_code_span_still_counts(self) -> None:
        """The defect that motivated this check was written exactly this way.

        `conventions.md` said "`astro-mine-api` … is not built yet" with the
        subject in a code span. A check that skipped inline code would have
        been blind to the one sentence it was built to catch.
        """
        page = write(self.root, "a.md", "The `astro-mine-api` is not built yet.\n")
        self.assertTrue(gate.check_status([page]))

    def test_the_marker_excuses_a_line(self) -> None:
        page = write(
            self.root,
            "a.md",
            "<!-- status-ok: quotes a false notice to correct it -->\n"
            "It said `astro-mine-api` is not yet stood up, which was wrong.\n",
        )
        self.assertEqual(gate.check_status([page]), [])

    def test_the_marker_must_carry_a_reason(self) -> None:
        page = write(
            self.root,
            "a.md",
            "<!-- status-ok: -->\nThe astro-mine-api is not yet stood up.\n",
        )
        failures = gate.check_status([page])
        messages = self.messages(failures)
        self.assertIn("no reason", messages)
        # And it excuses nothing: a hatch with no justification is not a hatch,
        # so the claim underneath is still reported.
        self.assertIn("not yet stood up", messages)
        self.assertEqual(len(failures), 2, messages)

    def test_history_directories_are_not_swept(self) -> None:
        """`tpm/` declares itself point-in-time; sweeping it would rewrite history."""
        page = write(self.root, "tpm/old.md", "astro-mine-api is not yet stood up.\n")
        self.assertTrue(gate.check_status([page]))  # outside the repo, no prefix
        under_repo = gate.REPO / "tpm" / "README.md"
        self.assertTrue(
            gate._rel(under_repo).startswith(gate.STATUS_EXEMPT_DIRS),
            "tpm/ must be recognised as exempt by its repo-relative path",
        )


class TestFormat(TempTree):
    def test_trailing_whitespace_fails(self) -> None:
        page = write(self.root, "a.md", "text   \nmore\n")
        failures = gate.check_format([page])
        self.assertEqual(len(failures), 1, self.messages(failures))
        self.assertEqual(failures[0].line, 1)

    def test_crlf_fails(self) -> None:
        page = self.root / "a.md"
        page.write_bytes(b"text\r\n")
        self.assertTrue(any("CRLF" in f.message for f in gate.check_format([page])))

    def test_a_missing_final_newline_fails(self) -> None:
        page = self.root / "a.md"
        page.write_bytes(b"text")
        self.assertTrue(
            any("newline at end" in f.message for f in gate.check_format([page]))
        )

    def test_a_star_list_marker_fails(self) -> None:
        page = write(self.root, "a.md", "* one\n* two\n")
        failures = gate.check_format([page])
        self.assertEqual(len(failures), 2, self.messages(failures))
        self.assertIn("`*`", failures[0].message)

    def test_bold_at_the_start_of_a_line_is_not_a_bullet(self) -> None:
        """`**Component vs. distribution.**` opens paragraphs throughout."""
        page = write(self.root, "a.md", "**Bold lead.** And prose.\n")
        self.assertEqual(gate.check_format([page]), [])

    def test_a_star_inside_a_fence_is_not_a_list_marker(self) -> None:
        page = write(self.root, "a.md", "```\n* not markdown\n```\n")
        self.assertEqual(gate.check_format([page]), [])

    def test_a_clean_file_passes(self) -> None:
        page = write(self.root, "a.md", "# Title\n\nBody.\n")
        self.assertEqual(gate.check_format([page]), [])


class TestTheRealTree(unittest.TestCase):
    """The gate must be green on the tree it ships with.

    A gate landed red is a gate that gets disabled, so this is the acceptance
    criterion from docs#112 expressed as a test rather than as a promise.
    """

    def setUp(self) -> None:
        self.files = gate.tracked_markdown()

    def test_the_tree_is_discovered_through_git(self) -> None:
        self.assertGreater(len(self.files), 50)
        self.assertIn(gate.REPO / "architecture" / "conventions.md", self.files)

    def test_every_check_is_clean_on_this_repository(self) -> None:
        for name, (_, check) in gate.CHECKS.items():
            with self.subTest(check=name):
                failures = check(self.files)
                self.assertEqual(
                    failures, [], "\n" + "\n".join(f.render() for f in failures)
                )

    def test_the_checks_actually_have_something_to_check(self) -> None:
        """Guard against a green that means 'found nothing to look at'.

        `iter_links` skipping every link would make the link and anchor lanes
        pass on any tree at all. Assert the corpus is real.
        """
        links = [t for f in self.files for _, t in gate.iter_links(
            f.read_text(encoding="utf-8").splitlines()
        )]
        self.assertGreater(len(links), 1000)
        relative = [t for t in links if not t.startswith(("http", "mailto:", "#"))]
        self.assertGreater(len(relative), 100)
        fragments = [t for t in links if "#" in t]
        self.assertGreater(len(fragments), 20)


if __name__ == "__main__":
    unittest.main()
