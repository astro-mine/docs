# Technical Program Management (TPM)

Program-management working documents for Astro-Mine — planning and analysis artifacts that sit
alongside the authoritative spec (`architecture/`, `scenarios/`, `roadmap/`, `rfc/`) rather than
inside it. These are **point-in-time** analyses: they capture a decision or a plan as of their
date, and are superseded by later work rather than continuously maintained.

## Contents

| Document | What it is |
|---|---|
| [phase-0-1-user-surface-analysis.md](phase-0-1-user-surface-analysis.md) | **Phase 0/1 user-surface analysis & gap report** (2026-07-16). Designs the complete user-oriented surface (CLI + GUI) for the Phase-0 and Phase-1 objectives, inventories what ships today against it, and gap-analyses the difference. Defines 7 personas, 46 use cases, 6 user journeys, and the single-console GUI architecture. |
| [issue-plan.md](issue-plan.md) | **The Waves 21–26 issue backlog** derived from the gap report — 34 issues across 9 repos, with per-issue detail, verified evidence, and board conventions. |

## Status

The backlog in `issue-plan.md` has been **filed** (Waves 21–26, all Phase 1) and is tracked on the
[AstroMine board](https://github.com/orgs/astro-mine/projects/3). Two RFCs gate the console/CLI
work: **RFC-0010** (console shell + Surface contract) and **RFC-0011** (umbrella CLI + naming).
The critical path is **Wave 21** — publish the anchor content and make Sim-backed scoring honest —
which unblocks everything else.
