# Astro-Mine — Flagship Scenarios

> **Status:** Normative. These are the **authoritative, high-level scenario documents
> that drive requirements** — the layer between the [project charter](../charter/Swarm_Exploration_ISRU_Orchestrator_OSS_Project.md)'s
> vision and the per-component [technology architecture](../architecture/README.md). They are
> derived from, and must stay aligned with, the charter and `architecture/`. Scenario 1 is built and
> shipping; scenario 2 is a Phase-3 design.

A **scenario** is a concrete, measurable mission the platform must be able to design, simulate,
score, and (eventually) operate end to end. Scenarios turn the charter's ambition into testable
requirements per component and into reproducible [Bench](../architecture/bench.md) benchmarks.
They are the requirements **source of truth**: where the architecture docs say *how a component
works*, the scenario docs say *what the platform must accomplish* — and trace that down to
per-component requirements.

## The scenario set

The two flagship scenarios deliberately **bracket the platform's scope** — the single-regime
surface case and the full multi-regime launch-to-return case — so that together they exercise
nearly every component and both the design and operations loops.

| # | Scenario | Mission shape | Roadmap | Status |
|---|---|---|---|---|
| 1 | [Lunar polar water-ice prospecting & extraction](1-lunar-polar-ice-prospecting.md) | Single `surface`-phase Mission | **Phase 0** anchor | Draft |
| 2 | [Asteroid mining (launch & return)](2-asteroid-mining.md) | Full multi-regime Mission (`launch_ascent → interplanetary_transit → proximity_orbit → surface → ascent_return → earth_interface`) | **Phase 3** capstone (NEO sample-return stepping-stone) | Draft |

Scenario 1 is the **Phase-0 anchor** the whole MVP is built to run; Scenario 2 is the **Phase-3
capstone**, modeled at baseline as a **NEO rendezvous + sample-return** mission — the named
stepping-stone toward full asteroid mining ([mission-model](../architecture/mission-model.md) §3).
A single-`surface`-phase Mission (Scenario 1) is the degenerate one-phase case of the
Mission/Phase/Regime model, so the two are points on one continuum, not different systems.

## How a scenario flows into the rest of the platform

```
charter (vision)
   └─► scenario doc (this directory) ──┬─► derived requirements (§12) ─► per-component architecture (../architecture/)
                                       ├─► design/operation workflows (§8) ─► Studio / Ops surfaces
                                       └─► evaluation & metrics (§13) ─► Bench benchmark + leaderboard
```

## Shared document template

Both scenario documents follow one **shared section template**, mirroring the shared-template
convention already used in [`architecture/`](../architecture/README.md). Each carries an H1
title and a header blockquote (scenario id · anchor body · regime(s) · roadmap phase · status ·
links to charter / architecture), then:

1. **Summary** — one-paragraph elevator description.
2. **Strategic rationale** — why this is a flagship scenario, what capability it proves, who it serves.
3. **Mission objective & success criteria** — the concrete, measurable goal + quantified acceptance criteria and stretch goals.
4. **Mission / Phase / Regime breakdown** — the Mission as an ordered set of Phases across Regimes.
5. **Environment & world** — body, terrain, illumination/PSRs, thermal, resource field + uncertainty, comms geometry, deep-space hazards.
6. **Fleet & assets** — the heterogeneous robots/spacecraft, roles, key declared SADF capabilities, scale, reusable-LEO inventory.
7. **Concept of operations (ConOps)** — narrative walkthrough of the *mission* unfolding.
8. **Design & operation workflows** — complete, end-to-end description of how the *platform* is used to design and to run the scenario, in both modes.
9. **Hard problems exercised** — which charter §6 (research) and §8 (engineering) problems the scenario stresses.
10. **Constraints & assumptions** — power, comms, thermal, Δv, schedule, microgravity, export-control + explicit modeling assumptions.
11. **Components exercised** — per-package mapping: what the scenario demands of each `Astro-Mine-*` component.
12. **Derived requirements** — the authoritative, traceable requirements, in four parts: **functional & technical**, **UX / high-level workflows**, **data**, and **security**.
13. **Evaluation & metrics** — what "good" means; the Bench scenario(s), metrics, scoring/value function, reproducibility.
14. **Dual-use & export-control considerations.**
15. **Roadmap alignment.**
16. **Open questions.**
17. **References.**

## Conventions

- **Requirement IDs.** Each derived requirement carries a stable ID so component specs and Bench
  metrics can trace to it: `LUNAR-<CAT>-NNN` (Scenario 1) and `AST-<CAT>-NNN` (Scenario 2),
  where `<CAT>` ∈ `FR` (functional), `TR` (technical), `UX` (user-experience/workflow),
  `DR` (data), `SR` (security). IDs are append-only; never renumber.
- **Options vs. decisions.** Where there are genuinely multiple, comparably-valuable approaches,
  the doc presents *all options* and **highlights the recommended one** with rationale.
  Settled or platform-mandated choices are stated directly. The recommended choices together
  form one coherent, feature-complete baseline.
- **Honesty discipline.** Uncertainty is first-class (conventions.md §1.6); mission-specific
  numbers (production rates, Δv, target IDs) are **illustrative baselines**, not commitments;
  sim-to-real credibility is framed, not overclaimed.
- **Naming.** Files are kebab-case `.md` with a 1-indexed numeric prefix; relative cross-links;
  Mermaid for diagrams (renders inline on GitHub) plus ASCII where it matches `system.md` style.

## License

Apache-2.0 — see [LICENSE](../LICENSE).
