# The console

**The platform's single GUI front door** — one application, statically exported, that talks to the
REST tier from your browser.

Covers **UC-A4** (find the docs for my task) · **UC-G5** (view the leaderboard) · **UC-B6** (inspect
a run). Personas: **P5** Mission Designer, **P6** Educator/Student, **P1** Benchmark Researcher.

---

> ## Status: being rebuilt — read this before anything below
>
> The console is **mid-rebuild**, and this page describes the application being built rather than a
> finished product. Concretely, today:
>
> - **The workspace, the application and its build ship.** `pnpm dev` runs, `pnpm build` produces a
>   static export, and CI gates it.
> - **No page has been written yet, and nothing calls the API.** There is a placeholder home page and
>   nothing else. The registry, benchmark, design and compute pages land across Waves 29–30.
> - **The previous console still exists**, in the `astro-mine-console` repository, and is what
>   actually renders a leaderboard or a study today. It is superseded and will be retired, but it has
>   not been yet.
>
> Everything below marked *(not built yet)* is the design, not a description of running software.
> Saying so is the same honesty rule the GUI itself is held to: a stand-in must never look like the
> real thing.

## What it is

Before the console, each component with a web face had its own application, its own navigation and
its own visual language. The console replaces that with **one application** — a conventional
multi-page app with a sidebar, where every component with a web face is a set of pages.

The previous design did this differently: a shell that composed per-component *surface* plugins at
build time over a small contract. That contract is retired. **Adding a page is now adding a route**,
which is the change worth knowing if you read the older documentation
([ui.md §11](../architecture/ui.md) records what went and why).

The rule underneath it is unchanged, and it is the platform's narrow waist applied to the GUI
([concepts/narrow-waist.md](concepts/narrow-waist.md)): **no capability originates in the front end.**
A page renders what a component already exposes through the API. If a page needs new behaviour, the
behaviour goes in the platform, then in the API, then on the page.

## What you will find in it *(not built yet)*

```
Home         /            what this is, who you are, what is configured
Registry     /registry    browse and search artifacts · resolve a version · publish
Benchmark    /bench       leaderboard · a submission's scores, provenance and replay · submit
Design       /design      state an objective, compare candidate swarms, publish a campaign
Compute      /compute     backends, jobs, sweeps and workflows
Help         /help        concepts, personas, and where the CLI is the answer
```

**There is no View page.** `@astro-mine/view` is the widget library — the Cesium globe, the MCAP
replay, the timeline — that other pages render *through*. It is not a page and has no nav entry.

**Links carry their subject in the query string**, not in the path — `/registry/artifact?name=…` and
`/bench/submission?id=…`. That is worth knowing when you share one: the whole address matters, and a
link without its query is just the empty page.

## Who can install it today

**This is the honest part, and it has been decided rather than solved.**

The `@astro-mine/*` libraries are published to **private GitHub Packages — never npmjs.com** — and
they **flip public with the repositories** at the first public-benchmark milestone.
`@astro-mine/console` is an application and is never published at all.

| You are | Can you install it? | How |
|---|---|---|
| Another `astro-mine` repo's CI | **Yes** | Grant that repo read access under the package's **Manage Actions access** settings; `actions/setup-node` with `registry-url` + `scope` writes the auth from the job's `GITHUB_TOKEN`. |
| A developer inside the org, locally | **Yes** | `pnpm config set "//npm.pkg.github.com/:_authToken" "$(gh auth token)"` — a **user-level** token with `read:packages`. Never in a committed project `.npmrc`: pnpm refuses to expand `${NODE_AUTH_TOKEN}` from one, because a swapped registry line there could leak the token. |
| An unauthenticated outsider (a student, a new contributor) | **Not until the flip** | No credential grants access while the repositories are private. |

That last row is the audience the commons is ultimately for, and it stays blocked until the flip.
This is a property of the org still being private, not something any package can grant around.

Note that building the console itself needs **no** credential: every `@astro-mine` dependency in the
workspace is a local link. The token is for consuming the published libraries from outside.

