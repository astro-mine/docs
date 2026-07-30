# AstroMine — Phase 0/1 User-Surface Analysis & Gap Report

> **Point-in-time, 2026-07-16.** Read as history. This predates the platform's consolidation into four
> distributions ([conventions.md](../architecture/conventions.md) §7.1) and the retirement of the
> formal design-proposal process; per-component install lines, per-repo issue counts and RFC numbers
> in what follows describe the world as it then was. See [tpm/README.md](README.md).


> **Purpose:** design the complete user-oriented surface (CLI + GUI) needed to satisfy the Phase-0
> and Phase-1 objectives, then gap-analyse it against what ships today — as the input to a wave of
> UI and user-guide GitHub issues.
>
> **Status:** analysis complete · **Date:** 2026-07-16 · **Author:** product/PM pass
> **Scope discipline:** Phase 0 + Phase 1 objectives only. No Phase-2/3 use cases are designed here.
> **Evidence:** ground truth from shipped code across all 18 repos, not from architecture docs.
> Where a claim was load-bearing it was executed, not read.

> ### ⚑ Acted on and superseded (2026-07-24)
>
> This report drove **Waves 21–26**, which are now complete — see
> [issue-plan.md § Outcome](issue-plan.md#outcome). **It is deliberately not updated**: it records
> the platform as of 2026-07-16, which is what makes it readable as a diagnosis rather than a
> changelog. Everything below describes a state that no longer holds.
>
> **The headline finding — *"the platform is far more built than it is usable"* — has been
> answered.** The ❌ cluster §4 identified on the two phase objectives is closed: running the anchor
> for real (UC-B3/B4), the policy artifact (UC-D2), the design GUI (UC-F1/F3/F7), the leaderboard
> face (UC-G5), and plugin onboarding (UC-H1/H2). There is now a
> [user guide](../guide/README.md) (G1.7), an umbrella CLI (G2.1), and one console (G1.5).
>
> **Three of this report's own claims did not survive verification** and are corrected where they
> were acted on, not here:
>
> - **G3.5** (committed `.venv` in `astro-mine core`) — **false**. Untracked, gitignored, never
>   committed. Struck; no issue was filed.
> - **G3.1**'s companion claim that Hub's README *"omits `search`"* — **false**. It does not.
> - **G3.2** (`1 - Planning` classifiers) named Hub and Seal; the drift was **15 of 18** repos.
>   **G3.4** listed Surrogate as missing from the org package map; it was present. Spice and Seal
>   were the omissions.
>
> Treat the analysis as a snapshot and the gap IDs as stable references. For current state, read the
> [guide](../guide/README.md) — which, unlike this document, is maintained.

---

## 1. Executive summary

**The platform is far more built than it is usable.** Phase 0 and Phase 1 are functionally
complete — 297/299 board items Done — and the engineering underneath is genuinely strong. But
almost none of it is reachable by the users those phases were built for. The gap is not
capability. It is **assembly, distribution, and documentation**.

Five findings dominate, in priority order:

1. **The Phase-0 headline promise is not met in substance.** `astro-mine bench score` runs from a
   clean clone in seconds and prints seven plausible physical quantities — but it scores a
   **deterministic hash-derived fixture, not the simulator**. The real Sim-backed path exists and
   works, but has no CLI, and with the shipped baseline policy it returns an **empty scorecard**
   (`water_mass = 0.0`, six of seven metrics `None`). A researcher cannot today "run the anchor
   scenario and score a baseline" in the sense the charter means.

2. **The anchor content has no distribution channel.** The anchor scenario pins nine content
   hashes. All nine resolve — but only from a hand-built local OCI registry that exists on one
   developer's disk by workspace convention. There is no published registry, no `fetch` command,
   and no documented source. A fresh cloner cannot obtain the bytes at any price short of
   rebuilding a GB-scale LOLA DEM pipeline from a fourth repo.

3. **There is no GUI front door.** Two real, well-tested web UIs exist (Hub, Studio) plus an
   excellent View component gallery. None is reachable by a new user: Studio's UI is gated behind
   five undocumented steps including a **private npm registry that hard-blocks anyone outside the
   org**, its backend 503s on 5 of 9 routes without hand-wiring, and nothing serves the bundle.

4. **The Phase-1 flywheel is broken at the artifact.** `astro-mine learn` trains, then **discards
   the `PolicyExport`** (`report, _export = train(...)`). The ONNX `PolicyPackage` — the artifact
   Mind, Guard, and Bench all consume, and the unit of exchange for the entire commons — cannot be
   produced from the CLI at all.

5. **There is zero user documentation.** The `docs` repo contains architecture, scenarios,
   roadmap and charter — all excellent, all written for builders. There is not one
   getting-started page, tutorial, or how-to for a user. This report is the prerequisite for
   fixing that; the user guide cannot be written against the current surface without documenting
   its dead ends.

**The through-line:** every component was built to be *composed*, and nothing was built to
*compose them*. The seams are clean and the dependency discipline is real (Bench never imports
Sim; that is correct). But the last mile — the thing that turns sixteen good libraries into one
platform — was never anyone's deliverable.

**Encouraging counterweight:** the fixes are mostly small and additive. `Fleet`'s 14-command CLI
is a genuine exemplar of what good looks like here. The codebase is unusually candid about its own
stand-ins — Sim's own docstring documents the missing `--runner` flag. Nothing needs redesign; it
needs a front door.

---

## 2. Method & scope

**In scope** — the two phase objectives, verbatim:
- **Phase 0:** *"a runnable, reproducible benchmark on the lunar-polar anchor scenario — clone,
  run, score in an afternoon."*
- **Phase 1:** *"become the MARL + planning commons; first public leaderboards & community
  plugins."*

**Out of scope** — deliberately not designed here: operations/console UX (Ops/Bridge/View full
viewer = Phase 2), mission-architecture surfaces (Trajectory/Sizing/Ledger = Phase 3), and any
use case the two objectives above do not imply.

**Product decisions taken 2026-07-16** (recorded here because they bound §8):
1. **One GUI, not an app per component** — see §8.2 for the architecture that makes this
   extensible across components.
2. **A unified REST API surface is deferred — not Phase 1.** Surfaces consume each component's
   existing FastAPI directly.
3. **GUI is comparison + inspection in Phase 1**, but will grow to authoring/operations later, and
   **all personas eventually get GUI capability**. The §3 CLI/GUI persona affinity is a Phase-1
   prioritization, not a permanent architectural split — nothing may be GUI-unreachable by
   construction.
4. **The GUI must be designed, not merely functional** — a design pass with mockups precedes
   implementation (§8.2.6).

**Method.** Five parallel inventories across all 18 repos, reading `pyproject.toml`
entry points, CLI modules, FastAPI/gRPC apps, `package.json`, and READMEs. Load-bearing claims
were executed rather than inferred. Notable verifications:
- Ran `astro-mine bench score` from a clean env (works; fixture-scored).
- Ran the Sim-backed `run(..., runner=SimEpisodeRunner(...))` against the workspace registry
  (works; empty scorecard — §7 G1).
- Verified all nine anchor pins resolve in the workspace registry (they do).
- Verified Studio's FastAPI mounts world/asset caches but **not** `ui/dist`.
- Verified `@astro-mine/view` requires a GitHub Packages token with `read:packages`.
- Verified `astro-mine learn`'s `main()` binds the export to `_export` and drops it.

**Caveat retracted — the root cause is now known (2026-07-16, found while filing Wave 21).** The
first draft hedged that "a longer episode or a real Mind-composed policy may score non-zero."
**It would not, at any horizon.** `BaselinePolicy` (`baseline/_policy.py:47`) emits *only*
`ActionKind.MODE` with `mode="prospect"`. Sim gates extraction on
`DEFAULT_EXTRACTION_MODES = {"excavate","drill","dig","extract","isru"}`
(`sim/isru/__init__.py:31`), and `IsruModel.step` returns state unchanged for anything else.
`"prospect"` is not in that set, so **`water_mass` is structurally pinned at 0.0** — no horizon,
seed, or episode length changes it. G1.3 is therefore a **decision**, not an investigation.

### G1.3 resolved (2026-07-18) — and this diagnosis was wrong

Recorded here because the reasoning above was confidently stated and is not what was happening.
Shipped in astro-mine-sim#61 / astro-mine-bench#65.

**The mode gate is real. The conclusion drawn from it was not.** `water_mass` never read the ISRU
tank at all, so it could not have been "pinned at 0.0" by the mode gate. Two stacked defects:

1. **The gauge was bypassed.** `render_sensor` dispatched on `sensor.resource` *before* `sensor.kind`,
   and a `resource_storage` gauge declares a `ResourceTarget` to say *what the tank holds*. So the
   plant's tank rendered a noisy draw of the **Prospect ice field**, tagged `unit="kg"` /
   `species="water"` — exactly the pair Bench's `water_mass` filters on. Measured: `0.0848`, the ice
   mass fraction under the plant, reported as kilograms of stored water. The metric moved with the
   terrain, not with anything the swarm did.
2. **The channel index was wrong.** The gauge emits `[stored_water_kg, extraction_energy_j]`;
   `_total_stored_water` read `values[-1]` — joules, labelled kg.

The test that should have caught this (`test_the_scored_trace_carries_real_isru_telemetry`) was green
and asserted "water really accumulated": it was comparing two field samples that had drifted apart
under the kinematic engine's ±0.01 m jitter.

**"Six of seven metrics `None`" was also mis-attributed.** That measurement was taken in an
environment with no producer packages installed, so `astro_mine.providers` registered **no factories**
and the world / ice field / contact plan silently failed to reconstruct — content resolves by digest,
providers do not. With them installed the same run scores `nights_survived`, `comms_robustness`
(0.205) and `discovery_latency`. The silent degradation is now astro-mine-sim#67.

**The answer to the open question was neither option offered.** A Mind-composed stack emits
`ActionKind.ACTUATOR` / `VELOCITY` exclusively — its `TASK` actions are internal tier plumbing,
replaced by the control tier before egress — so it sets no mode and would have scored zero water too.
What shipped is a **capability-aware mode policy**: one mode per agent derived from that asset's own
SADF capability tags and declared `loads_by_mode`, reaching Bench through a new optional
`DefaultPolicyProvider` seam.

**`water_mass` scores `0.0` — deliberately, and now measurably.** `IsruModel` is uncoupled from
excavation (no dig target, no delivered feedstock, no proximity check), so commanding the plant into
`extract` would manufacture water that no digging and no haulage earned. Zero is the true stored mass
of a swarm that has delivered nothing. Coupling extraction to delivered material is
astro-mine-sim#64.

**Lesson for this report's method.** §10 records that findings were "executed rather than inferred",
and the G1.3 root cause was presented as verified in source. It was read in source and not executed —
running it would have shown `0.0848`, not `0.0`, and the whole diagnosis would have gone differently.
Reading a gate and concluding what a metric reports skips the step where the metric is actually
computed.

---

## 3. Personas

Derived from charter §2 and system.md §2, filtered to Phase 0/1 (operators are Phase 2 and
excluded). Ordered by strategic priority to the two objectives.

| # | Persona | Who they are | Primary goal | Phase | Success feels like |
|---|---|---|---|---|---|
| **P1** | **Benchmark Researcher** (MARL practitioner) | ML/RL researcher, grad student, lab member. Python-fluent, not a planetary scientist. **The single most important persona — the academic flywheel's ignition point.** | Run the anchor, train a policy that beats the baseline, publish it, appear on the leaderboard | 0+1 | "I cloned it before lunch and had a score by dinner; my policy is on the board by Friday" |
| **P2** | **Planning / Autonomy Researcher** | Robotics/planning academic. Cares about allocators, planners, shields — not RL. | Swap in a new planner/allocator/solver, compose a stack, measure it against the same benchmark | 1 | "My CP-SAT alternative dropped in behind the same interface and I can prove it's better" |
| **P3** | **Planetary Scientist / World Author** | Domain scientist with real PDS data. Python-capable, not a software engineer. | Author a world and a resource prior from real data; publish for others to use | 0+1 | "My Cabeus world is on the Hub and someone else's rover is driving on it" |
| **P4** | **Roboticist / Asset Author** | Robotics engineer with a vehicle concept. Knows URDF, not SADF. | Describe a robot in SADF, validate it, see it in sim, publish it | 0+1 | "I imported my URDF and my excavator appears in the menu" |
| **P5** | **Mission Designer** | Systems/mission engineer at an agency, prime, or startup. **GUI-expectant** — the least CLI-tolerant persona. | State a goal, explore swarm designs, compare on a Pareto front, export a campaign | 1 | "I typed a goal and got a ranked set of designs I can defend in a review" |
| **P6** | **Educator / Student** | Instructor building a course; student on a laptop, possibly Windows, with no cluster and no org membership. | Run something real, see it, understand it, complete an assignment | 0+1 | "The whole class ran it in the first session and nobody filed an IT ticket" |
| **P7** | **Commons Steward** *(secondary)* | Core maintainer / leaderboard operator. | Run the hosted leaderboard, curate submissions, keep results trustworthy | 1 | "Submissions flow in, verify, and rank without me touching a database" |

**Persona notes that shape the design:**
- **P1 and P6 are the volume.** Both are outsiders. Both are blocked today by the private-registry
  and content-distribution gaps (§7 G2, G3) before they write a line of code.
- **P5 is the only persona for whom "CLI is acceptable" is false.** A mission designer will not
  URL-encode a `TradeStudy` JSON into a query string. Studio's GUI is not a nice-to-have for P5;
  it is the product.
- **P3 and P4 are content contributors** — they are how the commons compounds, and they are
  well-served by CLI. Fleet already nearly serves P4.

---

## 4. Use-case catalog (Phase 0/1 only)

Grouped by journey stage. **Interface** = the surface that *should* carry it (design position, not
current state). Status uses: ✅ works · ⚠️ works with friction/caveat · ❌ blocked or absent.

### Stage A — Discover & install

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-A1 | Understand what AstroMine is and whether it fits my problem | all | Docs / org README | ⚠️ builder-oriented; package map stale |
| UC-A2 | Install the platform on a laptop, offline, no account | P1 P6 | CLI | ⚠️ per-repo conda+uv; private Git deps |
| UC-A3 | Discover which command does what | all | CLI (`astro-mine --help`) | ❌ no umbrella CLI exists |
| UC-A4 | Find the docs for my task | all | Docs site | ❌ no user docs exist |

### Stage B — Run & score the anchor *(the Phase-0 objective)*

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-B1 | List available benchmark scenarios | P1 P6 | CLI | ✅ `astro-mine bench list` |
| UC-B2 | Score the reference baseline offline, no account | P1 P6 | CLI | ⚠️ works — **but scores a fixture, not Sim** |
| UC-B3 | **Obtain the anchor content (world/fleet/prior/link)** | P1 P3 P6 | CLI | ❌ **no fetch path exists** |
| UC-B4 | **Run the anchor scenario in the actual simulator and score it** | P1 P6 | CLI | ❌ **no CLI; empty scorecard via Python** |
| UC-B5 | Reproduce a score byte-for-byte / prove determinism | P1 P7 | CLI | ⚠️ gate uses the fixture, not Sim |
| UC-B6 | Inspect what happened in a run (replay/trace) | P1 P6 | GUI | ⚠️ View demo replays a *fixture* episode only |
| UC-B7 | Score my own policy instead of the baseline | P1 | CLI + Python | ⚠️ Python subclass required; no CLI path |

### Stage C — Author content

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-C1 | Scaffold a new SADF asset | P4 | CLI | ✅ `fleet new` |
| UC-C2 | Validate / lint a SADF asset | P4 | CLI | ✅ `fleet validate` / `fleet lint` |
| UC-C3 | Import an existing URDF/SDF robot | P4 | CLI | ✅ `fleet import` |
| UC-C4 | Preview asset geometry | P4 P5 | CLI + GUI | ⚠️ `fleet render`; GUI only via Studio |
| UC-C5 | Author a WorldSpec | P3 | CLI + file | ❌ **YAML front door with zero on-disk examples** |
| UC-C6 | Build the anchor world from real DEM data | P3 | CLI/script | ⚠️ documented script; hours; needs external data |
| UC-C7 | Validate a WorldSpec before an hours-long build | P3 | CLI | ❌ no validate command |
| UC-C8 | Author/publish a resource prior | P3 | CLI | ⚠️ `prospect publish` (1 cmd); **priors are Python, not files** |
| UC-C9 | Validate any Core-owned spec (Objective/Mission/Plan/manifest) | P1–P5 | CLI | ❌ **no CLI for any of them** |

### Stage D — Train & improve *(the Phase-1 objective)*

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-D1 | Train a baseline MARL policy on one workstation | P1 | CLI | ⚠️ `astro-mine learn` — but `--env-factory` has no shipped example |
| UC-D2 | **Export a trained policy as an ONNX PolicyPackage** | P1 | CLI | ❌ **CLI discards the export** |
| UC-D3 | Evaluate honestly (seed sweeps, comms-stress curves) | P1 | CLI/Python | ⚠️ Python only |
| UC-D4 | Train against the anchor scenario specifically | P1 | CLI | ❌ depends on UC-B3 |
| UC-D5 | Scale training to a cluster | P1 | CLI | ✅ `astro-mine cloud` + `--num-workers` |
| UC-D6 | Track experiments | P1 | GUI | ⚠️ MLflow (third-party) |

### Stage E — Compose & assure

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-E1 | Compose a planner stack from a spec | P2 | CLI + file | ⚠️ **6 reference stacks ship; no CLI; README shows none** |
| UC-E2 | Validate a stack spec | P2 | CLI | ❌ no CLI |
| UC-E3 | Run a composed stack against the anchor | P2 | CLI | ❌ no CLI |
| UC-E4 | Author a SafetySpec | P2 | file | ⚠️ excellent example — **not shipped as package data** |
| UC-E5 | Validate/compile a SafetySpec | P2 | CLI | ❌ no CLI despite a shipped compiler |
| UC-E6 | Swap in a new allocator/solver | P2 | plugin | ❌ **solver registry is a hardcoded dict** |
| UC-E7 | Inspect why a plan/assignment was chosen | P2 P5 | CLI/GUI | ⚠️ Python; explanation UI is Phase 2 |

### Stage F — Design *(Studio; P5's whole journey)*

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-F1 | State a goal in structured form → ObjectiveSpec | P5 | GUI | ❌ API only; **no UI** |
| UC-F2 | Pick robots from a catalog | P5 | GUI | ⚠️ UI exists; 503s without wiring |
| UC-F3 | Launch a trade study | P5 | GUI | ❌ API only; **no UI** |
| UC-F4 | Compare candidates on a Pareto front w/ uncertainty | P5 | GUI | ⚠️ UI exists; unreachable |
| UC-F5 | Inspect a candidate swarm in 3D | P5 | GUI | ⚠️ UI exists; unreachable |
| UC-F6 | Publish a design/campaign | P5 | GUI | ❌ API only; no UI |
| UC-F7 | Start Studio at all | P5 | CLI | ❌ **no CLI, no documented command** |

### Stage G — Share & compete *(the Phase-1 flywheel)*

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-G1 | Publish an artifact to Hub, signed | P1–P5 | CLI | ✅ `astro-mine hub publish` |
| UC-G2 | Search/discover artifacts | all | CLI + GUI | ✅ CLI + Hub UI |
| UC-G3 | Pull + verify an artifact fail-closed | all | CLI | ✅ `astro-mine hub pull` |
| UC-G4 | Submit a policy to the leaderboard | P1 | CLI | ❌ **no submit CLI; REST only** |
| UC-G5 | **View the public leaderboard** | P1 P6 P7 | GUI | ❌ **no UI** (bench#27) |
| UC-G6 | Reproduce someone else's published result | P1 P7 | CLI | ❌ depends on UC-B3/B4 |
| UC-G7 | Operate the leaderboard (curate, audit) | P7 | CLI/GUI | ⚠️ REST + `zoo-sync` |

### Stage H — Extend *(community plugins; the Phase-1 objective)*

| ID | Use case | Personas | Interface | Status |
|---|---|---|---|---|
| UC-H1 | Learn how to write a plugin | P1–P4 | Docs | ❌ **no recipe anywhere** |
| UC-H2 | Scaffold a plugin | P1–P4 | CLI | ❌ no scaffold |
| UC-H3 | Register a new MARL algorithm | P1 | plugin | ✅ mechanism works, undocumented |
| UC-H4 | Register a new planner/shield tier | P2 | plugin | ✅ mechanism works, undocumented |
| UC-H5 | Register a new Bench metric | P1 P7 | plugin | ✅ mechanism works, undocumented |
| UC-H6 | Register a new solver backend | P2 | plugin | ❌ **closed — hardcoded `_LOADERS`** |
| UC-H7 | Publish a plugin for others to discover | P1–P4 | CLI | ✅ via Hub |

**Tally: 46 use cases — ✅ 12 · ⚠️ 17 · ❌ 17.** The ❌ cluster is concentrated exactly on the two
phase objectives: running the anchor for real (B3/B4), the policy artifact (D2), the design GUI
(F1/F3/F7), the leaderboard face (G5), and plugin onboarding (H1/H2).

---

## 5. User journeys — current state

### J1 — "Clone, run, score in an afternoon" (P1) — **fails**

```
 1. Find the docs                    ❌ none exist → read architecture/bench.md
 2. Clone astro-mine bench           ⚠️ private repo; needs CORE_REPO_TOKEN for the uv Git source
 3. conda create + uv sync           ✅
 4. astro-mine bench score           ✅ 7 metrics in seconds
      ↳ but: "scored with the reference runner (deterministic fixture, not Sim)"
 5. "How do I run it for real?"      ❌ no --runner flag; no docs
 6. Read Sim's source docstring      ⚠️ discover the Python snippet
 7. Install astro-mine-sim[bench]    ⚠️ second repo, second env
 8. open_bundle_store("files/hub-registry")
                                     ❌ path is a docstring placeholder; no such dir ships
 9. "Where do I get the content?"    ❌ NO ANSWER EXISTS — not published, not fetchable, undocumented
10. (with a hand-built registry)     ⚠️ resolves — then scores 0.0 / None / None / None...
```
**Verdict:** step 4 gives a false summit. Steps 5–10 have no documented path, and the end of the
road is an empty scorecard. **Time-to-value: minutes to a fake score; unbounded to a real one.**

### J2 — "Become the MARL commons" (P1) — **fails at the artifact**

```
1. astro-mine learn --env-factory your_pkg:make_env   ⚠️ placeholder — no shipped factory exists
2. Write my own env factory                            ⚠️ Python, undocumented, no example
3. Train                                               ✅ produces a run report
4. Export the ONNX PolicyPackage                       ❌ CLI DISCARDS IT (`report, _export = ...`)
5. Publish to Hub                                      ✅ if I hand-write the export in Python
6. Submit to the leaderboard                           ❌ no CLI; REST only
7. See my rank                                         ❌ no leaderboard UI
```
**Verdict:** the flywheel cannot turn. The unit of exchange (the ONNX package) is unobtainable
from the documented command, and neither the submission nor the ranking has a user surface.

### J3 — "Goal in, design out" (P5) — **fails at the front door**

```
1. Start Studio                       ❌ no CLI, no documented uvicorn command
2. Install the UI                     ❌ HARD BLOCK — @astro-mine/view needs a GitHub Packages
                                         token with read:packages. An outsider cannot proceed.
3. Wire the [hub] seams               ❌ undocumented; without it 5/9 routes 503
4. Open the app                       ❌ FastAPI never mounts ui/dist
5. Author a goal                      ❌ no authoring UI
6. Supply a study                     ❌ hand-craft TradeStudy JSON → URL-encode into ?study=
```
**Verdict:** P5 cannot begin. Not "it's rough" — there is no reachable entry point, and step 2 is
an absolute blocker for anyone outside the org.

### J4 — "Contribute a plugin" (P2) — **works, if you read source**

```
1. Read how to write one              ❌ CONTRIBUTING mentions "plugins" as a principle, no recipe
2. Find a template                    ❌ none; best refs are two well-commented source files
3. Implement against the contract     ✅ contracts are clean and real
4. Register the entry point           ✅ 3 groups work (mind.tier_plugins, learn.algorithms, ...)
5. ...unless it's a solver backend    ❌ hardcoded `_LOADERS` — requires a PR to Allocate
6. Publish to Hub                     ✅
```
**Verdict:** the machinery is genuinely good and the seams are real. The gap is pure onboarding —
plus one advertised-but-closed extension point.

### J5 — "Author a world" (P3) — **works, with a cliff**

```
1. Write a WorldSpec YAML             ❌ no example on disk anywhere; the one real spec is Python
2. Validate it                        ❌ no validate command
3. Build                              ⚠️ hours of CPU; needs LOLA DEM + SPICE kernels not shipped
4. Publish                            ✅ worlds publish
```
**Verdict:** viable for a determined expert; hostile to a newcomer. No small/synthetic world exists
to learn on.

### J6 — "Teach a class" (P6) — **fails**

```
1. Have 30 students install it        ❌ private repos + private npm registry + tokens
2. Run something real                 ⚠️ the fixture score, or View's fixture gallery
3. See something                      ⚠️ View demo: pnpm install && pnpm dev → real lunar terrain ✅
4. Assign an exercise                 ❌ nothing to modify with a feedback loop
```
**Verdict:** only View's demo harness survives contact — and it is a gallery, not an application.
Note the private-repo blocker is intentional during incubation and resolves at the public flip;
the *other* blockers do not resolve by themselves.

---

## 6. Interface inventory — what ships today

### 6.1 CLI surface (8 of 18 repos)

| Repo | Command | Subcommands | Assessment |
|---|---|---|---|
| fleet | `fleet` | `new · validate · lint · resolve · package · keygen · verify · publish · catalog · import · export · render · fidelity · families · resolve-family` (15) | ✅ **The exemplar.** Complete authoring lifecycle |
| bench | `astro-mine bench` | `score · list · zoo-sync · zoo-search · eval-worker` | ⚠️ good, but no `--runner` |
| cloud | `astro-mine cloud` (+`-harness`) | `submit · expand · compile · sweep · workflow · backends` | ✅ solid |
| hub | `astro-mine hub` | `publish · search · resolve · pull · verify` | ✅ solid (README advertises a phantom `cache`) |
| learn | `astro-mine learn` | *(flat flags)* | ⚠️ **discards the policy export** |
| worlds | `worlds` | `publish · keygen` | ⚠️ publish-only; cannot build or validate |
| link | `link` | `publish · keygen` | ⚠️ publish-only |
| prospect | `prospect` | `publish` | ⚠️ one command |
| **core, spice, seal, sim, surrogate, mind, allocate, guard, studio, view** | — | **none** | ❌ |

**Naming is inconsistent:** bare (`fleet`, `worlds`, `link`, `prospect`) vs prefixed
(`astro-mine bench`, `astro-mine hub`, `astro-mine cloud`, `astro-mine learn`). All argparse — at
least that is uniform. **There is no `astro-mine` umbrella command.**

**The two most important components for their phases — `sim` (Phase 0) and `studio` (Phase 1) —
have no CLI at all.**

### 6.2 Service surface

| Repo | Type | Routes | Startup documented? |
|---|---|---|---|
| hub | FastAPI | 6 | ✅ uvicorn documented |
| cloud | FastAPI | 7 | ✅ uvicorn documented |
| bench | FastAPI | 15 (leaderboard) | ❌ |
| studio | FastAPI | 9 | ❌ |
| prospect | **gRPC** | 3 RPCs, auth-by-default | ✅ |
| sim | **gRPC** | 3 RPCs | ❌ no CLI to launch |

### 6.3 GUI surface

| Repo | What exists | Reachable? |
|---|---|---|
| **view** | Component library + **9-story hash-routed demo harness** with committed fixtures (real Shackleton 3D-Tiles terrain, 12-rover swarm, MCAP replay) | ✅ **`pnpm install && pnpm dev` — the only thing that works today.** But it is a gallery: every scene is a fixture; nothing loads user data |
| **hub** | React SPA: SearchBar, ArtifactList, CompareView, ArtifactDetailView | ⚠️ uses 2 of 6 routes; no publish/resolve in UI |
| **studio** | React SPA: AssetMenu, AssetPreviewPane, CandidateInspector, CandidateComparison (Plotly Pareto + uncertainty) | ❌ 5 undocumented gates; private npm blocker; no `ui/dist` mount; no study authoring |
| **bench** | — | ❌ no leaderboard UI (bench#27) |
| view stubs | `dashboards/`, `explain/`, `telemetry/` = `export {}` | Phase 2 — correctly out of scope |

### 6.4 Content & examples

- **`examples/` exists in 2 of 18 repos** (core: 12 files across 6 spec types; guard: 1).
- **Anchor content ships and is complete** — 22 artifacts in the workspace registry; all 9 anchor
  pins resolve. **But it lives only on one disk**, by workspace convention.
- **Anchor content is invisible in READMEs:** Fleet's 6-asset reference roster and Prospect's
  Shackleton priors both ship, are one call away, and are mentioned in neither README.
- **Mind ships 6 reference stacks + 13 manifests as package data** — genuinely good, entirely
  undocumented in its own README (which has zero Python blocks).

### 6.5 Documentation

- `docs` repo: **zero user-facing pages.** Architecture (26), roadmap (4), scenarios
  (2), charter (1) — all builder-facing.
- `.github/CONTRIBUTING.md`: mentions "plugins" once, as a principle. No authoring recipe.
- README quality is inverted against importance: `sim` (the Phase-0 heart) has **35 lines** and
  says *"Phase 0 — scaffolding"*; `surrogate` (not on any critical path) has 280 excellent lines.

---

## 7. Gap analysis

Severity: **G1** = blocks a phase objective · **G2** = major friction/credibility · **G3** = polish.

### G1 — Blockers

| # | Gap | Evidence | Impact |
|---|---|---|---|
| **G1.1** | **`bench score` scores a fixture, and says so only in the last line of output.** No `--runner` flag. | `cli.py:66` hardcodes `run(spec, BaselinePolicy(), seeds=seeds)`; `sim/bench/__init__.py` documents the missing flag | Phase-0 promise is **nominally** met, substantively not. A researcher reasonably believes they ran a simulation |
| **G1.2** | **Anchor content is never published.** 9 pins resolve only from a hand-built local registry. | No published registry; no `ghcr.io`/`oci://` reference in any README or zoo file; the workspace registry is a local convention | **Nobody outside this workspace can run the anchor for real.** Root blocker for J1, J2, J6 |
| **G1.3** | **The real Sim path yields an empty scorecard.** ~~Structural, not incidental.~~ **Resolved 2026-07-18 — the stated cause was wrong** (§2). `water_mass` never read the ISRU tank: a dispatch bug routed the storage gauge to the ice-field sampler, so it scored a mass *fraction* as kilograms. | Measured `0.0848` (the ice under the plant), not `0.0`. Six `None`s were a missing-provider-package artifact | Fixed in astro-mine-sim#61 / astro-mine-bench#65; baseline is a capability-aware mode policy |
| **G1.8** | **A fixture scorecard and a Sim scorecard are indistinguishable by provenance.** `Scorecard` carries only `scenario_id` + `metrics`; `content_hash` digests exactly those. No `runner` field exists. | `metrics/_score.py:86-88`; verified — my two scorecards differ only because the *values* differ | **The integrity hole under G1.1.** Two runs claiming the same score cannot be told apart by what produced them. `--json` omits the fixture disclaimer entirely, so **the machine-readable path that feeds leaderboards and papers is the least honest one.** Fixing it re-hashes every existing scorecard (version bump) |
| **G1.4** | **`astro-mine learn` discards the PolicyExport.** | `run.py`: `report, _export = train(...)`; `export_policy_package` never imported in `train/` | **The Phase-1 flywheel's unit of exchange cannot be produced from the CLI** |
| **G1.5** | **No GUI front door.** Studio unreachable via 5 gates; private npm hard-blocks outsiders. | `.npmrc` requires `read:packages`; `app.py` mounts no `ui/dist`; `main.tsx` reads `?study=` | **P5 and P6 cannot use the platform at all** |
| **G1.6** | **No leaderboard UI.** | bench#27 open | M1.2's public face is curl-only. "Public leaderboards" is unmet in the sense users mean |
| **G1.7** | **No user documentation of any kind.** | `docs/` has no guide/tutorial/how-to | Every gap above is discoverable only by reading source |

### G2 — Major

| # | Gap | Evidence | Impact |
|---|---|---|---|
| **G2.1** | No `astro-mine` umbrella CLI; inconsistent naming | 8 CLIs, 2 naming schemes | No discoverable entry point; UC-A3 |
| **G2.2** | **Sim has no CLI and a 35-line README** saying "scaffolding" | verified | The most important Phase-0 component is the least usable |
| **G2.3** | **Studio has no CLI and no documented server start** | no `[project.scripts]`; README has no `uvicorn` | UC-F7 |
| **G2.4** | Studio's backend 503s on 5/9 routes without hand-wiring | `app.py:120-125` `_require()` | Asset menu + 3D pane dead by default |
| **G2.5** | **No validate CLI for Core-owned specs** (Objective/Mission/Plan/manifest) | Core has no CLI; only SADF via `fleet validate` | UC-C9 — 9 authored formats, 1 has a checker |
| **G2.6** | Guard/Mind/Allocate have no CLI despite shipping compilers/validators/composers | verified | UC-E2/E3/E5 |
| **G2.7** | **Guard's `anchor.safety.yaml` is not package data** | outside `src/`; Mind's anchor stack inlines the spec text and documents why | The reference safety contract ships only to repo cloners |
| **G2.8** | **Plugin authoring has no recipe, template, or scaffold** | CONTRIBUTING has one principle line; no cookiecutter | Phase-1 "community plugins" rests on reverse-engineering |
| **G2.9** | **Allocate's solver registry is closed** despite being marketed as pluggable | hardcoded `_LOADERS` dict; no `entry_points()` | UC-H6 — a community solver needs a PR |
| **G2.10** | `--env-factory` has no shipped example | `your_pkg:make_env` placeholder | Learn's quickstart is not copy-pasteable |
| **G2.11** | **WorldSpec YAML front door with zero on-disk examples** | only spec is authored in Python in a build script | UC-C5 |
| **G2.12** | No `examples/` in 16 of 18 repos | verified | Nothing to copy |
| **G2.13** | Anchor content invisible in READMEs (Fleet's 6 assets, Prospect's priors, Mind's 6 stacks) | verified | Ships, loadable, undiscoverable |
| **G2.14** | No leaderboard submit CLI | REST only | UC-G4 |
| **G2.15** | Prospect has **no user-authored file format**; priors are Python | zero `from_yaml` in `src/` | P3 must write code to add a prior — a design question, not just a gap |
| **G2.16** | Determinism gate uses the fixture, not Sim | `scripts/determinism_gate.py` | Repro oracle doesn't exercise physics |

### G3 — Polish / hygiene

*Corrected 2026-07-16 — every G3 item was re-verified while filing Wave 26; three were wrong.*

| # | Gap | Status |
|---|---|---|
| G3.1 | Hub README advertises a `cache` command that doesn't exist | ⚠️ **half wrong** — the phantom `cache` is real (README:30), but "omits `search`" is **false**; `search` is documented at README:43 |
| G3.2 | `Development Status :: 1 - Planning` classifiers | ⚠️ **badly understated** — not just Hub + Seal: **15 of 17 repos** say it. Only `core` and `spice` say `3 - Alpha`. Fleet (15-subcommand CLI) and Mind (6 stacks + 13 manifests) both still say "Planning". Hub's `__init__` docstring also denies its own shipped API/UI |
| G3.3 | Sim README says "Phase 0 — scaffolding" | ✅ confirmed. `docs/README.md` itself also says *"early incubation (Phase 0). Content is being scaffolded."* |
| G3.4 | Org profile package map stale | ⚠️ **partly wrong** — omits `Spice` and `Seal`, but **`Surrogate` is present**. Status line does say Phase 0 |
| ~~G3.5~~ | ~~`core/examples/.../.venv/` committed; build artifacts too~~ | ❌ **STRUCK — the claim is false.** The `.venv/` exists on disk (36M) but is **not tracked** (`git ls-files examples/` → 17 legitimate files), is **explicitly ignored** (`.gitignore:10`), and was **never committed on any branch**. No `target/`, `__pycache__`, `.egg-info`, `dist/`, or `build/` is tracked either. Core's `.gitignore` is exemplary and documents its own policy; the tracked `_pb2.py`/`Cargo.lock` are intentional. **Nothing to fix — no issue filed.** |
| G3.6 | Hub artifact naming inconsistent: `astro-mine.fleet.excavator` vs `excavation-gns` vs `shackleton_water_ice_v1` | ✅ confirmed |
| G3.7 | Seal has no CLI despite being an archetypal sign/verify tool | ✅ confirmed |
| G3.8 | `--kind` validated on `hub publish`, free-form on `hub search` | ✅ confirmed |

**Nuance on G2.13** (verified): "mentioned in **none** of their READMEs" is slightly too strong —
Fleet's README lists `library/` in its module tree; Prospect's mentions `shackleton_water_ice` as a
dict key in a `serve()` snippet. The substantive claim holds completely: **none names the shipped
items, gives a path, or shows a load call**, so a reader cannot get from README to file.

---

## 8. Proposed target surface

Design principles, in tension-resolution order:
1. **One front door.** `astro-mine <verb>` is the discoverable entry; component CLIs remain as the
   implementation and stay usable directly.
2. **CLI is the product; GUI is for comparison and inspection.** Per the brief, scripting via files
   is acceptable. GUI investment concentrates where visual comparison is the task (P5's Pareto
   front, P1's leaderboard, replay).
3. **Never let a stand-in look like the real thing.** Honesty in output is a feature.
4. **The local tier stays sacred.** Everything below must work offline, no account.

### 8.1 The umbrella CLI

```
astro-mine
├── fetch <scenario|artifact>       # ← NEW. Populate the local registry from the published one. G1.2
├── score <scenario> [--runner fixture|sim] [--policy REF]   # ← --runner + honest labels. G1.1
├── run <scenario> [--out run.mcap]  # ← NEW. Sim-backed episode w/o Bench ceremony. G2.2
├── list                             # scenarios in the zoo
├── validate <file>                  # ← NEW. Dispatch on schema: SADF/Objective/Mission/Plan/
│                                    #   Stack/SafetySpec/WorldSpec/manifest. G2.5
├── train ... --export policy.onnx   # ← wire the export through. G1.4
├── submit <policy> --to <url>       # ← NEW. Leaderboard submission. G2.14
├── publish / search / pull / verify # delegate to hub
├── studio serve                     # ← NEW. Composed backend + mounted UI + seeded example. G2.3
├── plugin new <kind>                # ← NEW. Scaffold from template. G2.8
└── new asset|world|stack|safety     # delegate to fleet new; extend to other kinds
```

**Naming:** standardize on `astro-mine <noun/verb>`; keep `fleet`/`worlds`/`link`/`prospect` as
aliases for one deprecation cycle.

### 8.2 The GUI — one console, many surfaces

**Decision (2026-07-16, product):** AstroMine ships **one GUI**, not an app per component. It must
be **designed, not merely functional** — modern, clean, simple. Today's reality is the opposite:
three visual languages (Hub on Pico CSS, Studio on raw CSS + Plotly, View its own), two separate
SPAs, and no shared design vocabulary. Left alone this diverges further with every component.

**Forward-looking positions that shape the design (product direction, not Phase-1 scope):**
- GUI is **for comparison and inspection in Phase 1**, but will grow to authoring, operations, and
  explanation in later phases. The architecture must not assume read-only.
- **All personas** eventually get GUI capability — the CLI/GUI affinity in §3 is a Phase-1
  prioritization, not a permanent split. Nothing may be GUI-unreachable *by construction*.
- A **unified REST API surface may come later — explicitly not Phase 1.** Surfaces therefore talk
  to their own component's existing FastAPI. No new API surface is invented here.

#### 8.2.1 The architecture: the narrow waist, transplanted

The extensibility question — *how does one GUI span components without becoming a monolith?* — is
the same question Core already answers for Python, and it takes the same answer: **a thin, stable
contract with thick, swappable edges.** Components contribute plugins against a shared vocabulary
and never import one another.

```
@astro-mine/surface    the contract — types only, zero deps        ← "Core for the GUI"
@astro-mine/ui         design system — tokens, primitives, a11y, light/dark
@astro-mine/view       domain viz primitives — globe, replay, timeline, frames  (exists)
        ↑
@astro-mine/hub-ui · studio-ui · bench-ui        surfaces (owned by their component repos)
        ↑
@astro-mine/console    the shell — nav, routing, surface registry, config
```

Layering rules (each mirrors an existing platform rule):
- `@astro-mine/surface` carries **no dependencies** — the GUI's narrow waist (core.md §2 principle 3).
- A surface depends on `surface` + `ui` + optionally `view`. **A surface never imports another
  surface** (conventions.md §1.1 — no private side-channels).
- `console` depends on everything; **nothing depends on `console`**. This is what breaks the cycle
  that would otherwise appear if the shell lived inside `view` (`studio-ui → view`, so
  `view/app → studio-ui` would be circular).

#### 8.2.2 The Surface contract

```ts
export interface Surface {
  id: string;                      // "hub" | "studio" | "bench"
  title: string;
  nav?: NavEntry[];                // where it appears in the shell
  routes: SurfaceRoute[];          // path → component
  capabilities?: string[];         // backends it needs; shell degrades honestly if absent
  contributions?: Contribution[];  // ← the extensibility hinge
}
```

**`contributions` is what makes this extensible rather than merely modular.** A contribution
registers against a **shared extension point keyed by an existing, closed, append-only artifact
vocabulary** — not a new UI-side one. So:

- Hub's surface lists a **`world_provider`** artifact → **Worlds' contribution renders it in a globe.**
- A **`policy`** artifact → **Bench's contribution renders its scorecard.**
- An **`asset`** artifact → **Fleet's contribution renders the geometry preview.**

Hub imports none of them. It renders `<InspectorSlot kind={artifact.kind} />` and the registry
resolves it. **Reusing an existing vocabulary rather than inventing a UI-side one is the whole
trick** — it is why "contribute once, use everywhere" holds in the GUI too, and it costs Core
nothing.

Adding a component to the GUI becomes: *publish a surface package, add one line to the registry.*
Not: *modify the console.*

#### 8.2.2a The two artifact vocabularies — resolved

> **This section has been wrong twice.** Draft 1 said "key on `PluginKind`" and illustrated it with
> a `world` artifact — but `world` is not a `PluginKind`. Draft 2 corrected it to "key on Hub's
> `ARTIFACT_KINDS`" — also wrong, because **`ARTIFACT_KINDS` never reaches a UI**. This is the
> third pass, settled against code rather than inference.

**There are two vocabularies, and they answer different questions at different levels:**

| | Core `PluginKind` (16) | Hub `ARTIFACT_KINDS` (8) |
|---|---|---|
| Question | *What Core interface does this implement?* | *What kind of bytes is this?* |
| Owner | `core/registry/enums.py` | `hub/registry/_oci.py` |
| Granularity | fine — Core's extension surfaces | coarse — shipping containers |
| Reaches | registry resolution · version negotiation · capability gating · **the Hub catalog** | **only** the OCI media type `…astro-mine.<kind>.v1` and `hub publish --kind` |

- **In both (4):** `asset` · `campaign` · `design` · `policy`
- **Hub only (4):** `plugin` · `schema` · `surrogate` · `world`
- **Core only (12):** `world_provider` · `body_pack` · `field_model` · `regime_engine` ·
  `sensor_model` · `coupling_scheme` · `resource_field_backend` · `observation_model` ·
  `prior_recipe` · `info_gain_objective` · `comms_model` · `metric`

**The two-level split is legitimate in principle** — a published Worlds bundle really is one
container (`world`) carrying one contract (`world_provider`). Container ≠ contract. But the mapping
has decayed into four different relationships:

| Published thing | Hub kind | Core manifest kind | Relationship |
|---|---|---|---|
| Fleet asset · Learn policy · Studio design/campaign | `asset`/`policy`/`design`/`campaign` | same | 1:1 ✅ |
| Worlds bundle | `world` | `world_provider` | **renamed** (`spec/_publish.py:52` vs `:110`) |
| Surrogate model | `surrogate` | `field_model` **or** `regime_engine` | **1:many**, domain-dependent (`manifest.py:63`) |
| Link ContactPlan · Prospect prior | `plugin` | `comms_model` / `resource_field_backend` | **collapsed into a junk drawer** |
| Core schema bundle | `schema` | *(none)* | **no Core counterpart** |

**How we got here.** Two docs wrote two vocabularies for two jobs and never reconciled them.
**The `design`/`campaign` artifact-kind decision is the archaeology**: it quoted *both* sets side by side in its own text, observed that
neither described a design study, appended `design`/`campaign` to both — and never asked why the
sets differ. It fixed the instance, not the class; the same shape the schema-resolution contract later named. The residue
is a docstring that convicts itself — `_oci.py` claims *"this tuple grows only when Core's does — a
new kind is a Core change, not a Hub extension"*, which is **false for half its members and was false
when written**, and which `hub.md` §2 principle 2 explicitly forbids.

**What settles the console question:** the catalog is a projection of the *manifest*.

```python
CatalogEntry.kind  ->  self.manifest.kind.value        # a PluginKind (_catalog.py:64-65)
ingest(catalog, manifest, *, digest, publisher, namespace, provider)
                                                       # ← the artifact kind is never passed in
```

`ingest()` never receives the Hub artifact kind, `CatalogEntry` never stores it, `_hit()` cannot
return it. **`ARTIFACT_KINDS` dies at the storage layer.** Anything reading Hub's catalogue — the
API, the UI, the console — sees `world_provider`, `comms_model`, `resource_field_backend`.

**So: the console keys on `PluginKind`, and the no-Core-change claim survives.** But that
surfaces the real defect:

> **`PluginKind` is the wrong key for an inspector, on its own.** It answers *what interface does
> this implement*; an inspector needs *what am I looking at*. Those diverge **today**: a Worlds
> illumination field model and a Surrogate excavation model **both carry `field_model`**. Keying on
> kind alone routes a Surrogate model into Worlds' inspector. A live collision, not a hypothetical.
>
> Ironically the catalog is *better* than the media type here: it distinguishes `comms_model` from
> `resource_field_backend`, where Hub's storage layer flattens both to `plugin`.

**Resolution (the accepted decision):** key on **`PluginKind` + a declared predicate over
`manifest.attributes`**, not kind alone. A contribution declares *"I render `field_model` where
`attributes.physics_domain` is present."* Surrogate already carries its facets there — Core's
`PluginManifest` is `extra="forbid"` and cannot be subclassed, so `attributes` is the sanctioned
extension point (the `build_surrogate_manifest` precedent). This needs **no Core change** and
resolves the collision.

**The two-vocabulary mess therefore downgrades from console blocker to an adjacent Hub defect** —
Hub dropping the artifact kind at ingest and asserting a false rule in its docstring. **Filed as
`astro-mine-hub#33`**; it does **not** gate the console. the console contract (`docs#31`) records this
resolution as a decision rather than an open question.

**One obligation survives from draft 2.** `@astro-mine/surface` is TypeScript and cannot import the
Python enum, so `PluginKind` gets **mirrored** — exactly the drift the schema-resolution contract was written to end after
View's vendored units schema went stale in silence. The mirror **MUST** carry a hard-failing CI
drift guard (conventions.md §3.1's vendored-consumer rule), not a comment.

#### 8.2.3 Composition: build-time, not runtime federation

| Option | Verdict |
|---|---|
| **Build-time composition** — console depends on surface packages; registry composes at build | ✅ **Recommended.** Offline, deterministic, version-pinned, no runtime loader |
| Runtime **Module Federation** — shell fetches remotes | ❌ **Rejected for Phase 1.** Fetches over a network → **breaks the local tier, which is sacred** (CX-LOCAL). Version skew + non-determinism fight CX-REPRO |
| Monolithic app owning all UI | ❌ Rejected. One repo becomes the bottleneck; breaks component ownership and one-repo-per-package |

Build-time composition is not a ceiling: if a third party later needs to ship a surface without
rebuilding the console, runtime discovery is an **additive** change behind the same contract.

#### 8.2.4 Backends without a new API surface

The console is a static SPA configured with per-surface base URLs, each surface receiving its own
injected API client:

```ts
createConsole({
  surfaces: [hubSurface, studioSurface, benchSurface],
  endpoints: { hub: "http://localhost:8000", studio: "…", bench: "…" },
})
```

Dev uses a Vite proxy. **No gateway, no unified API — deferred per product direction.** View's
architecture already reserves a "View Gateway" for Phase 2 (its `telemetry/` barrel is a
deliberate `export {}` stub), so deferring is consistent with the plan of record rather than a new
invention. A surface whose `capabilities` are unmet **degrades visibly** ("Hub not configured"),
never blank — View's principle 5.

#### 8.2.5 Phase-1 scope vs. later

**Land in Phase 1 — the contract and the shell:**

| Deliverable | Why now |
|---|---|
| `@astro-mine/surface` — the contract | **Reserve the hooks while the waist is soft.** This is the 001 argument exactly: retrofitting a shell around three grown-up apps later is the leaky-god-interface failure the charter warns about |
| `@astro-mine/ui` — design system | Three visual languages already exist. Every week without it adds drift |
| `@astro-mine/console` — the shell | The front door that does not exist today (G1.5) |
| **Leaderboard surface** | M1.2's public face; bench#27 |
| **Studio surface** | Convert `studio/ui`; wire the 3 orphaned routes (`/intent`, `/studies`, `/campaigns/publish`); study picker; **seeded example study** |
| **Hub surface** | Convert `hub/ui`; add publish/resolve |
| **View harness** | Keep. Document as the developer component gallery it is — it is not the console and should not pretend to be |

**Explicitly deferred:** ops console, live telemetry, plan-explanation UI, OpenMCT dashboards (all
Phase 2 — View's stubs are correctly empty); the unified REST gateway; runtime surface federation;
authoring surfaces for P2/P3/P4 (they remain CLI personas *in Phase 1*).

#### 8.2.6 What "designed well" means here — the design-system brief

Functional-but-ugly is the current state and is not acceptable. The bar:
- **One visual language.** Tokens (color, type scale, spacing, elevation, motion), light **and**
  dark, WCAG 2.1 AA, keyboard-navigable. Retire Pico CSS and Studio's ad-hoc CSS.
- **Honest by default.** Uncertainty renders as uncertainty (View's principle: no false-precision
  heatmaps); stand-ins are visibly labelled (G1.1's lesson applied to pixels); degraded states are
  explicit, never blank.
- **Simple.** The console is nav + surface. No chrome for its own sake. A student should find the
  leaderboard in one click.
- **A charter-level constraint:** the platform's own charts must follow the dataviz discipline the
  domain demands — comparison and uncertainty are the product, not decoration.

This warrants a **design pass with real mockups before implementation**, not CSS applied at the end.

### 8.3 Content distribution (the unblock for everything)

The single highest-leverage fix. Options:
- **(a) Publish the anchor registry to GHCR** and have `astro-mine fetch` pull by digest.
  *Recommended* — reuses the shipped Hub client, respects content-addressing, works offline after
  first fetch.
- (b) Ship a small synthetic anchor world in-package for a 5-minute path, with the real Shackleton
  world fetched on demand. *Recommended as a complement* — serves P6 and gives P3 a WorldSpec to
  copy.
- (c) Document the rebuild path only. *Rejected* — hours of CPU and a 4th repo is not an afternoon.

### 8.4 Documentation (the deliverable this report precedes)

```
docs/guide/
├── getting-started.md          # the honest 10-minute path
├── tutorials/
│   ├── 01-score-the-anchor.md          # P1 · Phase 0
│   ├── 02-run-it-in-the-simulator.md   # P1 · the real path (needs G1.1–G1.3)
│   ├── 03-train-and-publish-a-policy.md# P1 · Phase 1 (needs G1.4)
│   ├── 04-author-an-asset.md           # P4 · works today
│   ├── 05-author-a-world.md            # P3 (needs G2.11)
│   ├── 06-compose-a-planner-stack.md   # P2 (needs G2.6)
│   ├── 07-design-a-swarm-in-studio.md  # P5 (needs G1.5)
│   └── 08-write-a-plugin.md            # all (needs G2.8)
├── how-to/                     # task recipes
├── reference/
│   ├── cli.md                  # every command
│   ├── file-formats.md         # all 9 authored specs, with examples
│   └── personas.md
└── concepts/                   # narrow waist, content-addressing, fidelity, uncertainty
```

**Sequencing rule:** tutorials 01, 04 can be written against today's code. **02, 03, 07, 08 cannot
be written honestly until their gaps close.** Writing them first would document a platform that
doesn't exist.

---

## 9. Recommendations & sequencing

Ordered by *unblocking power per unit effort*.

### Wave 1 — Make the Phase-0 claim true (highest priority)
1. **G1.2** — Publish the anchor content + `fetch`. *Unblocks J1, J2, J6 — nothing else matters
   until this lands.* **Smaller than first assessed:** the OCI remote transport already ships in
   full — `hub/registry/_remote.py` is a 584-line Distribution-Spec v2 client with
   `publish`/`attach`/`verify`, `oci://`+`https://`+bare-host parsing, `open_registry()`
   local-vs-remote dispatch, and **GHCR auth already reading `$GITHUB_TOKEN`**
   (`registry/_auth.py:121`). What is missing is only the **release lane**: the sole workflow is
   `ci.yml` with `permissions: contents: read`, triggering on push/PR — no tags, no
   `workflow_dispatch`, no `packages: write`. Note the anchor store is **556 MB / 73 manifests**,
   so the job must publish the **9-pin subset**, not mirror. Private GHCR still needs a token, so
   this does **not** fully unblock outsiders until the public flip.
2. **G1.1 + G1.8** — `bench score --runner sim|fixture`, **and** put the runner *in the `Scorecard`
   and its `content_hash`* so a fixture score and a Sim score are distinguishable by provenance,
   not just by value. Fix `--json`, which drops the disclaimer entirely today. Re-hashes existing
   scorecards → version bump. Note the determinism gate uses a **different** protocol (harness
   `Runner`, `(resolved, seed) -> RunOutcome`) than the `EpisodeRunner` the flag threads — **two
   protocols need selection**, not one.
3. **G1.3** — **Now a decision, not an investigation** (root cause above). Either make
   `BaselinePolicy` emit an extraction-set mode, or declare it fixture-only and ship a
   Mind-composed anchor stack as the honest baseline. Pin the result with a golden test.
4. **G2.2** — Sim CLI (`astro-mine run`) + a real README.

### Wave 2 — Make the Phase-1 flywheel turn
5. **G1.4** — Wire `--export` through `astro-mine learn`. *One-line-ish; unblocks the entire
   commons exchange.*
6. **G2.10** — Ship an anchor env factory so the Learn quickstart is copy-pasteable.
7. **G1.6 / G2.14** — Leaderboard UI + `astro-mine submit`.
8. **G2.8 / G2.9** — Plugin authoring guide + `plugin new` scaffold; open Allocate's solver
   registry to entry points.

### Wave 3 — Open the front door (the console)
9. **Write it up first** — the console + Surface contract is settled before implementation: it introduces new
   top-level packages and a cross-cutting convention, exactly the bar the Spice and Seal companions cleared. **This is the gating deliverable — nothing else in this wave starts
   until it is accepted.**
10. **Design pass** — mockups + design tokens for the shell and the three Phase-1 surfaces, before
    implementation (§8.2.6).
11. **G1.5 / G2.3 / G2.4** — `@astro-mine/surface` + `@astro-mine/ui` + `@astro-mine/console`;
    convert `hub/ui` and `studio/ui` to surfaces; `astro-mine studio serve` (composed backend,
    mounted bundle, seeded example study). Resolve the `@astro-mine/view` distribution question —
    it currently hard-blocks every outsider (P5, P6).
12. **G2.5** — `astro-mine validate` across all 9 spec formats.
13. **G2.6 / G2.7** — Guard/Mind CLIs; ship `anchor.safety.yaml` as package data.

### Wave 4 — Documentation
12. **G1.7** — The user guide, per §8.4. Tutorials 01/04 now; the rest as their gaps close.
13. **G2.11 / G2.12 / G2.13** — `examples/` everywhere; surface the shipped anchor content in
    READMEs.

### Wave 5 — Polish
14. G2.1 (umbrella CLI + naming), G3.* (doc drift, hygiene, artifact naming).

**Open questions for the team:**
- **G2.15** — Should Prospect gain a file-authored prior format, or is "priors are Python" the
  intended design? This decides whether P3 is a CLI persona or a Python persona.
- ~~**G1.3** — Is `BaselinePolicy` meant to be Sim-runnable at all, or is a Mind-composed stack the
  only honest anchor baseline? Determines Wave 1 item 3's shape.~~ **Closed 2026-07-18 — neither,
  and the diagnosis in this report was wrong. See "G1.3 resolved" below.**
- **Distribution** — does `@astro-mine/view` go public at the flip, or does Studio vendor it?
  Blocks P5/P6 either way, and now blocks the console too.
- **Umbrella CLI** — one package (`astro-mine`) depending on all, or a thin dispatcher that shells
  out to whatever's installed? The local-tier rule favors the dispatcher.
**Resolved 2026-07-16 (product):**
- **Console work is Phase 1**, not Phase 2 — the hooks-while-the-waist-is-soft argument.
  Waves 21–26 are all Phase 1; **Phase 2 now starts at Wave 27** (superseding the earlier
  "P2 starts at Wave 21" note).
- **Console repo shape** — **one repo**, `astro-mine-console`, a pnpm workspace holding
  `packages/surface` + `packages/ui` + `packages/console`. They version and release together, and
  `astro-mine-view` sets the workspace precedent.
- **Surface ownership** — surface packages live **in their component repos**
  (`astro-mine-hub/ui` → `@astro-mine/hub-ui`), matching today's layout and keeping UI ownership
  with the component team. Cost: a Node toolchain in ~4 repos; 3 already have one.
- **Backlog scope** — all six waves are filed up front so the board reflects the whole plan; waves
  23–24 carry an explicit "may be revised by the console contract" note.

---

## 10. Appendix — key evidence

**Executed, not inferred:**
- `astro-mine bench score` → 7 metrics, seconds, trailing disclaimer "scored with the reference
  runner (deterministic fixture, not Sim)".
- `run(load_scenario('lunar-polar-ice-prospecting-v1'), BaselinePolicy(),
  runner=SimEpisodeRunner(store=open_bundle_store('<local-hub-registry>')), seeds=(0,))`
  → `sha256:4c758c87…` · `water_mass 0.0 kg` · six metrics `None`.
- All 9 anchor pins verified present in the workspace registry (22 artifacts).
- `astro-mine learn` `main()`: `report, _export = train(...)` — export dropped.
- Studio `app.py`: mounts `/worlds/files` + `/assets/files`; **no `ui/dist` mount**.
- `astro-mine-studio/ui/.npmrc`: `@astro-mine:registry=https://npm.pkg.github.com`.
  **Correction:** this is **Studio's consumer-side** file. `astro-mine-view` has **no `ui/` dir and
  no `.npmrc` at all** — its side is `lib/package.json`'s `publishConfig` plus a README snippet. So
  the fix is a **cross-repo policy decision, not one file to edit**.
- **Correction — the report recommended the rejected option.** View's README (`:61-64`) argues
  access should come from the package's **Manage Actions access** settings, *"(free, and preferred
  over an org PAT with `read:packages`)"*. Framing the blocker as "needs a `read:packages` token"
  adopts the option View explicitly argues against. The blocker is real; the remedy named was wrong.
- `main.tsx`: `const studyParam = params.get("study")`.
- Entry-point groups confirmed live: `astro_mine.mind.tier_plugins`, `astro_mine.learn.algorithms`,
  `astro_mine.learn.curricula`, `astro_mine.providers`, `astro_mine.field_models`.
- Allocate `solvers/registry.py`: hardcoded `_LOADERS`, no `entry_points()`.

**Counted:** 18 repos · 8 CLIs · 6 services · 3 web UIs (1 reachable) · 2 `examples/` dirs ·
0 user-doc pages · 46 use cases (12 ✅ / 17 ⚠️ / 17 ❌).

### Found during issue-filing — not in the original analysis

Each was verified against code while drafting the backlog, and each is recorded on its issue.

- **`Scorecard` has no runner provenance** → **G1.8** above. The integrity hole under G1.1.
- **The empty Sim score is structural** → G1.3's root cause. `MODE("prospect")` ∉
  `DEFAULT_EXTRACTION_MODES`.
- **The OCI remote transport already ships** → G1.2 is a CI release lane, not a distribution build.
- **Verify-twice does not actually ship.** `supply_chain/_supply_chain.py:5` documents verification
  at "admission (publish) *and* at pull". **Nothing verifies at admission** — the module concedes it
  at `:111` with an instruction no caller follows, and the only test asserting it calls `verify()`
  directly. Both real verifications are pull-side. This contradicts hub.md §2 principle 3 and
  RM-P1-HUB-03's headline. **Not a UX gap — a supply-chain one; worth its own issue outside this
  backlog.**
- **Bench has no entry-point precedent.** Its metric plugins resolve a `module:attribute` string off
  a verified Hub manifest — *not* entry points. `astro_mine.bench.runners` would be net-new surface;
  Learn's registry is the real precedent.
- **Bench's `fetch` has a dependency conflict.** `astro-mine hub` is **not** a Bench base dependency
  (only `[leaderboard]`/`dev`), and the core+pydantic floor is a defended line. Extra-vs-base is a
  blocking decision on that issue.
- **Learn's registry is not the clean precedent claimed.** Its `_BUILTINS` dict is structurally the
  same shape as Allocate's `_LOADERS`, with discovery layered on top.
- **`learn.algorithms` / `learn.curricula` are consumer-side only** — nothing in the org registers
  into them, so they are untested third-party surfaces.
- **Bench's `scripts/measure_*.py` import Sim's private internals**
  (`astro_mine.sim.runtime._hub_adapter`) where a public re-export exists — the schema-resolution contract's
  private-import rule, violated in-house.
- **G3.5 is false and struck** (see above). **G3.1/G3.2/G3.4 were wrong or understated** and are
  corrected in the table.
- **The safety contract exists twice.** Guard's unpackaged `examples/` spec forced Mind's
  `lunar_prospecting_anchor.yaml` to inline it — so a **safety** document is duplicated across two
  repos with nothing syncing them. That is the high-value half of G2.7, not the packaging detail.
- **Studio is worse than "5 of 9 routes 503":** three of the **four** endpoints the UI actually
  calls are in the 503 set, so a hand-rolled uvicorn yields a Studio whose only working pane is the
  comparison. Also `main.tsx`'s **unguarded `JSON.parse`** on `?study=` throws before `createRoot`
  — a malformed param blanks the page, the exact failure the console's degrade-never-blank rule
  forbids.
- **"The Studio UI calls none of the three" is imprecise** — `ui/src/api.ts:102` *does* define
  `publishCampaign()` → `POST /campaigns/publish`; it is dead code no component invokes. Only
  `/intent` and `/studies` have no client at all. Same outcome; a method to wire, not to write.
- **Naming is a third wrinkle, not two.** Beyond bare-vs-prefixed, `astro-mine learn` ships a binary
  named `astro-mine-**train**` (package ≠ command), and `fleet`/`link`/`prospect` are generic
  `PATH` land-grabs.
- **`bench#27`'s premise is doubly stale** — it says View is "Phase 2 with no repo yet" (View exists,
  thin slice shipped) and assigns the leaderboard UI *to View*, which the console's layering inverts.
  `bench#57` supersedes it. Note `Closes #27` in an **issue** body does not auto-close — the
  implementing **PR** must carry the keyword.
