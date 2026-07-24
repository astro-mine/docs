# Personas

Who the platform is for, and what serves each. This is the guide's routing table: find yourself,
then follow the row.

Derived from the charter and `architecture/system.md`, filtered to what Phase 0 and Phase 1 ship.
Operators are Phase 2 and appear here only as a forward pointer.

---

## P1 — Benchmark Researcher (MARL practitioner)

ML/RL researcher, grad student, lab member. Python-fluent, not a planetary scientist.

**The single most important persona** — the academic flywheel's ignition point. If P1 cannot get a
score and publish a policy, the commons has no reason to exist.

**Goal:** run the anchor, train a policy that beats the baseline, publish it, appear on the
leaderboard.
**Success:** *"I cloned it before lunch and had a score by dinner; my policy is on the board by
Friday."*

| | |
|---|---|
| **Tutorials** | [01 — score the anchor](../tutorials/01-score-the-anchor.md) → [02 — run it in the simulator](../tutorials/02-run-it-in-the-simulator.md) → [03 — train and publish a policy](../tutorials/03-train-and-publish-a-policy.md) |
| **Commands** | `astro-mine-bench list` · `fetch` · `score --runner sim` · `submit` · `astro-mine-learn --export` · `astro-mine-sim run` · `astro-mine-hub publish` |
| **Concepts** | [determinism & provenance](../concepts/determinism-and-provenance.md) · [content-addressing](../concepts/content-addressing.md) · [fidelity](../concepts/fidelity.md) |
| **Watch out for** | The default runner is the **fixture**, not physics. Check the scorecard's `runner` field. |

## P2 — Planning / Autonomy Researcher

Robotics/planning academic. Cares about allocators, planners, and shields — not RL.

**Goal:** swap in a new planner, allocator, or solver behind the same interface, and measure it
against the same benchmark.
**Success:** *"My CP-SAT alternative dropped in behind the same interface and I can prove it's
better."*

| | |
|---|---|
| **Tutorials** | [06 — compose a planner stack](../tutorials/06-compose-a-planner-stack.md) → [08 — write a plugin](../tutorials/08-write-a-plugin.md) |
| **Commands** | `astro-mine-mind stacks` · `validate` · `compose` · `astro-mine-guard validate` · `compile` · `falsify` · `sign` · `astro-mine plugin new tier\|solver` |
| **Concepts** | [the narrow waist](../concepts/narrow-waist.md) · [determinism & provenance](../concepts/determinism-and-provenance.md) |
| **Watch out for** | **Mind has no `run`** — deliberately. Composing is Mind's job; executing needs a Core `Environment`, which is Sim's. Measure through Bench/Sim. |

## P3 — Planetary Scientist / World Author

Domain scientist with real PDS data. Python-capable, not a software engineer.

**Goal:** author a world and a resource prior from real data, and publish them for others to use.
**Success:** *"My Cabeus world is on the Hub and someone else's rover is driving on it."*

| | |
|---|---|
| **Tutorials** | [05 — author a world](../tutorials/05-author-a-world.md) |
| **Commands** | `astro-mine new world` · `astro-mine-worlds validate` · `schema` · `publish` · `astro-mine-prospect publish` |
| **Concepts** | [uncertainty](../concepts/uncertainty.md) · [content-addressing](../concepts/content-addressing.md) |
| **Watch out for** | Building the *anchor* world needs the LOLA DEM and SPICE kernels, neither shipped, and hours of CPU. Start from the synthetic example, which needs neither. Prospect priors are Python, not an authored format (G2.15). |

## P4 — Roboticist / Asset Author

Robotics engineer with a vehicle concept. Knows URDF, not SADF.

**Goal:** describe a robot in SADF, validate it, see it in sim, publish it.
**Success:** *"I imported my URDF and my excavator appears in the menu."*

**The best-served persona today.** Fleet's 14-subcommand lifecycle is the model the rest of the
platform's UX is working towards.

