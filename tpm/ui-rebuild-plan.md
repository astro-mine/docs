# The UI rebuild — plan and issue backlog (Waves 28–30)

> **Point-in-time, 2026-07-31.** The plan as drafted. It records the decisions taken, the feature
> inventory the rebuild must not lose, and the issue backlog derived from both. Like every document
> in `tpm/`, it is superseded by execution rather than maintained — the normative home for the
> design is [`architecture/ui.md`](../architecture/ui.md), which the first issue here rewrites.

`astro-mine-ui` is the fourth distribution ([`conventions.md`](../architecture/conventions.md) §7.1)
and the last one not stood up. `RM-DIST-04` scoped that as a **move**: take the five package trees
that exist today — `astro-mine-console`'s `surface`/`ui`/`console`, `astro-mine-view`, and the `ui/`
trees of Hub, Studio and Bench — and put them in one workspace.

**This plan replaces that move with a rebuild.** The front end is re-implemented as a
**TypeScript / React / Next.js application on Material UI** — a multi-page app with a real sidebar
and navigation, not a single-page shell composing plugin surfaces. Every capability the current UI
has is carried over; almost none of the code is.

---

## 1. Decisions taken (2026-07-31)

| # | Decision | Consequence |
|---|---|---|
| **D1** | **Next.js (app router) + Material UI**, multi-page, sidebar navigation | Replaces Vite + `react-router` + the bespoke token/primitive design system |
| **D2** | **The `Surface` contract is retired.** Pages are ordinary Next.js routes | `@astro-mine/surface`, `buildRegistry`, `createConsole`, `SurfaceRouteHost` and the per-component surface packages all go. Adding a page is adding a route |
| **D3** | **One survivor of the plugin model: the artifact inspector registry** | A `world` artifact still renders a globe and a `policy` still renders a scorecard, resolved by Core `kind` + Hub `artifact_kind` + an attribute predicate. This is the part that earned its keep |
| **D4** | **The UI calls `astro-mine-api` over REST, through a generated TypeScript client** | No hand-written client per surface. The OpenAPI document is the contract, and CI fails on drift |
| **D5** | **Static export** (`output: 'export'`), browser calls the API directly | Keeps today's property: a static bundle any host serves, no Node process to run. Costs: CORS must be enabled on the API, there are no server components or route handlers, and **route identity lives in search params** (§4.3) |
| **D6** | **Light and dark only.** No multi-theme | The three-theme system (`instrument`/`editorial`/`mission`) and its derivation/contrast/palette generators are retired; MUI's `colorSchemes` carries light/dark |
| **D7** | **Charts on MUI X Charts** | Replaces both visx (`@astro-mine/ui`'s chart layer) and Plotly (Studio's Pareto + parallel coordinates). The uncertainty discipline moves from *enforced by the library's API* to *enforced by our own wrapper components and their tests* — see §5.1, which is now a load-bearing obligation rather than a free property |
| **D8** | **Scope: Hub + Bench + Studio at parity, plus three new areas** — the Bench write path, a Cloud jobs surface, and a home/getting-started page | Three REST surfaces the platform has served all along and no UI has ever called |

**What does not change.** The honesty rules (§5), the degrade-never-blank rule, CX-LOCAL, CX-REPRO,
accessibility as a build gate, and the rule that **no platform capability originates in the front
end** — a page that needs new behaviour needs it in the platform, then in the API
([`conventions.md`](../architecture/conventions.md) §2).

---

## 2. What exists today — the inventory the rebuild must not lose

Read from the shipped code, not from the docs. ~9,000 lines of application TypeScript across four
repositories, plus ~5,000 lines of visualization library.

### 2.1 The shell — `@astro-mine/console`

Nav rail with grouped entries · skip link · keyboard chords (`g l` leaderboard, `g b` bench, `g d`
design, `/` focuses a search) · focus moved to the content region on every navigation and the new
title announced in a live region · route error boundary that renders rather than blanks · runtime
endpoint configuration fetched at boot · theme + mode persisted to `localStorage` · a surface with an
unmet capability **stays in the nav** carrying a "not configured" badge.

### 2.2 The design system — `@astro-mine/ui`

