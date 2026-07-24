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
uv pip install "./astro-mine-studio[serve]"
astro-mine-studio serve --registry /path/to/hub-registry
```

One command composes the whole thing: the FastAPI backend, the Hub seams wired to your local
OCI-layout registry, the built UI mounted, and **an example study seeded** so you land on a
populated workspace rather than an empty one. It prints a startup banner naming every seam and its
state.

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
([console guide](../console.md)) — point `endpoints.studio` at this server.

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
`astro-mine-fleet catalog` prints, with capability tags. Capability tags are what make an asset
*usable*: they are Core's negotiation vocabulary, and an asset without them will never be assigned
work ([tutorial 04](04-author-an-asset.md)).

With the anchor content fetched, this is the six-asset roster the benchmark itself uses:
prospecting rover, excavator, hauler, ISRU plant, lander, relay orbiter.

## 5. Launch a trade study (UC-F3)

A trade study explores swarm compositions against your objective — how many rovers, how many
haulers, what the ISRU plant costs you in mass and power — and evaluates each candidate.

Launch it from the workspace and watch it populate. This is the step that, before the Wave-24 work,
existed only as a REST endpoint; it is now a button.

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

Uncertainty is rendered as uncertainty; there are no false-precision heatmaps
([concepts/uncertainty.md](../concepts/uncertainty.md)). This is not decoration. P5's output has to
survive a design review, and the fastest way to lose one is to present a ranking the analysis does
not support. A front drawn with honest error is a stronger argument than a crisp one, because it
tells your reviewer where you are and are not confident.

## 7. Inspect a candidate in 3D (UC-F5)

Select a candidate and inspect the swarm in the 3D scene — assets placed on the real world bundle,
rendered through `@astro-mine/view`'s Cesium globe.

If an asset shows as a plain box: that is the **inertia-equivalent proxy**, drawn because the asset
declares mass and inertia but no visual mesh. It is labelled as a proxy rather than passed off as
geometry ([tutorial 04 §6](04-author-an-asset.md)).

## 8. Publish the campaign (UC-F6)

Publishing writes a **Campaign** — a Core artifact kind
([RFC-0008](../../rfc/0008-design-campaign-artifact-kinds.md)) — signed with `--signing-key` and
content-addressed like everything else.

That is the deliverable: not a screenshot in a slide deck, but an artifact carrying the objective,
the chosen composition, and the study that justified it, which a reviewer can pull by digest and a
simulator can run.

---

## 9. What you did

You stated a goal, picked robots from a real catalog, ran a trade study, read a Pareto front with
its uncertainty, inspected a candidate in 3D, and published a signed campaign — **without touching
a command line after the first line**, and without hand-writing a single JSON document.

- **See it alongside the other surfaces:** [the console guide](../console.md).
- **Run your campaign as a benchmark:** [02 — run it in the simulator](02-run-it-in-the-simulator.md).
- **Author the assets it picks from:** [04 — author an asset](04-author-an-asset.md).
- **The artifacts it wrote:** [reference/file-formats.md](../reference/file-formats.md).
