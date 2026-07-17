# Phase-1 UX & User-Guide backlog — issue plan (Waves 21–26)

Source of truth for the issue-drafting pass. Derived from
`phase-0-1-user-surface-analysis.md` (the gap report). Gap IDs (G1.x/G2.x/G3.x)
and use-case IDs (UC-xx) below refer to that report.

**Product decisions (2026-07-16):** one GUI not per-component apps · unified REST API deferred (not
Phase 1) · console work is **Phase 1** · console = **one repo** `astro-mine-console` (pnpm
workspace: `packages/surface`, `packages/ui`, `packages/console`) · surface packages live **in their
component repos** · all six waves filed up front.

**Wave numbering:** global topological sequence. P0 = 0–9, P1 = 10–20 (incl. the gap-analysis
waves 18–20). **This backlog = Waves 21–26, all Phase 1. Phase 2 now starts at Wave 27** —
superseding the earlier "P2 starts at Wave 21" note.

---

## Conventions (apply to every issue)

- **Title:** `[<GAP-ID>] <imperative title>` — e.g. `[G1.1] Score the anchor against Sim, not the fixture`.
  Where an issue realizes a roadmap item, prefix with the RM ID instead.
- **Labels:** exactly one `Wave N` + `enhancement`. (`[security]` prefix in title where apt.)
- **Phase:** board field only — **never** a repo label. All issues here: **Phase 1**.
- **Board:** org project #3. Status=Backlog, Phase=Phase 1, Priority + Size always set.
  Milestone M1.1/M1.2 and Workstream CX-* where applicable.
- **Board gotcha:** the auto-add workflow defaults Status to `Ready` and races field-setting. Set
  fields as a **separate step after all issues exist**, then re-query and sweep any `Status!=Backlog`
  back to Backlog and verify.
- **Header blockquote** (board fields are set *from this line*):
  `> **Component:** \`Astro-Mine-X\` (astro-mine-x) · **Phase 1**[ · **Milestone M1.x**] · **Priority P** · **Size S**[ · **Workstream CX-***]`
- **Body template:** header → 1–2 sentence summary → optional `### Constraints — narrow waist
  (non-negotiable)` → `### Scope & deliverables` → `### Dependencies` → `### Acceptance criteria`
  → `### Out of scope (deferred)` → `### Traceability` → footer
  `*Part of the Phase-1 UX backlog ([gap report](phase-0-1-user-surface-analysis.md)). Tracked on the [AstroMine board](https://github.com/orgs/astro-mine/projects/3) (Phase 1 · Backlog).*`
- **No AI attribution anywhere.**
- **Tooling:** `gh issue view/edit` without `--json` fails here (projects-classic). Use
  `gh issue create`, `gh issue view --json`, `gh api .../issues/N/labels` for labels, and
  `gh api graphql` for board mutations.

**Non-negotiable constraints to fold into acceptance criteria where relevant:**
- **CX-LOCAL** — the local tier is sacred: works on one workstation, offline, no account, no cluster.
- **CX-REPRO** — determinism, provenance, content-addressing.
- **conventions.md §1.1** — no private side-channels; components integrate through Core contracts.
  **Bench must never import Sim.** The console must never make a surface import another surface.

---

## Wave 21 — Make the Phase-0 claim true (5 issues)

*The only wave that unblocks anything. Until 21.2 lands, waves 22–26 describe a platform nobody
outside this workspace can run.*

| # | Repo | Title | Gap | Pri | Size | Milestone |
|---|---|---|---|---|---|---|
| 21.1 | `astro-mine-bench` | `[G1.1]` Score against Sim, not the fixture — add `--runner`, and make the stand-in unmistakable | G1.1 | High | M | M1.1 |
| 21.2 | `astro-mine-hub` | `[G1.2]` Publish the anchor content set so it can be fetched by digest | G1.2 | **High** | L | M1.1 |
| 21.3 | `astro-mine-bench` | `[G1.2]` `astro-mine-bench fetch` — populate a local registry from the published anchor content | G1.2 | High | M | M1.1 |
| 21.4 | `astro-mine-sim` | `[G2.2]` Give Sim a CLI and a README a user can start from | G2.2 | High | M | M1.1 |
| 21.5 | `astro-mine-sim` | `[G1.3]` An anchor baseline that scores non-empty against Sim | G1.3 | High | M | M1.1 |

