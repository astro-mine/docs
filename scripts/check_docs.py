#!/usr/bin/env python3
"""Gate the spec the way the code is gated.

This repository is normative for every other tree in the organization, and until
now it was the only one with no check of any kind. The charter's governance
principle is the argument (§9.4): *a process that cannot fail a bad change is
decoration; a check that fails the build is governance.* Applied to prose, that
is this file.

Four checks, in the order they earn their keep:

``links``
    Every relative link resolves to a file that exists.

``anchors``
    Every ``#fragment`` resolves to a heading in the target document.

``status``
    Prose does not contradict the declared status of the platform, and a claim
    that was corrected once cannot come back.

``format``
    The mechanical things only — trailing whitespace, CRLF, a final newline.

Run it with a bare interpreter; the repository has no dependencies and this
file adds none::

    python3 scripts/check_docs.py             # everything
    python3 scripts/check_docs.py status      # one check
    python3 scripts/check_docs.py --list      # what the checks are

Exit status is 0 when clean and 1 when anything failed, so it is usable as a
pre-commit hook and as a CI step without a wrapper.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# What the platform's status actually is.
#
# This table is the fact the `status` check compares prose against. It is the
# one place to edit when something ships: a distribution moves from `PLANNED`
# to `BUILT` here, and every sentence in the tree that still calls it unbuilt
# fails on the next run. That is the whole design — the table is small enough
# to keep true, and the prose is too large to sweep by hand.
# ---------------------------------------------------------------------------

BUILT = "built"
PLANNED = "planned"

SUBJECT_STATUS: dict[str, str] = {
    # The four distributions (conventions.md §7.1).
    "astro-mine-platform": BUILT,
    "astro-mine-cli": BUILT,
    "astro-mine-api": BUILT,
    "astro-mine-ui": BUILT,
    # Phases (roadmap/README.md).
    "Phase 0": BUILT,
    "Phase 1": BUILT,
    "Phase 2": PLANNED,
    "Phase 3": PLANNED,
    # Components that do not exist yet (system.md §"Design & operations").
    "Ops": PLANNED,
    "Bridge": PLANNED,
    "Transit": PLANNED,
    "Trajectory": PLANNED,
    "Sizing": PLANNED,
    "Ledger": PLANNED,
}

# Phrases that assert a subject is not built. Deliberately literal: this is a
# regression lock on the wording the audit actually found, not an attempt to
# understand English.
UNBUILT_PHRASES: tuple[str, ...] = (
    "not yet stood up",
    "not stood up yet",
    "is not stood up",
    "is not built yet",
    "not yet built",
    "does not exist yet",
    "has not been built",
    "is unbuilt",
    "not yet shipped",
    "when it ships",
    "once it ships",
    "is in progress",
    "still in progress",
)

# Claims that were true once, were corrected, and must not return. Each entry
# is (pattern, what is wrong with it). Adding one when you fix a sentence is
# how a finding stops being a recurring finding.
RETIRED_CLAIMS: tuple[tuple[str, str], ...] = (
    (
        r"archived rather than deleted",
        "the nineteen superseded repositories were deleted, not archived "
        "(roadmap/README.md §RM-DIST-05)",
    ),
    (
        r"repositories (?:are|were) archived",
        "the nineteen superseded repositories were deleted, not archived "
        "(roadmap/README.md §RM-DIST-05)",
    ),
    (
        r"kept readable rather than deleted",
        "archival was reversed; the history survives only in a local mirror "
        "(roadmap/README.md §RM-DIST-05)",
    ),
    (
        r"eighteen (?:component )?repositor",
        "there were seventeen component repositories and nineteen deleted in "
        "total (seventeen components plus the two front ends)",
    ),
    (
        # `RFC-00NN` was this project's own proposal numbering, retired with the
        # process. Scoped to `00` on purpose: RFC-2119 is the IETF keywords
        # document, this tree cites it deliberately, and a rule that flagged it
        # would be a rule everyone learns to ignore.
        r"\bRFC-00\d{2}\b",
        "the RFC process was retired; a decision is recorded in the document "
        "where it is normative (GOVERNANCE.md)",
    ),
    (
        r"the four (?:composition )?roots?\b",
        "`svcs` is used at two composition roots, both inside the wheel; the "
        "CLI and the API wire without it (conventions.md §3.3)",
    ),
)

# `tpm/` is declared point-in-time history by its own README, and the charter
# export is generated. Neither is swept for status claims.
STATUS_EXEMPT_DIRS: tuple[str, ...] = ("tpm/",)

# An escape hatch, because a document that *quotes* a false claim in order to
# correct it is doing the right thing and must not be punished for it. The
# marker carries a reason and the reason is asserted non-empty: an exemption
# nobody had to justify is an exemption nobody will revisit.
ALLOW_RE = re.compile(r"<!--\s*status-ok:\s*(?P<reason>[^>]*?)\s*-->")

# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Failure:
    path: str
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _rel(path: Path) -> str:
    """Repository-relative display path, tolerant of files outside it.

    The checks are given a list of paths rather than discovering their own, so
    the self-test can point them at a fixture tree in `tmp`. That only works if
    reporting does not assume every file lives under `REPO`.
    """
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def tracked_markdown() -> list[Path]:
    """Every markdown file git knows about.

    Discovery is `git ls-files` rather than a walk, for the reason the
    platform's licence-header gate learned the hard way: a walk finds build
    output, scratch copies and anything a contributor left lying around, and a
    check that fails on untracked files is a check people learn to ignore.
    """
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [REPO / name for name in out.split("\0") if name]


def strip_code(lines: list[str]) -> list[str]:
    """Blank out fenced code blocks, preserving line numbering.

    Verbatim output belongs to the program that emitted it. `guide/reference/
    cli.md` quotes a command that prints "not stood up yet"; the quote is
    correct precisely because it is what the command says today, and a status
    check that flagged it would be demanding the documentation misquote the
    software. Indented code is *not* stripped — four-space indentation is used
    for continuation paragraphs throughout this tree, and blanking those would
    hide real prose.
    """
    result: list[str] = []
    fence: str | None = None
    for line in lines:
        opener = re.match(r"\s*(`{3,}|~{3,})", line)
        if fence is None and opener:
            fence = opener.group(1)[0] * 3
            result.append("")
            continue
        if fence is not None:
            closer = re.match(rf"\s*{re.escape(fence[0])}{{3,}}\s*$", line)
            result.append("")
            if closer:
                fence = None
            continue
        result.append(line)
    return result


def strip_inline_code(text: str) -> str:
    return re.sub(r"`[^`]*`", "``", text)


# --- links and anchors -----------------------------------------------------

LINK_RE = re.compile(r"(?<!\!)\[(?P<text>(?:[^\[\]]|\[[^\]]*\])*)\]\(")


def iter_links(lines: list[str]):
    """Yield (line_number, target) for inline links outside code.

    Written as a balance scan rather than a regex for the target, because URLs
    in this tree contain parentheses (Wikipedia links do, and so does at least
    one anchor) and `\\([^)]*\\)` truncates them into targets that then fail to
    resolve for a reason that has nothing to do with the link being broken.
    """
    for number, line in enumerate(strip_code(lines), start=1):
        pos = 0
        while (match := LINK_RE.search(line, pos)) is not None:
            start = match.end()
            depth = 1
            index = start
            while index < len(line) and depth:
                if line[index] == "(":
                    depth += 1
                elif line[index] == ")":
                    depth -= 1
                index += 1
            if depth:  # unbalanced: a stray bracket, not a link
                pos = match.end()
                continue
            target = line[start : index - 1].strip()
            # Strip an optional link title: [x](path "title")
            title = re.match(r"""(?P<url>\S+)\s+["'(].*""", target)
            if title:
                target = title.group("url")
            yield number, target
            pos = index


HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*#*\s*$")
EXPLICIT_ANCHOR_RE = re.compile(r"""<a\s+(?:id|name)=["'](?P<id>[^"']+)["']""")


def slugify(text: str) -> str:
    """GitHub's heading-anchor algorithm.

    Reimplemented rather than approximated, because the failure mode of an
    approximation is a check that reports broken anchors that work in the
    browser — which trains everyone to distrust it.
    """
    text = re.sub(r"<[^>]+>", "", text)  # inline HTML
    text = re.sub(r"!?\[(?P<t>[^\]]*)\]\([^)]*\)", r"\g<t>", text)  # links
    text = text.replace("`", "").replace("*", "").replace("~", "")
    # `_` survives: it is a word character, GitHub keeps it, and the headings
    # here that contain one contain it as part of an identifier
    # (`astro_mine.core`) rather than as emphasis.
    text = text.lower().strip()
    text = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def anchors_of(path: Path) -> set[str]:
    """Every fragment that resolves inside `path`."""
    lines = path.read_text(encoding="utf-8").splitlines()
    found: set[str] = set()
    seen: Counter[str] = Counter()
    for line in strip_code(lines):
        for match in EXPLICIT_ANCHOR_RE.finditer(line):
            found.add(match.group("id"))
        heading = HEADING_RE.match(line)
        if not heading:
            continue
        slug = slugify(heading.group("text"))
        if not slug:
            continue
        count = seen[slug]
        seen[slug] += 1
        found.add(slug if not count else f"{slug}-{count}")
    return found


