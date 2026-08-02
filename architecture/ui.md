# Astro-Mine-UI — the front-end distribution

> Distribution: **`@astro-mine/*`** (npm packages) · Repository: `astro-mine-ui`
> The application, the generated API client, the design system, the visualization library, and the
> artifact inspector registry — one workspace, one baseline, one build.
> Talks to [`astro-mine-api`](api.md) over HTTP at runtime. Cross-cutting standards: see
> [conventions.md](conventions.md) §2.1 (the front-end baseline, normative), §7.1 (the four
> distributions) and §13 (naming).
>
> **This document is the design authority for the front end.** It replaces the retired
> `architecture/console.md`; §11 records what was retired and why.

## 1. Purpose

**One GUI, not an app per component.** The platform has one graphical front door: a single Next.js
application, statically exported, that calls the REST tier from the browser. Every component with a
web face is a set of pages in that application, and no component ships an application of its own.

That commitment is unchanged from the design this replaces. What changed is how it is met. The front
end used to be a shell that composed per-component *surface* plugins at build time over a
zero-dependency contract; it is now an ordinary multi-page application, and adding a page is adding a
route (§11).

The narrow-waist discipline the platform applies to Python applies here too, one layer up: a small set
of shared packages, a dependency direction asserted by a check rather than by review (§3), and no
capability that originates in the front end (§10).

## 2. What is in it

| Package | Kind | What it is |
|---|---|---|
| `@astro-mine/console` | application | The app: pages, layout, navigation. Next.js app router, static export. **Private and unpublished** — it is deployed, not consumed. |
| `@astro-mine/api-client` | generated | The TypeScript client for [`astro-mine-api`](api.md), generated from its OpenAPI document. Not hand-written, and not hand-edited. |
| `@astro-mine/ui` | design system | The Material UI theme (light and dark), the honesty kit, and **every chart the application renders** (§7.1). |
| `@astro-mine/view` | library | Visualization: the Cesium globe, world terrain, asset models, swarm and replay layers, the MCAP replay source, the timeline, and the frames layer. Client-only. See [view.md](view.md). |
| `@astro-mine/inspectors` | registry | The artifact-kind → panel registry (§6) — the one part of the retired plugin model that earned its keep. |

The workspace root is `private: true` and publishes nothing; only the packages that ship carry the
`@astro-mine` scope (`conventions.md` §13).

**The honesty kit is the part of `@astro-mine/ui` that is not Material UI's job.** MUI supplies the
ordinary components — buttons, tables, tabs, dialogs. These seven exist because the platform found
ways to mislead a reader, and each is a named acceptance criterion on the pages that use it:

| Component | What it is for |
|---|---|
| `UncertaintyValue` | A value with its cross-seed bound. A **null** bound renders as an open mark, never a zero-length error bar. |
| `AsyncState` | The one loading / error / **empty** discipline. Empty is a state with words, not a blank pane. |
| `DegradedState` | Reason **and** remediation, for an absent backend or an unmet capability. |
| `StandInBanner` | A stand-in must never look like the real thing. |
| `Digest` | Content address as identity — abbreviated, expandable to the full value. |
| `EmptyState` | Title and hint, never an empty div. |
| `InspectorSlot` | The extension point for §6. |

## 3. Layering is the product

```
   api-client      ui      view          packages/ — published; they know nothing of the app
                    ↖      ↗
                 inspectors
                       ↑
                    console              apps/ — the application. Nothing sits above it.
```

Three rules, and they are why this is one workspace rather than five repositories:

1. **The application may import any package.** It is the composition root.
2. **A package MUST NOT import the application.** The app is the sink. If the app holds something a
   package needs, the something is in the wrong place — move it down.
3. **A package MUST NOT import a sibling**, with exactly one exception: `inspectors` may import `ui`
   and `view`, because it renders artifacts and so needs the design system and — for a world — the
   globe. Two packages needing the same thing means the thing belongs in `ui` or `view`; and if it is
   *platform* behaviour, it belongs in the platform and then in the API (§10).

**The rules are enforced mechanically.** `scripts/check-layering.mjs` fails the build on any
violation, checking both what a package *declares* in its manifest and what its sources actually
*import* — including `import type`, because a type dependency is still a direction in the graph, and
including dynamic `import(…)`, because Cesium and the replay layer mount that way and would otherwise
be an unchecked back door. The permitted edges are an explicit allowlist, not numeric ranks: ranks
encode a total order the design does not have, and would quietly permit `ui → api-client` the day
someone renumbered. *A layering rule enforced only by review is a layering rule that erodes.*