| | |
|---|---|
| **Tutorials** | [04 — author an asset](../tutorials/04-author-an-asset.md) |
| **Commands** | `astro-mine-fleet new` · `validate` · `lint` · `import` · `render` · `package` · `publish` · `catalog` (+ 6 more) |
| **Concepts** | [content-addressing](../concepts/content-addressing.md) · [fidelity](../concepts/fidelity.md) |
| **Watch out for** | `fleet import` brings across kinematics and mass, never capabilities, power, or sensors — URDF has no vocabulary for them. An asset with no capability tags will never be assigned work. |

## P5 — Mission Designer

Systems/mission engineer at an agency, prime, or startup. **GUI-expectant** — the least
CLI-tolerant persona.

**Goal:** state a goal, explore swarm designs, compare them on a Pareto front, export a campaign.
**Success:** *"I typed a goal and got a ranked set of designs I can defend in a review."*

**The only persona for whom "CLI is acceptable" is false.** A mission designer will not URL-encode a
`TradeStudy` JSON into a query string. Studio's GUI is not a nice-to-have for P5; it is the product.

| | |
|---|---|
| **Tutorials** | [07 — design a swarm in Studio](../tutorials/07-design-a-swarm-in-studio.md) · [the console guide](../console.md) |
| **Commands** | `astro-mine-studio serve` — and then nothing else; everything is in the GUI |
| **Concepts** | [uncertainty](../concepts/uncertainty.md) — reading a Pareto front honestly |
| **Watch out for** | The console's packages are private until the public flip. See the console guide's install section for who can run it today. |

## P6 — Educator / Student

Instructor building a course; student on a laptop, possibly Windows, with no cluster and no org
membership.

**Goal:** run something real, see it, understand it, complete an assignment.
**Success:** *"The whole class ran it in the first session and nobody filed an IT ticket."*

**P1 and P6 are the volume, and both are outsiders.** Everything they need must work on one
workstation, offline, with no account — the CX-LOCAL constraint this guide is held to.

| | |
|---|---|
| **Tutorials** | [getting-started](../getting-started.md) → [01 — score the anchor](../tutorials/01-score-the-anchor.md) → [02](../tutorials/02-run-it-in-the-simulator.md) · [the console guide](../console.md) |
| **Commands** | `astro-mine-bench list` · `score` · `astro-mine-sim record` (fully offline, no content) |
| **Concepts** | [scenarios](../concepts/scenarios.md) · [the narrow waist](../concepts/narrow-waist.md) |
| **Watch out for** | The private-repo reality is the first wall a class hits. Until the public flip, everyone needs org read access. Plan the session around `astro-mine-sim record` and the fixture runner, which need no token. |

## P7 — Commons Steward *(secondary)*

Core maintainer or leaderboard operator.

**Goal:** run the hosted leaderboard, curate submissions, keep results trustworthy.
**Success:** *"Submissions flow in, verify, and rank without me touching a database."*

| | |
|---|---|
| **Tutorials** | none yet — the operator surface lands in Phase 2 |
| **Commands** | `astro-mine-bench zoo-sync` · `zoo-search` · `astro-mine-hub search` · `verify` |
| **Concepts** | [determinism & provenance](../concepts/determinism-and-provenance.md) · [content-addressing](../concepts/content-addressing.md) |
| **Watch out for** | Leaderboard scoring uses **held-out seeds** whose commitment hash ships in the scenario. That is what makes a submitted result trustworthy without trusting the submitter. |

---

## Design facts that follow from the persona set

- **P1 and P6 are the volume, and both are outsiders.** Nothing in the critical path may require an
  account, a cluster, or org membership. Where something does today — the content fetch — it is
  called out inline, not buried.
- **P5 is the only persona for whom CLI is not acceptable.** Everything P5 needs must be reachable
  through the console.
- **P3 and P4 are the content contributors** — they are how the commons compounds. A world or an
  asset someone else can pull by digest is worth more than either of them running one more
  benchmark.
- **P7 is secondary in Phase 1** and becomes primary in Phase 2 with the operations bridge.
