# Astro-Mine-Console — Technology Architecture

> Layer: **Design & operations (the single GUI front door)** · Phase: **1** · Added by [RFC-0010](../rfc/0010-console-surface-contract.md)
> One GUI, not an app per component — a thin, stable contract with thick, swappable edges.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Console` is the platform's **single graphical front door**. Every other component
already exposes its capability from Python and, where it has a web edge, from its own FastAPI. What
did not exist was one place a human could start. The console is that place: a static single-page
application that composes per-component **surfaces** into one navigable shell.

It does, and only does:

- **Compose surfaces.** Each component owns a surface package (`@astro-mine/bench-ui`,
  `studio-ui`, `hub-ui`, …) published from its own repo; the console merges their navigation,
  mounts their routes, and indexes their contributions.
- **Own the shell.** Navigation, routing, theming, the surface registry, the `InspectorSlot`
  resolver, and per-surface endpoint configuration.
- **Ship the design system.** `@astro-mine/ui` — tokens, primitives, accessibility, light/dark —
  so the platform has one visual language instead of three.
- **Ship the contract.** `@astro-mine/surface` — the types every surface implements and the shell
  consumes, with **zero runtime dependencies**.

**Explicitly out of scope.** The console **computes nothing** and **stores nothing
authoritative**. It introduces **no REST API of its own** and **no gateway**: each surface talks to
its own component's existing FastAPI at its own base URL (§6). It is **not** the operations
console — supervisory control, command authority, and live telemetry are [Ops](ops.md) and
[View](view.md) in Phase 2 (§12). It is not a visualization library: the globe, replay, timeline,
and frame helpers are [View](view.md)'s, and `@astro-mine/ui` does not re-implement them.

**It is a front-end package set, not a component.** This distinction is load-bearing.
`conventions.md` §2 requires that *"the public API surface of any component MUST be reachable from
Python"*, and §2's own carve-out excludes front-end packages — not as an exemption but as a
consequence: a front-end package renders capability a component already exposes, and adds none of
its own. *A front-end package that needed its own Python API would be a component wearing the wrong
clothes.* Nothing in this document creates platform capability; it describes how existing
capability is surfaced.

**Primary users:** mission designers (the least CLI-tolerant audience — for them the GUI *is* the
product), educators and students, and benchmark researchers reading the leaderboard. Secondarily
every developer, who uses the console to inspect an artifact without writing a script.

**Charter alignment:** §2 (designers, educators/students as named audiences), §8 (the
god-interface failure mode a shell must avoid), §11 (scope explosion mitigated by *"ruthless
narrow-waist discipline"*).

---

## 2. Architecture principles

The first three are the normative layering rules of [RFC-0010](../rfc/0010-console-surface-contract.md),
each a transplant of an existing platform rule rather than a new invention.

1. **`@astro-mine/surface` declares zero runtime dependencies.** Not "few" — zero. It is the GUI's
   narrow waist; every surface and the shell agree on it, so it must not drag anything into their
   installs. This is [core.md](core.md) §2 principle 3 transplanted one layer up.
2. **A surface never imports another surface.** Surfaces are siblings, wired together only by the
   shell and only through the contribution model (§3). This is the GUI's transplant of
   `conventions.md` §1.1 — components MUST NOT create private side-channels that bypass Core
   contracts — and the direct analogue of *Bench must never import Sim*.
3. **Nothing depends on `@astro-mine/console`.** The shell is the top of the graph: composed, never
   imported. This is what keeps the graph acyclic (§11).
4. **The rules are enforced mechanically.** `scripts/check-layering.mjs` in `astro-mine-console`
   fails the build on a manifest dependency on the console, a runtime dependency in `surface`, or a
   source import pointing sideways or up — type-only imports included, because a type dependency is
   still a direction in the layer graph. *A layering rule enforced only by review is a layering rule
   that erodes.*
5. **Degrade visibly, never blank.** A surface whose declared `capabilities` are unmet renders an
   explicit, self-explanatory state — *"Hub not configured"* — and **stays in the navigation**. A
   missing backend is a *state*, not an absence ([view.md](view.md) principle 5).
6. **Honesty is a UI concern.** The platform's rule that a stand-in must never look like the real
   thing only holds if the primitives make it cheap. A fixture-scored result must *look*
   fixture-scored; uncertainty must render *as* uncertainty. These ship as shared components in
   `@astro-mine/ui` precisely so no surface has to re-invent honesty — or quietly skip it.
7. **Adding a component to the GUI is publishing a package, not modifying the console.** If a new
   surface needs a console change beyond its one registry line, the contract is wrong and RFC-0010
   needs amending. Treat that as the design's acceptance test.
8. **The architecture must not assume read-only.** Phase 1 is comparison and inspection, but the GUI
   grows to authoring, operations, and explanation. **Nothing may be GUI-unreachable by
   construction** — today's CLI-only personas are a prioritization, not a permanent split.

---

## 3. Application architecture

Four layers. A package MAY import a strictly lower layer and MUST NOT import a sibling or anything
above it.

```
@astro-mine/surface    the contract — types only, zero deps        ← "Core for the GUI"
@astro-mine/ui         design system — tokens, primitives, a11y, light/dark
@astro-mine/view       domain viz primitives — globe, replay, timeline, frames   (exists)
        ↑