Thirty components. The ordinary ones (Button, Input, Select, Table, Tabs, Dialog, Toast, Tooltip,
Panel, Grid, Stack, …) are MUI's job now. **Seven are not, and are the ones that matter:**

| Component | What it is for |
|---|---|
| `UncertaintyValue` | A value with its cross-seed bound. A **null** bound renders as an open mark, never a zero-length error bar |
| `AsyncState` | The one loading / error / **empty** discipline. Empty is a state with words, not a blank pane |
| `DegradedState` | Reason **and** remediation, for a backend that is absent or a capability that is unmet |
| `StandInBanner` | A stand-in must never look like the real thing |
| `Digest` | Content address as identity — abbreviated, expandable to the full value |
| `EmptyState` | Title + hint, never an empty div |
| `InspectorSlot` | The extension point (D3) |

Plus: the token layer, light/dark, an axe-based a11y test helper, and a visx chart layer whose
`BarChart` carries per-bar error bars.

### 2.3 Hub surface — `@astro-mine/hub-ui`

- **Browse** — semantic/text search, result table (reference, kind, namespace, publisher, `yanked` /
  `deprecated` badges), master-detail with the inspector.
- **Artifact detail** — **digest as the headline identity**, catalog facets (Core kind, container
  kind, license, namespace, publisher), attestation types present in the registry rendered
  *honestly* ("types present — not verified in the browser"), and the `InspectorSlot`.
- **Resolve** — name + PEP-440 version spec → the one immutable digest that satisfies it.
- **Publish** — manifest upload + digest + publisher, gated on its **own** `hub.publish` capability
  so reads stay account-free; per-status honest outcomes (503 unconfigured / 403 refused / 422
  admission verdict shown verbatim, never a green check the browser did not earn).

### 2.4 Bench surface — `@astro-mine/bench-ui`

- **Leaderboard** — scenario picker, primary-metric bar chart with cross-seed error bars, sortable
  ranked table with one uncertainty-rendered column per metric, and **the runner badge in the row
  itself**: a fixture-scored entry is unmissably labelled, not footnoted.
- **Scorecard detail** — tabbed. *Scores*: every metric with its bound, aggregation, seed count and
  direction. *Provenance*: the reproducibility bundle — scenario spec hash, Core schema digest, code
  version, environment lockfile, held-out seeds, per-seed values, and the pinned content digests.
  *Replay*: the MCAP manifest summarised (agents, seed, sim-time span, frame count, digest) and a
  lazily-mounted 3D episode replay.

### 2.5 Studio surface — `@astro-mine/studio-ui`

The whole P5 journey: **objective → candidates → study → compare → inspect → publish.**

- **New study** — a structured objective form (name, region, body/frame/reference radius, target
  products, constraints) → `POST /intent` → the returned document validated against Core's schema
  client-side before anything runs → `POST /studies`.
- **Candidate composition** — each candidate row picks a robot **from the catalog**, so it carries a
  real content digest, and shows what that digest names: identity, kind, capability tags.
- **Study / candidate / world pickers** — including a seeded example study badged *"Example — not
  your result"*, and a `?study=` deep link with a guarded parse.
- **Comparison** — Pareto scatter with error bars where a bound exists, parallel coordinates across
  every metric, and three honesty callouts above the plots: the evaluator's provenance (a stand-in
  says so), a degenerate front explained as a property of the scoring, and which metrics carry no
  measured bound.
- **3D candidate inspection** — the resolved world's terrain with the candidate's swarm placed on
  it, labelled *"design-time layout, not a simulated pose"*, and an explicit reason whenever no
  swarm is shown.
- **Publish** — the chosen candidate published as a signed, content-addressed campaign, authored
  server-side.

### 2.6 The visualization library — `@astro-mine/view`

Not superseded by MUI and carried over as a package: the Cesium globe scene, world terrain from
published bundles (3D Tiles + anchor transform), asset models from SADF/glTF, swarm and replay
layers, coordinate readout, the MCAP replay source (range reads, **content-hash verified before
decode**), replay tracks and channels, the shared timeline clock and scrubber, and the frames layer
(CRS, poses, projection, epochs, unit guards).