**21.1 detail.** `astro-mine-bench score --runner fixture|sim` (default `fixture`, honest).
**Bench must not import Sim** — resolve runners through an entry-point group
(`astro_mine.bench.runners`) that `astro-mine-sim[bench]` registers into; Bench discovers, never
imports. Fix the same gap in `scripts/determinism_gate.py` (**G2.16** — the repro oracle currently
never exercises physics). Make the fixture unmistakable *in the scorecard itself* (a `runner` field
+ a visible banner), not a trailing line of prose. Today `cli.py` hardcodes
`run(spec, BaselinePolicy(), seeds=seeds)`.

**21.2 detail.** The anchor pins 9 digests (world · 6 fleet assets · prospect prior · link
ContactPlan). All 9 exist today **only** in a hand-built local registry on one developer's disk
(`files/hub-registry`, a local-workspace convention). Publish them as an immutable,
content-addressed set to private GHCR via a release workflow, reusing the shipped Hub publish path
+ Seal signing. Must stay pullable offline after first fetch. **This is the root blocker.**

**21.3 detail.** `astro-mine-bench fetch [scenario]` resolves a ScenarioSpec's pins and pulls them
via the Hub client into a local OCI-layout registry, verify-twice fail-closed. Prints the store path
for `open_bundle_store(...)`. Consider a small synthetic anchor world shipped in-package for a
5-minute offline path (also gives P3 a WorldSpec to copy — see 26.x / G2.11).

**21.4 detail.** Sim ships no console script; `python -m astro_mine.sim` is documented as a
container entrypoint and consumes a **different schema** (Sim `Scenario`) from Bench's
`ScenarioSpec` — a real trap. Add `astro-mine-sim run <scenario> [--seed] [--out run.mcap]`
accepting a **Bench ScenarioSpec id** and resolving via `sim_scenario_from_spec`. Rewrite the
35-line README (it still says *"Phase 0 — scaffolding"*): quickstart, the two scenario schemas and
when each applies, the `[bench]` extra, MCAP output.

**21.5 detail.** Verified: `run(load_scenario('lunar-polar-ice-prospecting-v1'), BaselinePolicy(),
runner=SimEpisodeRunner(store=...), seeds=(0,))` → `water_mass=0.0`, six of seven metrics `None`.
The path is real; the baseline produces nothing. Decide and implement: is `BaselinePolicy`
Sim-runnable at all, or is a Mind-composed stack the only honest anchor baseline? Ship whichever
produces a non-empty scorecard, and a golden test pinning it. **Open question flagged in the gap
report §9.**

---

## Wave 22 — Make the Phase-1 flywheel turn (5 issues)

| # | Repo | Title | Gap | Pri | Size | Milestone |
|---|---|---|---|---|---|---|
| 22.1 | `astro-mine-learn` | `[G1.4]` Export the trained policy — the CLI currently discards it | G1.4 | **High** | S | M1.2 |
| 22.2 | `astro-mine-learn` | `[G2.10]` Ship an anchor env factory so the quickstart is copy-pasteable | G2.10 | High | M | M1.2 |
| 22.3 | `astro-mine-bench` | `[G2.14]` `astro-mine-bench submit` — a CLI path to the leaderboard | G2.14 | Med | M | M1.2 |
| 22.4 | `astro-mine-allocate` | `[G2.9]` Open the solver registry — it is advertised as pluggable and is a hardcoded dict | G2.9 | Med | M | M1.2 |
| 22.5 | `docs` | `[G2.8]` Write the plugin-authoring guide — 5 live entry-point groups, zero recipes | G2.8 | High | M | M1.2 |

**22.1 detail.** `train/run.py` `main()` does `report, _export = train(...)` and drops the export;
`export_policy_package` is never imported under `train/`. Add `--export <path>` (+ `--export-format
onnx`) wiring `astro_mine.learn.export.export_policy_package`, running the existing ONNX-Runtime
equivalence gate, emitting the typed metadata sidecar with honest provenance (comms assumptions,
surrogate-fidelity caveats). **This is the commons' unit of exchange; small fix, large unblock.**

**22.2 detail.** `--env-factory your_pkg:make_env` is a placeholder — no shipped factory satisfies
it, so Learn's README quickstart cannot be run. Ship an anchor `SwarmEnv` factory (Sim-backed,
Surrogate-accelerated where budgeted) with a schema'd `TrainConfig` example — Learn ships **no**
JSON Schema and **no** reference config today, unlike Mind (6 stacks) and Guard (anchor spec).