@astro-mine/bench-ui · studio-ui · hub-ui        surfaces (owned by their component repos)
        ↑
@astro-mine/console    the shell — nav, routing, surface registry, config
```

```
astro-mine-console/                 (pnpm workspace; the repo root is private/unpublished)
├── packages/
│   ├── surface/    @astro-mine/surface   the Surface + Contribution types, zero runtime deps
│   ├── ui/         @astro-mine/ui        tokens, primitives, honesty components, chart layer
│   └── console/    @astro-mine/console   shell, registry, InspectorSlot, runtime config
├── design/                              the design system's source of truth
│   ├── tokens/     tokens.json → generated tokens.css; three themes; PALETTE/CONTRAST records
│   └── mockups/    static HTML mockups the tokens render (a design artifact, not the console)
└── scripts/                             gates and generators (Node built-ins, zero deps, offline)
```

**Surfaces do not live here.** Each component repo owns and publishes its own surface package, so
**UI ownership follows component ownership** — `@astro-mine/hub-ui` ships from `astro-mine-hub`,
`@astro-mine/bench-ui` from `astro-mine-bench`. The console takes them as dependencies.

### Key abstractions

- **`Surface`** — what a component contributes to the GUI:

  ```ts
  export interface Surface {
    id: string;                      // "hub" | "studio" | "bench"
    title: string;
    nav?: NavEntry[];                // where it appears in the shell
    routes: SurfaceRoute[];          // path → component
    capabilities?: string[];         // backends it needs; the shell degrades honestly if absent
    contributions?: Contribution[];  // the extensibility hinge
  }
  ```

  Every type here is a type every surface must live with, so the package stays small on purpose:
  when in doubt, leave it out.

- **`Contribution`** — a required Core interface kind plus optional discriminators:

  ```ts
  export interface Contribution {
    readonly slot: SlotId;                 // which extension point ("inspector", …)
    readonly kind: PluginKind;             // REQUIRED — the Core interface vocabulary
    readonly artifactKind?: ArtifactKind;  // OPTIONAL — Hub's container facet
    readonly where?: AttributePredicate;   // OPTIONAL — a predicate over manifest.attributes
    readonly render: ContributionRenderer;
  }
  ```

- **The surface registry** — composes registered surfaces at build time: merges navigation, mounts
  routes under each surface's namespace, and indexes contributions by kind.

- **`InspectorSlot`** — the extension point that makes the model extensible rather than merely
  modular. Hub's surface renders `<InspectorSlot subject={entry} />` and the registry resolves
  whichever contribution claims that subject. **Hub imports none of the contributors:** a `policy`
  artifact gets Bench's scorecard, an `asset` gets Fleet's geometry preview, a `world_provider`
  gets Worlds' globe.

### Contributions are keyed by Core's vocabulary

Reusing Core's existing closed, RFC-governed [`PluginKind`](core.md) rather than inventing a
UI-side vocabulary is the whole trick: it is what makes *contribute once, use everywhere*
(`conventions.md` §1.2) hold in the GUI, and it costs Core nothing.

**But `PluginKind` alone is not a sufficient key.** It answers *what interface does this
implement*; an inspector needs *what am I looking at*. Those diverge: a [Worlds](worlds.md)
illumination field model and a [Surrogate](surrogate.md) excavation model **both carry
`field_model`**, so keying on kind alone routes a Surrogate model into Worlds' inspector — a live
collision, not a hypothetical.

[hub.md](hub.md) §2 principle 2 supplies the discriminator. A catalog entry carries the Core
interface kind and Hub's **container** kind as separate queryable facets — *never one field holding
two vocabularies* — with the container kind derived from the stored OCI `artifactType` so it
**cannot drift from the bytes**. A served surrogate is container `surrogate`; a Worlds bundle is
container `world`.

### Resolution is normative

A UI that resolves differently on two machines is a **reproducibility defect (CX-REPRO)**, not a
cosmetic one. Therefore:

- **Match.** A contribution matches a subject when its `kind` equals the subject's `manifest.kind`
  **and** every declared discriminator matches. A contribution that declares `artifactKind` MUST
  NOT match a subject with no container kind — `artifact_kind` is nullable (an artifact published
  by another tool, or indexed before the facet existed), and a null MUST **fail closed** rather
  than match loosely.
- **Specificity.** Among matches, the contribution declaring **more** discriminators wins. Surrogate
  claims `field_model` *where container is `surrogate`*; Worlds claims `field_model` unqualified
  and is the fallback.
- **Ties.** Two matches at equal specificity are a **modelling bug**, not a runtime condition to
  absorb silently. The registry MUST resolve deterministically by a stable total order (surface
  `id`, then contribution index) — never registration order — **and** MUST surface the ambiguity as
  a visible diagnostic.
- **No match.** The slot MUST render an honest *"no inspector for kind X"*. Never blank.

`where` is the escape hatch for collisions the two closed vocabularies cannot separate. Core's
`PluginManifest` is `extra="forbid"` and cannot be subclassed, so `attributes` is the sanctioned
extension point. It is deliberately last-resort: a predicate over a free-form dict is the weakest
of the three keys, and a contribution that needs one is evidence the artifact's facets are
under-modelled.

### Extension points

- **A new component in the GUI** — publish a surface package, add one line to the registry.
- **A new inspector for an existing artifact kind** — declare a `Contribution`; no console change,
  and no coordination with the surface that renders the slot.
- **A new slot** — additive to `SlotId` in `@astro-mine/surface`.
- **A new `PluginKind`** — **not** an extension point here. That is a Core RFC, and an amendment to
  RFC-0010. The console must never become a back door for widening the waist.

---

## 4. Application programming & runtime platforms

The stack is **not this component's to choose** — it is the platform front-end baseline in
`conventions.md` §2.1, which is the only normative home for it. Console-specific points only:

- **Vite in app mode** for `@astro-mine/console`; **library mode** for `surface` and `ui`
  (`conventions.md` §2.1).
- **react-router**, whose nested routes map onto surface namespaces — a surface's routes mount
  without the surface knowing where.
- **No data-fetching or client-cache library.** The platform ships none; each surface receives an
  injected client and uses `fetch` with the design system's `AsyncState` primitive. Adding a cache
  layer is an RFC, not an import.
- **visx + `d3-scale`** for charts, owned by `@astro-mine/ui`. Chosen because it enforces the
  discipline *by the API rather than by care*: a second y-axis is unrepresentable, and a value with
  no uncertainty bound renders as an open mark by construction. Parallel coordinates is the one form
  visx does not provide and is hand-built.
- **No Storybook.** Storybook caps at Vite ≤ 6 and Vite-version parity across the front ends was
  prioritized; the component gallery plus the Playwright lane serve the same purpose.
- **Three themes** (`instrument` default, `editorial`, `mission`), each derived from seeds rather
  than hand-picked, in light and dark.

---

## 5. Data architecture

The console **owns almost no data** — it is a shell.

| Data | Direction | Format / store | Source / sink |
|---|---|---|---|
| Catalog entries, scorecards, design candidates | consumed | JSON over REST + OpenAPI | [Hub](hub.md), [Bench](bench.md), [Studio](studio.md) |
| Domain geometry, terrain, replays | consumed | via [`@astro-mine/view`](view.md) primitives | [Worlds](worlds.md), [Sim](sim.md) |
| Runtime endpoint configuration | consumed | JSON fetched at boot (§7) | the deployment |
| Theme choice, nav state, layout preferences | **owned** | browser `localStorage` | the browser only |

- **No database, no server-side session, no authoritative state.** Anything the console appears to
  "have" belongs to a component behind it.
- **Schemas.** The console reads Core-owned schemas by their absolute `$id` per `conventions.md`
  §3.1. Because TypeScript cannot import a Python enum, both `PluginKind` and Hub's `ArtifactKind`
  are **mirrored**, and a mirrored vocabulary kept in step only by a comment goes stale in silence —
  that is not speculation, it is what happened to View's vendored units mirror. `PluginKind` MUST be
  **generated**, resolved from the published bundle via `schema_index` or vendored against a pinned
  `astro_mine.core.SCHEMA_DIGEST`; `ArtifactKind` carries the same obligation against Hub's source
  of truth. **Both guards MUST fail hard when their token or upstream is absent. A drift guard that
  skips is not a guard.**
- **Units and frames** are rendered as declared, never inferred (`conventions.md` §5, RFC-0007).

---

## 6. Integration architecture

**No new REST surface, and no gateway.** `system.md` §5.1 already describes what the console needs:
independent REST/OpenAPI edges at [Studio](studio.md), [Hub](hub.md), [Bench](bench.md), and
[View](view.md). The console is a **static SPA configured with per-surface base URLs**; each surface
receives its own injected client and talks to its own component's existing FastAPI.

> **Two different things are called "gateway."** [View](view.md)'s `gateway/` is View's *own*
> stateless telemetry/tile fan-out backend. A *platform* API gateway — one unified REST edge in
> front of every component — is a separate idea, deferred to Phase 2 at the earliest. **Neither
> exists in Phase 1, and they are not the same future thing.**

- **Composition is build-time.** The console imports each surface as a package and bundles one
  artifact. **Runtime module federation is rejected for Phase 1**: a shell fetching remotes over a
  network at load is exactly what the local tier forbids (`roadmap/README.md` **CX-LOCAL**;
  `conventions.md` §7 tier 1 — *this tier MUST always work*), and version skew across
  independently-built remotes fights CX-REPRO. **This is not a ceiling** — runtime discovery is an
  additive change behind the same contract if a third party ever needs to ship a surface without
  rebuilding the console.
- **Capabilities** declare which backends a surface needs. Unmet capabilities produce a visible
  degraded state, not a hidden nav entry (§2 principle 5).

---

## 7. Infrastructure & deployment

- **Tier 1 (local/dev) — the one that must always work.** `pnpm install && pnpm build` produces a
  working console on one workstation, **offline after the first install, with no account and no
  cluster**. A Vite dev proxy fronts the component APIs.
- **Tier 2 (hosted).** Any static host or object store; optionally an OCI image serving the built
  assets. There is no server to run.
- **Endpoint configuration MUST be settable without a rebuild.** A static bundle with backend URLs
  baked in at build time is deployable only by its builder. Configuration is fetched at boot, not
  compiled in.
- **Distribution.** `@astro-mine/surface` and `@astro-mine/ui` publish to npm under the
  `@astro-mine` scope (`conventions.md` §7, §13); `@astro-mine/console` is an application build and
  is not published as a library. Versioning follows `VERSIONING.md` §2.0 (npm packages).

> **Open precondition for external adoption.** [`@astro-mine/view`](view.md) publishes to private
> GitHub Packages behind a token, so any dependency on it makes the console uninstallable by an
> outsider — the audience it exists for. The console deliberately takes **no `view` dependency
> until it needs one**; resolving the distribution question is tracked in `astro-mine-view`.

---

## 8. Performance & scalability

The console is a static client; its scale limits are bundle and render, not throughput.

- **Bundle budget.** Surfaces are route-split so a student opening the leaderboard does not download
  Studio's trade-study machinery. Adding a surface must not degrade first paint for the others.
- **Rendering large results.** Leaderboard and catalog views virtualize long lists; heavy domain
  rendering (globe, replay) is [View](view.md)'s, with its own budgets ([view.md](view.md) §8).
- **Offline-first assets.** Fonts and assets are bundled, never CDN-fetched at runtime (CX-LOCAL).
- **The scaling axis that matters is surfaces, not users.** Composition cost is build-time and
  linear; the design's real limit is how many contributions a slot can resolve without ambiguity,
  which is bounded by the vocabularies, not by traffic.

---

## 9. Security, safety & compliance

Stated honestly for what Phase 1 actually is, rather than describing a posture the console does not
have:

- **No accounts and no authentication in the local tier.** [Bench](bench.md) is the one
  public, anonymous-read surface — leaderboard reads are account-free, and the capability model must
  not assume an authenticated session.
- **The console holds no credentials and no authority.** It originates no command, dispatches no
  job, and gates nothing. Like [View](view.md), it is safe to expose widely because a compromised
  console cannot drive anything.
- **It inherits its backends' posture, including their gaps.** [Hub](hub.md) §9 records that its
  write path currently authenticates nobody and `publisher` is a self-declared label. A console
  write path against Hub inherits exactly that, and must not present self-declared provenance as
  verified.
- **Honest rendering is a security-adjacent property.** Signature and verification state must render
  as what it is — verified, unverified, or unknown — never collapsed into a reassuring default.
- **Hosted deployments** sit behind the platform's normal edge controls (OIDC, OPA) per
  `conventions.md` §9; that is the host's concern, not the bundle's.
- **Export control.** The console surfaces capability-tagged artifacts and MUST respect the gating
  those tags carry (`conventions.md` §12); it introduces no new capability to gate.

---

## 10. Observability & operability

- **Phase 1 ships no product telemetry**, and that is deliberate: the local tier has no account and
  no server to report to.
- **The degraded state *is* the observability surface.** An unreachable backend, a failed drift
  guard, an ambiguous contribution — each is rendered to the user rather than logged where nobody
  looks. That is the operability model for a client with no operator.
- **Build-time gates** are where this component's health is actually observed: the layering check,
  the token/contrast/palette gates, unit and e2e lanes, and the automated accessibility lane, all
  failing the build rather than reporting (`conventions.md` §11).
- **Testing.** Vitest + Testing Library for logic and components; **Playwright against the built
  artifact**, so the test exercises what ships; an **automated a11y lane that fails the build**;
  and design-system gates that check contrast conformance across every theme and mode and
  colour-vision separation for chart palettes. *An accessibility claim nobody runs is an
  accessibility claim that quietly stops being true.*

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Where the shell lives** | Inside [View](view.md)'s reserved `app/`; a new leaf repo; a monolith owning all UI | **A new leaf repo.** View's `app/` closes a cycle: `view.md` §6 embeds View's library in Studio and §2.4 makes Studio and Ops peers, so `studio-ui → view` holds by View's own design, and a shell inside View that hosts Studio's surface closes `view → studio-ui → view`. **View's `app/` is descoped;** View stays a leaf. A monolith breaks component ownership and is the god-interface shape this design exists to prevent. |
| **Composition** | Build-time; runtime module federation | **Build-time** — federation fetches remotes over a network at load (breaks CX-LOCAL) and independently-built remotes fight CX-REPRO. Additive later behind the same contract. |
| **Contribution key** | `PluginKind` alone; Hub's `ARTIFACT_KINDS` alone; a new UI-side vocabulary; **kind + discriminators** | **`PluginKind` required, `artifactKind` and an attribute predicate optional, resolved by specificity.** Kind alone mis-routes the `field_model` collision; the container vocabulary is coarse, Hub-owned, and null for anything not published through Hub — the right *discriminator*, the wrong *key*; a fourth vocabulary would repeat [RFC-0008](../rfc/0008-design-campaign-artifact-kinds.md)'s reconciliation debt. |
| **Backends** | Per-surface base URLs; a unified REST gateway | **Per-surface base URLs**, no new API surface. A gateway is Phase 2 at the earliest. |
| **Package split** | `surface` + `ui` + `view`; one `@astro-mine/common` | **The split.** A grab-bag becomes a dependency magnet with no single reason to change — the reason [RFC-0005](../rfc/0005-seal-supply-chain-companion.md) rejected `astro-mine-common`. Each package here has exactly one reason to change, and none is so narrow it forces a rename within a phase. |
| **Charts** | **visx + d3-scale**; Plotly | **visx** (`conventions.md` §2.1). Plotly is Studio's incumbent and ~1 MB under CX-LOCAL, and its defaults coerce a null bound to `0` — drawing a zero-length error bar that asserts a precision never measured. |
| **Adopt OpenMCT as the console** | Yes; no | **No, for Phase 1, without prejudice.** Charter §6/§9.5 name OpenMCT for mission control and mandate bridging rather than competing — and that remains the plan for the **operations** console in Phase 2. OpenMCT is a telemetry-dashboard framework; Phase 1's need is design-time comparison, artifact inspection, and a leaderboard. |

**Open questions / research dependencies:**

- **`capabilities` string semantics** — free-form, or a closed set tied to endpoint keys? Free-form
  is assumed for Phase 1; a closed set can be adopted additively once three surfaces exist and the
  real vocabulary is observable rather than guessed.
- **Should [Hub](hub.md) publish `ARTIFACT_KINDS` at a stable `$id`?** It would put the container
  mirror under the same `conventions.md` §3.1 bundle mechanism as `PluginKind` and retire a bespoke
  drift check. A Hub concern.
- **`@astro-mine/view`'s distribution** (§7) — a precondition for external adoption, not for the
  design.
- **Authoring in the GUI.** Phase 1 leaves asset, world, and autonomy authors on the CLI. That is a
  prioritization of effort; §2 principle 8 forbids making it permanent by construction. What those
  surfaces should look like is genuinely unknown and should be designed against observed need.

---

## 12. Roadmap alignment

- **Phase 1, Wave 23 — the foundation.** `@astro-mine/surface` (the contract), the design pass,
  `@astro-mine/ui` (the design system), then `@astro-mine/console` (the shell). The contract lands
  **before** the surfaces exist, on purpose: reserve the hooks while the waist is soft — the
  [RFC-0001](../rfc/0001-multi-regime-missions.md) argument one layer up. Retrofitting a shell
  around three grown-up applications later is precisely the *"leaky, ever-growing god-interface"*
  failure charter §8 warns against.
- **Phase 1, Wave 24 — the surfaces.** `@astro-mine/bench-ui` (the leaderboard — Bench owns the
  surface and *uses* View's replay primitives), `@astro-mine/studio-ui`, `@astro-mine/hub-ui`, and
  the retirement of Hub's Pico CSS and Studio's ad-hoc CSS onto `@astro-mine/ui`.
- **Phase 2 — operations.** The ops console, live telemetry, the plan-explanation UI, and OpenMCT
  dashboards land with [Ops](ops.md) and [View](view.md). View's `telemetry/` barrel is a deliberate
  `export {}` stub today, and it is correct that it is empty. A unified REST gateway, if it is ever
  justified, is no earlier than here.
- **Later, additive.** Runtime surface federation; authoring surfaces; accounts and authentication.

**The design must not preclude any of these. It must not attempt them.**

> **Implementation status.** As of RFC-0010's acceptance the repo is stood up — pnpm workspace, CI,
> the layering check, the design pass (tokens, three themes, mockups) and its gates — and the three
> package slots hold honest placeholders. The contract, the design system, and the shell are Wave-23
> work in progress. This document describes the **accepted design**, not shipped code; where the two
> differ today, the code is behind.