The check carries its own tests, which prove each failure mode against fixture trees. A gate nobody
has seen reject anything is a gate nobody should trust.

## 4. Layout

```
apps/console/                @astro-mine/console     the Next.js application (private, deployed)
packages/api-client/         @astro-mine/api-client  generated from the API's OpenAPI document
packages/ui/                 @astro-mine/ui          MUI theme + the honesty kit + every chart
packages/view/               @astro-mine/view        Cesium globe, MCAP replay, timeline, frames
packages/inspectors/         @astro-mine/inspectors  the artifact-kind → panel registry
e2e/                         Playwright, against the built export
scripts/                     the gates: layering, OpenAPI drift, a11y, bundle budget
```

## 5. Information architecture

A persistent sidebar, grouped, with a top bar carrying breadcrumbs, search and the light/dark toggle.

```
Home                     /                     what this is, who you are, what is configured
Registry                 /registry             browse & search artifacts
  Artifact               /registry/artifact    identity, facets, attestations, inspector
  Resolve                /registry/resolve     version spec → digest
  Publish                /registry/publish     manifest → admission verdict
Benchmark                /bench                scenarios
  Leaderboard            /bench/leaderboard    rankings, primary metric, uncertainty
  Submission             /bench/submission     scores · provenance · replay
  Submit                 /bench/submit         policy → leaderboard
  Jobs                   /bench/jobs           evaluation status
  Audit                  /bench/audit          steward view
Design                   /design               studies
  New study              /design/new           objective → candidates
  Study                  /design/study         comparison · 3D inspection · publish
  Campaign               /design/campaign      a published campaign
Compute                  /compute              what this deployment can run
  Jobs                   /compute/jobs         submit · compile · sweeps · workflows
  Backends               /compute/backends     the execution backends on offer
Help                     /help                 concepts, personas, where the CLI is the answer
```

**What bounds this is what the API serves**, and that is the right constraint: the front end renders
capability the platform already exposes. Fleet, Worlds, Prospect, Mind, Guard, Learn and Allocate
have no REST surface — Sim and Prospect speak gRPC, which is not a web edge — so authoring an asset,
a world, a planner stack or a safety spec stays on the CLI, exactly as
[personas.md](../guide/reference/personas.md) describes. **Nothing here makes that permanent.** It is
a prioritization, and the way to change it is a platform capability, then an API route, then a page
(§10). Consistent with that: **nothing may be GUI-unreachable by construction.**

### 5.1 Identity lives in the search params (normative)

The application is a **static export** (`output: 'export'`): a bundle any host serves, with no Node
process to run, the browser calling the API directly. That is the property the previous front end had
and this one keeps.

It has a consequence that governs every route. `output: 'export'` pre-renders every route at build
time, so a **dynamic segment needs a closed, enumerable set of parameters** — and artifact names,
content digests, scenario ids and submission ids are none of those.

**Identity therefore lives in the query string, not in the path:**

```
/registry/artifact?name=…&version=…     not  /registry/artifact/[name]/[version]
/bench/submission?id=…                  not  /bench/submission/[id]
```

This is enumerable, shareable, and honest about what the page is: a client of a live API, not a
pre-rendered document. Where a set genuinely *is* closed, `generateStaticParams` MAY be used; nothing
else may use a dynamic segment.

The other consequences of static export, recorded so nobody rediscovers them: no server components
doing data work, no route handlers, no image optimizer, and **the API MUST send CORS headers or the
application is inert.**

## 6. The artifact inspector registry (normative)

One piece of the retired plugin model survives, because it is the piece that earned its keep: a
`world` artifact renders a globe and a `policy` renders a scorecard, resolved without the registry
page knowing what a world is.

**Contributions are keyed by Core's vocabulary.** Reusing Core's closed, append-only `PluginKind`
rather than inventing a UI-side vocabulary is what makes *contribute once, use everywhere*
(`conventions.md` §1.2) hold in the GUI, and it costs Core nothing.