**22.4 detail.** `solvers/registry.py` is a hardcoded `_LOADERS` dict with **no `entry_points()`
call**, while the README markets `solvers/` as "backend plugins". A community solver cannot register
without a PR to Allocate. Add an `astro_mine.allocate.solvers` entry-point group; keep CP-SAT and
the trivial stub as built-ins discovered through the same path (Learn's registry is the precedent —
its built-ins are "discovered exactly like a third-party plugin").

**22.5 detail.** Five groups work and are undocumented: `astro_mine.mind.tier_plugins` (the hub —
Allocate and Guard both register into it), `astro_mine.learn.algorithms`,
`astro_mine.learn.curricula`, `astro_mine.providers`, `astro_mine.field_models`, plus Bench's
manifest-driven metric plugins. CONTRIBUTING mentions "plugins" once, as a principle. Write the
recipe per plugin kind, with `[project.entry-points]` snippets. Best existing references to build
from: `allocate/mind.py` and `guard/mind/plugin.py` (both exceptionally well-commented). Note the
`plugin new` scaffold is **25.x**, gated on the umbrella-CLI RFC.

---

## Wave 23 — Console foundation (6 issues)

*RFC-0010 gates the rest of this wave. Issues 23.3–23.5 carry: "may be revised by RFC-0010."*

| # | Repo | Title | Gap | Pri | Size | Workstream |
|---|---|---|---|---|---|---|
| 23.1 | `docs` | **RFC-0010: the console shell and the Surface contract** | G1.5 | **High** | L | CX-GOV |
| 23.2 | `astro-mine-console` | `[setup]` Repo standup — pnpm workspace, CI, ARCHITECTURE.md | — | High | M | — |
| 23.3 | `astro-mine-console` | Design pass — mockups and design tokens before implementation | G1.5 | High | L | — |
| 23.4 | `astro-mine-console` | `@astro-mine/surface` — the contract (types only, zero deps) | G1.5 | High | M | — |
| 23.5 | `astro-mine-console` | `@astro-mine/ui` — the design system | G1.5 | High | L | — |
| 23.6 | `astro-mine-console` | `@astro-mine/console` — the shell and surface registry | G1.5 | High | L | — |

**23.2 is Wave 0**, not 23 — per convention, per-repo `[setup]` scaffold issues go in `Wave 0`
regardless of phase, Phase=Phase 1, Priority High. The repo is created from `.repo-template` and is
bare (LICENSE + README).

