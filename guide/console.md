# The console

**The platform's single GUI front door** — one application, statically exported, that talks to the
REST tier from your browser.

Covers **UC-A4** (find the docs for my task) · **UC-G5** (view the leaderboard) · **UC-B6** (inspect
a run). Personas: **P5** Mission Designer, **P6** Educator/Student, **P1** Benchmark Researcher.

---

> ## Status: built, and not yet installable by an outsider
>
> Every page below exists and calls the API. What is not yet true is that **you can get it without
> being inside the org**: the repositories are private during incubation, so running the console
> means cloning [`astro-mine-ui`](https://github.com/astro-mine/astro-mine-ui) and building it. That
> unblocks at the public flip, and nothing on this page is waiting on anything else.
>
> The five package trees the front end used to live in — `astro-mine-console`, `astro-mine-view`,
> and the `ui/` trees of `astro-mine-hub`, `astro-mine-studio` and `astro-mine-bench` — are gone,
> and so are all five repositories: they were **deleted**, not archived. If you follow an old link
> you get a 404. If you land on one of the `@astro-mine/*-ui` packages in the registry, you are
> reading history;
> [`architecture/ui.md` §11](../architecture/ui.md) records what went and why.

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

## What you will find in it

```
Home         /            what this is, who you are, what is configured
Registry     /registry    browse and search artifacts · resolve a version · publish
Benchmark    /bench       leaderboard · a submission's scores, provenance and replay · submit
Design       /design      state an objective, compare candidate swarms, publish a campaign
Compute      /compute     backends, jobs, sweeps and workflows
Help         /help        concepts, personas, and where the CLI is the answer
```

**What bounds this is what the API serves**, and that is the right constraint. Fleet, Worlds,
Prospect, Mind, Guard, Learn and Allocate have no REST surface, so authoring an asset, a world, a
planner stack or a safety spec stays on the command line — exactly as
[reference/personas.md](reference/personas.md) describes. That is a prioritization, not a permanent
boundary: the way to change it is a platform capability, then an API route, then a page.

**There is no View page.** `@astro-mine/view` is the widget library — the Cesium globe, the MCAP
replay, the timeline — that other pages render *through*. It is not a page and has no nav entry.

**Links carry their subject in the query string**, not in the path — `/registry/artifact?name=…` and
`/bench/submission?id=…`. That is worth knowing when you share one: the whole address matters, and a
link without its query is just the empty page.

## Run it

```bash
corepack enable
pnpm install
pnpm dev            # http://localhost:3000
```

Node **24** and pnpm **11.10.0**, both pinned in the repository. pnpm workspaces throughout.

To serve what actually ships rather than the dev server:

```bash
pnpm build          # → apps/console/out, a static bundle any host can serve
```

There is no Node process behind the built app. That is deliberate: it deploys to any static host, and
what it needs from the outside is one API.

## Configure it

The endpoint is **runtime** configuration, never baked into the bundle — a static app whose backend
URL is compiled in is deployable only by whoever built it. Write `config.json` at the **root of the
deployment**:

```json
{
  "apiBaseUrl": "http://localhost:8000"
}
```

Developing locally that file is `apps/console/public/config.json`; on a deployed bundle it sits beside
`index.html`. It is untracked in the repository on purpose, so a fresh build ships **no** endpoint and
says so rather than pretending to be configured and failing somewhere less obvious.
`config.example.json` is the shape, and it is never served as a fallback — an example endpoint
answering as the real one would be exactly the stand-in this platform refuses to ship.

**One endpoint, not one per surface.** The older console configured a separate base URL for each
component's backend; there is one REST tier now ([api.md](../architecture/api.md)), so there is one
address to set.

**Changing it is a file edit, never a rebuild.** The same built bundle serves two deployments — point
one copy at staging and another at production by writing two different `config.json` files. The
repository asserts that rather than claiming it: `e2e/deployment.spec.ts` drives one build at two
endpoints in a single run.

Because the browser calls the API directly from a different origin, **the API must send CORS
headers**, or the app loads and can do nothing. That is a deployment requirement, not an optional
hardening step.

## Deploy it

Any static host will do — an object store, a CDN bucket, a static site host, or a directory:

```bash
pnpm build
echo '{"apiBaseUrl":"https://api.example.org"}' > apps/console/out/config.json
pnpm dlx serve apps/console/out          # or upload apps/console/out anywhere
```

For the hosted tier there is an image, which adds the one thing a bucket cannot do for itself: put
`config.json` in place at container start.

```bash
docker build -t astro-mine-ui .
docker run --rm -p 8080:8080 astro-mine-ui                                        # unconfigured
docker run --rm -p 8080:8080 -e ASTRO_MINE_API_BASE_URL=https://api.example.org astro-mine-ui
```

- **Unset variable → nothing written.** The console serves the unconfigured state, honestly, on every
  route. It is not an error, and the container does not refuse to start.
- **A mounted `config.json` wins.** Mount one at `/usr/share/nginx/html/config.json` — a ConfigMap, a
  compose volume — and the entrypoint leaves it alone.
- **A malformed URL fails at start.** If you set the variable you meant to configure this deployment,
  and a typo must not hide behind a page that reads like a design decision.

The image runs as a non-root user on port 8080 and serves the bundle as a plain static host would — no
rewrites, no single-page fallback. Nothing is pushed to a registry yet (see below), so building it is
how you get it.

**Nothing the console loads comes from a CDN.** Fonts, icons, and Cesium's workers, decoders and
WebAssembly are all served by the deployment itself, so it works on a disconnected network
(CX-LOCAL). The only host it talks to is the API you configured.

## Degraded pages

A page whose backend is absent or whose capability is unmet **degrades visibly and stays in the
navigation** — it never blanks and never silently disappears. With no API configured, the nav is
intact and each page says what is missing and what would fix it.

| What you see | What it means | What fixes it |
|---|---|---|
| *No API is configured* | No `config.json` beside the application, or it could not be read | Write one at the deployment root, or set `ASTRO_MINE_API_BASE_URL` on the container |
| *…is not JSON* / *…is not an absolute http(s) URL* | The file is there and is wrong | Correct it — a JSON object with an `apiBaseUrl` like `https://api.example.org` |
| *This deployment does not offer that* | The API is reachable but does not grant the capability the page needs | Nothing on this side. Publishing is gated this way: the control is disabled with an explanation rather than offering a button that will fail |
| Every page reports a backend it cannot reach, but the address is right | The API is not sending CORS headers for this origin | Configure the API's allowed origins |

Reading a degraded page as breakage is the usual mistake. It is the honesty rule applied to the GUI —
the same rule that makes a scorecard name its runner and a render label its proxy geometry
([concepts/fidelity.md](concepts/fidelity.md)).

## The leaderboard (UC-G5)

The **Leaderboard** page is P1's and P6's entry point, and the bar it is held to is *a student finds
the leaderboard in one click.* Pick a scenario and the board ranks submissions on the primary metric,
with the other metrics beside it.

Each ranking row renders **the runner that produced the entry**. That is the same required
`Scorecard.runner` field the CLI prints — a fixture-scored entry and a Sim-scored entry are
distinguishable on the board, not just in the artifact. A metric with no cross-seed bound renders as
an open mark, never as a zero-length error bar: the board will not assert a precision nobody measured.

**Leaderboard reads are account-free.** Submitting needs a token
([tutorial 03](tutorials/03-train-and-publish-a-policy.md) §7); looking does not.

`astro-mine bench leaderboard` prints the same rows, including the runner field, for anyone who would
rather stay on the command line.

## Inspecting a run (UC-B6)

Open a submission — `/bench/submission?id=…` — for its scores, its provenance and its replay. Run
inspection renders through `@astro-mine/view`'s widgets inside the page that owns the data: the MCAP
replay, the timeline scrubber and the 3D scene. The viewer is loaded on demand, so a reader who came
for a number does not download a globe to see it.

To produce a log of your own:

```bash
astro-mine sim run lunar-polar-ice-prospecting-sprint-v1 --seed 1001 --out run.mcap
```

See [tutorial 02 §7](tutorials/02-run-it-in-the-simulator.md), including the SPICE prerequisite.

## What is published, and what is merely built

**Nothing is published today**, and that is a decision rather than an omission.

`@astro-mine/console` is an application: deployed, never consumed, so it was never going to be
published. The four libraries it is built from — `api-client`, `ui`, `view` and `inspectors` — build
and are gated, and they are **not published either**. They had one class of external consumer, the
per-component surface packages, and the `Surface` contract that created it is retired. A release train
with nothing on the other end of it costs a hand-set version and a tag per cut, and buys optionality
nobody is waiting on.

Each package still pins its registry to GitHub Packages in its manifest. That is a safety control —
the `@astro-mine` scope cannot resolve to npmjs.com even on a machine holding a public-npm token — and
it means the destination is already right the day there is a consumer.

**The previous front end did publish**, and six packages are still in the registry.
`@astro-mine/surface`, `@astro-mine/hub-ui`, `@astro-mine/studio-ui` and `@astro-mine/bench-ui` are
**retired** — the contract that created them is gone, and nothing will republish those names.
`@astro-mine/ui` and `@astro-mine/view` are the same names this workspace uses, so only the versions
the old repositories cut (`<=0.1.1`) are history, not the names.

**None of them says so in the registry**, and that is not an oversight: GitHub Packages does not
implement `npm deprecate`, so the notice cannot be attached where you would meet it. If your
resolver hands you one of these, you have found history — the disposition lives in
[architecture/ui.md §8.2](../architecture/ui.md) and nowhere else.

| You are | Can you install it? |
|---|---|
| Inside the org, building from a clone | **Yes**, and no registry credential is needed: every `@astro-mine` dependency in the workspace is a local link |
| Inside the org, wanting the libraries as packages | **Not yet** — nothing is published. Clone and link |
| An unauthenticated outsider (a student, a new contributor) | **Not until the flip** — no credential grants access while the repositories are private |

That last row is the audience the commons is ultimately for, and it stays blocked until the flip. It is
a property of the org still being private, not something any package can grant around. Public npm
publication is the deferred item in
[`VERSIONING.md`](https://github.com/astro-mine/docs/blob/main/VERSIONING.md) §6.

## A gallery is not the console

**Every route in the console is in the navigation**, and there are no development pages left in it —
the last unlisted scaffold went at the same time as this page was written.

That is worth saying because of the mistake it forecloses. The retired View repository shipped a
widget gallery over fixture data, and landing in it and concluding *"so this is the GUI"* is the
failure that makes an evaluator walk away — the one J6 documents. If what you are looking at is a
grid of isolated widgets over fixture data, you are in a gallery in an old repository. The console is
at `/`, and its sidebar lists all of it.

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
