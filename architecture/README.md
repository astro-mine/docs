# Astro-Mine — Technology Architecture

Technology architecture for the [Astro-Mine](https://github.com/astro-mine) platform — the
open-source commons for designing, simulating, and operating planetary robotic swarms for
exploration and in-situ resource utilization (ISRU).

> **Status:** Phases 0 and 1 are **built** — the commons seed and the autonomy-and-studio stack ship
> and run. Phase 2 (operations bridge) is next. These documents describe what exists where they
> describe Phases 0–1, and intended design where they describe Phases 2–3; each component doc's
> header says which. They are derived from, and must stay aligned with, the
> [project charter](../charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md).

## How these documents fit together

- **[Scenarios](../scenarios/README.md)** — the **flagship use scenarios** (lunar polar ice;
  asteroid mining) the platform must satisfy. They are the authoritative requirements source
  these architecture docs are derived from: scenarios say *what* the platform must accomplish,
  this directory says *how*.
- **[system.md](system.md)** — the **integration view**: every component, where it runs, who
  uses it, what data it touches, and exactly how the pieces communicate. **Start here.**
- **[conventions.md](conventions.md)** — the **cross-cutting technology standards** (languages,
  schemas, transport, data, deployment, security, observability, naming). Normative for every
  component and every distribution; the per-component docs reference it rather than restating it.
- **One file per distribution** — what ships, how it is built, and what each repository must not do.
- **One file per component** — detailed architecture for each `Astro-Mine-*` component,
  using a shared 12-section template: purpose, architecture principles, application, runtime,
  data, integration, infrastructure, performance, security/safety, observability, options &
  recommendations, and roadmap alignment.

## Distributions — what actually ships

A **component** is a unit of design. A **distribution** is a unit of release. There are four, and
every component belongs to at least one:

| Distribution | Kind | What it is |
|---|---|---|
| **[platform.md](platform.md)** | Python wheel | `astro-mine-platform` — every component as `astro_mine.<name>`. A library; no commands, no server, no front end. |
| **[cli.md](cli.md)** | Python wheel | `astro-mine-cli` — the one executable, `astro-mine <component> <verb>`. |
| **[api.md](api.md)** | wheel + image | `astro-mine-api` — every REST surface as route modules over the library. *Stood up.* |
| **[ui.md](ui.md)** | npm `@astro-mine/*` | `astro-mine-ui` — the console application, the generated API client, the design system, View, and the artifact inspectors. *Stood up; every page ships.* |

Read the distribution docs when the question is *how does this ship, get built, or get released*, and
the component docs when the question is *how does this work*.

## Components by layer

| Layer | Components |
|---|---|
| **Commons backbone** | [Core](core.md) · [Spice](spice.md) ‡ · [Seal](seal.md) ‡ · [Bench](bench.md) · [Hub](hub.md) · [Cloud](cloud.md) |
| **World & environment** | [Worlds](worlds.md) · [Prospect](prospect.md) · [Link](link.md) · [Transit](transit.md) † |
| **Assets** | [Fleet](fleet.md) |
| **Simulation** | [Sim](sim.md) · [Surrogate](surrogate.md) |
| **Autonomy & coordination** | [Mind](mind.md) · [Learn](learn.md) · [Allocate](allocate.md) · [Guard](guard.md) |
| **Mission architecture & logistics** † | [Trajectory](trajectory.md) · [Sizing](sizing.md) · [Ledger](ledger.md) |
| **Design & operations** | [Studio](studio.md) · [Ops](ops.md) † · [Bridge](bridge.md) † · [View](view.md) ◊ · [Console](ui.md) ◊ |

[Core](core.md) is the "narrow waist" — the single most important component; if only one thing is
designed superbly, it must be Core.

† **Not yet built.** [Ops](ops.md) and [Bridge](bridge.md) are Phase 2; [Transit](transit.md),
[Trajectory](trajectory.md), [Sizing](sizing.md) and [Ledger](ledger.md) are the Phase-3
mission-architecture track (see [mission-model.md](mission-model.md) and [system.md](system.md) §13).
Each lands as a subpackage of [`astro-mine-platform`](platform.md) — a new layer, and no new
distribution.

‡ **Core companions.** [Spice](spice.md) and [Seal](seal.md) each realize a vocabulary Core defines
but cannot host — frame/time resolution needs SPICE, artifact integrity needs crypto, and both are
exactly the heavy dependencies the narrow waist excludes ([core.md](core.md) §2 principle 3). Each is
the platform's *single* implementation of its concern, so an aberration convention or a signature
encoding is decided once. Consolidation does not weaken the argument: the point was never that a user
could avoid installing SPICE or crypto, it is that exactly one code path resolves a frame and exactly
one decides whether a signature is valid.

◊ **Front-end packages.** [View](view.md) and **Console** are TypeScript packages of
[`astro-mine-ui`](ui.md), not Python components — and [ui.md](ui.md) is their design authority.
`conventions.md` §2's Python-reachability rule binds components; a front-end package renders
capability a component already exposes rather than adding its own. **Console** is the platform's
single GUI front door: one multi-page application in which every component with a web face is a set
of pages, so one application spans every component without any of them importing another. It changes
nothing in [Core](core.md): its artifact inspectors are keyed by Core's existing `PluginKind`
vocabulary,
consumed by its published `$id` rather than extended.

## Multi-regime missions

> Implementation lands in **Phase 3**; the additive Core schema hooks were reserved in **Phase 1**.
> The extension supports end-to-end interplanetary resource missions (asteroid mining, NEO
> sample-return, cislunar logistics) by generalizing "a campaign on a world" into a **Mission** of
> **Phases** across **Regimes**. A single-`surface`-phase Mission is exactly today's campaign, so the
> change is additive and existing scenarios are unchanged. It is **opt-in and must not gate the
> lunar MVP**.

- **[mission-model.md](mission-model.md)** — the Mission/Phase/Regime model and the additive
  Core schema sketch (SADF, Environment API, message schemas). Start here for the extension.
- **New components:** [Transit](transit.md) (deep-space environment) and the **Mission
  architecture & logistics** layer — [Trajectory](trajectory.md), [Sizing](sizing.md),
  [Ledger](ledger.md).
- **Extended (not replaced):** the existing components above gain multi-regime scope for small
  bodies, microgravity, deep-space comms, propulsion, and multi-phase operations — see
  [system.md](system.md) §13.2 for the per-component list.
- **Dual use:** [Trajectory](trajectory.md) is design-time only. Reference trajectories and Δv
  budgets are descriptive artifacts; operational maneuver targeting and guided atmospheric entry are
  out of scope and gated by an `operational_targeting` capability tag (`conventions.md` §12).

## Conventions for these docs

- Each component doc carries an H1 title and a blockquote (layer · phase · which distribution it
  ships in · one-line role · link to conventions).
- Cross-references use relative links (e.g. `[Sim](sim.md)`); cross-cutting decisions cite
  `conventions.md` by section.
- Where there is genuine uncertainty, options are documented with a marked recommendation
  (see each doc's §11).
- **This directory is where a decision is recorded.** There is no separate proposal archive: a
  cross-cutting decision lands in `conventions.md`, a component's own contract lands in its
  document, and scope lands in the charter. A change to any of them is an ordinary pull request, and
  what protects a published interface is the machinery in `conventions.md` §3 and §11, not a process
  gate.
- Per project policy, no AI-authorship attribution appears in any file. (References to the
  Anthropic Claude API in [Studio](studio.md) are a deliberate *technology choice* for optional
  LLM-assisted intent capture, not attribution.)

## License

Apache-2.0 — see [LICENSE](../LICENSE).
