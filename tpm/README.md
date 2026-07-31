# Technical Program Management (TPM)

Program-management working documents for Astro-Mine — planning and analysis artifacts that sit
alongside the authoritative spec (`architecture/`, `scenarios/`, `roadmap/`) rather than inside it.
These are **point-in-time** analyses: they capture a decision or a plan as of their date, and are
superseded by later work rather than continuously maintained.

> **Read these as history, and check the spec before acting on them.** They were written against a
> platform of eighteen component repositories governed by a formal design-proposal process. Both are
> gone: the Python code ships as **four distributions**
> ([conventions.md](../architecture/conventions.md) §7.1), and design decisions are recorded where
> they are normative rather than in a parallel archive of proposals. Where these documents say
> "install `astro-mine-<component>`", "the `docs` repo's RFCs", or count issues per component repo,
> that is what was true when they were written. The analysis and the record of what execution found
> are why they are kept; the plumbing they describe is not current. Issue references appear as plain
> `repo#number` labels rather than links, because the repositories they point into are being retired
> (`RM-DIST-05`).

## Contents

| Document | What it is |
|---|---|
| [phase-0-1-user-surface-analysis.md](phase-0-1-user-surface-analysis.md) | **Phase 0/1 user-surface analysis & gap report** (2026-07-16). Designs the complete user-oriented surface (CLI + GUI) for the Phase-0 and Phase-1 objectives, inventories what ships today against it, and gap-analyses the difference. Defines 7 personas, 46 use cases, 6 user journeys, and the single-console GUI architecture. |
| [issue-plan.md](issue-plan.md) | **The Waves 21–26 issue backlog** derived from the gap report — 33 issues across 9 repos, with per-issue detail, verified evidence, and board conventions. Closes with an **Outcome** section recording what execution found. |
| [ui-rebuild-plan.md](ui-rebuild-plan.md) | **The UI rebuild — plan and issue backlog (Waves 28–30)** (2026-07-31). Re-implements the front end as a Next.js + Material UI multi-page application over a generated REST client, replacing `RM-DIST-04`'s move of five package trees. Records the decisions, the feature inventory the rebuild must not lose, the target information architecture, the CI test lanes, and 25 issues. |

## Status

**Waves 28–30 — the UI rebuild — are planned and filed** (2026-07-31). See
[ui-rebuild-plan.md](ui-rebuild-plan.md). The front end is the last distribution not stood up, and it
is being rebuilt rather than moved.

**Waves 21–26 are complete** (2026-07-24). Every issue carrying a `Wave 21`–`Wave 26` label — 54 in
total, across 15 repos — is closed and Done on the
[AstroMine board](https://github.com/orgs/astro-mine/projects/3). The backlog planned 33; the
remainder were spun out during execution as the work found things the plan could not have known.

What the six waves produced:

| Wave | Outcome |
|---|---|
| 21 | The anchor content set published to `ghcr.io/astro-mine` and fetchable by digest; `bench score --runner sim` scoring real physics; a Sim CLI and README |
| 22 | The policy export wired up (`--export`), an anchor env factory, `bench submit`, an open solver registry, the plugin-authoring guide |
| 23 | The console: `@astro-mine/surface`, `@astro-mine/ui`, the shell — **the console + Surface contract** |
| 24 | Three real surfaces — Hub, Bench, Studio — plus `studio serve` and the View distribution decision |
| 25 | Component CLIs for Core, Guard and Mind, and the `astro-mine` umbrella — **the umbrella CLI + naming** |
| 26 | The [user guide](../guide/README.md): `getting-started`, eight tutorials, the console guide, and the full reference section (22 pages); plus the truth-in-docs sweep across 12 repos |

Both gating decisions were settled and implemented: the **console shell + `Surface` contract**, and
the **umbrella CLI + command naming**, which also produced a new repo, `astro-mine-cli`.

The critical path held as predicted — Wave 21's content publication unblocked everything, and the
tutorials that prove the Phase-0 promise were the last thing to land.

**Where the live state now lives:** the [user guide](../guide/README.md) is the user-facing surface
these waves existed to create, and it is maintained, not point-in-time. The documents here record
how it was planned and what execution found; see `issue-plan.md` § *Outcome* for the deviations
worth remembering.