---

## 3. What the API serves — and what bounds the scope

`astro-mine-api` serves **40 routes over 4 surfaces** (OpenAPI 3.1, 78 component schemas). That is
the whole of what the UI can do, and it is the right constraint: the front end renders capability the
platform already exposes.

> This said *37 routes, 70 component schemas* when the plan was drafted, which was before `api#2`,
> `api#3` and `api#4` landed; the figures above are the document at `api#4`. **Nothing should encode
> either number.** `ui#2`'s generated client asserts its surface against the document itself, which
> is the only count that cannot go stale — and this correction is the argument for that having been
> the right call.

**Served and never surfaced by any UI** — the new scope in D8:

| Route | What it gives a user |
|---|---|
| `POST /bench/submissions`, `/submissions/hub` | Submit a policy to the leaderboard from the GUI |
| `GET /bench/jobs/{id}` | Watch an evaluation run |
| `DELETE /bench/submissions/{id}` | Retract a submission (steward) |
| `GET /bench/audit` | The audit trail (steward) |
| `POST /bench/scenarios` | Author a scenario into the zoo |
| `POST /cloud/jobs`, `/jobs/compile`, `/sweeps/*`, `/workflows/compile`, `GET /cloud/backends` | Submit and preview a compiled job, sweep or workflow |
| `POST /hub/artifacts/{n}/{v}/download` | Materialize an artifact |
| `GET /studio/campaigns/{ref}` | Open a published campaign |

**Not served, therefore not in scope.** Fleet, Worlds, Prospect, Mind, Guard, Learn and Allocate have
no REST surface — Sim and Prospect speak gRPC, which is not a web edge. Authoring an asset, a world,
a planner stack or a safety spec stays on the CLI, exactly as
[`personas.md`](../guide/reference/personas.md) describes. **Nothing here makes that permanent** —
it is a prioritization, and the way to change it is a platform capability, then an API route, then a
page.

**Three API defects block a clean client** and are the first issues in the backlog: the browser
cannot call the API cross-origin at all (no CORS), FastAPI's default operation ids generate method
names like `do_search_hub_search_get`, and six routes answer `dict[str, Any]` so the generated client
types them as nothing.

---

## 4. The target

### 4.1 Stack

| Concern | Standard |
|---|---|
| Framework | **Next.js 15** (app router), **static export** |
| Language / UI | **TypeScript 5.7+** · **React 19** · **Material UI 7** (`@mui/material`, `@mui/icons-material`) |
| Charts | **MUI X Charts**, behind the honesty wrappers of §5.1 |
| 3D / replay | `@astro-mine/view` (Cesium, MCAP), client-only |
| API access | Generated client from the API's OpenAPI document |
| Server state | `fetch` through the generated client and one `AsyncState` discipline — unchanged, and still deliberately no cache library |
| Package manager | **pnpm**, pinned in the workspace root |
| Tests | **Vitest** + Testing Library + MSW (unit/component), **Playwright** against the built export (e2e), **axe** (a11y) |

### 4.2 Workspace layout

```
astro-mine-ui/                       pnpm workspace; root is private and unpublished
├── apps/console/                    the Next.js application — pages, layout, navigation
├── packages/api-client/             generated from the OpenAPI document + config + error mapping
├── packages/ui/                     MUI theme (light/dark) + the honesty kit + chart wrappers
├── packages/view/                   Cesium globe, MCAP replay, timeline, frames
├── packages/inspectors/             the artifact-kind → panel registry (D3)
├── e2e/                             Playwright, against the built export
└── scripts/                         gates: layering, OpenAPI drift, a11y, bundle budget
```

Dependency direction is one way — `api-client` and `ui` and `view` know nothing of the app — and is
asserted by a check rather than by review, which is the one rule worth keeping verbatim from the old
design.

### 4.3 Information architecture

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
Compute                  /compute              backends
  Jobs                   /compute/jobs         submit · compile · sweeps · workflows
