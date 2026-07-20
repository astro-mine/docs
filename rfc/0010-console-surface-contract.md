# RFC 0010: the console shell and the `Surface` contract

- **Status:** accepted
- **Author(s):** djankov
- **Created:** 2026-07-19
- **Accepted:** 2026-07-19
- **Amended:** 2026-07-20 — Amendment 1 (the `Surface` contract as the Wave-24 surfaces require it:
  a typed injection channel, capability *status* rather than capability *names*, a nav entry
  independent of the surface title, and a structural inspector subject), accepted; see
  [Amendment 1](#amendment-1--the-surface-contract-the-surfaces-actually-need-accepted-2026-07-20)
  below.
- **Affects Core:** no — introduces three **front-end packages** (`@astro-mine/surface`,
  `@astro-mine/ui`, `@astro-mine/console`) in a new repo `astro-mine-console`, and a cross-cutting
  layering convention for the platform's GUI. It makes **no** change to `astro-mine-core`: the
  contribution model **consumes** Core's existing closed `PluginKind` vocabulary rather than
  extending it — no new enum member, no new message, no new schema, no wire change — and
  `CORE_INTERFACE_VERSIONS` stays `0.1.0`. It goes through the RFC process because it introduces
  **new top-level packages** and a **cross-cutting convention**, the same double trigger
  [RFC-0002](0002-shared-spice-foundation.md) and [RFC-0005](0005-seal-supply-chain-companion.md)
  cited — [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

## Summary

Astro-Mine ships **one GUI**, not an app per component. That raises the same question Core already
answers for Python — *how does one surface span every component without becoming a monolith?* — and
it takes the same answer: **a thin, stable contract with thick, swappable edges**.

This RFC ratifies a four-layer front-end architecture. `@astro-mine/surface` is the GUI's narrow
waist: a types-only, zero-dependency contract describing what a *surface* is. `@astro-mine/ui` is
the platform design system. `@astro-mine/view` (existing) stays the domain-visualization library.
Each component owns its own surface package (`@astro-mine/bench-ui`, `studio-ui`, `hub-ui`, …) in
its own repo, and `@astro-mine/console` — the shell — composes them at build time. A surface
declares **contributions** keyed by Core's existing `PluginKind`, so Hub's artifact browser can
render a Worlds globe or a Bench scorecard without importing Worlds or Bench. Adding a component to
the GUI becomes *publish a surface package, add one line to the registry* — never *modify the
console*.

## Motivation

**There is no GUI front door.** Studio's web app is unreachable without hand-wiring five seams; the
Bench leaderboard — the public face of the academic flywheel — is REST-only; Hub's browser is a
separate SPA. `system.md` §2's audience table names a different "primary surface" for each of five
audiences and no shared entry point. Two personas the charter names explicitly (charter §2:
designers, educators/students) **cannot use the platform at all** without one.

**Three visual languages already ship and diverge every week.** Hub's UI is on Pico CSS, Studio's on
ad-hoc CSS plus Plotly, View has its own. `studio.md` §11 already commits to a *"shared
component/charting stack with View/Hub UI"* — a claim with no package behind it. Every component
added before that package exists makes the retrofit more expensive.

**The hooks must be reserved while the waist is soft.** This is [RFC-0001](0001-multi-regime-missions.md)'s
argument, one layer up. Retrofitting a shell around three grown-up applications later is precisely
the *"leaky, ever-growing god-interface"* failure charter §8 warns against, and charter §11 names
scope explosion as a top risk mitigated only by *"ruthless narrow-waist discipline."* The cost of not
doing this now is that the GUI accretes the way the two artifact vocabularies did (see
[RFC-0008](0008-design-campaign-artifact-kinds.md)) — three answers to one question, reconciled
expensively later.

**Honesty is a UI concern, not only a CLI one.** The platform's rule that a stand-in must never look
like the real thing only holds if the primitives make it cheap. A fixture-scored result must *look*
fixture-scored; an unreachable backend must say so. That belongs in a shared design system, not
re-invented (or quietly skipped) per surface.

## Design

### The layering

```
@astro-mine/surface    the contract — types only, zero deps        ← "Core for the GUI"
@astro-mine/ui         design system — tokens, primitives, a11y, light/dark
@astro-mine/view       domain viz primitives — globe, replay, timeline, frames  (exists)
        ↑
@astro-mine/bench-ui · studio-ui · hub-ui        surfaces (owned by their component repos)
        ↑
@astro-mine/console    the shell — nav, routing, surface registry, config
```

Three normative rules, each the transplant of an existing platform rule:

1. **`@astro-mine/surface` MUST declare zero runtime dependencies.** It is the GUI's narrow waist;
   every surface and the shell agree on it, so it must not drag anything into their installs
   (`core.md` §2 principle 3, transplanted).
2. **A surface MUST NOT import another surface.** Surfaces are siblings; they are wired together
   only by the shell, and only through the contribution model below. This is the GUI's transplant of
   `conventions.md` §1.1 — *components MUST NOT create private side-channels that bypass Core
   contracts* — and the direct analogue of *Bench must never import Sim*.
3. **Nothing MUST depend on `@astro-mine/console`.** The shell is the top of the graph: it is
   composed, never imported.

A package MAY import a strictly lower layer and MUST NOT import a sibling or anything above it.
These rules are enforced mechanically by `scripts/check-layering.mjs` in `astro-mine-console`, which
fails the build on a manifest dependency on the console, a runtime dependency in `surface`, or a
source import pointing sideways or up. A layering rule enforced only by review is a layering rule
that erodes.

### Why the shell is not in `astro-mine-view`

`view.md` §3's module tree reserves `app/  # standalone hosted application (routing, layout, session
shell)`. That is the obvious place to put a shell, and it is the wrong one.

`view.md` §6 establishes that View's component library is **embedded in Studio**, and §2.4 makes
Studio and Ops *peers* consuming it — so `studio-ui → view` holds by View's own design. A shell
inside View that hosts Studio's surface closes the cycle `view → studio-ui → view`. The shell must
sit **above** every surface, and every surface may use `view`, so the shell is a separate leaf
package in a separate repo. `view` stays a leaf that surfaces depend on — never the reverse.

**Decision:** View's planned `app/` is **descoped**. The console is the platform's standalone
application; View remains the embeddable component library its §2.4 *"embeddable first, app second"*
principle describes. View's `lib/` demo harness is a **developer component gallery** — not the
console, and it must not present itself as one.

### The packages

| Package | Kind | Role |
|---|---|---|
| `@astro-mine/surface` | library (ESM) | The `Surface` contract — types + tiny constants. **Zero runtime deps.** |
| `@astro-mine/ui` | library (ESM) | The platform design system — tokens, primitives, a11y, light/dark. React peer. |
| `@astro-mine/console` | application | The shell: nav, routing, the surface registry, per-surface config. |

All three live in **one repo**, `astro-mine-console` (a pnpm workspace), Apache-2.0, private during
incubation. **Surfaces do not live there** — each component repo owns and publishes its own surface
package, so UI ownership follows component ownership.

`ui` MUST NOT carry domain knowledge. It does not know what a scenario, a scorecard, or an artifact
*is*; domain visualization is `view`'s job and domain semantics are the surfaces'. It ships the
design system **and stops there** — it does not re-implement `view`'s globe, replay, or timeline.

### The `Surface` contract

```ts
export interface Surface {
  id: string;                      // "hub" | "studio" | "bench"
  title: string;
  nav?: NavEntry[];                // where it appears in the shell
  routes: SurfaceRoute[];          // path → component
  capabilities?: string[];         // backends it needs; the shell degrades honestly if absent
  contributions?: Contribution[];  // ← the extensibility hinge
}
```

Every type here is a type every surface must live with, so the package stays small on purpose: when
in doubt, leave it out.

### Contributions, and the `InspectorSlot` resolution contract

`contributions` is what makes this extensible rather than merely modular. Hub's surface renders
`<InspectorSlot subject={entry} />` and the registry resolves whichever contribution claims that
subject — **Hub imports none of the contributors.** A `policy` artifact gets Bench's scorecard, an
`asset` gets Fleet's geometry preview, a `world_provider` gets Worlds' globe.

**Contributions are keyed by Core's `PluginKind`.** This is the heart of the design, and reusing an
existing closed, RFC-governed vocabulary rather than inventing a UI-side one is the whole trick: it
is what makes *contribute once, use everywhere* (`conventions.md` §1.2) hold in the GUI, and it
costs Core nothing. `PluginKind` is also the vocabulary Hub's catalog actually exposes —
`CatalogEntry.kind` projects `manifest.kind`, so anything reading the catalog sees `world_provider`,
`comms_model`, `resource_field_backend`.

**But `PluginKind` alone is not a sufficient key, and this is the part the contract must solve.** It
answers *what interface does this implement*; an inspector needs *what am I looking at*. Those
diverge today: a Worlds illumination field model and a Surrogate excavation model **both carry
`field_model`** (Surrogate resolves to `FIELD_MODEL` or `REGIME_ENGINE` by physics domain). Keying on
kind alone routes a Surrogate model into Worlds' inspector — a live collision, not a hypothetical.

Hub now carries a second, orthogonal facet that separates them. Per `hub.md` §2 principle 2, a
catalog entry carries the Core interface kind and Hub's **container** kind *"both, as separate
queryable facets — never one field holding two vocabularies"*, with the container kind derived from
the stored OCI `artifactType` so it **cannot drift from the bytes**. A served surrogate is container
`surrogate`; a Worlds bundle is container `world`. The facet that disambiguates the collision is
already indexed, queryable, and on the read path.

So a contribution declares a **required kind plus optional discriminators**:

```ts
export interface Contribution {
  readonly slot: SlotId;                 // which extension point ("inspector", …)
  readonly kind: PluginKind;             // REQUIRED — the Core interface vocabulary
  readonly artifactKind?: ArtifactKind;  // OPTIONAL — Hub's container facet
  readonly where?: AttributePredicate;   // OPTIONAL — a predicate over manifest.attributes
  readonly render: ContributionRenderer;
}
```

Resolution is **normative**, because a UI that resolves differently on two machines is a
reproducibility defect (CX-REPRO), not a cosmetic one:

- **Match.** A contribution matches a subject when its `kind` equals the subject's `manifest.kind`
  **and** every declared discriminator matches. A contribution that declares `artifactKind` MUST NOT
  match a subject with no container kind — `artifact_kind` is nullable (an artifact published by
  another tool, or indexed before the facet existed), and a null MUST fail closed rather than match
  loosely.
- **Specificity.** Among matches, the contribution declaring **more** discriminators wins. This
  gives the collision its natural reading: Surrogate claims `field_model` *where container is
  `surrogate`*; Worlds claims `field_model` unqualified and is the fallback.
- **Ties.** Two matches at equal specificity are a **modelling bug**, not a runtime condition to
  absorb silently. The registry MUST resolve deterministically by a stable total order (surface `id`,
  then contribution index) — never registration order — **and** MUST surface the ambiguity as a
  visible diagnostic.
- **No match.** The slot MUST render an honest *"no inspector for kind X"*. Never blank.

`where` is the escape hatch for collisions the two closed vocabularies cannot separate. Core's
`PluginManifest` is `extra="forbid"` and cannot be subclassed, so `attributes` is the sanctioned
extension point (the `build_surrogate_manifest` precedent). It is deliberately last-resort: a
predicate over a free-form dict is the weakest of the three keys, and a contribution that needs one
is evidence the artifact's facets are under-modelled.

### Mirroring the vocabularies, and the drift guard

`@astro-mine/surface` is TypeScript and cannot import a Python enum, so both vocabularies are
mirrored — and **a mirrored vocabulary kept in step only by a comment goes stale in silence.** That
is not speculation: View's vendored units mirror drifted exactly this way, which is why
[RFC-0009](0009-cross-package-schema-resolution.md) exists.

`conventions.md` §3.1 already governs this case and **no extension to it is needed**:

- **`PluginKind` MUST be generated, not hand-written.** Core publishes it as a 16-member enum at
  `$defs/PluginKind` in the manifest schema, whose absolute `$id` is
  `https://schemas.astro-mine.org/core/registry/v0.1/manifest.schema.json`. §3.1's cross-language
  clause applies literally: resolve it from the **published bundle** via the `schema_index`, or
  vendor a copy that pins `astro_mine.core.SCHEMA_DIGEST` and **fails CI** when it no longer matches.
- **`ArtifactKind` carries the same obligation.** Hub's `ARTIFACT_KINDS` is a closed, append-only
  8-member tuple but is not currently published as a schema, so the mirror MUST be guarded by a
  hard-failing check against Hub's source of truth. It is typed as a closed union rather than a bare
  `string` deliberately: a free string lets a typo silently never match, which is the same
  fail-quiet mode the guard exists to prevent.

A drift guard that **skips** is not a guard. Both checks MUST fail hard when their token or upstream
is absent, never degrade to a no-op.

### Composition: build-time, not runtime federation

The console imports each surface as a package and bundles one artifact. **Runtime module federation
is rejected for Phase 1**: the shell fetching remotes over a network at load is exactly what the
local tier forbids — `roadmap/README.md` **CX-LOCAL** (*"the local tier is sacred… a change that
breaks this is a defect in any phase"*) and `conventions.md` §7 tier 1 (*"this tier MUST always
work"*). Version skew across independently-built remotes also fights CX-REPRO.

This is **not a ceiling.** If a third party later needs to ship a surface without rebuilding the
console, runtime discovery is an **additive** change behind the same contract.

### Backends: no new REST surface

The console is a static SPA configured with **per-surface base URLs**; each surface receives its own
injected client and talks to its own component's existing FastAPI. `system.md` §5.1 already
describes exactly this — four independent REST/OpenAPI edges (Studio, Hub, Bench, View) — and this
RFC introduces **no new API surface** and no gateway.

A **unified REST gateway stays out of Phase 1.** Note a name collision worth stating once: View's
`gateway/` (`view.md` §3) is View's *own* stateless telemetry/tile fan-out backend, not a platform
API gateway. Neither exists in Phase 1, and they are not the same future thing.

Endpoint configuration MUST be settable **without a rebuild** — a static bundle with backend URLs
baked in at build time is deployable only by its builder.

### Degrade visibly, never blank

A surface whose declared `capabilities` are unmet MUST render an explicit, self-explanatory degraded
state — *"Hub not configured"* — and MUST remain reachable in the nav. A missing backend is a
**state**, not an absence (`view.md` principle 5). Hiding it is the pixel-level version of the
stand-in dishonesty the platform forbids everywhere else.

### Forward-looking positions

These shape the design without being Phase-1 scope:

- **The architecture MUST NOT assume read-only.** Phase 1 is comparison and inspection; the GUI grows
  to authoring, operations, and explanation.
- **Nothing may be GUI-unreachable by construction.** The CLI/GUI persona affinity is a Phase-1
  prioritization, not a permanent split.
- **The leaderboard's surface home is `astro-mine-bench`**, as `@astro-mine/bench-ui`. This settles a
  contradiction in `bench.md`, which claims a Bench-owned React UI in §1/§4 while delegating
  leaderboard rendering to View in §6/§12. Bench owns the surface; it *uses* View's replay
  primitives. Bench is also the one **public, anonymous-read** surface — reads are account-free, and
  the capability model must not assume an authenticated session.

### Deferred scope

Explicitly **not** Phase 1, and not designed here:

- **The ops console, live telemetry, the plan-explanation UI, and OpenMCT dashboards** — Phase 2,
  with [Ops](../architecture/ops.md) and [View](../architecture/view.md). View's `telemetry/` barrel
  is a deliberate `export {}` stub today, and it is correct that it is empty.
- **The unified REST gateway** — Phase 2 at the earliest (see *Backends*).
- **Runtime surface federation** — additive later behind this same contract.
- **Authoring surfaces for the asset, world, and autonomy authors** — they remain CLI personas in
  Phase 1. That is a prioritization of effort, not a statement that they belong on the CLI
  permanently; per *Forward-looking positions*, nothing may be GUI-unreachable by construction.
- **Accounts and authentication** — the local tier has none, and leaderboard reads are account-free.

The design must not *preclude* any of these. It must not attempt them.

### Sequencing

The `astro-mine-console` repo is already stood up (workspace, CI, the layering check, three
placeholder packages). This RFC is therefore partly **ratification of decisions already made in
code** — stated plainly rather than dressed as greenfield, the way RFC-0008 described itself as
archaeology. What follows it: `@astro-mine/surface` (the contract), the design pass, `@astro-mine/ui`
(the design system), then `@astro-mine/console` (the shell); the Wave-24 surfaces consume them.

The contract lands **before** the surfaces exist, on purpose. That is the whole hooks-now argument.

## Impact on Core

**None to `astro-mine-core`.** No enum member, message, schema, or wire form changes;
`CORE_INTERFACE_VERSIONS` stays `0.1.0` (`VERSIONING.md` §4). The narrow waist does not widen: the
contribution model **reads** Core's `PluginKind` vocabulary by its published `$id` — a read of Core's
public API, not a change to it, the same move [RFC-0004](0004-safetyspec-safety-contract.md) made in
reusing `PluginKind.POLICY` rather than adding a kind.

If a surface appears to need a new `PluginKind`, that is a **Core RFC**, not a console change — and
an amendment to this one. The console must never become a back door for widening the waist.

`conventions.md` §2's rule that *"the public API surface of any component MUST be reachable from
Python"* is not violated: `surface`/`ui`/`console` are **front-end packages**, not components in the
conventions.md sense. Every capability they expose belongs to a component whose Python API remains
the authoritative surface; the console renders those APIs and adds none of its own. The
documentation impact below records this distinction explicitly.

## Alternatives considered

1. **Put the shell in `astro-mine-view`.** Rejected — it closes the cycle
   `view → studio-ui → view` (see *Why the shell is not in View*). View is a leaf by design.
2. **Runtime module federation.** Rejected for Phase 1 — it fetches remotes over a network at load,
   breaking **CX-LOCAL**, and independently-built remotes fight CX-REPRO. Additive later behind the
   same contract.
3. **A monolithic app owning all UI.** Rejected — one repo becomes the bottleneck for every
   component's UI, breaking component ownership and the one-repo-per-package rule. It is also the
   shape this RFC exists to prevent: the GUI equivalent of a god-interface.
4. **A UI-side kind vocabulary, invented for the console.** Rejected — a fourth artifact vocabulary
   alongside `PluginKind` and Hub's container kinds, with a fourth reconciliation debt. RFC-0008 is
   the cautionary precedent: two vocabularies grown independently, reconciled expensively later.
5. **Key contributions on Hub's `ARTIFACT_KINDS` alone.** Rejected — the container vocabulary is
   coarse (8 members; `plugin` collapses Link's `comms_model` and Prospect's
   `resource_field_backend`), it is Hub-owned rather than Core-owned, and it is null for anything not
   published through Hub. It is the right *discriminator* and the wrong *key*.
6. **A general-purpose `@astro-mine/common` front-end package.** Rejected for the reason RFC-0005
   rejected `astro-mine-common`: a grab-bag becomes a dependency magnet, accumulates unrelated
   transitive dependencies, and has no single reason to change. `surface` is defined by being the
   contract, `ui` by being the design system, `view` by being domain visualization — each has one
   reason to change. The split survives the opposite blade too: none is so narrow it forces a rename
   within a phase.
7. **Adopt OpenMCT as the console.** Rejected for Phase 1, without prejudice. Charter §6 and §9.5
   name OpenMCT for mission control and mandate bridging rather than competing — and that remains the
   plan for the **operations** console in Phase 2, where View already reserves an OpenMCT plugin.
   OpenMCT is a telemetry-dashboard framework; Phase 1's need is design-time comparison, artifact
   inspection, and a leaderboard, which is not what it is for.

## Documentation impact

The RFC lands with its entry in `architecture/README.md`'s package table and footnotes (the
convention RFC-0001/0002/0005 established). The remaining documentation changes are tracked as
follow-on issues so the normative decision is not gated on the sweep:

- **New `architecture/console.md`** — the per-component design for `astro-mine-console`.
- **`architecture/system.md`** — the console in the §2 context diagram and the §4 component catalog;
  §5.1 gains the static-SPA-over-N-component-APIs statement and the explicit no-gateway position,
  which currently lives only in TPM working docs.
- **`architecture/view.md`** — the `view` ↔ `console` boundary: `app/` descoped per *Design*, `lib/`
  documented as the developer component gallery, and the View-gateway/platform-gateway name
  collision disambiguated.
- **`architecture/conventions.md`** — §2 adds the console and records that front-end packages are not
  "components" for the Python-reachability rule; §11 gains the front-end test lanes (Vitest,
  Playwright, automated a11y); §13 gains the `@astro-mine/<name>` npm naming rule it currently lacks;
  §7 gains npm publication. Today the TypeScript stack is restated in four component docs with no
  shared normative home — the same failure class RFC-0009 addressed for schemas.
- **`VERSIONING.md`** — an npm/`package.json` clause; it is `pyproject.toml`-shaped throughout and
  `astro-mine-console` has no `pyproject.toml`.
- **`architecture/core.md`** — `PluginKind` is undocumented in its owning component's architecture
  doc, though this RFC, RFC-0004 and RFC-0008 all turn on it.
- **`architecture/bench.md`** — record that the leaderboard surface is Bench-owned (§*Forward-looking
  positions*), resolving the §1/§4-vs-§6/§12 contradiction.

**No accepted RFC's decision changes.** RFC-0009's §1 obligations are inherited, not amended;
RFC-0008's vocabulary is consumed, not extended.

## Decision

**Accepted 2026-07-19** by the steering group (the founding team), as specified in *Design*: the
four-layer front-end architecture and its three normative layering rules; `@astro-mine/console` as a
leaf package in its own repo, with View's planned `app/` descoped; the `Surface` contract; the
contribution model keyed on **Core's `PluginKind` with optional `artifactKind` / attribute-predicate
discriminators** and the specificity-ordered, deterministic, fail-closed resolution rule; the
generated-and-drift-guarded vocabulary mirrors under `conventions.md` §3.1; build-time composition
with runtime federation rejected for Phase 1; and no new REST surface — with `astro-mine-core`
unchanged and `CORE_INTERFACE_VERSIONS` staying `0.1.0`. Implementation is tracked as Phase-1
Wave-23 issues (the contract, the design pass, the design system, the shell) and Wave-24 surfaces.

## Unresolved questions

- **The inspector key — RESOLVED:** `PluginKind` required, `artifactKind` and an `attributes`
  predicate optional, resolved by specificity. Recorded here because the question was answered
  wrongly twice before: draft 1 keyed on `PluginKind` and illustrated it with `world`, which is not a
  `PluginKind`; draft 2 keyed on Hub's `ARTIFACT_KINDS`, which was then unreachable above the storage
  layer. Both are now settled against shipped code — Hub exposes both facets separately
  ([astro-mine-hub#33](https://github.com/astro-mine/astro-mine-hub/issues/33)), and the design uses
  each for the job it is fit for.
- **Should Hub publish `ARTIFACT_KINDS` at a stable `$id`?** It would put the container mirror under
  the same §3.1 bundle mechanism as `PluginKind` and retire a bespoke drift check. A Hub concern, not
  a blocker for this RFC.
- **`capabilities` string semantics — RESOLVED by [Amendment 1](#amendment-1--the-surface-contract-the-surfaces-actually-need-accepted-2026-07-20).**
  The question was posed as *free-form ids, or a closed set tied to endpoint keys?* and deferred until
  "three surfaces exist and the real vocabulary is observable rather than guessed." Three surfaces now
  exist as specified issues, and they answer a question this RFC did not think to ask: the id was never
  the hard part. **Capability is a runtime *status* with a reason, scoped to a route or an action —
  not a name on a list.** Ids stay free-form; the status type is the contract. See Amendment 1.
- **`@astro-mine/view`'s distribution block.** View publishes to private GitHub Packages behind a
  `read:packages` token, so an outsider cannot install the console at all — the same open question
  [RFC-0007](0007-units-frames-wire-schema.md) left for the generated TypeScript client. The console
  deliberately takes no `view` dependency until it needs one. Resolving it is Wave 24
  ([astro-mine-view#17](https://github.com/astro-mine/astro-mine-view/issues/17)); this RFC only
  records it as a precondition for external adoption.
- **Where the design system's chart discipline lands** — whether the console standardizes on Plotly
  (Studio's incumbent) is settled by the design pass, not here.

---

## Amendment 1 — the `Surface` contract the surfaces actually need (accepted 2026-07-20)

The *Design* section above sketches `Surface` as six fields and says, correctly, that the package
stays small on purpose. Writing the Wave-24 surface issues against that sketch — and then reading
them back — showed that four of the six cannot carry what the surfaces require, and that one thing
every surface needs has no field at all.

**This is the RFC's own acceptance test firing, and firing at the right time.** *Design* states it:
*"if a Wave-24 surface needs a console change beyond its registry line, the contract is wrong and
this RFC needs amending."* That was found **before** any surface was written, which is precisely
what landing the contract first was supposed to buy.

### What changed

Seven elaborations. Each is additive to the accepted design; none reverses a decision.

1. **A typed injection channel — `SurfaceProps`.** The gap: every surface is specified as receiving
   "its own injected API client" ([bench#57], [hub#31]) at "its own base URL" ([studio#31]), and the
   shell owns "per-surface endpoint config injection" ([console#5]) — but `Surface` had no
   `endpoints`, no config, and `routes: path → component` gave a component no channel to reach one.
   **No surface could call its backend.** The shell now injects `SurfaceProps` — the resolved
   endpoint, capability status, and surface id — into every route component. It is a *type*, so the
   zero-dependency rule is untouched, and `createConsole({ surfaces, endpoints })` keeps the exact
   signature *Backends* specifies. It also preserves the standalone dev lane that [hub#31] and
   [studio#31] both require stay green: that entry passes the same props by hand.

2. **Capability becomes a status, not a name.** The gap: `capabilities?: string[]` is whole-surface,
   static and boolean. Studio is none of those — it *"503s 5 of 9 routes without the `[hub]` extra"*,
   the degraded state applies to the asset menu and 3D pane rather than the surface, it is detected
   at runtime from the backend's own 503 detail, and it must **say why** ([studio#31]). A surface
   now declares free-form capability ids and receives `CapabilityStatus { id, met, reason?,
   remediation? }`. `reason` is what the degraded banner renders; `remediation` is what the design
   pass already mocked up naming the config key to set.

3. **Capability scopes to a route and to an action.** The gap: [hub#31] requires reads to be
   *"account-free"* — *"browsing and searching a local registry must never prompt for a login"* —
   while `POST /publish` sits *"behind an explicit capability"*, in **one surface**. A flat
   surface-level array forces gating everything (breaking account-free read) or gating nothing
   (shipping a button that lies, which [hub#31] explicitly forbids). `SurfaceRoute` may now declare
   its own `capabilities`, and a component may test one for an individual control.

4. **`NavEntry` is independent of `title`, and groups are shared.** The gap: the surface `id` is
   `bench`, its `title` is `Bench`, and its nav label is **`Leaderboard`** — three strings, where the
   sketch had one. Worse, the design pass's "Compare" group holds entries from **two different
   surfaces**, so no surface can own the group definition; had the shell hardcoded membership,
   adding a fourth surface would have become a console change — the exact failure this RFC's
   acceptance test names. `NavEntry` carries `label`, `path`, `group`, `order`, and `shortcut`. The
   shortcut is a field because the design pass reserves `g` then `l` for the leaderboard, and a
   shell that hardcoded that binding would know a surface by name.

5. **The inspector subject is a structural type — `ArtifactSubject`.** The gap: resolution reads
   `manifest.kind`, the nullable container kind, *and* `manifest.attributes`, and the honest
   no-match fallback must render identity, digest, size and kind ([hub#31]) — but `@astro-mine/surface`
   cannot import Hub's `CatalogEntry`, which is Python behind a zero-dependency waist. The subject
   is therefore defined structurally, in this package, carrying exactly what resolution and the
   fallback need and nothing more.

6. **`routes` becomes optional.** A package that ships only an inspector contribution — no nav, no
   pages — is a real and intended case ([hub#31] names Worlds, Fleet and Bench contributions as
   independently ownable). Requiring `routes: []` of it taught the wrong thing about the model.

7. **`SurfaceRoute` gains `title` and `errorElement`.** The shell announces the route title in a
   polite live region **before** the surface renders, so a static surface `title` cannot supply it.
   And [studio#32] requires that a malformed `?study=` *"renders a labelled error state — a test
   asserts the page is not blank"*; today an unguarded `JSON.parse` blanks the page before
   `createRoot`. A route needs somewhere to put its own failure.

`ContributionRenderer`'s props are specified here too: a contribution rendered inside another
surface receives the subject **and the contributing surface's own** endpoint and capability status.
Bench's scorecard rendered inside Hub calls *Bench's* API, and Bench may be unconfigured while Hub
is fine — without this, that contribution has no honest degraded path and would render blank inside
Hub's inspector, which *Degrade visibly, never blank* forbids.

### Why via (this) RFC

The changes are confined to the front-end packages this RFC introduced; they touch no other
component and no other RFC's decision. But they alter the **shape of a cross-cutting contract** that
every future surface implements — the same double trigger (new top-level surface + cross-cutting
convention) that sent the original through [GOVERNANCE.md]. Recording them as an amendment rather
than as implementation detail keeps the contract's authority in one readable place, which is the
argument *Mirroring the vocabularies* makes about vocabularies and applies equally here.

Two of the seven — items 2 and 3 — close an **unresolved question this RFC left open**, which is on
its own sufficient reason to amend rather than absorb.

### Impact on Core

**None, unchanged.** No enum member, message, schema, or wire form changes; `CORE_INTERFACE_VERSIONS`
stays `0.1.0`. The contribution model still *reads* Core's `PluginKind` by its published `$id`.
`ArtifactSubject` mirrors the *shape* Hub's catalog already exposes; it introduces no vocabulary and
no new facet.

### Deferred (updated)

Still explicitly not Phase 1, and unchanged by this amendment: runtime surface federation; the
unified REST gateway; the ops console and live telemetry; accounts and authentication.

Newly deferred, and named so they are not mistaken for oversights:

- **An imperative shell → surface handle.** The design pass reserves `/` to *"focus the surface's
  primary search field, if it has one."* That needs a callable handle, not a declaration, and the
  right shape is not yet observable from two examples. `NavEntry.shortcut` covers the declarative
  half; the imperative half waits.
- **A general `commands` concept.** Same reasoning — a command palette is a plausible Phase-2 want,
  and inventing its vocabulary now would violate this RFC's own *when in doubt, leave it out*.
- **A closed `capabilities` vocabulary.** Ids stay free-form. With the status type carrying the
  weight, a closed set buys less than it did when the id was the whole contract, and three surfaces
  is still a thin basis for closing a vocabulary.

### Decision

**Accepted 2026-07-20** by the steering group (the founding team), as specified in *What changed*:
the `SurfaceProps` injection channel; `CapabilityStatus` with `reason`/`remediation` and
route/action scoping; `NavEntry` with `label`/`group`/`order`/`shortcut`; the structural
`ArtifactSubject`; optional `routes`; `SurfaceRoute.title` and `errorElement`; and the
`ContributionRenderer` props contract — with `astro-mine-core` unchanged and
`CORE_INTERFACE_VERSIONS` staying `0.1.0`. Implementation is
[astro-mine-console#3](https://github.com/astro-mine/astro-mine-console/issues/3).

**One follow-up this amendment creates:** [hub#31] and [studio#31] were written against the original
sketch and still specify `<InspectorSlot kind={…} />`, which cannot implement the resolution rule —
a bare kind carries neither the container facet nor `attributes`. Both bodies need correcting to
`subject={…}` before Wave 24 starts, the same correction already applied to
[astro-mine-console#3](https://github.com/astro-mine/astro-mine-console/issues/3) and [console#5].

[bench#57]: https://github.com/astro-mine/astro-mine-bench/issues/57
[hub#31]: https://github.com/astro-mine/astro-mine-hub/issues/31
[studio#31]: https://github.com/astro-mine/astro-mine-studio/issues/31
[studio#32]: https://github.com/astro-mine/astro-mine-studio/issues/32
[console#5]: https://github.com/astro-mine/astro-mine-console/issues/5
[GOVERNANCE.md]: https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md