**23.1 — RFC-0010 scope.** Introduces new top-level packages **and** a cross-cutting convention —
the same bar RFC-0002 (Spice) and RFC-0005 (Seal) cleared, so it goes through GOVERNANCE.md. Must
record: the layering (`surface` ← `ui`/`view` ← surfaces ← `console`) and the no-cycles rule (a
shell inside `view` would be circular: `studio-ui → view`, `view/app → studio-ui`); the `Surface`
contract; **contributions keyed by Core's existing `PluginKind` vocabulary** rather than a
UI-side vocabulary (this is what makes "contribute once, use everywhere" hold in the GUI, and it
costs Core nothing — **no Core change**, `CORE_INTERFACE_VERSIONS` stays `0.1.0`); build-time
composition with runtime federation **rejected for Phase 1** because it fetches over a network and
breaks CX-LOCAL; **no new REST surface** (per-surface base URLs; the gateway stays Phase 2, as
view.md already reserves); and the Phase-1 hooks-now argument (RFC-0001's precedent). Doc impact:
new `architecture/console.md`, updates to `system.md`, `view.md`, `conventions.md §2`.

**23.3 — Design pass.** Deliverable is mockups + a token set, reviewed before code. Bar: one visual
language (retire Pico CSS and Studio's ad-hoc CSS — three visual languages exist today); light
**and** dark; WCAG 2.1 AA; keyboard-navigable; uncertainty rendered honestly (no false-precision
heatmaps); stand-ins and degraded states visibly labelled, never blank; simple enough that a student
finds the leaderboard in one click.

**23.4 — `@astro-mine/surface`.** Zero dependencies — the GUI's narrow waist. `Surface { id, title,
nav?, routes, capabilities?, contributions? }`; `Contribution` keyed by `PluginKind`; the
`InspectorSlot` resolution contract. A surface **never imports another surface**.

**23.6 — `@astro-mine/console`.** Shell, nav, routing, the surface registry, and per-surface
endpoint config injection. A surface whose `capabilities` are unmet **degrades visibly**, never
blank. Nothing depends on `console`.

---

## Wave 24 — Surfaces (6 issues)

| # | Repo | Title | Gap | Pri | Size | Milestone |
|---|---|---|---|---|---|---|
| 24.1 | `astro-mine-bench` | Leaderboard surface — `@astro-mine/bench-ui` (**closes bench#27**) | G1.6 | High | L | M1.2 |
| 24.2 | `astro-mine-studio` | `@astro-mine/studio-ui` — convert the SPA to a surface | G1.5 | High | M | M1.1 |
| 24.3 | `astro-mine-studio` | The authoring journey — wire `/intent`, `/studies`, `/campaigns/publish` into the UI | G1.5 | High | L | M1.1 |
| 24.4 | `astro-mine-studio` | `[G2.3/G2.4]` `studio serve` — one command to a working Studio | G2.3 | High | M | M1.1 |
| 24.5 | `astro-mine-hub` | `@astro-mine/hub-ui` — convert the SPA to a surface; add publish/resolve | G2.x | Med | M | M1.2 |
| 24.6 | `astro-mine-view` | Resolve `@astro-mine/view` distribution; document the harness as a dev gallery | G1.5 | **High** | M | — |

**24.1** — the leaderboard is REST-only today; M1.2's public face does not exist. Rankings,
scorecard detail, provenance, replay (reuse View's `ReplayLayer`/`TimelineScrubber`). Reads are
account-free.

**24.3** — Studio's backend exposes the full design loop (`POST /intent`, `POST /studies`,
`POST /campaigns/publish`) and **the UI calls none of them**. Today `main.tsx` reads the study from
a `?study=` URL param with no picker, no upload, no authoring. Ship: objective form → launch study →
compare → publish, plus a **seeded example study** so the surface is never empty on first open.

**24.4** — Studio has no console script and its README documents no server command; `_require()`
makes 5 of 9 routes **503** without hand-wired `[hub]` seams. `astro-mine-studio serve` should
compose the backend, wire the Hub seams, serve the built bundle (`app.py` mounts world/asset caches
but **never** `ui/dist`), and seed the example study.

**24.6 — the hard blocker.** `@astro-mine/view` is on private GitHub Packages needing a
`read:packages` token; **an outsider cannot install the UI at all** (blocks P5 and P6, and now the
console). Decide: public at the flip, vendored, or a public mirror. Also document the `lib/` demo
harness as the **developer component gallery** it is — nine committed-fixture stories; it is not the
console and should not pretend to be.

---

## Wave 25 — CLI coherence (4 issues)

| # | Repo | Title | Gap | Pri | Size |
|---|---|---|---|---|---|
| 25.1 | `docs` | **RFC-0011: the `astro-mine` umbrella CLI and command naming** | G2.1 | Med | M |
| 25.2 | `astro-mine-core` | `[G2.5]` `astro-mine-core validate <file>` — 9 authored formats, 1 has a checker | G2.5 | Med | M |
| 25.3 | `astro-mine-guard` | `[G2.6/G2.7]` Guard CLI + ship the anchor SafetySpec as package data | G2.6 | Med | M |
| 25.4 | `astro-mine-mind` | `[G2.6]` Mind CLI + a README with a stack spec in it | G2.6 | Med | M |

**25.1 — RFC-0011.** Decides the umbrella's **home and shape** (the open question): one package
depending on all components, or a **thin dispatcher** shelling out to installed `astro-mine-*`
binaries — the local-tier rule favors the dispatcher, since a dependency-heavy umbrella would drag
the whole platform into every install. Also settles naming: 8 CLIs today, 2 schemes (bare `fleet`,
`worlds`, `link`, `prospect` vs prefixed `astro-mine-bench`, `-hub`, `-cloud`, `-train`). Proposes
`astro-mine <verb>` with aliases for one deprecation cycle, and hosts `plugin new` (22.5's
scaffold) and `validate` dispatch.

**25.2** — Core owns 9 hand-authored formats (SADF, ObjectiveSpec, MissionSpec, Plan/ContingentPlan,
plugin manifest, PolicyPackage, RunProvenance, units, messages) and ships **no CLI**; only SADF has a
checker, via `fleet validate`. `jsonschema` + `pydantic` are already Core deps, so a validator adds
none — and core.md §1 explicitly says Core ships *"types and validators"*. Dispatch on `$id`/schema.

**25.3** — Guard ships a spec compiler, a validator, a signer, and a falsification harness, and
exposes **none** from a shell; `astro_mine.guard.__all__` is `["__version__"]`. Add
`validate|compile|falsify|sign`. **Ship `examples/safety_specs/anchor.safety.yaml` as package
data** — it currently sits outside `src/` and is unreachable from an installed wheel, which is why
Mind's `lunar_prospecting_anchor.yaml` must inline the whole spec and documents this as the reason.

**25.4** — Mind ships 6 reference stacks + 13 manifests as package data and its README has **zero
Python blocks** and never mentions them. Add `validate|compose|run`; put a stack spec in the README.

---

## Wave 26 — The user guide (6 issues)

*All in `docs`. Sequencing rule: **tutorials 02/03/07/08 cannot be written honestly until their
gaps close** — writing them first documents a platform that does not exist.*

| # | Title | Gap | Pri | Size | Gated on |
|---|---|---|---|---|---|
| 26.1 | Guide scaffold + `getting-started` — the honest 10-minute path | G1.7 | High | M | 21.x |
| 26.2 | Tutorials 01 (score the anchor) + 04 (author an asset) | G1.7 | High | M | 21.1–21.3 |
| 26.3 | Tutorials 02 (run it in the simulator) + 03 (train and publish a policy) | G1.7 | High | L | Waves 21, 22 |
| 26.4 | Tutorials 05 (author a world) + 06 (compose a stack) + 08 (write a plugin) | G1.7 | Med | L | 22.5, 25.3, 25.4, G2.11 |
| 26.5 | Tutorial 07 (design a swarm in Studio) + the console guide | G1.7 | Med | M | Wave 24 |
| 26.6 | Reference — CLI, all 9 file formats, personas, concepts | G1.7 | High | L | Wave 25 |

Target structure (gap report §8.4):
```
docs/guide/{getting-started.md, tutorials/, how-to/, reference/{cli,file-formats,personas}.md, concepts/}
```

---

## Wave 26b — Truth-in-docs sweep (3 issues)

| # | Repo | Title | Gap | Pri | Size |
|---|---|---|---|---|---|
| 26.7 | multi | `[G2.13]` Surface the shipped anchor content in the READMEs that hide it | G2.13 | Med | M |
| 26.8 | multi | `[G3.x]` Fix doc drift — phantom commands, "Planning" classifiers, stale status lines | G3.1–3.4 | Low | S |
| 26.9 | `astro-mine-core` | `[G3.5]` Repo hygiene — committed `.venv` and build artifacts | G3.5 | Low | S |

**26.7** — Fleet's 6-asset anchor roster, Prospect's Shackleton priors, and Mind's 6 reference
stacks all ship, are one call away, and are mentioned in **none** of their READMEs. Also **G2.12**:
`examples/` exists in only 2 of 18 repos, and **G2.11**: Worlds ships a `WorldSpec.from_yaml` front
door with **zero on-disk YAML examples** — the one real spec is authored in Python inside a build
script.

**26.8** — Hub README advertises a `cache` command that does not exist and omits `search`; Hub +
Seal `pyproject.toml` say `Development Status :: 1 - Planning`; Hub's `__init__` docstring denies its
own shipped API/UI; Sim's README says "Phase 0 — scaffolding"; the org profile package map omits
Spice/Seal/Surrogate and still says Phase 0. **G3.6** (Hub artifact naming: `astro-mine.fleet.excavator`
vs `excavation-gns` vs `shackleton_water_ice_v1`) and **G3.7** (Seal has no CLI) fold in here or spin
out if they grow.

---

## Totals

**33 issues** across 8 repos + 1 new: bench 5 · sim 2 · learn 2 · allocate 1 · hub 2 · studio 3 ·
view 1 · guard 1 · mind 1 · core 2 · console 5 · docs 8 (2 RFCs + 6 guide) · multi 2.

**Two RFCs gate real work:** RFC-0010 (console/Surface — gates wave 23–24) and RFC-0011 (umbrella
CLI — gates 25.x's dispatch surface and 22.5's scaffold).

**Critical path:** 21.2 (publish anchor content) → 21.3 (fetch) → 21.1/21.5 (honest Sim scoring) →
26.2/26.3 (the tutorials that prove the Phase-0 promise). Everything else is parallel.