**But `PluginKind` alone is not a sufficient key.** It answers *what interface does this implement*;
an inspector needs *what am I looking at*. Those diverge: a [Worlds](worlds.md) illumination field
model and a [Surrogate](surrogate.md) excavation model **both carry `field_model`**, so keying on kind
alone routes a Surrogate model into Worlds' inspector — a live collision, not a hypothetical.
[hub.md](hub.md) §2 principle 2 supplies the discriminator: a catalog entry carries the Core interface
kind and Hub's **container** kind as separate queryable facets — never one field holding two
vocabularies — with the container kind derived from the stored OCI `artifactType` so it **cannot drift
from the bytes**.

**Resolution is normative.** A UI that resolves differently on two machines is a **reproducibility
defect (CX-REPRO)**, not a cosmetic one. Therefore:

- **Match.** A contribution matches a subject when its `kind` equals the subject's `manifest.kind`
  **and** every declared discriminator matches. A contribution declaring `artifactKind` MUST NOT match
  a subject with no container kind — `artifact_kind` is nullable, and a null MUST **fail closed**
  rather than match loosely.
- **Specificity.** Among matches, the contribution declaring **more** discriminators wins. Surrogate
  claims `field_model` *where container is `surrogate`*; Worlds claims `field_model` unqualified and
  is the fallback.
- **Ties.** Two matches at equal specificity are a **modelling bug**, not a runtime condition to
  absorb silently. The registry MUST resolve deterministically by a stable total order — never
  registration order — **and** MUST surface the ambiguity as a visible diagnostic.
- **No match.** The slot MUST render an honest *"no inspector for kind X"*. Never blank.

An attribute predicate is the escape hatch for collisions the two closed vocabularies cannot
separate. It is deliberately last-resort: a predicate over a free-form dict is the weakest of the
three keys, and a contribution that needs one is evidence the artifact's facets are under-modelled.

**A new `PluginKind` is not an extension point here.** That is a Core change, argued from a named
consumer. The front end must never become a back door for widening the waist.

## 7. Conventions (normative)

The baseline — framework, language, package manager, test stack — is
[conventions.md](conventions.md) §2.1 and is not restated here. What follows is specific to this
distribution.

**The honesty rules.** Each exists because the platform found a way to mislead a reader:

1. **A stand-in must never look like the real thing.** A fixture-scored leaderboard row and a
   stand-in evaluator's Pareto front are labelled *in place*, not in a footnote.
2. **Uncertainty renders as uncertainty.** A null bound is an open mark, never a zero-length error
   bar, which asserts a precision nobody measured.
3. **Degrade visibly, never blank.** A missing backend is a *state*, with a reason and a remedy, and
   it stays in the navigation.
4. **The digest is the identity.** A tag is a query; the content address is what a reader pins.
5. **Provenance before interpretation.** What produced a number is read before the number is.
6. **Verification is claimed only where it happened.** Attestations *present in a registry* are not a
   verified supply chain, and the words differ.
7. **Accessibility is a build gate**, not an aspiration: keyboard reachability, focus management on
   navigation, live-region announcements, contrast in both modes.

**Core vocabulary on the wire.** A page consumes Core schemas by their published `$id` and does not
re-declare their shapes (`conventions.md` §3.1). It inherits Core's frame and unit rules: a value with
no unit is a bug upstream.

### 7.1 The obligation the chart library creates

`@astro-mine/ui` **owns every chart the application renders and exports no raw chart primitive.**

This is a rule now because it used to be a property. The previous design used visx, where a second
y-axis was unrepresentable and a null uncertainty bound rendered as an open mark *by construction* —
the discipline was enforced by an API that could not express the wrong thing. **MUI X Charts
guarantees neither and ships no error bars.** So the design system supplies the error-bar and
parallel-coordinates layers itself, and **MUST carry unit tests asserting that a null bound renders as
an open mark and that no chart can be given two y-axes.**

A rule enforced only by review is a rule that erodes — which is why it is a test. A chart in a page
that reaches past `@astro-mine/ui` is the failure mode to watch for.

## 8. Build, test & publish

The build has eight gates. Each exists because something it catches is invisible to the others:

| Lane | Fails the build on |
|---|---|
| **Typecheck** | any type error, across every package and the app |
| **Lint / format** | any error; zero warnings tolerated |
| **Unit / component** | a failing test, or coverage below the floor — every page and every honesty component against a faked API (MSW) |
| **Contract** | **any drift** between the committed generated client and the API's live OpenAPI document |
| **Honesty** | a null bound rendered as a zero-length bar; a stand-in rendered unlabelled (§7.1) |
| **Build** | a build error, or a route exceeding its bundle budget |
| **E2E** | a broken persona journey, driven against the **built export** |
| **Accessibility** | any axe violation, over every route, in **both** modes |

Two assertions run on the emitted bytes rather than on exit codes, because both properties are
invisible to a passing build: that the static export exists, and that its HTML carries the inlined
styles that make the first paint arrive styled instead of flashing.

**Publishing:** the libraries publish to a private npm registry (GitHub Packages) during incubation,
which is why installing them needs a `read:packages` token; the application is deployed as a built
static bundle and publishes nothing. Cesium ships binary assets the build copies rather than fetches,
so the app has no external CDN dependency at runtime.

**Two environment notes, because both look like product defects and are not.** Playwright cannot
launch a browser in this project's WSL development environment (a missing system library), so a red
browser lane *there* is environmental — units, typecheck, lint and build are the local truth, and CI
is the arbiter. And `jsdom` does not implement every `File` method, so a page reading an uploaded file
must use an API `jsdom` has.

## 9. Interfaces

- **Inward:** [`astro-mine-api`](api.md) over HTTP, at runtime, through the generated client. No
  package here imports Python or knows the platform's internals.
- **The OpenAPI document is the contract.** The client is generated from it and a CI lane fails on
  drift, so the API cannot change out from under the front end silently, and no page hand-writes a
  request.
- **Server state:** `fetch` through the generated client plus the one `AsyncState` discipline. The
  baseline deliberately ships no data-fetching or client-cache library (`conventions.md` §2.1).

## 10. What this distribution must not do

1. **No platform capability originates here.** A front end that needs new behaviour needs it in the
   platform, and then in the API — not in a component wearing the wrong clothes (`conventions.md` §2).
   Restated because the temptation grows with the page count.
2. **No package imports the application**, and no package imports a sibling outside the one permitted
   edge (§3).
3. **No second data-fetching stack** (§9).
4. **No raw chart primitive escapes `@astro-mine/ui`** (§7.1).
5. **No dynamic route segment** whose parameter set is not closed and enumerable (§5.1).
6. **No hand-edited generated client.** Regenerate; the drift gate is not advisory.

## 11. What was retired, and why

A reader who liked the previous design should be able to find out what happened to it.

- **The `Surface` contract, and with it `@astro-mine/surface`, `buildRegistry`, `createConsole`,
  `SurfaceRouteHost` and the per-component `<component>-ui` packages.** The shell composed plugin
  surfaces at build time over a zero-dependency contract. It bought third-party extensibility the
  platform never used — every surface was first-party — and it cost a bespoke routing layer that
  fought the framework, plus a publish-to-test loop across four repositories for any contract change.
  **Pages are ordinary routes now; adding a page is adding a route.** What the model got right, and
  what survives, is §6.
- **The separate console design document.** There is no longer a "console" distinct from the
  application — the shell *is* the app — so a document about the shell was a document about half a
  thing. It folded into this one.
- **Three derived themes** (`instrument`/`editorial`/`mission`) and their derivation, contrast and
  palette generators. **Light and dark only**; MUI's `colorSchemes` carries them. Three themes meant
  three times the contrast surface to prove and generators to maintain, for a choice no user asked to
  make.
- **visx, and Plotly in the design surface.** Replaced by MUI X Charts, at the cost recorded in §7.1 —
  a guarantee became an obligation.
- **`react-router` and Vite.** The framework routes and builds.
- **A base URL per surface.** One API, one client, one configured endpoint.

## 12. Roadmap alignment

`RM-DIST-04` — one front end, one workspace, one build. The workspace, the application, the package
skeletons and the CI gates are stood up; the client, the theme, the chart layer, the shell, the
inspector registry and the pages land across Waves 28–30, and the eighteen component repositories are
retired last (`RM-DIST-05`). See the [roadmap](../roadmap/README.md) and, for the user-facing view,
the [console guide](../guide/console.md).

Operations surfaces — the full operations viewer and the Ops supervisory console — are Phase 2 and
belong to [Ops](ops.md), not here.