## Run it

```bash
corepack enable
pnpm install
pnpm dev            # http://localhost:3000
```

Node **≥ 22.13** — that floor is pnpm's own, not a preference, and pnpm fails outright on Node 20.
pnpm workspaces throughout.

To serve what actually ships rather than the dev server:

```bash
pnpm build          # → apps/console/out, a static bundle any host can serve
```

There is no Node process behind the built app. That is deliberate: it deploys to any static host, and
what it needs from the outside is one API.

## Configure it

The endpoint is **runtime** configuration, never baked into the bundle — a static app whose backend
URL is compiled in is deployable only by whoever built it.

```json
{
  "apiBaseUrl": "http://localhost:8000"
}
```

**One endpoint, not one per surface.** The older console configured a separate base URL for each
component's backend; there is one REST tier now ([api.md](../architecture/api.md)), so there is one
address to set. A missing or unreachable config file is not an error — the app starts unconfigured
and says so.

Because the browser calls the API directly from a different origin, **the API must send CORS
headers**, or the app loads and can do nothing. That is a deployment requirement, not an optional
hardening step.

## Degraded pages

A page whose backend is absent or whose capability is unmet **degrades visibly and stays in the
navigation** — it never blanks and never silently disappears. With no API configured, the nav is
intact and each page says what is missing and what would fix it.

Two flavours you will meet:

- **Unconfigured backend** — the page exists, the endpoint is not set. Fix: point it at a running
  API.
- **Capability-gated** — the API is reachable, but does not grant the capability the page needs.
  Publishing is gated this way: it renders as unavailable rather than offering a button that will
  fail.

Reading a degraded page as breakage is the usual mistake. It is the honesty rule applied to the GUI —
the same rule that makes a scorecard name its runner and a render label its proxy geometry
([concepts/fidelity.md](concepts/fidelity.md)).

## The leaderboard (UC-G5) *(not built yet)*

The **Leaderboard** page is P1's and P6's entry point, and the bar it is held to is *a student finds
the leaderboard in one click.*

Each ranking row renders **the runner that produced the entry**. That is the same required
`Scorecard.runner` field the CLI prints — a fixture-scored entry and a Sim-scored entry are
distinguishable on the board, not just in the artifact.

**Leaderboard reads are account-free.** Submitting needs a token
([tutorial 03](tutorials/03-train-and-publish-a-policy.md) §7); looking does not.

Until this page lands, `astro-mine bench leaderboard` is the answer, and it prints the same runner
field.

## Inspecting a run (UC-B6) *(not built yet)*

Run inspection — MCAP replay, the timeline, the 3D scene — renders through `@astro-mine/view`'s
widgets inside the pages that own the data. Produce a log first:

```bash
astro-mine sim run lunar-polar-ice-prospecting-sprint-v1 --seed 1001 --out run.mcap
```

See [tutorial 02 §7](tutorials/02-run-it-in-the-simulator.md), including the SPICE prerequisite.

## `view/lib/` is not the console

`@astro-mine/view` ships a demo harness with committed fixtures. **It is a developer component
gallery** — a place to see each widget in isolation while working on it. It is not the console, not
an application, and not the product.

View's README says so itself. It is worth repeating here because landing in the gallery and
concluding *"so this is the GUI"* is exactly the failure that makes an evaluator walk away — the one
J6 documents. If what you are looking at is a grid of isolated widgets over fixture data, you are in
the gallery.

---

## See also

- [07 — design a swarm in Studio](tutorials/07-design-a-swarm-in-studio.md) — P5's whole journey.
- [reference/cli.md](reference/cli.md) — the command-line half of everything above, and the answer
  for anything the GUI has not reached yet.
- **Working on the console** is developer documentation, not user documentation: it lives in the
  `astro-mine-ui` repository's `ARCHITECTURE.md` and in
  [architecture/ui.md](../architecture/ui.md).
- **The operator/ops viewer** — a Phase 2 deliverable. Nothing in this guide covers operating a live
  mission.
