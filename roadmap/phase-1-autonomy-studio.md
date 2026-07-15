# Phase 1 — Autonomy & studio

> **Window:** ~12–30 mo · **Theme:** Autonomy & studio · **Roadmap home:** [README](README.md)
> **Goal:** become the **MARL and planning commons** for planetary swarms — first public
> leaderboards and community plugins (charter §10; system.md §11).

**Entry dependencies:** Phase 0 complete — a runnable, reproducible anchor benchmark on
`Core v0.1` + Sim + Worlds + Fleet + Bench (+ Prospect, Link MVP, local Cloud).

**Integration milestones:**

- **M1.1 — Closed design loop:** [Studio](../architecture/studio.md) turns a stated objective into a
  scored [Campaign](../architecture/studio.md) by orchestrating
  Sim ← (Learn → Mind → Allocate → Guard), scored by Bench, on the anchor scenario.
- **M1.2 — The flywheel turns:** an external party publishes a policy to [Hub](../architecture/hub.md)
  and a result to a **public** [Bench](../architecture/bench.md) leaderboard, reproducibly.

**Phase exit criteria:** M1.1 + M1.2 met; learned, safety-wrapped policies are publishable and
beat-able on the leaderboard; full Cloud scale-out runs the loop; the **RFC-0001 Core schema hooks
are reserved** (below). The narrow waist held — Core grew only additively, every change via RFC.

