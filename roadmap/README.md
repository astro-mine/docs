# Astro-Mine — Detailed Roadmap

> **Status:** **Phases 0 and 1 are built.** The distribution track between Phase 1 and Phase 2 is in
> progress, and **Phase 2 is next.** This is both a planning document and a record: it
> elaborates the high-level [charter §10 phased roadmap](../charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md)
> and [system.md §11](../architecture/system.md) into per-phase, per-component **scope and
> requirements** at a fidelity an implementation-planning session can turn into GitHub issues —
> **without** prescribing implementation steps. For the delivered phases it also records what
> actually shipped, because a plan that never records its outcome reads like a forecast forever.

This roadmap is **derived from, and must stay aligned with**, three sources, in this precedence:

1. the [project charter](../charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md) (vision — source of truth);
2. the [flagship scenarios](../scenarios/README.md) (authoritative requirements: `LUNAR-*` / `AST-*` IDs);
3. the per-component [architecture docs](../architecture/README.md) (the *how*; each carries a §11 options/recommendations and a §12 roadmap), plus the four [distribution docs](../architecture/README.md) for what ships.

Where this document and a source disagree, the source wins and this document is corrected.

---

## How to read this

- **[Phase backbone](#phase-backbone)** — the four phases, their themes, timeframes, and exit goals.
- **[Component × phase matrix](#component--phase-matrix)** — at a glance, when each `Astro-Mine-*`
  package first lands and when it gains major extensions.
- **The four phase files** — the detail. Each opens with a phase header (window · theme · goal ·
  entry dependencies · the integration milestone that defines "done" · cross-cutting workstreams),
  then one entry per active component.
  - [Phase 0 — Commons seed](phase-0-commons-seed.md)
  - [Phase 1 — Autonomy & studio](phase-1-autonomy-studio.md)
  - [Phase 2 — Operations bridge](phase-2-operations-bridge.md)
  - [Phase 3 — Flight, mission architecture & ecosystem](phase-3-flight-mission-architecture.md)
- **[The distribution track](#the-distribution-track)** — the packaging correction between Phases 1
  and 2: one platform wheel, one CLI, one API, one front end.
- **[Cross-cutting workstreams](#cross-cutting-workstreams)** — threads that span every phase.
- **[Resolved sequencing decisions](#resolved-sequencing-decisions)** — phase-assignment ambiguities
  in the source docs, pinned down here so a planner is not guessing.

---

## Conventions

**Roadmap item IDs.** Each scoped deliverable carries a stable ID: `RM-P<phase>-<COMP>-NN`
(e.g. `RM-P0-CORE-03`), where `<COMP>` is the component short name. IDs are **append-only — never
renumber**, so issues, dependencies, and later phases can cite them. An item is sized to become
**one to a few** GitHub issues, not a single commit.

**Per-component entry shape.** Each entry has:

- **Scope & deliverables** — IDed bullets, each a coherent chunk of work with embedded normative
  force (MUST/SHOULD in the RFC-2119 sense, per [conventions.md](../architecture/conventions.md))
  and a *(trace: …)* tag back to the governing source.
- **Dependencies** — upstream items/components/contracts that must exist first.
- **Exit criteria** — the observable signal this phase's slice is done (usually a
  [Bench](../architecture/bench.md) gate or a scenario milestone).
- **Deferred** — what is explicitly pushed to a later phase (keeps scope honest; mirrors the
  narrow-waist discipline).

**Options vs. decisions.** Each component doc's §11 presents options with a **recommended** choice.
This roadmap scopes the **recommended option as the baseline**; alternatives are out of scope for
an item unless the item says otherwise. Genuine in-phase forks are called out where they remain open.

**Honesty discipline.** Timeframes (`~0–12 mo`, etc.) are **illustrative** (charter §9), not
commitments. Every "MUST validate / reproduce / score" requirement assumes the platform's
determinism-and-provenance discipline (conventions.md §5, §11).

---

## Phase backbone

| Phase | Window | Theme | Headline ships | Goal (exit definition) | State |
|---|---|---|---|---|---|
| **[0](phase-0-commons-seed.md)** | ~0–12 mo | Commons seed | Core v0.1 · Spice · Sim · Worlds · Fleet · Bench (+ Prospect, Link MVP, local Cloud) | A runnable, reproducible benchmark on the lunar-polar anchor scenario — *clone, run, score in an afternoon* | **built** |
| **[1](phase-1-autonomy-studio.md)** | ~12–30 mo | Autonomy & studio | Mind · Learn · Allocate · Guard · Studio · Hub · Surrogate · Seal · full Link · full Cloud; the console and the CLI | Become the MARL + planning commons; first public leaderboards & community plugins | **built** |
| **[distribution](#the-distribution-track)** | — | Packaging correction | one platform wheel · one CLI · one API · one front end | Four distributions instead of eighteen repositories, with import paths, schemas and public APIs unchanged | **in progress** |
| **[2](phase-2-operations-bridge.md)** | ~30–54 mo | Operations bridge | Ops · Bridge · the full View ops viewer; digital-twin shadow mode | Cross the sim→operations threshold on terrestrial analogs | next |
| **[3](phase-3-flight-mission-architecture.md)** | 54 mo + | Flight, mission architecture & ecosystem | Bridge flight adapters; **Transit · Trajectory · Sizing · Ledger** + small-body/microgravity extensions; NEO sample-return → asteroid-mining scenarios | Become the default stack for surface ISRU *and* interplanetary resource missions | later |

**The governing principle:** the narrow waist barely changes — later phases add edges, not core
rewrites. Success is measured by how *little* [Core](../architecture/core.md) changes as the
platform grows (system.md §11; charter §8).

---

## Component × phase matrix

`●` first lands / MVP · `▲` major extension · `·` not active · `(○)` schema hook or thin reuse only.

| Layer | Component | P0 | P1 | P2 | P3 |
|---|---|:--:|:--:|:--:|:--:|
| Backbone | [Core](../architecture/core.md) | ● v0.1 | ▲ Mission/Phase/Regime + ObjectiveSpec hooks | · | · |
| | [Spice](../architecture/spice.md) ‡ | ● shared SPICE foundation | · | · | (○ Transit reuse) |
| | [Seal](../architecture/seal.md) ¶ | · | ● artifact-integrity companion (sign/verify/SLSA/SBOM) | ▲ keyless (Fulcio/Rekor) + trust-root policy | · |
| | [Bench](../architecture/bench.md) | ● anchor + repro harness | ▲ public leaderboards, Cloud eval | ▲ analog/twin scenarios | ▲ NEO/asteroid + mission metrics |
| | [Hub](../architecture/hub.md) | · | ● registry, signing, gating | ▲ replication/mirrors | ▲ mission-arch artifact types |
| | [Cloud](../architecture/cloud.md) | ● local/container-first | ● full K8s/Ray/Argo | ▲ stronger tenancy | ▲ mission-design sweep classes |
| World/env | [Worlds](../architecture/worlds.md) | ● lunar polar | ▲ Mars, GPU illumination | · | ▲ small/irregular bodies, microgravity regolith |
| | [Prospect](../architecture/prospect.md) | ● GP belief + ground truth | ▲ GMRF/deep-gen, richer info-gain | ▲ ops belief from real sensors | (reuse for asteroid fields) |
| | [Link](../architecture/link.md) | ● MVP: LOS+occlusion, relay+DSN windows, masks | ▲ constellation, multi-hop/CGR, Earth-link windows | ▲ ns-3 opt, live-mission pred (gated) | ▲ deep-space DSN/light-time/DTN |
| | [Transit](../architecture/transit.md) | · | (○) | · | ● environment + hazard fields |
| Assets | [Fleet](../architecture/fleet.md) | ● anchor library + toolchain | ▲ families, Hub/Studio integration | ▲ Bridge hardware mapping | ▲ launch/return vehicles, propulsion |
| Simulation | [Sim](../architecture/sim.md) | ● engine framework + initial engines, MCAP, determinism | ▲ Surrogate integ, Brax/MJX scale, error-budget scheduler | ▲ digital-twin shadow, terramechanics validation | ▲ microgravity engine, multi-regime propagation, multi-phase sequencer |
| | [Surrogate](../architecture/surrogate.md) | · | ● granular GNN + error bounds | ▲ neural-operator fields, ops drift | ▲ microgravity contact |
| Autonomy | [Mind](../architecture/mind.md) | · | ● 3-tier hierarchy, BT/PDDL/OMPL, Guard-wrap | ▲ online replanning, edge split | ▲ flight via Bridge; cross-phase |
| | [Learn](../architecture/learn.md) | · | ● Gym/PettingZoo, CommsModel, MAPPO/QMIX, ONNX | ▲ auto-curricula, learned allocation heuristics, sim-to-real | · |
| | [Allocate](../architecture/allocate.md) | · | ● CP-SAT IR, power/comms/terrain, anytime | ▲ MILP, learned guidance, decomposition, ops hardening | ▲ mission-level joint assignment |
| | [Guard](../architecture/guard.md) | · | ● SafetySpec, Rust core (CBF-QP+STL/MTL+simplex), PolicyShield | ▲ multi-agent latency, HJ filters, edge sidecar | ▲ embeddable core; per-phase deep-space assurance |
| Design/ops | [Studio](../architecture/studio.md) | · | ● intent→trade study→Campaign; LLM-assist | ▲ Campaign hand-off to Ops | ▲ Mission Architect mode |
| | [Ops](../architecture/ops.md) | · | · | ● orchestration runtime, shadow mode, SLAM, console | ▲ flight-asset & multi-phase mission ops |
| | [Bridge](../architecture/bridge.md) | · | (○ schemas/tags in Core) | ● hexagonal port + sim/ROS2 adapters, identical-plan test, CCSDS basics | ▲ cFS/F´, CFDP/DTN-BP, HIL, DSN (gated) |
| | [View](../architecture/view.md) | (○ thin reuse) | (○ thin reuse) | ● full ops viewer + explanation | ▲ heliocentric/multi-body, mission timeline |
| Mission-arch | [Trajectory](../architecture/trajectory.md) | · | (○) | · | ● impulsive→low-thrust→global, oracles |
| | [Sizing](../architecture/sizing.md) | · | · | · | ● OpenMDAO closure, staging, manifesting, SADF emit |
| | [Ledger](../architecture/ledger.md) | · | (○ objective hook) | · | ● ValueModel, CERs, MC uncertainty |

‡ [Spice](../architecture/spice.md) — the shared SPICE foundation; a Phase-0 deliverable sequenced
before the Link MVP.

¶ [Seal](../architecture/seal.md) — the shared artifact-integrity companion (signing / verification /
SLSA / SBOM); a Phase-1 deliverable, additive and non-urgent, that must not gate the lunar MVP.

**A component is not a distribution.** Every row above is a subpackage of
[`astro-mine-platform`](../architecture/platform.md), except the front-end packages
([View](../architecture/view.md), [Console](../architecture/ui.md)), which are packages of
[`astro-mine-ui`](../architecture/ui.md). Nothing in this matrix is separately released — see
[the distribution track](#the-distribution-track).

---

## The distribution track

Between Phase 1 and Phase 2 the platform's *packaging* was corrected: eighteen component
repositories became four distributions, with import paths, public APIs, schemas and their `$id`s,
entry-point groups, and configuration semantics **unchanged**. It adds no capability, which is why it
is not a phase — but it is real work with real exit criteria, and two of its five items are not done.

See [`conventions.md`](../architecture/conventions.md) §7.1 for the rule, and
[platform.md](../architecture/platform.md) · [cli.md](../architecture/cli.md) ·
[api.md](../architecture/api.md) · [ui.md](../architecture/ui.md) for the detail.

**Scope & deliverables**

- **RM-DIST-01** — **One platform wheel.** Consolidate every `astro_mine.<component>` package, test
  suite, schema source and example into `astro-mine-platform`; adopt maturin (Guard's Rust core MUST
  be in the wheel); merge eighteen dependency sets into one, with heavy optional stacks behind
  `<component>-<extra>` extras. Import paths, schemas, entry points and algorithms MUST be unchanged.
  *(trace: platform.md; conventions.md §7.1)* — **done**
- **RM-DIST-02** — **One CLI.** Remove every command surface from the platform and provide it from
  `astro-mine-cli` under one grammar, `astro-mine <component> <verb>`. The platform MUST declare no
  console scripts; a committed parity fixture MUST assert every verb and argument still matches what
  the per-component binaries declared. *(trace: cli.md §7, §8; conventions.md §13)* — **done**
- **RM-DIST-03** — **One REST tier.** Stand up `astro-mine-api` and move the Hub, Studio, Cloud and
  Bench route modules into it, over the components' unchanged public APIs. Restore the REST tests the
  consolidation had to exclude; converge the health-endpoint and error conventions; ship one image and
  one chart. A component MUST NOT ship a FastAPI application. *(trace: api.md; conventions.md §3)*
- **RM-DIST-04** — **One front end.** Stand up `astro-mine-ui` as one pnpm workspace holding the
  application and its packages, with the layering check asserting the dependency direction. **This is
  a rebuild, not a move.** It was originally scoped as relocating five package trees into one
  workspace; the front end is instead re-implemented as a multi-page Next.js application on Material
  UI, calling the REST tier through a generated client. Every capability the previous front end had
  is carried over; almost none of the code is, and the `Surface` contract is retired
  ([ui.md](../architecture/ui.md) §11). **Delivered** across Waves 28–30, deployment included: the
  static bundle, its runtime configuration and the image that serves it
  ([ui.md](../architecture/ui.md) §8.1). *(trace: ui.md §3, §5, §8, §12; conventions.md §2.1)*
- **RM-DIST-05** — **Retire the component repositories.** Once nothing references them: rehome the
  open issues, archive or delete the eighteen repositories, and sweep the remaining links. A link to a
  deleted repository is worse than no link. *(trace: conventions.md §13)*

**Dependencies** — RM-DIST-01 before everything; RM-DIST-02 landed with it; RM-DIST-03 and RM-DIST-04
are independent of each other; RM-DIST-05 last.

**Exit criteria** — four distributions build and test against the platform at `HEAD`; a user installs
`astro-mine-cli` and holds the whole platform at one self-consistent version; the local tier still
runs with no service, no account and no extra (CX-LOCAL); layering tests assert the import graph
(conventions.md §11); and no document or code references a retired repository.

**Deferred** — a unified REST gateway (Phase 2 at the earliest, if ever); public PyPI and public npm
publication (the public flip — VERSIONING.md §6); the artifact-name migration (also the flip).

---

## Cross-cutting workstreams

These threads run through **every** phase; each phase file lists the phase-specific slice. They are
not owned by one component, but they gate the phase exit.

- **CX-LOCAL — The local tier is sacred.** Every component's library/local tier MUST run on one
  workstation with no cloud and no accounts (conventions.md §7 tier 1). A change that breaks this is
  a defect in any phase.
- **CX-REPRO — Determinism, provenance, content-addressing.** Seeded, lockfile-pinned, content-
  addressed artifacts with recorded provenance, pervasive from P0; [Bench](../architecture/bench.md)
  is the platform-wide reproducibility oracle (conventions.md §5, §11).
- **CX-SEC — Security & supply chain.** Sigstore/cosign signing, SLSA provenance, SBOMs, OPA
  capability gating, org defaults (Dependabot/secret-scanning/push-protection); plugin isolation
  (out-of-process/gVisor; WASM forward-looking) (conventions.md §9). The signing / provenance / SBOM
  implementation is consolidated in [Seal](../architecture/seal.md) ([Seal](../architecture/seal.md),
  Phase 1) — one shared companion, the single home for `cryptography`, rather than a signer copied per
  producer.
- **CX-GOV — Governance, license, export-control posture** established **up front**, before the
  community forms (charter §11): Apache-2.0, the governance defaults in `astro-mine/.github`, and a
  documented EAR/ITAR posture and capability-tag taxonomy.
- **CX-MISSION — Multi-regime schema hooks.** The *only* early obligation of the opt-in
  mission-architecture track is **reserving the additive Core schema hooks in Phase 1**
  (`MissionSpec`/`regime`/`PhaseTransition`, `ObjectiveSpec`, propulsion/return SADF capabilities,
  `operational_targeting` tag). Implementations land in Phase 3 and **must not gate the lunar MVP**
  ([mission-model](../architecture/mission-model.md) §3). *(This workstream was `CX-RFC0001` while the
  design lived in a separate proposal; the scope is unchanged, and the board's `Workstream` field needs
  the same rename.)*
- **CX-S2R — Sim-to-real credibility.** Uncertainty-honest claims from P0; physics validation against
  external oracles with explicit error budgets; terrestrial-analog validation in P2 (charter §8).
- **CX-OBS — Observability.** OpenTelemetry traces/metrics/logs, Prometheus/Grafana/Loki, in every
  service as it ships (conventions.md §10).

---

## Resolved sequencing decisions

The source docs are mostly consistent on phase assignment; these four points carried minor
ambiguity and are pinned here. Each phase file follows these.

1. **Link MVP is Phase 0** (not deferred to Phase 1). The anchor scenario's comms-denied PSR
   coordination requires Link's observation masks and relay/DSN contact windows to be real in P0
   (link.md §12; `LUNAR-TR-003`). The **constellation / multi-hop / CGR** build-out is Phase 1.
2. **Cloud's container-first principle is Phase 0; the hosted scale-out platform is Phase 1.** Every
   P0 workload is built container-first and cluster-ready, but the dependency-free local tier is all
   P0 actually requires (cloud.md §12).
3. **Prospect is Phase 0.** Though absent from the charter §10 "ships" prose, the anchor scenario's
   belief field + ground-truth isolation are P0 deliverables (system.md §11; scenario §15).
4. **Surrogate is early-Phase-1, ordered after the minimum runnable loop** — it consumes Phase-0 Sim
   (surrogate.md §12). **View** has a sanctioned **thin-slice reuse from P0/1** (globe + MCAP replay
   for demos/teaching) even though it formally ships in P2 (view.md §12).

---

## License

Apache-2.0 — see [LICENSE](../LICENSE).