def check_links(files: list[Path]) -> list[Failure]:
    failures: list[Failure] = []
    for path in files:
        rel = _rel(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, target in iter_links(lines):
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            file_part = target.split("#", 1)[0]
            if not file_part:
                continue
            resolved = (path.parent / file_part).resolve()
            if not resolved.exists():
                failures.append(
                    Failure(rel, number, f"relative link does not resolve: {target}")
                )
    return failures


def check_anchors(files: list[Path]) -> list[Failure]:
    cache: dict[Path, set[str]] = {}
    failures: list[Failure] = []
    for path in files:
        rel = _rel(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, target in iter_links(lines):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if "#" not in target:
                continue
            file_part, fragment = target.split("#", 1)
            if not fragment:
                continue
            resolved = (path.parent / file_part).resolve() if file_part else path
            if not resolved.exists() or resolved.suffix != ".md":
                continue  # a missing file is the link check's finding, not ours
            if resolved not in cache:
                cache[resolved] = anchors_of(resolved)
            if fragment not in cache[resolved]:
                where = "in this document" if not file_part else f"in {file_part}"
                failures.append(
                    Failure(rel, number, f"anchor #{fragment} not found {where}")
                )
    return failures


# --- status ----------------------------------------------------------------


def check_status(files: list[Path]) -> list[Failure]:
    failures: list[Failure] = []
    for path in files:
        rel = _rel(path)
        if rel.startswith(STATUS_EXEMPT_DIRS):
            continue
        raw = path.read_text(encoding="utf-8").splitlines()

        # An empty marker is reported once, where it is written — not once per
        # line that can see it. Its reason is the whole point of the hatch, so
        # a marker without one excuses nothing either.
        excusing: set[int] = set()
        for number, line in enumerate(raw, start=1):
            marker = ALLOW_RE.search(line)
            if not marker:
                continue
            if not marker.group("reason"):
                failures.append(
                    Failure(rel, number, "status-ok marker carries no reason")
                )
                continue
            excusing.update({number - 1, number, number + 1})

        for number, line in enumerate(strip_code(raw), start=1):
            if number in excusing:
                continue

            # Inline code is *not* stripped. The defect this check exists to
            # catch was written as "`astro-mine-api` … is not built yet", with
            # the subject in a code span — blanking those would have made the
            # check blind to the exact sentence that motivated it.
            prose = line

            for pattern, why in RETIRED_CLAIMS:
                if re.search(pattern, prose, flags=re.IGNORECASE):
                    failures.append(
                        Failure(rel, number, f"retired claim: {why}")
                    )

            lowered = prose.lower()
            phrase = next((p for p in UNBUILT_PHRASES if p in lowered), None)
            if phrase is None:
                continue
            for subject, status in SUBJECT_STATUS.items():
                if status is not BUILT:
                    continue
                if re.search(rf"(?<![\w-]){re.escape(subject)}(?![\w-])", prose):
                    failures.append(
                        Failure(
                            rel,
                            number,
                            f'"{phrase}" in a sentence about {subject}, which is '
                            f"{BUILT} (scripts/check_docs.py SUBJECT_STATUS)",
                        )
                    )
    return failures


# --- format ----------------------------------------------------------------


def check_format(files: list[Path]) -> list[Failure]:
    failures: list[Failure] = []
    for path in files:
        rel = _rel(path)
        blob = path.read_bytes()
        if b"\r\n" in blob:
            failures.append(Failure(rel, 0, "CRLF line endings"))
        if blob and not blob.endswith(b"\n"):
            failures.append(Failure(rel, 0, "no newline at end of file"))
        lines = blob.decode("utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if line != line.rstrip():
                failures.append(Failure(rel, number, "trailing whitespace"))
        # List markers: the tree is uniformly `-`, and mixing markers changes
        # nothing about the render, which is exactly why it drifts unnoticed.
        # `**bold**` at the start of a line is not a bullet — the required
        # whitespace after a single `*` is what separates them.
        for number, line in enumerate(strip_code(lines), start=1):
            if re.match(r"\s*\*\s+\S", line):
                failures.append(
                    Failure(rel, number, "list marker `*`; this tree uses `-`")
                )
    return failures


# ---------------------------------------------------------------------------

CHECKS = {
    "links": ("relative links resolve", check_links),
    "anchors": ("#fragments resolve to a heading", check_anchors),
    "status": ("prose agrees with the declared status", check_status),
    "format": ("trailing whitespace, CRLF, final newline", check_format),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("checks", nargs="*", choices=[*CHECKS, []], default=[])
    parser.add_argument("--list", action="store_true", help="list the checks and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name, (blurb, _) in CHECKS.items():
            print(f"{name:8}  {blurb}")
        return 0

    selected = args.checks or list(CHECKS)
    files = tracked_markdown()
    if not files:
        print("no tracked markdown found — is this the docs repository?", file=sys.stderr)
        return 1

    total = 0
    for name in selected:
        blurb, check = CHECKS[name]
        failures = check(files)
        total += len(failures)
        if failures:
            print(f"\n{name}: {len(failures)} problem(s) — {blurb}")
            for failure in failures:
                print(f"  {failure.render()}")

    print(
        f"\nchecked {len(files)} files, {len(selected)} check(s): "
        + ("clean" if not total else f"{total} problem(s)")
    )
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
