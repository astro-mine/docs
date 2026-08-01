# Astro-Mine user guide

Task-oriented documentation: how to *do* things with the platform, as opposed to how it is
designed. The design lives in [`architecture/`](../architecture/), the requirements in
[`scenarios/`](../scenarios/), the plan in [`roadmap/`](../roadmap/), and accepted interface
and cross-cutting standards in
[`architecture/conventions.md`](../architecture/conventions.md).

**New here?** Start with [getting-started.md](getting-started.md) — the honest 10-minute path.

## Where to start, by who you are

The guide is organized around seven personas. Find yourself, then follow the row.

| | Persona | You want to | Start here |
|---|---|---|---|
| **P1** | Benchmark researcher (MARL practitioner) | Run the anchor, train a policy that beats the baseline, get on the leaderboard | [01 — score the anchor](tutorials/01-score-the-anchor.md) → [02 — run it in the simulator](tutorials/02-run-it-in-the-simulator.md) → [03 — train and publish a policy](tutorials/03-train-and-publish-a-policy.md) |
| **P2** | Planning / autonomy researcher | Swap in a planner, allocator, or solver and measure it against the same benchmark | [06 — compose a planner stack](tutorials/06-compose-a-planner-stack.md) → [08 — write a plugin](tutorials/08-write-a-plugin.md) |
| **P3** | Planetary scientist / world author | Author a world or a resource prior from real data and publish it | [05 — author a world](tutorials/05-author-a-world.md) |
| **P4** | Roboticist / asset author | Describe a robot in SADF, validate it, see it in sim, publish it | [04 — author an asset](tutorials/04-author-an-asset.md) |
| **P5** | Mission designer | State a goal and get a defensible ranked set of swarm designs | [07 — design a swarm in Studio](tutorials/07-design-a-swarm-in-studio.md) · [console guide](console.md) |
| **P6** | Educator / student | Run something real on a laptop, see it, understand it | [getting-started.md](getting-started.md) → [01](tutorials/01-score-the-anchor.md) → [console guide](console.md) |
| **P7** | Commons steward | Operate the leaderboard, curate submissions | [reference/cli.md](reference/cli.md) (Bench + Hub sections) — the full operator surface is Phase 2 |

Full persona detail, and which commands serve each, is in
[reference/personas.md](reference/personas.md).

## Contents

| | |
|---|---|
| [getting-started.md](getting-started.md) | Install, run something real, and understand what you ran |
| **Tutorials** — end-to-end, in order | |
| [01 — score the anchor](tutorials/01-score-the-anchor.md) | P1 · list, fetch, score, and prove it reproduces |
| [02 — run it in the simulator](tutorials/02-run-it-in-the-simulator.md) | P1 · the Sim-backed path, and reading a real scorecard |
| [03 — train and publish a policy](tutorials/03-train-and-publish-a-policy.md) | P1 · train, export ONNX, publish, submit |
| [04 — author an asset](tutorials/04-author-an-asset.md) | P4 · scaffold, validate, import a URDF, publish |
| [05 — author a world](tutorials/05-author-a-world.md) | P3 · WorldSpec, validate, build, publish |
| [06 — compose a planner stack](tutorials/06-compose-a-planner-stack.md) | P2 · Mind stacks, Guard SafetySpecs, measuring the result |
| [07 — design a swarm in Studio](tutorials/07-design-a-swarm-in-studio.md) | P5 · goal in, ranked designs out, entirely in the GUI |
| [08 — write a plugin](tutorials/08-write-a-plugin.md) | all · one plugin, end to end, published |
| **Guides** | |
| [console.md](console.md) | The GUI: one application, many pages |
| [how-to/write-a-plugin.md](how-to/write-a-plugin.md) | Extend the platform: one recipe per extension surface |
| **Reference** | |
| [reference/cli.md](reference/cli.md) | Every command, organized by task |
| [reference/file-formats.md](reference/file-formats.md) | The nine authored formats, with working examples |
| [reference/personas.md](reference/personas.md) | Who the platform is for, and what serves each |
| [concepts/](concepts/README.md) | The narrow waist, content-addressing, fidelity, uncertainty, determinism, scenarios |

## The rule this guide is held to

**Document what ships.** Every command and snippet here has been executed against the shipped
code, and the group names, constants, and file paths are quoted from source. A guide that
describes an aspiration reads exactly like a guide that describes a feature, which is worse than
having no guide at all — the reader cannot tell which one they are holding.

Where something is *not* built, or is built but not wired up, this guide says so and links to the
issue tracking it, rather than omitting it and leaving the reader to discover the gap themselves.
