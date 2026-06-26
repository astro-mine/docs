# Phase 0 — Commons seed

> **Window:** ~0–12 mo · **Theme:** Commons seed · **Roadmap home:** [README](README.md)
> **Goal:** a runnable, reproducible benchmark on the lunar-polar anchor scenario — a researcher can
> *clone, run, and score a baseline in an afternoon* (charter §10, §13; system.md §11).

**Entry dependencies:** none (this is the seed). **Governance, license, and export-control posture
must be stood up alongside the first code, not after** (charter §12 → [CX-GOV](README.md#cross-cutting-workstreams)).

**Integration milestones (the phase's definition of "done"):**

- **M0.1 — Prospecting-only slice:** the smallest end-to-end loop — author the world, place a scout
  fleet, prospect a synthetic ice field, score belief quality — runs locally and reproducibly. *First
  runnable milestone* (scenario §3, §15).
- **M0.2 — Water-extraction baseline (feature-complete P0):** the full
  prospect → allocate → excavate → haul → extract → store loop runs at low fidelity on the anchor
  scenario, scored on [Bench](../architecture/bench.md), surviving at least one lunar night cycle in
  reduced form (scenario §15).

**Phase exit criteria:** M0.2 met; the anchor `ScenarioSpec` is content-pinned and byte-for-byte
reproducible across two clean checkouts; `Core v0.1` is frozen for the phase (changes only via RFC);
the local tier runs with no cloud and no account ([CX-LOCAL](README.md#cross-cutting-workstreams)).

**Phase scope note (the anchor):** Phase 0 builds **only** what the
[lunar polar water-ice prospecting scenario](../scenarios/1-lunar-polar-ice-prospecting.md) demands.
Breadth (Mars, more engines, autonomy, studio) is deliberately out of scope.

---

## Core — the narrow waist, v0.1

> Architecture: [core.md](../architecture/core.md). The single most important package; invest
> disproportionately here. Lands first — everything else compiles against it.

**Scope & deliverables**

- **RM-P0-CORE-01** — **SADF v0.1**: identity, USD/glTF geometry refs, kinematics/dynamics,
  power/thermal budgets, sensor suite, comms capabilities, declared autonomy capability tags;
  human-authored YAML/JSON validated by **JSON Schema** with a canonical **Protobuf** wire form;
  composability (sub-assemblies, payload slots). MUST be engine-neutral. *(trace: core.md §3; conventions §3; `LUNAR-FR-008`)*
- **RM-P0-CORE-02** — **Environment API v0.1**: `reset()/step(action) → observation, reward?, info`
  generalized for multi-agent, partial observability, variable timestep, and **explicit
  comms/observation masks**; maps cleanly onto Gymnasium/PettingZoo without being limited to them.
  *(trace: core.md §3; `LUNAR-TR-003`; charter §8)*
- **RM-P0-CORE-03** — **Policy/Planner API v0.1**: one uniform "observations + context →
  actions/assignments" contract with composable sub-interfaces (mission planner · TAMP · allocator ·
  controller). *(trace: core.md §3; charter §5.4)*
- **RM-P0-CORE-04** — **Message-schema catalog v0.1**: the typed cross-component vocabulary
  (state, action, sensor, comms-mask, contact-plan, observation), **including the `ObjectiveSpec`
  schema and the objective→metric binding** as a first-class contract. Per-tick hot-path payloads
  identify the FlatBuffers/Cap'n Proto encoding. *(trace: core.md §3, §3 "objective contract"; `LUNAR-FR-008`; conventions §3)*
- **RM-P0-CORE-05** — **Plugin manifest + registry + version negotiation**: manifest (kind,
  supported Core interface versions, inputs/outputs, capability tags, provenance, signature);
  `compat` refuses incompatible loads with a clear error. **Capability-tag vocabulary** is the
  substrate for export-control gating. *(trace: core.md §3, §9; conventions §9, §12; `LUNAR-SR-001/002`)*
- **RM-P0-CORE-06** — **units / frames / time**: SI everywhere; SPICE-backed body-fixed/inertial
  frames and TDB/ET epochs; explicit planetary CRS; ingest fails loudly on a missing/defaulted frame.
  *(trace: core.md §2; conventions §5; `LUNAR-TR-001`)*
- **RM-P0-CORE-07** — **Codegen + validators + contract-test utilities**: `buf` (proto lint,
  breaking-change CI, multi-language generation for Py/C++/Rust/TS) + `datamodel-code-generator`
  (Pydantic from JSON Schema); **Python reference validator** plus an optional **Rust fast path**;
  ship contract-test utilities so any component can assert it honors the Core versions it claims.
  *(trace: core.md §4, §10; conventions §11)*
- **RM-P0-CORE-08** — **Distribution**: make Core a versioned, consumable artifact — **version from
  the Git tag** (`v0.1.0`, `hatch-vcs`), pinned by downstream via a `uv` **Git source + CI PAT**
  during private incubation; per-language client libs; a **versioned, content-addressed schema
  bundle (OCI artifact, private GHCR)**. Public-PyPI wheel + signed GitHub Releases are **deferred
  to the public flip**. *(trace: VERSIONING.md §2, §5–7; core.md §7; conventions §7)*

**Dependencies:** none upstream. **Exit criteria:** Sim/Worlds/Fleet/Bench compile and run the M0.1
slice against frozen `Core v0.1` (pinned via a tag + `uv.lock`); contract tests green; schema bundle
published to private GHCR and content-addressed.
**Deferred → P1:** Mission/Phase/Regime + propulsion-SADF schema hooks (RFC-0001, *reserved* P1,
[CX-RFC0001](README.md#cross-cutting-workstreams)); autonomy-composition / hub-indexing / studio-intent
additions; Rust validator hardening.

---

## Worlds — the lunar polar world

> Architecture: [worlds.md](../architecture/worlds.md). Real data in, simulatable world out.

**Scope & deliverables**

- **RM-P0-WORLDS-01** — **Lunar south-polar terrain ingest**: LOLA DEM for the
  Shackleton–de Gerlache region → **COG/Zarr** via GDAL, reprojected to an explicit lunar body-fixed
  CRS (PROJ planetary `+R`); derived slope/aspect/roughness layers; carried vertical/void-fill
  uncertainty. *(trace: worlds.md §5, §12; `LUNAR-FR-001`, `LUNAR-TR-001`, `LUNAR-DR-001`)*
- **RM-P0-WORLDS-02** — **SPICE frames, epochs, Sun/Earth geometry** via SpiceyPy (meta-kernel
  management; TDB/ET). *(trace: worlds.md §3; conventions §5)*
- **RM-P0-WORLDS-03** — **Illumination + PSR detection**: precomputed per-azimuth **horizon maps**
  (O(1) per-epoch sun visibility) and **permanently-shadowed-region masks** over a defined epoch
  window. The comms-/sun-denied core of the anchor scenario. *(trace: worlds.md §3, §12; `LUNAR-FR-001`)*
- **RM-P0-WORLDS-04** — **Surface thermal (first-cut)**: 1-D thermophysical model, per-terrain-class
  precomputed diurnal curves driving the ~14-day-night survival constraint. *(trace: worlds.md §11, §12; scenario §5)*
- **RM-P0-WORLDS-05** — **Regolith terramechanics parameter field**: bulk density, cohesion, friction
  angle, bearing, thermal inertia, with companion uncertainty — *parameters only*; constitutive law
  lives in [Sim](../architecture/sim.md). *(trace: worlds.md §1, §6; `LUNAR-FR-003`)*
- **RM-P0-WORLDS-06** — **Environment-API world provider** + **terrain occlusion / LOS service**
  (`ray_intersect`, horizon maps) that [Link](../architecture/link.md) queries. *(trace: worlds.md §3, §6)*
- **RM-P0-WORLDS-07** — **`WorldSpec` + content-addressed world bundle + STAC catalog + 3D-Tiles
  export** (for early [View](../architecture/view.md) reuse). *(trace: worlds.md §5, §12)*

**Dependencies:** Core (`RM-P0-CORE-01,02,06`). **Exit criteria:** "Shackleton vN" opens locally and
serves terrain/illumination/PSR/regolith queries; illumination/PSR regression-tested against
published lunar references with explicit error budgets; world hash reproducible from `WorldSpec` +
pinned toolchain. **Deferred → P1+:** Mars worlds, richer dust, GPU on-demand illumination, learned
illumination surrogate. **Deferred → P3:** small/irregular bodies, microgravity regolith.

---

## Prospect — the ice belief field

> Architecture: [prospect.md](../architecture/prospect.md). Uncertainty is the product, not a footnote.

**Scope & deliverables**

- **RM-P0-PROSPECT-01** — **`ResourceField` contract** (`mean/variance/quantile/sample/posterior` +
  metadata) implemented identically by ground-truth and belief variants. MUST forbid a
  point-estimate-only API. *(trace: prospect.md §2, §3; conventions §1.6)*
- **RM-P0-PROSPECT-02** — **GP backend (GPyTorch, sparse/variational)** + a simple **grid** backend
  behind the contract. *(trace: prospect.md §11, §12)*
- **RM-P0-PROSPECT-03** — **Water-ice / hydrogen priors** derived from public lunar datasets
  (LOLA/Diviner/LEND/M³) with cited provenance and a documented fit recipe. *(trace: prospect.md §2.4, §12; `LUNAR-DR-001`)*
- **RM-P0-PROSPECT-04** — **Sealed `GroundTruthField` + Bayesian `BeliefField` updating** from an
  ordered observation log (replayable prior→posterior chain). *(trace: prospect.md §5, §12; `LUNAR-FR-002`)*
- **RM-P0-PROSPECT-05** — **Ground-truth/belief isolation**: ground truth access-gated and
  unreachable through the agent-facing Environment API; enforced by capability tags + contract tests.
  A leak is a security-class defect. *(trace: prospect.md §9; `LUNAR-FR-002`, `LUNAR-SR-005`, `LUNAR-DR-005`)*
- **RM-P0-PROSPECT-06** — **Information-gain maps (variance / mutual information)** for active
  perception. *(trace: prospect.md §3, §12; `LUNAR-FR-002`; charter §8)*
- **RM-P0-PROSPECT-07** — **Calibration gate**: credible-interval coverage checked against held-out
  ground truth; CI fails on miscalibration. *(trace: prospect.md §10, §12; `LUNAR-DR-005`)*

**Dependencies:** Core (`RM-P0-CORE-01,04`), Worlds (`RM-P0-WORLDS-01`, shared CRS/grid).
**Exit criteria:** a researcher loads a prior, samples a sealed ground-truth ice field for the target
PSR, and updates a calibrated belief from a CSV of synthetic sensor hits on a workstation; isolation
contract test green. **Deferred → P1+:** GMRF/deep-generative backends, EVPI tied to ISRU yield,
multi-species/depth-resolved fields, the distributed field service.

---

## Fleet — the anchor reference asset library

> Architecture: [fleet.md](../architecture/fleet.md). Consume the waist, never widen it.

**Scope & deliverables**

- **RM-P0-FLEET-01** — **SADF authoring/validation/lint toolchain + CLI** (`fleet new|lint|validate|
  render|import|export|resolve|package`), reusing Core's SADF types and (optional) Rust validator.
  *(trace: fleet.md §3, §4)*
- **RM-P0-FLEET-02** — **URDF/SDF importers + USD/glTF geometry handling** (LOD, collision-hull,
  unit/frame normalization). *(trace: fleet.md §3, §11)*
- **RM-P0-FLEET-03** — **Physical-plausibility lint** (positive-definite inertia, power balance,
  sensor FOV/range sanity) running in CI over assets and sampled template parameters. *(trace: fleet.md §10)*
- **RM-P0-FLEET-04** — **Minimal reference library for the anchor scenario**: relay **orbiter**,
  **lander**, prospecting **rover** (neutron/NIR/GPR/drill), **excavator/hauler**, basic **ISRU
  plant** — each with a low-fi mass model and ≥1 higher-fi profile under one identity. *(trace: fleet.md §12; scenario §6; `LUNAR-FR-003`)*
- **RM-P0-FLEET-05** — **Multi-fidelity profiles** (`massmodel`/`kinematic`/`articulated`) under one
  stable asset identity, for Sim's scheduler. *(trace: fleet.md §3, §11)*
- **RM-P0-FLEET-06** — **Signed, content-addressed OCI asset packaging** (pre-Hub: a local/object-
  store path, upgraded to Hub publish in P1). *(trace: fleet.md §5, §12)*
- **RM-P0-FLEET-07** — **Sim instantiation smoke test** in CI (a representative asset spawns and
  steps), catching SADF that validates but cannot be realized. *(trace: fleet.md §10)*

**Dependencies:** Core (`RM-P0-CORE-01,05,06,07`). **Exit criteria:** the anchor robot menu lints,
packages, and instantiates in Sim; assets pinned by content hash for Bench. **Deferred → P1:** broader
parametric families, capability-taxonomy growth, Hub publish/discover, Studio asset menu. **Deferred
→ P3:** launch/return vehicle kinds and propulsion content.

---

## Sim — the multi-physics engine & scenario runtime

> Architecture: [sim.md](../architecture/sim.md). Engine-pluralist, contract-singular. The beating heart.

**Scope & deliverables**

- **RM-P0-SIM-01** — **Deterministic stepping core**: scenario loader, SPICE-backed multi-rate clock,
  seed/RNG manager, the `reset/step` episode loop implementing the Core Environment API. *(trace: sim.md §3; conventions §1.5)*
- **RM-P0-SIM-02** — **Engine-adapter framework** (`RegimeEngine` plugin: `advance/export/import
  coupling-state`, declared frames + determinism class + fidelity descriptor) so engines route behind
  the waist. *(trace: sim.md §3, §11)*
- **RM-P0-SIM-03** — **Initial engine set for the anchor scenario**: orbital (Basilisk/Orekit +
  SPICE) for the relay; mobility/contact (MuJoCo/Brax, CPU-capable) for rovers; manipulation (Drake)
  for excavator linkages; a **reduced-order + DEM/MPM granular** path for excavation. *(trace: sim.md §4, §12; `LUNAR-FR-003`)*
- **RM-P0-SIM-04** — **Multi-domain coupler** (explicit co-sim: named coupling boundaries, multi-rate
  sub-stepping, SPICE-frame/SI bridging, tracked coupling residuals). *(trace: sim.md §3, §11)*
- **RM-P0-SIM-05** — **First-cut rule-based multi-fidelity scheduler with error tracking** (the
  error-budget-driven scheduler is P1). *(trace: sim.md §11, §12)*
- **RM-P0-SIM-06** — **Sensor models** (range/LIDAR, IMU/odometry, imaging, neutron/NIR
  spectrometer, contact) rendering observations *of* Prospect fields, never a point guess. *(trace: sim.md §3; prospect.md §6)*
- **RM-P0-SIM-07** — **Power/thermal evolution** (battery, radiator, RTG/RHU, eclipse) for the
  night-survival constraint. *(trace: sim.md §3; scenario §10)*
- **RM-P0-SIM-08** — **Comms masking** (consume [Link](../architecture/link.md) connectivity →
  per-tick observation/comms masks). *(trace: sim.md §3; `LUNAR-TR-003`)*
- **RM-P0-SIM-09** — **Headless + interactive modes; MCAP recording + provenance stamping** (input
  hashes, engine versions/tiers, seed, error-budget outcomes). *(trace: sim.md §3, §5)*
- **RM-P0-SIM-10** — **Oracle-validated orbital regression** (STK/GMAT/Basilisk) and terramechanics
  validation against analytic/lab cases, each with explicit error budgets; determinism gates in CI.
  *(trace: sim.md §9, §10; conventions §11; `LUNAR-TR-005`)*

**Dependencies:** Core (`RM-P0-CORE-02,04,06`), Worlds, Prospect, Fleet, Link MVP. **Exit criteria:**
the anchor scenario runs headless and interactively, deterministically, at mid-fidelity on a
workstation, emitting MCAP that Bench scores (M0.2). **MVP priority:** correctness + determinism +
the always-works local tier **over breadth of regimes** (sim.md §12). **Deferred → P1:** Surrogate
integration, Brax/MJX swarm-scale, error-budget scheduler, richer sensors. **Deferred → P2:**
digital-twin shadow. **Deferred → P3:** microgravity engine, multi-regime propagation, multi-phase
sequencer.

---

## Bench — the anchor benchmark & reproducibility harness

> Architecture: [bench.md](../architecture/bench.md). Reproducibility is the product. Ships first.

**Scope & deliverables**

- **RM-P0-BENCH-01** — **`ScenarioSpec` schema + content-hash resolver**: pins the Core interface
  version and references Worlds/Fleet/Prospect/Link content by hash, plus seeds, episode/horizon,
  termination, metric set, and per-submission budgets. *(trace: bench.md §3, §5; conventions §5)*
- **RM-P0-BENCH-02** — **The anchor `ScenarioSpec`** ("Lunar Polar Water-Ice Prospecting v1") in the
  zoo, with public dev seeds and an embargoed held-out seed set. *(trace: bench.md §12; scenario §13)*
- **RM-P0-BENCH-03** — **Reference metric set + scoring/aggregation**: water mass, energy/kg,
  information gain, PSR area characterized, nights survived, comms robustness, discovery latency —
  each metric a plugin with units/direction/uncertainty handling. *(trace: bench.md §3; scenario §13; `LUNAR-FR-009`)*
- **RM-P0-BENCH-04** — **Deterministic reproducibility harness**: containerized, seeded, lockfile-
  pinned execution; **determinism gates** that fail CI on non-reproducibility (the platform's
  regression oracle). *(trace: bench.md §3, §10; conventions §11; `LUNAR-DR-004`, `LUNAR-TR-006`)*
- **RM-P0-BENCH-05** — **A baseline policy** + the **local scoring path** (`run(spec, policy)`):
  *clone → run anchor → score in an afternoon*, offline, no account. *(trace: bench.md §7, §8, §12; `LUNAR-TR-004`)*
- **RM-P0-BENCH-06** — **Minimal leaderboard service** (FastAPI + Postgres) with submit-policy-we-run
  + held-out seeds + sampled re-execution as the integrity baseline. *(trace: bench.md §9, §12; `LUNAR-UX-005`)*

**Dependencies:** Core, Sim, Worlds, Fleet, Prospect, Link MVP. **Exit criteria:** the anchor
scenario scores a baseline reproducibly across two clean checkouts; determinism gate wired into CI.
**Deferred → P1:** public leaderboards, community metric plugins, Cloud-scale eval, View leaderboard
UI, Studio scoring integration. **Deferred → P3:** NEO/asteroid mission scenarios + mission metrics.

---

## Link — the comms environment (MVP)

> Architecture: [link.md](../architecture/link.md). Geometry is ground truth; RF is a layer on top.
> **Phase-0 MVP only** — enough to make the anchor scenario comms-denied *for real*
> ([resolved sequencing #1](README.md#resolved-sequencing-decisions)).

**Scope & deliverables**

- **RM-P0-LINK-01** — **Geometric LOS + terrain occlusion** via SPICE GF + Worlds horizon maps;
  degrade-loudly on missing kernels/DEM tiles (never default "connected"). *(trace: link.md §2, §11, §12)*
- **RM-P0-LINK-02** — **Relay-orbiter contact windows + DSN ground-station windows** over an epoch
  window (single relay orbiter baseline). *(trace: link.md §3, §12; scenario §5)*
- **RM-P0-LINK-03** — **Parametric link budget** (gain/path-loss/SNR→rate; CCSDS-aligned mod/cod
  table) for per-link rate/latency. *(trace: link.md §3, §11)*
- **RM-P0-LINK-04** — **`ContactPlan` + `ConnectivitySampler` + `CommsObservationMask`** products,
  content-addressed and wired through the Core Environment API into [Sim](../architecture/sim.md).
  *(trace: link.md §3, §12; `LUNAR-TR-003`)*
- **RM-P0-LINK-05** — **Determinism + content-addressed caching** keyed on kernels/DEM/node-set/
  epoch/config; oracle cross-checks (GMAT/STK/Skyfield) for pass times. *(trace: link.md §5, §10, §12)*

**Dependencies:** Core (`RM-P0-CORE-02,06`), Worlds (occlusion/horizon), Fleet (SADF radios).
**Exit criteria:** surface agents in/near PSRs lose LOS and Earth contact for real in the anchor
scenario; masks flow into Sim; plans reproduce from pinned inputs. **Deferred → P1:** constellation
geometry, multi-hop/CGR, store-and-forward `DeliveryModel`, full latency/bandwidth time-series to
Allocate/Mind, Earth-link windows to Ops, ground-station catalog beyond DSN. **Deferred → P3:**
deep-space DSN scheduling / light-time / DTN.

---

## Cloud — container-first principle (no hosted platform yet)

> Architecture: [cloud.md](../architecture/cloud.md). Local-first, never a hard dependency.
> **Phase 0 ships no cluster** — it ships the *discipline* ([resolved sequencing #2](README.md#resolved-sequencing-decisions)).

**Scope & deliverables**

- **RM-P0-CLOUD-01** — **Container-first, cluster-ready packaging** of every P0 workload (Sim, Bench):
  OCI images pinned by digest, reproducible builds on pinned bases, so they scale out in P1 without
  rework. *(trace: cloud.md §12; conventions §7)*
- **RM-P0-CLOUD-02** — **The `submit()` backend-equivalence contract (local backend)**: the same call
  site runs in-process / `docker compose` on a workstation as it later will on a cluster. *(trace: cloud.md §2, §3)*
- **RM-P0-CLOUD-03** — **Content-addressed artifact I/O convention** (S3-compatible; MinIO local) +
  `RunContext` provenance envelope, so a future scaled run reproduces a laptop run. *(trace: cloud.md §5; conventions §5)*

**Dependencies:** Core (interface-version declaration), Sim/Bench images. **Exit criteria:** P0
workloads run unchanged in-process and in a local container; no hosted cluster required by any P0
milestone. **Deferred → P1:** the full K8s + KubeRay + Argo + Kueue + GPU-Operator platform.

---

← [Roadmap index](README.md) · [Phase 1 →](phase-1-autonomy-studio.md)