**Phase-level cross-cutting obligation — [CX-RFC0001](README.md#cross-cutting-workstreams):**
this is the *only* phase where the mission-architecture track touches the critical path, and only as
**additive schema**, while Core is already being extended for autonomy. See **Core (this phase)** below.

---

## Core — autonomy additions + reserved mission hooks

> Architecture: [core.md](../architecture/core.md). Still **schema only**; mechanism/policy live above.

**Scope & deliverables**

- **RM-P1-CORE-01** — **Policy/Planner API hardening for composition**: the sub-interfaces
  ([Mind](../architecture/mind.md)/[Allocate](../architecture/allocate.md)/[Guard](../architecture/guard.md)/[Learn](../architecture/learn.md))
  compose cleanly; ONNX policy artifacts satisfy the contract. *(trace: core.md §12; charter §5.4)*
- **RM-P1-CORE-02** — **Hub-indexing manifest fields** (capability negotiation, provenance,
  signatures) finalized so [Hub](../architecture/hub.md) indexes by the Core manifest, not a private
  schema. *(trace: core.md §3, §6; hub.md §2)*
- **RM-P1-CORE-03** — **`ObjectiveSpec` + objective→metric binding** matured for Studio authoring /
  Bench measurement (the P0 schema, now exercised end-to-end). *(trace: core.md §3; `LUNAR-FR-008,009,010`)*
- **RM-P1-CORE-04** — *(RFC-0001, reserved hooks — no implementation)* **`MissionSpec` / `regime`
  descriptor / `PhaseTransition`** schema, **propulsion/staging/return SADF capability declarations**,
  the **descriptive `TrajectoryRef`/`ManeuverBudget`** message schemas, and the reserved
  **`operational_targeting`** capability tag — all **append-only minors**, proto3 unknown-field
  tolerant. *(trace: RFC-0001 R5, "Impact on Core"; mission-model §2, §3; [CX-RFC0001](README.md#cross-cutting-workstreams))*
- **RM-P1-CORE-06** — *(RFC-0007)* **canonical `units.schema.json`**: the missing authority layer for
  the `RM-P0-CORE-06` frames/CRS/time vocabulary — `ReferenceFrame`/`PlanetaryCRS`/`Epoch`/
  `EpochWindow`/`FrameClass`/`TimeScale` as a `$defs` catalog, pinned by `check_model_drift.py` and
  published in the schema bundle. *(trace: RFC-0007 Design §1a; core.md §2 principle 5)*
- **RM-P1-CORE-07** — *(RFC-0007)* **the vocabulary on the wire**: `units.proto` mirroring the schema
  (closed vocabularies as `string`, the SADF pattern), additive typed `frame_ref`/`epoch`/`window`/
  `crs` fields on the message and mission catalogs, additive `PlanetaryCRS`/`EpochWindow` Cap'n Proto
  structs, and `units/wire.py`. **Append-only**; `CORE_INTERFACE_VERSIONS` unchanged, no new entry.
  *(trace: RFC-0007 Design §1c–§2; conventions.md §3)*
- **RM-P1-CORE-08** — *(RFC-0007)* **guards as contract**: `require_frame`/`require_crs` semantics
  ratified as normative MUSTs, the Earth-CRS **body/datum consistency** rule implemented in
  `validate.py`, and shared conformance vectors every binding runs. *(trace: RFC-0007 Design §3,
  "Resolved decisions"; conventions.md §5, §11; core.md §10)*

**Dependencies:** `Core v0.1`. **Exit criteria:** autonomy + hub + studio run against the additions;
a single-`surface`-phase mission validates as a one-phase `MissionSpec` with no author action;
existing P0 consumers ignore `regime` and operate unchanged; every Core binding that resolves frames
or epochs passes the shared `units` conformance vectors. **Deferred → P3:** all mission-architecture
*implementations* (Transit/Trajectory/Sizing/Ledger).

---

## Surrogate — the granular/excavation surrogate

> Architecture: [surrogate.md](../architecture/surrogate.md). Error is the product. Ordered **after**
> the P0 minimum runnable loop ([resolved sequencing #4](README.md#resolved-sequencing-decisions)).

**Scope & deliverables**

- **RM-P1-SURR-01** — **`SurrogateModel` Protocol + `ErrorReport` + `build_surrogate_manifest()`**
  behind the Core physics-step contract; `predict(state, action=None) → Prediction` (channels +
  calibrated uncertainty + `in_domain`/`ood_margin`). *(trace: surrogate.md §3)*
- **RM-P1-SURR-02** — **Granular/excavation GNN particle simulator** with **deep-ensemble + conformal**
  calibrated error bounds and enforced trust regions. *(trace: surrogate.md §11, §12; charter §8, §9; `LUNAR-TR-002`)*
- **RM-P1-SURR-03** — **`datagen` from high-fidelity Sim** (Sobol/LHS + active learning) and the
  **offline-retrain + gated-promotion** loop. *(trace: surrogate.md §3, §11)*
- **RM-P1-SURR-04** — **ONNX-served fidelity tier loaded by Sim**, whose **scheduler consumes the
  `ErrorReport`** to admit/fall-back per task tolerance; drift/OOD monitors trigger re-validation.
  *(trace: surrogate.md §6, §11; sim.md §3)*

**Dependencies:** Core physics-step contract, working high-fidelity **Sim** (P0), Cloud GPU (P1).
**Exit criteria:** demonstrated **speedup at a published, calibrated error bound** on a Bench
scenario; Sim substitutes the tier only within budget. **Deferred → P2:** neural-operator field
(thermal) surrogates, ops-twin drift monitoring. **Deferred → P3:** microgravity contact/anchoring.

---

## Learn — the MARL toolkit

> Architecture: [learn.md](../architecture/learn.md). Library first, cluster second.

**Scope & deliverables**

- **RM-P1-LEARN-01** — **`SwarmEnv` adapter**: Core Environment API → Gymnasium / PettingZoo
  `ParallelEnv`, with per-agent observation/action spaces keyed by SADF capabilities. *(trace: learn.md §3; `LUNAR-FR-005`)*
- **RM-P1-LEARN-02** — **`CommsModel` wrapper**: declarative observation masks + drop/delay/budget
  channel, driven by [Link](../architecture/link.md) when present — the knob that makes charter §8
  measurable and comparable across algorithms. *(trace: learn.md §3, §11; charter §8)*
- **RM-P1-LEARN-03** — **Baselines: IPPO + MAPPO + QMIX** as reproducible plugins (CTDE default;
  comms-learning as a first-class research track). *(trace: learn.md §11, §12)*
- **RM-P1-LEARN-04** — **Single-GPU-workstation training that just works** (tier 1) + **KubeRay
  distributed training** on Cloud; surrogate-accelerated and GPU-vectorized rollout paths. *(trace: learn.md §7, §12)*
- **RM-P1-LEARN-05** — **`PolicyPackage` export (ONNX + typed metadata sidecar)** with ONNX-Runtime
  equivalence check and honest provenance (comms/observability assumptions, surrogate-fidelity
  caveats). *(trace: learn.md §3, §5, §10)*
- **RM-P1-LEARN-06** — **Honest evaluation harness**: held-out eval envs, seed sweeps, variance and
  comms-stress curves. *(trace: learn.md §10; charter §8)*

**Dependencies:** Core (`RM-P1-CORE-01`), Sim, Surrogate, Link (full), Cloud (full). **Exit criteria:**
a comms-limited cooperative prospecting policy trains overnight on one GPU, exports to ONNX, and is
consumed by Mind/Guard and scored by Bench. **Deferred → P2:** automatic curricula, learned allocation
heuristics for Allocate, sim-to-real-aware training validated on analogs.

---

## Allocate — the combinatorial core

> Architecture: [allocate.md](../architecture/allocate.md). Feasibility non-negotiable; optimality a budget.

**Scope & deliverables**

- **RM-P1-ALLOC-01** — **Allocation IR + Core allocation sub-interface** (`AllocationRequest →
  Allocation`), the solver-neutral canonical model. *(trace: allocate.md §3, §5)*
- **RM-P1-ALLOC-02** — **CP-SAT (OR-Tools) backend** behind the strategy interface (interval/
  cumulative/no-overlap scheduling + assignment + solver hints). *(trace: allocate.md §4, §11; `LUNAR-FR-004`)*
- **RM-P1-ALLOC-03** — **Constraint builders: power, comms-window, terrain traversability** —
  consuming Link contact graph, Worlds traversability, Fleet budgets, Prospect value (with
  uncertainty). *(trace: allocate.md §3, §5; `LUNAR-FR-004`)*
- **RM-P1-ALLOC-04** — **Info-gain-vs-ROI objective** (active perception traded against extraction).
  *(trace: allocate.md §11; scenario §7; charter §8)*
- **RM-P1-ALLOC-05** — **Anytime contract** (streaming incumbents + monotone bounds + optimality gap)
  for online re-solve. *(trace: allocate.md §2, §3)*
- **RM-P1-ALLOC-06** — **Explainability**: objective decomposition, binding constraints, and an
  **IIS** on infeasibility ("which window/power floor bound the result"). *(trace: allocate.md §10; `LUNAR-UX-004`)*
- **RM-P1-ALLOC-07** — **Determinism** (recorded seeds + pinned solver) so a Bench score reproduces.
  *(trace: allocate.md §8; conventions §11)*
- **RM-P1-ALLOC-08** — **Canonical Core `Epoch`/`ReferenceFrame`/`Volume` on Allocate's contract
  surfaces**: `CommsPolicy.epoch0_tdb_s` becomes a required `epoch0: Epoch` (no silent J2000 anchor),
  `ConstraintConfig.comms` becomes optional (`None` ⇒ no relay gating), and the exported
  `allocation_request.schema.json` `$ref`s Core's `Volume`/`ReferenceFrame` instead of inlining a
  private copy — removing two re-derivations of Core message types. The IR proto and CP-SAT goldens
  are unchanged. *(trace: allocate.md §5; RFC-0007; conventions.md §1, §5)*

**Dependencies:** Core (`RM-P1-CORE-01`), Link (full), Worlds, Fleet, Prospect. **Exit criteria:**
tens-of-robots / hundreds-of-tasks solved to a few-% gap within a deadline on the anchor scenario,
delegated from Mind, wrapped by Guard, scored by Bench. **Deferred → P1-late/P2:** MILP track
(HiGHS/SCIP), learned warm-starts/branching, decomposition (rolling-horizon/spatial), auction
fallback, stochastic/robust formulations, ops-replan hardening. **Deferred → P3:** mission-level
joint asset↔target↔window↔trajectory assignment.

---

## Mind — the hierarchical autonomy framework

> Architecture: [mind.md](../architecture/mind.md). Compose, don't centralize.

**Scope & deliverables**

- **RM-P1-MIND-01** — **Three-tier hierarchy over the Core Policy/Planner API** (mission planner →
  per-agent TAMP → local controller) composed from a declarative **stack spec**. *(trace: mind.md §3, §12)*
- **RM-P1-MIND-02** — **Groot-compatible behavior-tree execution scaffold** (BehaviorTree.CPP v4 XML
  dialect) with selector/decorator fallbacks — shipped as a **pure-Python** parse/validate/round-trip
  layer + reactive tick engine. The native BehaviorTree.CPP/pybind11 engine is deliberately out of
  scope: no Python binding is distributed, and vendoring a CMake+pybind11 build into a pure-Python
  wheel would breach the tier-1 local-install rule (conventions.md §7; astro-mine-mind#17).
  *(trace: mind.md §4, §11)*
- **RM-P1-MIND-03** — **PDDL/temporal mission backend** (unified-planning) + **OMPL-based TAMP** +
  **classical (MPC/PID) and ONNX controllers**, all pluggable. *(trace: mind.md §4, §11; `LUNAR-FR-005`)*
- **RM-P1-MIND-04** — **Delegation to Allocate** for assignment (Mind owns decomposition/execution,
  not the combinatorics). *(trace: mind.md §6, §11)*
- **RM-P1-MIND-05** — **Mandatory Guard-wrapping** of every emitted action (the only output path).
  *(trace: mind.md §2, §7)*
- **RM-P1-MIND-06** — **Degrade-not-collapse**: validity-horizoned `ContingentPlan`s + decentralized
  `coord/` so agents act on cached intent through comms-denied PSR intervals, validated under
  injected blackouts. *(trace: mind.md §2, §10; `LUNAR-FR-005`; charter §8, §9)*
- **RM-P1-MIND-07** — **Determinism + decision-trace (MCAP)** for reproducibility and plan
  explanation. *(trace: mind.md §5, §10; `LUNAR-UX-003`)*

**Dependencies:** Core (`RM-P1-CORE-01`), Allocate, Guard, Learn (ONNX policies), Sim, Link, Fleet.
**Exit criteria:** a composed stack runs the anchor scenario against Sim, scored on Bench, with the
degrade-not-collapse fallback validated under comms loss. **Deferred → P2:** online replanning inside
Ops, the ground/edge split. **Deferred → P3:** window-gated cross-phase composition.

---

## Guard — runtime assurance

> Architecture: [guard.md](../architecture/guard.md). **Safety-critical.** Minimal trusted computing base.

**Scope & deliverables**

- **RM-P1-GUARD-01** — **`SafetySpec` schema** (declarative hard constraints: collision/keep-out,
  power floor, thermal/torque ceilings, kinematic limits, STL/MTL temporal clauses) + constraint
  compiler. RFC-gated as a safety contract. *(trace: guard.md §3, §9.3; `LUNAR-FR-006`)*
- **RM-P1-GUARD-02** — **Rust safety core (the TCB)**: `arbiter` + **CBF-QP shield (OSQP/Clarabel)**
  + **STL/MTL runtime monitors** + **simplex backup controller**, deterministic, allocation-free on
  the hot path, fail-safe-never-open. *(trace: guard.md §2, §3, §9; conventions §2; `LUNAR-SR-004`)*
- **RM-P1-GUARD-03** — **`PolicyShield`** implementing the Core Policy/Planner API (a shielded policy
  *is* a policy), wrapping Mind/Allocate/Learn outputs transparently. *(trace: guard.md §3, §6)*
- **RM-P1-GUARD-04** — **Power-floor & thermal monitors + night-survival safe behaviors** for the
  anchor scenario; **slope/keep-out** shields from Worlds. *(trace: guard.md §6; scenario §10; `LUNAR-FR-006`)*
- **RM-P1-GUARD-05** — **Signed spec/model loading + adversarial/falsification testing** (search for
  actions that try to violate; confirm the shield prevents them). *(trace: guard.md §9.5, §10)*
- **RM-P1-GUARD-06** — **`SafetyVerdict` stream (MCAP)** with spec-clause/cert provenance, for
  Bench scoring ("violations per scenario", "performance cost of shielding") and View overlays.
  *(trace: guard.md §5, §6)*
- **RM-P1-GUARD-07** — **Typed `SafetySpec` frames**: replace the free-form `frame: str` in all four
  Guard contract formats (Python / proto / JSON-Schema / Rust) with a typed Core `ReferenceFrame`
  sibling `frame_ref`, and add a fail-closed `require_frame` guard inside the Rust TCB that validates
  frame name / `frame_class` / center tokens against Core's shared conformance vectors — so a keep-out
  volume in an unknown frame is rejected at compile time before it reaches the trusted core. The TCB
  dependency surface is not grown. *(trace: guard.md §3; RFC-0007; conventions.md §5; `LUNAR-TR-001`)*

**Dependencies:** Core (`RM-P1-CORE-01`), Worlds (keep-out/slope), Fleet (limits), Sim (dynamics).
**Exit criteria:** a Learn policy runs **shielded** in Sim on the anchor scenario; zero hard-constraint
violations under adversarial test; shielding-cost measured and reproducible. **Deferred → P1-late/P2:**
multi-agent latency-aware shielding (`coord`), HJ-reachability filters, edge sidecar + central
supervisor, View overlays. **Deferred → P3:** embeddable flight-adjacent core; per-phase deep-space
one-shot assurance.

---

## Studio — the design front door

> Architecture: [studio.md](../architecture/studio.md). Studio computes nothing; it orchestrates.

**Scope & deliverables**

- **RM-P1-STUDIO-01** — **Structured (no-LLM) intent capture → Core-validated `ObjectiveSpec`** (the
  deterministic `intent.forms` path; the LLM is optional and added later). *(trace: studio.md §3, §9; `LUNAR-UX-001`)*
- **RM-P1-STUDIO-02** — **Trade-study / DSE engine** (pluggable Ax/BoTorch · Optuna · pymoo · Ray
  Tune) producing **Pareto-ranked** `DesignCandidate`s; multi-fidelity evaluation (Surrogate prune →
  Sim escalate). *(trace: studio.md §3, §11; `LUNAR-FR-010`, `LUNAR-UX-006`)*
- **RM-P1-STUDIO-03** — **The design loop orchestration** (fan candidates to
  Sim/Learn/Mind/Allocate/Guard/Bench over gRPC; async durable/cancelable/resumable jobs; Cloud
  fan-out). *(trace: studio.md §3, §6, §12)*
- **RM-P1-STUDIO-04** — **`Campaign` authoring + contingencies + hand-off package** consumed
  unchanged by Ops in P2. *(trace: studio.md §3, §12)*
- **RM-P1-STUDIO-05** — **Optional, provider-abstracted LLM intent capture** (Claude API adapter;
  structured outputs validated against Core schemas; never on a safety/planning/flight path). *(trace: studio.md §9, §11; `LUNAR-UX-001`)*
- **RM-P1-STUDIO-06** — **Embedded [View](../architecture/view.md) + publish-to-Hub** for candidate
  inspection and sharing. *(trace: studio.md §6, §12)*
- **RM-P1-STUDIO-07** — **Reproducibility-by-construction** (every candidate records inputs/seeds/
  versions; a re-run reproduces the Pareto front). *(trace: studio.md §5, §10)*
- **RM-P1-STUDIO-08** — **Validate the content-addressed `PlanetaryCRS`**: pin the CRS dict Studio
  content-addresses (`GeoRegion.crs` on an `IntentDraft`, carried into a `Campaign`) to Core's
  canonical `units.schema.json` `PlanetaryCRS` at the point it enters the hashed artifact — resolving
  the cross-file `$ref` offline via Core's `schema_registry`, recording the units-schema digest as
  sidecar provenance (never inside the hashed payload). *(trace: studio.md §5; RFC-0007; RFC-0009;
  conventions.md §5)*
- **RM-P1-STUDIO-09** — **Selectable robot menu + asset geometry preview**: project the Hub catalog
  into `MenuEntry` rows (kind + display name from the Core manifest, capability-filtered) and a
  Hub-asset preview materializer (resolve → verify-before-trust pull → content-addressed cache) that
  feeds the embedded [View](../architecture/view.md) `AssetPreview` widget — a pure Core/Hub consumer,
  no `astro_mine.fleet` import. *(trace: studio.md §3, §6; pairs with `RM-P1-VIEW-03`)*

**Dependencies:** the full autonomy stack + Bench + Hub + Cloud. **Exit criteria:** goal-in →
scored-design-out end-to-end on the anchor scenario, producing a `Campaign` (M1.1). **Deferred → P2:**
the Campaign→Ops hand-off matures into the live design→operations loop. **Deferred → P3:** Mission
Architect mode.

---

## Hub — the artifact registry

> Architecture: [hub.md](../architecture/hub.md). The supply-chain trust boundary; the flywheel's other half.

**Scope & deliverables**

- **RM-P1-HUB-01** — **OCI-backed, content-addressed registry** (Zot/Harbor) for worlds, SADF
  assets, ONNX policies, surrogates, plugins, schema bundles; immutable `name:version→digest`.
  *(trace: hub.md §3, §5, §11)*
- **RM-P1-HUB-02** — **Index by the Core plugin manifest** (kind, interface versions, capability tags,
  provenance) into Postgres; **faceted + full-text + pgvector semantic + capability-match** discovery.
  *(trace: hub.md §3, §11)*
- **RM-P1-HUB-03** — **Verify-twice supply chain** (cosign signatures + SLSA provenance + SBOM at
  **publish and at pull**, client-side re-verification). *(trace: hub.md §9; `LUNAR-SR-002`)*
- **RM-P1-HUB-04** — **SemVer + Core-interface-range dependency/compat resolution**. *(trace: hub.md §3, §11)*
- **RM-P1-HUB-05** — **License + export-control download gating** (OPA against capability tags;
  tiered open vs. curated/verified namespaces). *(trace: hub.md §9; conventions §12; `LUNAR-SR-001`)*
- **RM-P1-HUB-06** — **`astro-mine-hub` client/CLI** that resolves/verifies/pulls against *any* OCI
  registry (so the local tier needs no hosted Hub). *(trace: hub.md §3, §7)*

**Dependencies:** Core (`RM-P1-CORE-02`), Cloud (deploys on it). **Exit criteria:** a contributor
publishes a signed policy/world/asset and another pulls + verifies it; Bench resolves submissions by
digest (M1.2). **Deferred → P2:** multi-region replication / offline mirrors. **Deferred → P3:**
mission-architecture artifact types + `operational_targeting`-aware gating.

---

## Seal — the artifact-integrity companion

> Architecture: [seal.md](../architecture/seal.md). A thin **Core companion** (the [Spice](../architecture/spice.md)
> shape) added by [RFC-0005](../rfc/0005-seal-supply-chain-companion.md); the single home for
> `cryptography` (Core stays crypto-free). **Additive and non-urgent — must not gate the lunar MVP.**

**Scope & deliverables**

- **RM-P1-SEAL-01** — **Package scaffold**: the importable `astro_mine.seal` library, Core-pinned
  dependency wiring (and the one home for `cryptography`), and CI with a ≥95% coverage gate. The seed
  for all `RM-P1-SEAL-*` feature work. *(trace: RFC-0005; conventions.md §2, §3)*
- **RM-P1-SEAL-02** — **Signer + cross-package conformance test**: `generate_keypair` / `sign_digest`
  / `verify_signature` / `make_verifier` (ECDSA **P-256**, `SIGSTORE_COSIGN` scheme) on Core's frozen
  `Signature`/`Verifier` surface, with a conformance test that **pins the signature bytes** for a known
  digest+key so any drift turns CI red. *(trace: RFC-0005 §"The package"; seal.md §3, §9; `LUNAR-SR-002`)*
- **RM-P1-SEAL-03** — **SLSA / SBOM / verify-twice relocation**: move Hub's `_attest.py` /
  `_supply_chain.py` (`build_slsa_provenance` / `build_cyclonedx_sbom` / `attest`; the verify-twice
  `verify` with `DEFAULT_REQUIRED = (signature, slsa, sbom)`) into Seal; Hub imports them from there,
  behavior-preserving. *(trace: RFC-0005 §Sequencing; seal.md §3; hub.md §9)*

**Consumer migrations** — landing **signer-dedup first**, each adopts `astro_mine.seal` and **deletes
its local signer copy**: [Guard](../architecture/guard.md) (`spec/signing.py`, from `RM-P1-GUARD-05`),
[Fleet](../architecture/fleet.md) (`packaging/signing.py`), and [Hub](../architecture/hub.md)
(`supply_chain/`, after SEAL-03).

**Dependencies:** Core (`registry.Signature`/`Verifier`, `hashing`); founding content **extracted**
from Hub's `supply_chain/` (`RM-P1-HUB-03`). **Exit criteria:** the signer + conformance test are green
and Guard/Fleet/Hub consume Seal with their duplicated copies deleted; existing signatures still verify
(byte-compatible). **Deferred → P2:** keyless cosign (Fulcio/Rekor) and the production **trust-root
policy** (cosign identities, key distribution, rotation/revocation) — the mechanism lives in Seal, the
org policy is decided with Hub.

---

## Cloud — the hosted scale-out platform

> Architecture: [cloud.md](../architecture/cloud.md). Infrastructure, not logic.

**Scope & deliverables**

- **RM-P1-CLOUD-01** — **Helm-installable platform on conformant Kubernetes**: KubeRay (RayJob/
  RayCluster), Argo Workflows, plain K8s Jobs, the NVIDIA GPU Operator (MIG). *(trace: cloud.md §3, §4, §12)*
- **RM-P1-CLOUD-02** — **`JobSpec`/`SweepSpec`/`WorkflowSpec` contracts + submission client/CLI**,
  with the **local↔cluster backend-equivalence** guarantee (same call site). *(trace: cloud.md §3)*
- **RM-P1-CLOUD-03** — **Kueue queueing + quotas/fair-share; Karpenter/cluster-autoscaler; spot-first
  + content-addressed checkpoint-resume; per-tenant budgets.** *(trace: cloud.md §3, §11)*
- **RM-P1-CLOUD-04** — **Data-locality layer** (lazy Zarr/COG/Parquet chunk-streaming + pull-through
  cache; co-locate cluster with object store). *(trace: cloud.md §5, §8)*
- **RM-P1-CLOUD-05** — **MLflow + content-addressed artifact I/O** (`RunContext` provenance);
  **namespace-per-tenant isolation** (RBAC/OPA, NetworkPolicies); admission of cosign-verified images
  only. *(trace: cloud.md §5, §9)*
- **RM-P1-CLOUD-06** — **NATS+JetStream eventing substrate + Redis job-status store**: a durable,
  replayable JetStream stream with a durable pull consumer (at-least-once, explicit-ack,
  replay-from-cursor, resume-across-restart) behind the `EventPublisher` seam, plus a Redis-backed
  **ephemeral** job-status read model, with `emit_completion` wired into the run lifecycle
  (`submitted`/`started`/`completed`/`failed`). The local/dev tier stays broker-free (`NullPublisher`
  + in-memory status defaults), so a laptop `submit()` needs no NATS or Redis. *(trace: cloud.md §4,
  §5, §6; conventions.md §4, §5, §7)*

**Dependencies:** Core (interface-version declaration), Sim/Learn/Allocate/Bench images. **Exit
criteria:** the design/training loop runs "at scale on Cloud" — Studio heavy jobs + first public Bench
leaderboard eval fan out; a cluster run reproduces the laptop run for the same inputs+seed. **Deferred
→ P2:** vCluster/stronger tenancy, hosting ops-tier services. **Deferred → P3:** mission-design sweep
workload classes (no new primitive).

---

## Link — full constellation & multi-hop

> Architecture: [link.md](../architecture/link.md). Builds on the P0 MVP.

**Scope & deliverables**

- **RM-P1-LINK-10** — **Richer constellation geometry + multi-hop reachability** (multiple lunar
  and/or Earth relay orbiters as SADF nodes with their own ephemerides). *(trace: link.md §3, §12; see the relay-fleet Q&A)*
- **RM-P1-LINK-11** — **Contact-graph / CGR delivery model + abstract store-and-forward
  `DeliveryModel`** for delay-tolerant routing. *(trace: link.md §3, §11, §12)*
- **RM-P1-LINK-12** — **Full latency/bandwidth time-series to [Allocate](../architecture/allocate.md)/
  [Mind](../architecture/mind.md)** (contact graph for combinatorics + continuous cube for fidelity).
  *(trace: link.md §6, §11)*
- **RM-P1-LINK-13** — **Earth-link windows delivered to Ops (forward-looking)** + ground-station
  catalog beyond DSN (ESTRACK/custom). *(trace: link.md §6, §12)*
- **RM-P1-LINK-14** — **Core time vocabulary on Link's contract surfaces**: the CGR contact graph, the
  store-and-forward `DeliveryModel`, the Earth-link Ops products, and the latency/bandwidth
  time-series carry typed `Epoch`/`EpochWindow` and record a `TimeScale` instead of scale-by-naming
  `*_tdb_s` floats; raw float columns stay only inside the numeric kernels. A representation change,
  not a numerics change (the oracle path is untouched). *(trace: link.md §5; RFC-0007; conventions.md §5)*

**Dependencies:** Link MVP (P0), Fleet relay assets. **Exit criteria:** a multi-relay constellation's
time-varying coverage of the PSR work is modeled, masks/windows drive Allocate/Mind, and a Studio
trade study can compare relay geometries. **Deferred → P2:** optional ns-3 packet-level fidelity,
live-mission link prediction (capability-gated). **Deferred → P3:** deep-space DSN/light-time/DTN.

---

## Sim — Phase-1 extensions

**Scope & deliverables**

- **RM-P1-SIM-01** — **Content-pinned `ScenarioSpec → Sim Scenario` bridge**: resolve the
  Worlds/Fleet/Prospect content a [Bench](../architecture/bench.md) `ScenarioSpec` pins **by content
  hash** (Hub-published) into a Sim `Scenario`, replacing the `RM-P0-SIM-11` inline reduced-order
  anchor. Sim resolves via Hub + Core manifests — no sibling-package import. *(trace: sim.md §3, §5; bench.md §5, §6)*
- **RM-P1-SIM-02** — **ISRU extraction/storage support**: a reduced-order extraction/storage process
  model + an ISRU-storage sensor (a new `RESOURCE_STORAGE` `SensorKind` via RFC — Core is frozen in
  P0) reporting stored water (kg), unblocking Bench's `water_mass` / `energy_per_kg` metrics. *(trace: sim.md §1, §3; bench.md §3)*
- **RM-P1-SIM-03** — **Error-budget-driven multi-fidelity scheduler**: upgrade the `RM-P0-SIM-05`
  rule-based scheduler to consume the [Surrogate](../architecture/surrogate.md) `ErrorReport` and
  admit / fall back per task tolerance, emitting error-budget reports. *(trace: sim.md §11, §12;
  surrogate.md §6; pairs with `RM-P1-SURR-04`)*
- **RM-P1-SIM-04** — **Brax/MJX GPU-vectorized swarm-scale rollout**: a JAX (Brax/MJX) GPU-batched
  engine/rollout path behind the `RegimeEngine` framework for [Learn](../architecture/learn.md)
  swarm-scale training, with Ray fan-out on Cloud. *(trace: sim.md §12; charter §8)*
- **RM-P1-SIM-05** — **Richer sensor models**: extend the `RM-P0-SIM-06` sensor suite with additional
  / higher-fidelity models, still rendering observations *of* Prospect fields (never a point guess).
  *(trace: sim.md §3; prospect.md §6)*
- **RM-P1-SIM-06** — **DEM granular-excavation high-fidelity engine**: a soft-sphere discrete-element
  granular-contact engine as a `RegimeEngine` plugin behind the reduced-order `GranularEngine` seam
  (a blade sweeps a settled particle bed → tool-reaction/draft force, excavated mass, per-particle
  kinematics) — the high-fidelity ground-truth oracle the [Surrogate](../architecture/surrogate.md)
  tier trains and validates against and escalates back to on drift. *(trace: sim.md §3, §8, §11;
  surrogate.md §3; `LUNAR-TR-002`)*

**Dependencies:** `RM-P0-SIM-11`, Hub (publish/discover), the Hub-published Worlds/Fleet/Prospect
bundles (`RM-P0-WORLDS-07` / `RM-P0-FLEET-06` / `RM-P0-PROSPECT-04`); `RM-P1-SIM-02` additionally a
Core RFC for the `SensorKind`; `RM-P1-SIM-03`/`04` on [Surrogate](../architecture/surrogate.md)
(`RM-P1-SURR-04`) + Cloud GPU (`RM-P1-CLOUD-01`). **Exit criteria:** the anchor's provisional content
pins resolve to real Hub digests and a Sim run reproduces from them; a Sim run reports stored-water so
Bench scores `water_mass`/`energy_per_kg`; the scheduler substitutes the Surrogate tier only within
its error budget. **Deferred → P3:** microgravity/small-body regimes; multi-species extraction.

---

## Worlds & Prospect — Phase-1 extensions

**Worlds**

- **RM-P1-WORLDS-10** — **GPU on-demand fine illumination + learned illumination surrogate**
  (co-designed with [Surrogate](../architecture/surrogate.md)) for swarm-scale queries. *(trace: worlds.md §11, §12)*
- **RM-P1-WORLDS-11** — **Mars worlds (MOLA/HiRISE) + Martian frames + richer dust model** as the
  first non-anchor body, validating "support a new world = a package, not a core change." *(trace: worlds.md §12; charter §10.2)*
- **RM-P1-WORLDS-12** — **Full per-cell topocentric horizon maps**: replace the `RM-P0-WORLDS-03`
  grid-azimuth horizon approximation (and its grid-convergence correction) with a rigorous per-cell
  topocentric computation — a drop-in fidelity upgrade behind the same `IlluminationModel` API and
  PSR semantics. *(trace: worlds.md §3, §11, §12; refines `RM-P0-WORLDS-03`)*
- **RM-P1-WORLDS-13** — **Illumination-driven per-cell surface thermal**: drive the `RM-P0-WORLDS-04`
  1-D thermophysical solver with real horizon-mapped per-cell insolation (+ SPICE Sun geometry)
  instead of the representative per-class arc; keep the class curves as a fast low-fi tier.
  *(trace: worlds.md §8, §11; refines `RM-P0-WORLDS-04`)*
- **RM-P1-WORLDS-14** — **Diviner/LEND/M³ conditioning-layer ingest**: ingest Diviner temperature,
  LEND epithermal-neutron (WEH), and M³ OH/H₂O rasters as world layers on the Shackleton–de Gerlache
  CRS/grid, so [Prospect](../architecture/prospect.md) can condition real priors on them (unblocks
  `RM-P1-PROSPECT-12`). *(trace: worlds.md §6, §12; prospect.md §6; `LUNAR-DR-001`)*
- **RM-P1-WORLDS-15** — **Hub-publish the world bundle + Core `world_provider` manifest**: emit the
  built bundle as a signed, content-addressed `world` OCI artifact (each product carries its own
  `manifest.json` so a pulled bundle is self-describing and re-openable offline), fold the
  SPICE-derived PSR mask into `world_hash`, and add the `worlds` publish/keygen CLI + a repeatable
  Shackleton anchor build recipe. *(trace: worlds.md §5; hub.md §3)*
- **RM-P1-WORLDS-16** — **Publish the tileset-to-body transform**: the 3D-Tiles `root.transform` + a
  `tiles_anchor` on `world.json`, so [View](../architecture/view.md) reads where a tileset's local
  frame sits on the body instead of applying its own `modelMatrix` (no double-transform).
  *(trace: worlds.md §5; view.md §3)*
- **RM-P1-WORLDS-17** — **Pin `world.json` `crs` / `tiles_anchor.frame` to Core's units schema**:
  emit-time validation of the serialized CRS/frame objects against Core's canonical
  `units.schema.json`, typing the anchor frame as a Core `ReferenceFrame` and adopting `require_crs`
  at the authoring boundary. *(trace: worlds.md §5; refines `RM-P1-CORE-08`; RFC-0007)*

**Prospect**

- **RM-P1-PROSPECT-10** — **GMRF and deep-generative backends** behind the `ResourceField` contract
  (large lattice domains; non-Gaussian/multimodal structure). *(trace: prospect.md §11, §12)*
- **RM-P1-PROSPECT-11** — **Richer active-perception objectives (EVPI tied to ISRU yield)** for
  Learn/Allocate, + the **distributed field service** + Hub-published community priors. *(trace: prospect.md §11, §12)*
- **RM-P1-PROSPECT-12** — **Real PDS raster-ingest prior-recipe**: replace the P0 *parametric* prior
  with a real public-dataset (LOLA / Diviner / LEND / M³) raster-ingest recipe, reprojected onto the
  Worlds Shackleton CRS/grid with per-product content-addressed provenance and Hub-published; the
  parametric prior stays the offline default. *(trace: prospect.md §2.4, §3, §4, §6, §12; defers from `RM-P0-PROSPECT-03`)*
- **RM-P1-PROSPECT-13** — **Hub-publish the parametric belief prior + import-light `from_bundle`
  loader**: serialize the P0 parametric prior (`shackleton_water_ice_v1`) into a content-addressed
  bundle, emit a Core `resource_field_backend` manifest, and publish it signed; a consumer rebuilds a
  live `ResourceField` via `from_bundle` using only NumPy + Core, never importing `astro_mine.prospect`.
  Publishes the **public belief prior only** — the sealed `GroundTruthField` is never serialized
  (`RM-P0-PROSPECT-05` invariant). *(trace: prospect.md §3, §4, §6; hub.md §3, §9)*
- **RM-P1-PROSPECT-14** — **`PlanetaryCRS`/`ReferenceFrame` on the wire + schema-guarded ingest CRS**:
  add typed `ReferenceFrame`/`PlanetaryCRS` to `field_service.proto` (importing Core's `units.proto`)
  so a gRPC-served `ResourceField` carries its georeference, and replace the hand-rolled ingest
  CRS-presence check with Core's `require_crs` guard. *(trace: prospect.md §6; RFC-0007; refines
  `RM-P1-CORE-08`)*

**Dependencies:** P0 Worlds/Prospect, Surrogate, Cloud; `RM-P1-PROSPECT-12` on `RM-P1-WORLDS-14`
(conditioning layers) + Hub. **Exit criteria:** a second body (Mars) and a second field backend ship
as plugins with no Core change; the EVPI objective is consumable by Allocate; the real-ingest prior
reproduces from cited public inputs and is Hub-published while the offline parametric default still
runs with no network. **Deferred → P2:** operational belief from real *mission* sensors (Ops/Bridge).
**Deferred → P3:** small/irregular-body Worlds; asteroid volatile fields (Prospect reuse).

---

## Bench — public leaderboards

**Scope & deliverables**

- **RM-P1-BENCH-10** — **Public leaderboard service** (hosted FastAPI + Postgres + Redis + object
  store on Cloud) with ingestion of community **ONNX/plugin submissions from Hub by digest**. *(trace: bench.md §12)*
- **RM-P1-BENCH-11** — **Scale-out evaluation on Cloud** (Argo + Ray; KubeRay GPU rollouts). *(trace: bench.md §7, §12)*
- **RM-P1-BENCH-12** — **Pluggable community metrics** (Core-registry plugins via Hub) + richer
  scenario zoo + **[View](../architecture/view.md) leaderboard/replay UI** + **Studio scoring
  integration**. *(trace: bench.md §3, §12; `LUNAR-UX-005,006`)*
- **RM-P1-BENCH-13** — **Anchor pins → real Hub digests**: replace the anchor scenario's *provisional*
  content pins with the real Hub artifact digests the producers publish (world / fleet / prospect),
  which Sim's `ContentResolver` resolves into a runnable `Scenario` — the capstone of the
  content-pinning chain. *(trace: bench.md §5, §6.)* *(Numbering note: this shipped ahead of
  `RM-P1-BENCH-10..12`; append-only IDs record registration order, not delivery order.)*

**Dependencies:** Hub, Cloud, View (thin slice), Studio. **Exit criteria:** an external lab beats a
baseline on the public leaderboard, reproducibly (M1.2). **Deferred → P2:** analog/digital-twin
validation scenarios, hidden test scenarios, multi-objective ranking. **Deferred → P3:** mission-level
scenarios + metrics.

---

## Fleet — Phase-1 extensions

- **RM-P1-FLEET-10** — **Broaden parametric families + capability taxonomy** + **Hub publish/discover
  integration** (the P1 upgrade from the P0 local/object-store OCI path). *(trace: fleet.md §12)*
- **RM-P1-FLEET-11** — **Expose the asset menu in Studio** + **feed capability declarations to
  Mind/Allocate** for role negotiation / task allocation as autonomy lands. *(trace: fleet.md §12)*

**Dependencies:** `RM-P1-FLEET-10` on Hub; `RM-P1-FLEET-11` on Studio + Mind/Allocate. **Exit
criteria:** new vehicle types arrive as Hub packages and appear in Studio's menu with no Fleet code change. **Deferred → P2:** Bridge hardware
mapping. **Deferred → P3:** launch/return vehicle kinds + propulsion content.

---

## View — thin-slice reuse (View formally ships in Phase 2)

> Architecture: [view.md](../architecture/view.md). The roadmap-sanctioned **Phase-0/1 thin-slice
> reuse** ([resolved sequencing #4](README.md#resolved-sequencing-decisions); view.md §12): a
> **front-end-only, embeddable component library** — no gateway, no live-ops plane — whose purpose is
> to unblock [Studio](../architecture/studio.md) candidate inspection and [Bench](../architecture/bench.md)
> replay. The full operations viewer (live Ops telemetry, OpenMCT dashboards, plan-explanation, the
> View Gateway) remains View's Phase-2 MVP (`RM-P2-VIEW-01..06`).

**Scope & deliverables**

- **RM-P1-VIEW-01** — **Repo scaffold**: the `@astro-mine/view` embeddable TS+React component-library
  workspace (Vite / pnpm / Vitest / Playwright) + CI + a reference widget proving library consumption
  without a renderer. *(trace: view.md §3, §12)*
- **RM-P1-VIEW-02** — **Embeddable Cesium globe** (`GlobeScene`) over Worlds 3D-Tiles terrain, with
  `frames/` CRS/SPICE-time helpers — never assuming WGS84. *(trace: view.md §3, §5)*
- **RM-P1-VIEW-03** — **Asset & candidate-swarm geometry**: an `AssetModel` / `SwarmLayer` entity
  layer placing Fleet glTF geometry at supplied poses — the widget Studio's `AssetPreview` mounts
  (`RM-P1-STUDIO-09`). *(trace: view.md §3, §6)*
- **RM-P1-VIEW-04** — **MCAP replay + shared timeline**: read a pinned Sim MCAP episode in the browser
  (opened **by content hash**, verified fail-closed before decode) driven by a shared scrub `Clock`.
  *(trace: view.md §3, §5, §6; conventions.md §4)*
- **RM-P1-VIEW-05** — **Package publish**: `@astro-mine/view` to the org's **private GitHub Packages**
  registry (never npmjs.com) + the Cesium asset-staging bin, tag-driven release. *(trace: view.md §3, §7, §12)*
- **RM-P1-VIEW-06** — **Retire the `frames/` mirror**: alias Core's **generated** `TimeScale`/
  `FrameClass` types from `units.schema.json` (`satisfies`-tied, so a schema change breaks the build)
  + run Core's units conformance vectors. *(trace: view.md §5, §3; refines `RM-P1-CORE-08`; RFC-0007)*

**Dependencies:** Worlds (tiles + `tiles_anchor`, `RM-P1-WORLDS-16`), Fleet (glTF geometry), Sim
(MCAP), Core (generated units types, `RM-P1-CORE-08`). **Exit criteria:** Studio embeds the globe +
asset preview and a Bench recording replays by digest, all from the published library. **Deferred → P2:**
the full ops viewer — live telemetry, OpenMCT dashboards, plan-&-assignment explanation, and the View
Gateway (`RM-P2-VIEW-01..06`).

---

← [Phase 0](phase-0-commons-seed.md) · [Roadmap index](README.md) · [Phase 2 →](phase-2-operations-bridge.md)
