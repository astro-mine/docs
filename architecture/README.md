# Astro-Mine — Technology Architecture

Technology architecture for the [Astro-Mine](https://github.com/astro-mine) platform — the
open-source commons for designing, simulating, and operating planetary robotic swarms for
exploration and in-situ resource utilization (ISRU).

> **Status:** Phase-0 draft. These documents describe *intended* architecture; nothing is built
> yet. They are derived from, and must stay aligned with, the
> [project charter](../charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md).

## How these documents fit together

- **[system.md](system.md)** — the **integration view**: every component, where it runs, who
  uses it, what data it touches, and exactly how the pieces communicate. **Start here.**
- **[conventions.md](conventions.md)** — the **cross-cutting technology standards** (languages,
  schemas, transport, data, deployment, security, observability). Normative for every component;
  the per-component docs reference it rather than restating it.
- **One file per component** (below) — detailed architecture for each `Astro-Mine-*` package,
  using a shared 12-section template: purpose, architecture principles, application, runtime,
  data, integration, infrastructure, performance, security/safety, observability, options &
  recommendations, and roadmap alignment.

## Components by layer

| Layer | Components |
|---|---|
| **Commons backbone** | [Core](core.md) · [Bench](bench.md) · [Hub](hub.md) · [Cloud](cloud.md) |
| **World & environment** | [Worlds](worlds.md) · [Prospect](prospect.md) · [Link](link.md) · [Transit](transit.md) † |
| **Assets** | [Fleet](fleet.md) |
| **Simulation** | [Sim](sim.md) · [Surrogate](surrogate.md) |
| **Autonomy & coordination** | [Mind](mind.md) · [Learn](learn.md) · [Allocate](allocate.md) · [Guard](guard.md) |
| **Mission architecture & logistics** † | [Trajectory](trajectory.md) · [Sizing](sizing.md) · [Ledger](ledger.md) |
| **Design & operations** | [Studio](studio.md) · [Ops](ops.md) · [Bridge](bridge.md) · [View](view.md) |

† Added by [RFC-0001](../rfc/0001-multi-regime-missions.md) (accepted; implementation Phase 3). [Core](core.md) is the "narrow waist" — the single most important package; if only one thing is designed superbly, it must be Core.

## Multi-regime missions (RFC-0001, accepted)

> **Status: Accepted** ([RFC-0001: Multi-regime missions](../rfc/0001-multi-regime-missions.md)) —
> implementation lands in **Phase 3**; the additive Core schema hooks are reserved in **Phase 1**.
> The extension supports end-to-end interplanetary resource missions (asteroid mining, NEO
> sample-return, cislunar logistics) by generalizing "a campaign on a world" into a **Mission** of
> **Phases** across **Regimes**. A single-body surface campaign is the degenerate one-phase case,
> so the change is additive and existing scenarios are unchanged.

- **[mission-model.md](mission-model.md)** — the Mission/Phase/Regime model and the additive
  Core schema sketch (SADF, Environment API, message schemas). Start here for the extension.
- **New components:** [Transit](transit.md) (deep-space environment) and the **Mission
  architecture & logistics** layer — [Trajectory](trajectory.md), [Sizing](sizing.md),
  [Ledger](ledger.md).
- **Extended (not replaced):** the existing components above gained multi-regime scope for small
  bodies, microgravity, deep-space comms, propulsion, and multi-phase operations — see
  [RFC-0001](../rfc/0001-multi-regime-missions.md) §4 for the per-component list.

## Conventions for these docs

- Each component doc carries an H1 title and a blockquote (layer · phase · one-line role · link
  to conventions).
- Cross-references use relative links (e.g. `[Sim](sim.md)`); cross-cutting decisions cite
  `conventions.md` by section.
- Where there is genuine uncertainty, options are documented with a marked recommendation
  (see each doc's §11).
- Per project policy, no AI-authorship attribution appears in any file. (References to the
  Anthropic Claude API in [Studio](studio.md) are a deliberate *technology choice* for optional
  LLM-assisted intent capture, not attribution.)

## License

Apache-2.0 — see [LICENSE](../LICENSE).
