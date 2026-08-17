#!/usr/bin/env python3
"""Check that external links still resolve.

Separate from `check_docs.py`, and scheduled rather than run on pull requests,
for one reason: a third-party outage must not fail somebody's documentation
edit. A link check that goes red because a university web server rebooted is a
link check people learn to re-run until it passes, which is worse than not
having one.

**What this covers today is small, and the reason is worth stating.** Of the
external URLs in this tree, all but a handful point at `github.com/astro-mine`
— repositories that are private during incubation and therefore answer 404 to
an anonymous request. Checking them would report the whole organization as
broken. They are skipped until the public flip, at which point deleting
`SKIP_WHILE_PRIVATE` turns this lane from covering a handful of links to
covering nearly all of them. That is the day this file becomes useful; until
then it guards the third-party references.

    python3 scripts/check_external_links.py
    python3 scripts/check_external_links.py --include-private   # after the flip
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_docs as docs  # noqa: E402  (path set above, deliberately)

# Private during incubation: anonymous requests get 404 whether or not the page
# exists, so a result here means nothing. Remove at the public flip.
SKIP_WHILE_PRIVATE = (
    "https://github.com/astro-mine",
    "https://github.com/orgs/astro-mine",
)

TIMEOUT = 20
ATTEMPTS = 3
AGENT = "astro-mine-docs-link-check"

# 403 is not evidence of a broken link: several hosts refuse unknown agents.
# The check answers "does this resolve", not "may a robot read it".
TOLERATED = {403, 429}


def collect() -> dict[str, list[str]]:
    """Every external URL, mapped to the places that cite it."""
    where: dict[str, list[str]] = {}
    for path in docs.tracked_markdown():
        rel = docs._rel(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, target in docs.iter_links(lines):
            if target.startswith(("http://", "https://")):
                where.setdefault(target, []).append(f"{rel}:{number}")
    return where


def probe(url: str) -> tuple[str, str | None]:
    """Return (url, problem-or-None). HEAD first, GET on refusal."""
    last = "unknown error"
    for attempt in range(ATTEMPTS):
        for method in ("HEAD", "GET"):
            request = urllib.request.Request(
                url, method=method, headers={"User-Agent": AGENT}
            )
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                    if response.status < 400:
                        return url, None
                    last = f"HTTP {response.status}"
            except urllib.error.HTTPError as error:
                if error.code in TOLERATED:
                    return url, None
                last = f"HTTP {error.code}"
                if error.code == 405:  # HEAD not allowed; the GET pass follows
                    continue
                break
            except Exception as error:  # noqa: BLE001 — network, be permissive
                last = f"{type(error).__name__}: {error}"
        if attempt + 1 < ATTEMPTS:
            continue
    return url, last


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="also check github.com/astro-mine (needs an authenticated network)",
    )
    args = parser.parse_args(argv)

    citations = collect()
    urls = sorted(citations)
    if not args.include_private:
        skipped = [u for u in urls if u.startswith(SKIP_WHILE_PRIVATE)]
        urls = [u for u in urls if not u.startswith(SKIP_WHILE_PRIVATE)]
        if skipped:
            print(
                f"skipping {len(skipped)} link(s) into the private organization "
                "(they 404 anonymously; this lifts at the public flip)"
            )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(probe, urls))

    broken = [(url, problem) for url, problem in results if problem]
    for url, problem in broken:
        print(f"\n{url}\n  {problem}")
        for citation in citations[url]:
            print(f"  cited at {citation}")

    print(f"\nchecked {len(urls)} external link(s): " + (
        "all resolve" if not broken else f"{len(broken)} broken"
    ))
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
