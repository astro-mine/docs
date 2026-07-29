# The console

**One shell, many surfaces** — the platform's single GUI front door.

Covers **UC-A4** (find the docs for my task) · **UC-G5** (view the leaderboard) · **UC-B6** (inspect
a run). Personas: **P5** Mission Designer, **P6** Educator/Student, **P1** Benchmark Researcher.

---

## What it is

Before the console, each component that had a web face had its own application, its own navigation,
and its own visual language. The console replaces that with **one shell** into which components
contribute **surfaces** ([console.md](../architecture/console.md)
and 2).

A surface is a package — `@astro-mine/<component>-ui` — that declares what it contributes: nav
entries, routes, and inspector contributions. Registering one in the shell is **one line**. That is
the RFC's own acceptance test: *publish a surface package, add one line*, and nothing else changes.

The rule underneath it: **a surface never imports another surface.** They compose only through the
shell and the `Surface` contract, which is the console's expression of the platform's narrow waist
([concepts/narrow-waist.md](concepts/narrow-waist.md)).

## What ships today

Three real surfaces, composed in `packages/console/src/App.tsx`, alongside the built-in example
surfaces:

| Surface | Package | Routes | For |
|---|---|---|---|
| **Hub** | `@astro-mine/hub-ui` 0.2.0 | Browse · Resolve · Publish | everyone — the artifact registry |
| **Bench** | `@astro-mine/bench-ui` 0.1.1 | Leaderboard | P1, P6, P7 |
| **Studio** | `@astro-mine/studio-ui` 0.2.0 | Design workspace | P5 |

There is **no View surface**. `@astro-mine/view` is the widget library — the Cesium globe, the MCAP
replay, the timeline — that the other surfaces render *through*. It is not a surface itself and has
no nav entry of its own.

## Who can install it today

**This is the honest part, and it has been decided rather than solved.**

`@astro-mine/view`, `@astro-mine/surface`, and `@astro-mine/ui` are published to **private GitHub
Packages — never npmjs.com** — and they **flip public with the repositories** at the first
public-benchmark milestone. `@astro-mine/console` is an application and is never published at all.

| You are | Can you install it? | How |
|---|---|---|
| Another `astro-mine` repo's CI | **Yes** | Grant that repo read access under the package's **Manage Actions access** settings; `actions/setup-node` with `registry-url` + `scope` writes the auth from the job's `GITHUB_TOKEN`. |
| A developer inside the org, locally | **Yes** | `pnpm config set "//npm.pkg.github.com/:_authToken" "$(gh auth token)"` — a **user-level** token with `read:packages`. Never in a committed project `.npmrc`: pnpm refuses to expand `${NODE_AUTH_TOKEN}` from one, because a swapped registry line there could leak the token. |
| An unauthenticated outsider (a student, a new contributor) | **Not until the flip** | No credential grants access while the repositories are private. |

That last row is the audience the commons is ultimately for, and it stays blocked until the flip.
This is a property of the org still being private, not something any package can grant around.
`@astro-mine/view`'s README carries the authoritative version of this matrix — check it there rather
than trusting a copy.

## Run it

```bash
corepack enable
pnpm install
pnpm dev
```

Node **≥ 20.19**. pnpm workspaces throughout.

The console starts **with no endpoints configured**, and that is deliberate: every surface degrades
visibly out of the box, so the shell is useful with zero configuration and says what it is missing.

## Configure the surfaces

Endpoints are **runtime** configuration, never baked into the bundle — a static SPA whose backend
URLs are compiled in is deployable only by whoever built it. Three layers, later winning:

1. the `createConsole` defaults,
2. `/console.config.json`, fetched at startup,
3. anything already present.

```json
{
  "endpoints": {
    "hub": "http://localhost:8080",
    "bench": "http://localhost:8081",
    "studio": "http://localhost:8000"
  }
}
```

Each key is **one surface's own base URL**. There is no gateway and no unified API — that is
deferred, and the gateway is Phase 2. A missing or unreachable config file is not an error; the
defaults stand.

## Degraded surfaces

A surface whose capabilities are unmet **degrades visibly and stays in the navigation** — it never
blanks and never silently disappears. With no `endpoints.studio` configured, the Design nav entry
remains and the route says *"Studio is not configured."*

Two flavours you will meet:

- **Unconfigured backend** — the surface is installed, its endpoint is not set. Fix: point it at a
  running backend (e.g. `astro-mine studio serve`).
- **Capability-gated** — the surface is configured, but the backend does not grant the capability
  the route needs. Hub's Publish route is gated this way: it renders as unavailable rather than
  offering a button that will fail.

Reading a degraded surface as breakage is the usual mistake. It is the honesty rule applied to the
GUI, the same rule that makes a scorecard name its runner and a render label its proxy geometry
([concepts/fidelity.md](concepts/fidelity.md)).

## The leaderboard (UC-G5)

The Bench surface's **Leaderboard** route is P1's and P6's entry point, and the bar it is held to is
*a student finds the leaderboard in one click.*

Each ranking row renders **the runner that produced the entry**. That is the same required
`Scorecard.runner` field the CLI prints — a fixture-scored entry and a Sim-scored entry are
distinguishable on the board, not just in the artifact.

**Leaderboard reads are account-free.** Submitting needs a token
([tutorial 03](tutorials/03-train-and-publish-a-policy.md) §7); looking does not.

## Inspecting a run (UC-B6)

Run inspection — MCAP replay, the timeline, the 3D scene — renders through `@astro-mine/view`'s
widgets inside the surfaces that own the data. Produce a log first:

```bash
astro-mine sim run lunar-polar-ice-prospecting-sprint-v1 --seed 1001 --out run.mcap
```

See [tutorial 02 §7](tutorials/02-run-it-in-the-simulator.md), including the SPICE prerequisite.

## `view/lib/` is not the console

`@astro-mine/view` ships a demo harness with committed fixtures. **It is a developer component
gallery** — a place to see each widget in isolation while working on it. It is not the console, not
an application, and not the product.

View's README says so itself. It is worth repeating here because landing in the gallery and
concluding *"so this is the GUI"* is exactly the failure that makes an evaluator walk away — the
one J6 documents. If what you are looking at is a grid of isolated widgets over fixture data, you
are in the gallery. The console is the shell with nav, surfaces, and configurable endpoints.

---

## See also

- [07 — design a swarm in Studio](tutorials/07-design-a-swarm-in-studio.md) — P5's whole journey,
  entirely in the GUI.
- [reference/cli.md](reference/cli.md) — the command-line half of everything above.
- **Writing a surface** is developer documentation, not user documentation: it lives in the
  `astro-mine-console` repository's `ARCHITECTURE.md` and
  [console.md](../architecture/console.md).
- **The operator/ops viewer** — a Phase 2 deliverable. Nothing in this guide covers operating a live
  mission.