Help                     /help                 concepts, personas, where the CLI is the answer
```

**Static export makes route identity a design constraint.** `output: 'export'` pre-renders every
route at build time, so a dynamic segment needs a closed, enumerable set of parameters — and
artifact names, digests, scenario ids and submission ids are none of those. **Identity therefore
lives in the query string** (`/registry/artifact?name=…&version=…`,
`/bench/submission?id=…`), which is enumerable, shareable, and honest about the fact that the page is
a client of a live API rather than a pre-rendered document. Where a set genuinely is closed it may
use `generateStaticParams`; nothing else may.

---

## 5. The rules that survive the rewrite

These are not decoration. Each one exists because the platform found a way to mislead a reader, and
each is a named acceptance criterion on the issues that touch it.

1. **A stand-in must never look like the real thing.** A fixture-scored leaderboard row and a
   stand-in evaluator's Pareto front are labelled *in place*, not in a footnote.
2. **Uncertainty renders as uncertainty.** A null bound is an open mark. Never a zero-length error
   bar, which asserts a precision nobody measured.
3. **Degrade visibly, never blank.** A missing backend is a *state*, with a reason and a remedy, and
   it stays in the navigation.
4. **The digest is the identity.** A tag is a query; the content address is what a reader pins.
5. **Provenance before interpretation.** What produced a number is read before the number is.
6. **Verification is claimed only where it happened.** Attestations *present in a registry* are not
   a verified supply chain, and the words differ.
7. **Accessibility is a build gate**, not an aspiration: keyboard reachability, focus management on
   navigation, live-region announcements, contrast in both modes.

### 5.1 The obligation D7 creates

visx was chosen because a second y-axis was unrepresentable and a null bound rendered as an open mark
*by construction*. MUI X Charts makes neither guarantee, and it ships no error bars. So the discipline
becomes ours to enforce: `packages/ui` owns every chart the app renders, exposes no raw MUI X chart,
supplies the error-bar and parallel-coordinates layers, and **carries unit tests asserting that a
null bound renders as an open mark and that no chart can be given two y-axes.** A rule enforced only
by review is a rule that erodes — which is why it is a test.

---

## 6. Testing and CI

The old front end's build had six gates. The new one keeps five of them, drops the three-theme
generators D6 retires, and adds two the REST client makes possible.

| Lane | What it runs | Fails the build on |
|---|---|---|
| **Typecheck** | `tsc --noEmit` across every package | any type error |
| **Lint / format** | ESLint + Prettier | any error, zero warnings tolerated |
| **Unit / component** | Vitest + Testing Library + **MSW**, every page and every honesty component against a faked API | a failing test, or coverage below the floor |
| **Contract** | the generated client regenerated from `astro-mine-api` at `HEAD` | **any drift** between the committed client and the live OpenAPI document |
| **Honesty** | the §5.1 assertions, as ordinary unit tests | a null bound rendered as a zero-length bar; a stand-in rendered unlabelled |
| **Build** | `next build` (static export) + a bundle budget | a build error, or a route exceeding its budget |
| **E2E** | Playwright against the **built export**, driving each persona journey end to end against a seeded API | a broken journey |
| **Accessibility** | axe over every route, in **both** modes | any violation |

Two environment facts, recorded because both look like product defects and are not: Playwright
cannot launch a browser in this workspace's WSL environment, so a red browser lane *there* is
environmental and CI is the arbiter; and `jsdom` does not implement every `File` method, so a page
reading an uploaded file must use an API `jsdom` has.

**The test harness lands before the pages** (Wave 28), not after them, so every page issue can carry
"tested" in its acceptance criteria and mean it.

---

## 7. The backlog

26 issues over three waves, continuing the platform's global topological wave numbering (Wave 27 was
the CLI's departure from the platform). Repo standup is `Wave 0` by the standing convention.

**Wave 28 — decide, then build the foundations.** Issue 28.1 is gating: the architecture is settled
in `docs` before any of it is implemented, exactly as the console's own contract was.

| # | Issue | Title | Pri | Size |
|---|---|---|---|---|
| 0.1 | `ui#1` | `[setup]` Repo standup — pnpm workspace, Next.js app, MUI, CI | High | M |
| 28.1 | `docs#92` | Rewrite the front-end architecture for the Next.js/MUI UI **(gating)** | High | L |
| 28.2 | `api#2` | CORS for the browser tier — the static UI cannot call the API at all today | High | S |
| 28.3 | `api#3` | Stable operation ids and typed responses, so a generated client is usable | High | M |
| 28.4 | `api#4` | One error contract and one health endpoint spelling | Medium | M |
| 28.5 | `ui#2` | `@astro-mine/api-client` — generated from OpenAPI, with a drift gate | High | L |
| 28.6 | `ui#3` | The MUI theme (light/dark) and the honesty kit | High | L |
| 28.7 | `ui#4` | The chart layer on MUI X Charts — error bars, parallel coordinates, honesty tests | High | L |
| 28.8 | `ui#5` | The app shell — sidebar, navigation, breadcrumbs, keyboard, a11y | High | L |
| 28.9 | `ui#6` | Port `@astro-mine/view` into the workspace and make it Next-safe | High | L |
| 28.10 | `ui#7` | The artifact inspector registry — the one survivor of the Surface contract | Medium | M |
| 28.11 | `ui#8` | The test harness and CI lanes — before the pages, not after | High | M |

