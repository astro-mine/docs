# Tutorial 07 — design a swarm in Studio

**Persona:** P5 Mission Designer
**Covers:** UC-F7 (start Studio) · UC-F1 (state a goal → ObjectiveSpec) · UC-F2 (pick robots from a
catalog) · UC-F3 (launch a trade study) · UC-F4 (compare candidates on a Pareto front with
uncertainty) · UC-F5 (inspect a candidate swarm in 3D) · UC-F6 (publish a design/campaign)
**Time:** ~30 minutes.

P5's success sentence: *"I typed a goal and got a ranked set of designs I can defend in a review."*

**This tutorial is GUI-first throughout.** P5 is the one persona for whom "CLI is acceptable" is
false — a mission designer will not URL-encode a `TradeStudy` JSON into a query string. Exactly one
command appears below, and it is the one that starts the application.

---

## 1. Start Studio (UC-F7)

```bash
# Build the UI. `serve` mounts a built directory; it does not build one.
cd ui && pnpm install && pnpm run build:harness && cd ..

astro-mine studio serve --registry /path/to/hub-registry
```

> **This tutorial is blocked today, and the command says so.** Studio's REST application was
> deliberately not migrated into the platform wheel — it belongs to
> [`astro-mine-api`](../../architecture/api.md), which is **not yet stood up**. `astro-mine studio
> serve` therefore reports what is missing rather than failing obscurely:
>
> ```
> astro-mine studio serve needs the Studio REST surface (astro_mine.studio.api), which is not
> included in astro-mine-platform.
> ```
>
> Everything below describes the shipped application and is accurate about what it does; you cannot
> currently start it from a released distribution. It comes back with `RM-DIST-03`
> ([roadmap](../../roadmap/README.md#the-distribution-track)), which the command now names itself.

Then one command composes the whole thing: the FastAPI backend, the Hub seams wired to your local
OCI-layout registry, the built UI mounted, and **an example study seeded** so you land on a populated
workspace rather than an empty one. It prints a startup banner naming every seam and its state.

> **`build:harness`, not `build`.** Since the surface conversion, `pnpm build` emits the *library*
> (`ui/dist`, no `index.html`) for the console to compose. Only `build:harness` produces the
> browsable standalone app at `ui/dist-harness` that `serve` mounts. Skip this step and you get a
> **"not built"** page — deliberately, so `serve` says what is missing instead of 404-ing the root —
> and every section below is unreachable.
>
> **Rebuild after pulling.** `ui/dist-harness` is a gitignored local build artifact, so a fresh clone
> has none and a stale one is served silently: the banner prints `UI: mounted from <path>` with no
> indication of when it was built. A bundle older than the source will show you defects that are
> already fixed.

| Flag | Default | For |
|---|---|---|
| `--host` / `--port` | `127.0.0.1` / `8000` | where it binds |
| `--registry` | `$ASTRO_MINE_HUB_REGISTRY` | the local content store |
| `--trusted-key` | `<registry>/keys/cosign.pub` | verifies pulled content |
| `--signing-key` | `<registry>/keys/cosign.key` | signs published campaigns |
| `--cache-dir` | `$ASTRO_MINE_STUDIO_CACHE` | materialized-content cache |
| `--ui-dir` / `--no-ui` | `<cwd>/ui/dist-harness` | the built UI |
| `--no-seed` | — | start without the example study |

**Read the banner.** Each seam reports composed or not, and *why*. A seam that genuinely cannot be
satisfied locally stays unsatisfied and says so — both in the banner and, through the route's 503,
in the UI itself. Nothing 503s silently, and nothing 503s by default when you passed a registry.

Studio also appears as a surface inside the console
([console guide](../console.md)) — point the console's `apiBaseUrl` at the REST tier.

## 2. Open the Design workspace

Everything from here is in the browser. Open `http://127.0.0.1:8000`.

You arrive at the **seeded example study**, which matters: a designer's first impression of a trade
tool should be a populated Pareto front, not an empty form. Look at the seeded study before
authoring your own — it shows you what the output of this workflow looks like, so you know what you
are working towards.

## 3. State a goal (UC-F1)

The goal becomes an **ObjectiveSpec** — a Core-owned document
([reference/file-formats.md](../reference/file-formats.md)) describing what the mission is trying to
achieve. You author it in the workspace; Studio writes the document.

That indirection is the point. The thing you typed becomes a **validatable, publishable artifact**
that Mind, Allocate, and Bench all consume through the same Core contract. Your goal is not a
setting inside a design tool; it is an object the rest of the platform can act on.

## 4. Pick robots (UC-F2)

The catalog is your Hub registry rendered as the robot menu — the same view
`astro-mine fleet catalog` prints, with capability tags. Capability tags are what make an asset
*usable*: they are Core's negotiation vocabulary, and an asset without them will never be assigned
work ([tutorial 04](04-author-an-asset.md)).

With the anchor content fetched, this is the six-asset roster the benchmark itself uses:
prospecting rover, excavator, hauler, ISRU plant, lander, relay orbiter.

**Compose the swarms you want to compare.** In **New study**, each *candidate* row names a swarm:
give it a name, pick a robot from the menu, and set a count. Add a row per composition — "4 rovers"
against "2 rovers + 2 haulers" is two rows each naming one robot, and a swarm mixing kinds is
several candidates you compare side by side.

Picking from the menu is what puts the artifact's **real content digest** on the candidate, and the
row then shows you what that digest names — `namespace/name@version` and the capability tags it
declares. You are not typing a hash: a reference that is not in the catalog is refused at authoring
time, and a row missing either a name or a robot blocks the launch rather than being posted
half-formed.

## 5. Launch a trade study (UC-F3)

A trade study explores swarm compositions against your objective — how many rovers, how many
haulers, what the ISRU plant costs you in mass and power — and evaluates each candidate.

Launch it from the workspace and watch it populate. This is the step that, before the Wave-24 work,
existed only as a REST endpoint; it is now a button.

### What evaluated your candidates — read this before the front

The study you just ran was scored by a **stand-in**, and the comparison view says so: it opens with
*"Stand-in evaluator — no physics ran"*, naming `stand-in/0.1.0`. That banner is the same contract
as `runner: fixture/0.1.0` on a Bench scorecard ([tutorial 01 §4, "The runner is the story"](01-score-the-anchor.md)) — **a
stand-in never looks like the real thing**, and you never infer which one you have from the numbers.

The shipped local evaluator is a deterministic stub. Each metric's base value scales with swarm size,
with a per-metric factor derived from the metric's own *name*, so:

- the numbers are **not domain-realistic** and are not predicted performance;
- renaming a metric changes its score, because the letters changed;
- every metric is a *positive* multiple of swarm size, so a bigger swarm wins on every axis at once
  and **no candidate can dominate another**.

That last one is why any study you run here reports "N candidates, **N** on the front". The surface
labels that too, under *"Every candidate is on the front"* — it is a property of the scoring, not a
finding about your designs.

The evaluator identity rides the artifact, not just the pixels: `TradeStudy.evaluator` is part of the
study's content hash, and a published campaign carries it forward, so a reviewer pulling either by
digest can tell what justified it.

**What this tutorial does demonstrate honestly**, all of it real and exercised end to end: the
authoring journey, the objective as a validated Core artifact, the Pareto math, the uncertainty
rendering, the provenance and lineage, and the publish path. Only the physics behind the metric
values is stubbed — and the loop is built precisely so that swapping in a sibling evaluator changes
that one seam and nothing else.

## 6. Read the Pareto front — with its uncertainty (UC-F4)

The front shows candidates that are **not dominated**: no other candidate is better on every
objective at once.

**What it licenses you to say:**

- these designs are not dominated *under the modelled assumptions*
- moving along the front trades one objective against another, and here is the exchange rate

**What it does not license you to say:**

- *"this is the best design"* — best needs preferences the model does not hold; the front
  deliberately does not rank across objectives
- *"A beats B"* when their uncertainty overlaps — however far apart their centres sit, that ranking
  is **not resolved**
- anything about a dimension the study did not model
- anything at all about *physical* performance while the banner reads `stand-in/0.1.0` — under the
  stand-in the front is complete by construction (§5), so its shape is telling you about the scoring
  function, not about your designs

Uncertainty is rendered as uncertainty; there are no false-precision heatmaps
([concepts/uncertainty.md](../concepts/uncertainty.md)). This is not decoration. P5's output has to
survive a design review, and the fastest way to lose one is to present a ranking the analysis does
not support. A front drawn with honest error is a stronger argument than a crisp one, because it
tells your reviewer where you are and are not confident.

## 7. Inspect a candidate in 3D (UC-F5)

**Pick a world first.** The workspace's **World** menu lists the world bundles in your registry;
choosing one resolves the terrain the swarm is placed on. Until you do, the scene is a bare body —
which is a legitimate design-time view, and the pane says so rather than looking broken. The
`?world=` query parameter still works as a deep link and seeds the menu.

Then pick a candidate from the **Candidate** menu — the front members are labelled *on the front* —
and its swarm is placed on the resolved world, rendered through `@astro-mine/view`'s Cesium globe.
The first candidate on the front is selected for you, so a resolved world shows a swarm without a
click.

### Where the swarm is standing, and where it is not

The pane says so itself, above the scene: **these are design-time layout positions, not simulated
poses.** A candidate is a *proposal* — it has no run, so it has no poses to show. Rather than invent
coordinates silently, Studio applies one stated convention: an evenly spaced ring around the world
bundle's own published tileset anchor, at that anchor's datum height, with the units in the
candidate's own declaration order.

Which means, precisely:

- The centre is the world's, not Studio's — the same anchor View places the terrain at, so the swarm
  cannot drift off the ground it is drawn on.
- It is **not terrain-conformed**. Nothing samples the DEM, so a unit sits at the tile origin's datum
  height rather than on the local mesh.
- It is a **layout, not a plan**: no reachability, no slope, no illumination, no collision. It exists
  so you can see the size and mix of a candidate on the terrain it would work.

If the pane shows no swarm it names the reason — no candidate selected, no world resolved, or a world
bundle that publishes no tileset anchor (older bundles) — because each has a different fix.

### Reading what the scene draws

Assets whose geometry resolved are drawn as **geometry**. Everything else is marked with an 8-pixel
**glyph** at its position, and the colour tells you which case you are in:

| What you see | What it means |
| --- | --- |
| Rendered geometry | The asset's mesh resolved and is drawn. |
| **Cornflower-blue** glyph | Geometry resolved, but the swarm exceeded the scene's model budget or the asset is far away. Status: *"Swarm exceeds the model budget: N rendered as geometry, M as glyphs."* |
| **Orange-red** glyph | Geometry could **not** be resolved. Status: *"N of M assets have no renderable geometry — showing their positions only."* |

Both are honest degradations, not bugs: the scene marks a position it cannot draw rather than
silently omitting the asset or inventing a shape for it.

The anchor roster's SADF documents carry `geometry: []`, so on the shipped content you should expect
orange-red glyphs and that status line.

> **The table above is the swarm pane's, not the catalog preview's.** Selecting a robot in §4's
> catalog also draws an orange-red glyph, from a different component with a different message:
> *"Asset unavailable (SADF asset declares no "geometry" — there is nothing to render) — showing its
> position only."* Same honesty, one asset rather than a swarm. If the status line you are reading
> says "its position" rather than "N of M assets", you are looking at the preview, not the swarm.

> **Not to be confused with the inertia-equivalent proxy.** Fleet's `render` CLI *synthesizes* a
> proxy box from an asset's mass and inertia and writes it out as glTF
> ([tutorial 04 §6](04-author-an-asset.md)). That is an offline authoring step, and its output is a
> real mesh a scene can draw. View's browser panes never do this: a live scene refuses to invent
> geometry it was not given, and marks the position instead. If you want proxy boxes in the viewer,
> render them with Fleet and publish them as geometry.

## 8. Publish the campaign (UC-F6)

Publishing writes a **Campaign** — a Core artifact kind
([core.md](../../architecture/core.md)) — signed with `--signing-key` and
content-addressed like everything else.

That is the deliverable: not a screenshot in a slide deck, but an artifact carrying the objective,
the chosen composition, and the study that justified it, which a reviewer can pull by digest and a
simulator can run.

It also carries **what evaluated it** and **which world you inspected it on** — `evaluator` and
`world_ref` on the campaign. A reviewer holding only the digest can therefore tell that this design
was justified by `stand-in/0.1.0` rather than by physics, without having to take your word for it or
re-run anything.

---

## 9. What you did

You stated a goal, composed candidate swarms from a real catalog, ran a trade study, read a Pareto
front with its uncertainty *and knew what produced it*, resolved a world and stood a candidate's
swarm on it in 3D, and published a signed campaign that records both — **without touching a command
line after the setup**, and without hand-writing a single JSON document.

**Two things were not real, and the platform said so where it mattered.** The physics behind the
metric values is a stand-in, disclosed on the comparison view and on the published artifact. And the
swarm's positions are a stated layout convention rather than simulated poses, disclosed on the
inspection pane. Both are the same rule: a surface that cannot tell you *how* it knows something
tells you that instead.

- **See it alongside the rest of the GUI:** [the console guide](../console.md).
- **Run your campaign as a benchmark:** [02 — run it in the simulator](02-run-it-in-the-simulator.md).
- **Author the assets it picks from:** [04 — author an asset](04-author-an-asset.md).
- **The artifacts it wrote:** [reference/file-formats.md](../reference/file-formats.md).
