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
| **World & environment** | [Worlds](worlds.md) · [Prospect](prospect.md) · [Link](link.md) |
| **Assets** | [Fleet](fleet.md) |
| **Simulation** | [Sim](sim.md) · [Surrogate](surrogate.md) |
| **Autonomy & coordination** | [Mind](mind.md) · [Learn](learn.md) · [Allocate](allocate.md) · [Guard](guard.md) |
| **Design & operations** | [Studio](studio.md) · [Ops](ops.md) · [Bridge](bridge.md) · [View](view.md) |

[Core](core.md) is the "narrow waist" — the single most important package; if only one thing is
designed superbly, it must be Core.

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