**Wave 29 — the pages.** Parallel once Wave 28 lands.

| # | Issue | Title | Pri | Size |
|---|---|---|---|---|
| 29.1 | `ui#9` | Home — what this is, who you are, what is configured | Medium | M |
| 29.2 | `ui#10` | Registry: browse, search and the artifact page | High | L |
| 29.3 | `ui#11` | Registry: resolve, publish and download | Medium | M |
| 29.4 | `ui#12` | Benchmark: the leaderboard and the scorecard | High | L |
| 29.5 | `ui#13` | Benchmark: provenance and episode replay | High | L |
| 29.6 | `ui#14` | Benchmark: submit, jobs, retract and audit — the write path | Medium | L |
| 29.7 | `ui#15` | Design: the objective and the candidate swarms | High | L |
| 29.8 | `ui#16` | Design: run the study and compare the front | High | L |
| 29.9 | `ui#17` | Design: the world and the 3D candidate inspection | High | L |
| 29.10 | `ui#18` | Design: publish the campaign, and open a published one | Medium | M |
| 29.11 | `ui#19` | Compute: jobs, sweeps, workflows and backends | Low | M |

**Wave 30 — close it out.**

| # | Issue | Title | Pri | Size |
|---|---|---|---|---|
| 30.1 | `ui#20` | The end-to-end journey suite and the accessibility gate | High | L |
| 30.2 | `ui#21` | Ship it — the static bundle, its runtime config, and an image that serves it | Medium | M |
| 30.3 | `docs#93` | Retire the console, the view repo and the three `ui/` trees (`RM-DIST-04`/`05`) | Medium | M |

### Critical path

`28.1` (the architecture) → `28.2`/`28.3` (the API can be called and generated from) → `28.5` (the
client) → `28.6`–`28.8` (theme, charts, shell) → the pages. `28.9` (View) gates only `29.5` and
`29.9`; `28.10` gates only `29.2`. `28.11` should land alongside `28.6` so no page is written
untested.

---

## 8. Risks

- **MUI X Charts is a downgrade in enforced honesty** (§5.1). The mitigation is tests, and tests are
  weaker than an API that cannot express the wrong thing. Watch for a chart in a page that reaches
  past `packages/ui`.
- **Static export forbids server-side anything.** Every data fetch is a browser fetch, every identity
  is a search param, and the API must send CORS headers or the app is inert. `28.2` is not optional.
- **Cesium in Next.js** needs client-only mounting, dynamic import, and its assets copied into the
  export. It works, and it will not work by accident.
- **React 19** moves `@astro-mine/view`'s peer range, and Cesium's React bindings are the surface to
  check first.
- **Scope.** Three of the four Wave-29 areas are re-implementations of a known shape; the Bench write
  path and Compute are new UX with no incumbent to copy. Expect the estimates there to be softest.

---

## 9. Superseded

This plan supersedes `RM-DIST-04`'s framing of the front-end distribution as a move of five package
trees. The roadmap item's intent — *one front end, one workspace, one build* — is unchanged, and
`30.3` still ends with the old repositories retired.
