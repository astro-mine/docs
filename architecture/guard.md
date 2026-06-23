# Astro-Mine-Guard — Technology Architecture

> Layer: **Autonomy & coordination** · Phase: **1** · **safety-critical** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> Runtime assurance: the verifiable shield that wraps any policy so hard constraints cannot be violated.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Guard` is the platform's **runtime assurance** layer. It wraps any decision producer —
a learned policy from [Learn](learn.md), a hierarchical planner from [Mind](mind.md), an allocation
from [Allocate](allocate.md), or a hand-written controller — and **guarantees that declared hard
constraints cannot be violated**, regardless of what the wrapped component proposes. It is the
component that makes a learned or planned policy *deployable* by supplying the assurance story that
learning otherwise lacks.

Concretely, Guard provides three cooperating capabilities, each enforcing the same declarative
safety specification:

- **Safety shields / filters** — sit between a policy's proposed action and actuation, and minimally
  modify (or replace) that action so the system provably stays inside a safe set (collision-free,
  above power floors, outside keep-out zones, within thermal/torque limits).
- **Runtime monitors** — continuously evaluate temporal-logic properties (STL/MTL) over the state
  and action streams, raising verdicts when a property is at risk or violated.
- **Fallback / safe-mode behaviors** — verified backup controllers and safe states that Guard hands
  control to when the shield cannot certify the primary action, when a monitor fires, or when comms
  or compute degrade.

**Explicitly out of scope.** Guard does **not** plan, learn, allocate, or optimize for performance —
those are [Mind](mind.md), [Learn](learn.md), and [Allocate](allocate.md). It does **not** implement
physics or terramechanics (it *consumes* reachability/dynamics models, it does not build them — see
[Sim](sim.md) / [Surrogate](surrogate.md)). It is **not** a general controller and is **not** a
certification authority for flight hardware (certification-grade flight assurance is partitioned out
per charter §2.2 / §10.5). Crucially, Guard **does not depend on the learned components it protects**:
its trusted core must be analyzable independently of any network it shields.

**Primary users:** autonomy and safety engineers, who declare constraints and wrap policies; and,
transitively, everyone who deploys a policy into [Sim](sim.md) training, [Studio](studio.md) trade
studies, or [Ops](ops.md) operations.

**Charter alignment:** §5.4 (Guard: "wrap any policy to make it deployable; provides the assurance
story that learned methods otherwise lack"); §8 ("verifiable runtime assurance for learned
multi-agent policies"); §9 ("verifiable safety of learned policies under latency" — guarantee learned
controllers cannot violate hard constraints in a domain with no recovery and seconds-to-minutes of
delay, *without neutering performance*). Roadmap Phase 1 (§11).

**Deep-space, one-shot assurance (RFC-0001).** Under multi-regime missions, Guard's remit extends to
**deep-space, one-shot, window-gated** events — proximity ops, landing/anchoring, and maneuvers that
are *no-recovery* under tens-of-minutes light-time latency (from [Link](link.md)). Guard's existing
discipline carries directly: it remains independent of the policies it protects and fail-safe, and its
verdicts/clearance still gate actuation through [Ops](ops.md)→[Bridge](bridge.md). The per-phase
[mission model](mission-model.md) means the **assurance posture is set per regime** (a different
`SafetySpec` profile, shield set, and margins for each phase), not once per mission. This is a Phase-3
extension; the only Phase-1 obligation is that nothing in the core design precludes it.

---

## 2. Architecture principles

1. **Minimal trusted computing base (TCB).** The set of code that *must be correct* for the safety
   guarantee to hold is kept as small, simple, and auditable as possible. Performance optimizers,
   learned models, and convenience features live **outside** the TCB. If a feature is not required
   for the guarantee, it does not go in the shield core.
2. **Independence from the protected component.** Guard never imports, calls, or trusts the policy it
   shields beyond reading its *proposed action*. The guarantee derives from Guard's own model of the
   constraints and dynamics — never from the policy's internals. A compromised or pathological policy
   degrades performance, never safety (this is the simplex/runtime-assurance discipline).
3. **Deterministic and verifiable.** The shield core is deterministic given inputs and produces an
   auditable verdict. Favor **Rust** for the high-assurance core (conventions.md §2) for memory
   safety, predictable execution, and a tractable proof/analysis surface; no nondeterministic data
   structures, no unbounded allocation, no GC on the safety path.
4. **Fail safe, never fail open.** Any uncertainty — an infeasible filter, a missed deadline, a stale
   model, lost comms, a monitor fault — resolves to a *verified safe action* (brake, hold, retreat to
   a safe state), never to "pass the policy's action through unchecked." Absence of a positive safety
   certificate is treated as unsafe.
5. **Constraints are declared, not coded.** Hard constraints are authored declaratively in a
   versioned **safety-spec** schema (collision, keep-out, power floor, thermal/torque, velocity,
   temporal properties) and compiled into monitors and shields. The same spec drives design-time
   training, sim validation, and operations, so "what is safe" is reviewed once and reused everywhere
   (conventions.md §1, contribute-once-use-everywhere).
6. **Bounded latency, bounded resources.** Every shield/monitor has a hard per-tick deadline and a
   static worst-case resource bound. The safety path must complete within the control period even on
   the edge controller; if it cannot, the fallback is invoked. No best-effort behavior on the safety
   path.
7. **Layered, defense-in-depth assurance.** No single technique is trusted to cover all constraints.
   Guard composes runtime monitors (detect), reachability/CBF filters (correct), and a
   simplex backup controller (recover). A property uncovered by a fast filter is still caught by a
   monitor or the backup.
8. **Latency- and comms-aware by construction.** Multi-agent guarantees are computed against
   *worst-case* information staleness, not the optimistic case. When neighbor state is delayed or
   absent, the safe set shrinks conservatively rather than the guarantee being silently dropped
   (charter §9; conventions.md §8 graceful degradation).
9. **Honest, auditable verdicts.** Every intervention (modify, override, fall back, veto) is logged
   with the spec clause invoked, the inputs, and the certificate, so operators and post-hoc analysis
   can trust *why* Guard acted (conventions.md §10).

---

## 3. Application architecture

Guard is consumed primarily **as a library that wraps a [Core](core.md) Policy/Planner**, and
secondarily as a co-located sidecar service alongside a controller. Its modules:

```
astro_mine.guard
├── spec/            # Safety-spec schema, parser, validator; constraint compiler
├── monitors/        # Runtime verification: STL/MTL monitors, predicate evaluators, fault detectors
├── shields/         # Action filters: CBF-QP, HJ-reachability filter, model-predictive shielding
├── backup/          # Simplex architecture: verified backup controllers & safe-state library
├── arbiter/         # Decision core (TCB): combines monitor verdicts + filter + backup → safe action
├── models/          # Constraint/dynamics adapters: reachable sets, barrier fns, keep-out, budgets
├── coord/           # Multi-agent / latency-aware shielding: responsibility partitioning, staleness
├── wrap/            # PolicyShield adapter implementing the Core Policy/Planner API
└── audit/           # Verdict logging, certificates, telemetry emission (OTel/MCAP)
```

A two-tier split is deliberate: the **Rust safety core** (`arbiter`, `shields`, `monitors`,
`backup`, the `spec` evaluator) is the small, verifiable TCB; the **Python orchestration layer**
(`wrap`, `models` authoring, `coord` configuration, `audit` plumbing) provides ergonomics and
integration but is **not** trusted for the guarantee. The Python surface calls the Rust core over a
stable FFI / in-process binding (PyO3); on the edge the Rust core can run with no Python at all.

### Key abstractions exposed

- **Safety specification (`SafetySpec`)** — a declarative, versioned document of *hard* constraints:
  geometric keep-out volumes and collision pairs, power/energy floors, thermal and torque ceilings,
  kinematic limits, and **temporal-logic clauses** (STL/MTL) such as "battery SoC ≥ floor *until*
  charging window" or "always: distance to keep-out ≥ margin." Consumed by every Guard layer.
- **`PolicyShield`** — the headline abstraction. It *implements* the [Core](core.md) Policy/Planner
  API and *wraps* another Policy/Planner. From the rest of the platform's perspective a shielded
  policy is just a policy — `act(obs, ctx) -> action` — so any consumer ([Sim](sim.md), [Ops](ops.md),
  [Studio](studio.md)) can drop Guard in transparently (conventions.md §3 RL/policy contracts).
- **`Shield` / `Monitor` / `BackupController` interfaces** — plugin points; each filter, monitor, and
  backup controller is a Core-registered plugin (conventions.md §1 plugins-over-patches).
- **`SafetyVerdict`** — the auditable output of every tick: the certified action, whether/why an
  intervention occurred, the spec clause(s) invoked, the active layer, and a certificate handle.

### Key abstractions consumed

- The **[Core](core.md) Policy/Planner API** (the action it shields) and the **Environment API**
  (the observation/state it reads).
- **Constraint inputs** from siblings: keep-out volumes and terrain/slope limits from
  [Worlds](worlds.md); power, thermal, and torque budgets and articulation limits from
  [Fleet](fleet.md) SADF; comms-window and latency geometry from [Link](link.md); reachability and
  dynamics models / surrogates from [Sim](sim.md) / [Surrogate](surrogate.md).

### Extension points

New `Shield`s, `Monitor`s, and `BackupController`s are Core plugins discovered via the registry. New
constraint *kinds* extend the `SafetySpec` schema (an additive, RFC-gated change because the spec is
a safety contract). Reachability/barrier *models* are pluggable adapters so a body, robot, or process
can ship its own verified safe-set representation.

### Interaction patterns

In-process by default: `PolicyShield` wraps a policy and is called per control tick. In operations,
Guard runs as an **edge sidecar** co-located with each controller (sub-millisecond local call) so the
last line of defense never depends on a network round-trip. A **central Guard supervisor** aggregates
verdicts, manages multi-agent responsibility partitioning in `coord`, and surfaces fleet-level safety
state — but the per-agent local shield can enforce its agent's hard constraints autonomously even if
the supervisor is unreachable.

**Deep-space, one-shot assurance (RFC-0001).** In deep-space phases this hybrid tilts further toward
the edge: at tens-of-minutes light-time ([Link](link.md)) any ground-side or central supervisor is
**far off the critical path**, so the autonomous per-agent edge shield carries even more of the safety
story for no-recovery events. The active `SafetySpec`/shield profile is selected per phase from the
[mission model](mission-model.md)'s regime, so proximity, landing/anchoring, and maneuver phases each
run their own assurance posture.

---

## 4. Application programming & runtime platforms

- **Languages.** **Rust** for the safety core — monitors, shields, arbiter, backup, spec evaluator —
  per conventions.md §2 (high-assurance, memory-safe, deterministic, small TCB). **Python 3.11+** for
  the orchestration/authoring layer, the `PolicyShield` wrapper, and integration glue, so Guard's
  public API is reachable from Python (conventions.md §2 rule). **C++20** only where a shield must
  link a native solver in a hot inner loop (e.g., embedding a QP solver), behind a stable boundary.
- **Frameworks & libraries.**
  - *Runtime verification:* an STL/MTL monitoring engine. Recommended baseline: a Rust monitoring
    crate implementing robust-semantics STL/MTL (drawing on the RTAMT / MoonLight / Reelay lineage);
    online, incremental, bounded-memory evaluation.
  - *CBF shielding:* a quadratic-program (QP) safety filter — minimally perturb the proposed action
    subject to control-barrier-function constraints. Solver: **OSQP** (or Clarabel, Rust-native) for
    a small, fast, deterministic QP per tick. Aligns with [Allocate](allocate.md)'s optimization stack
    conceptually but is a separate, tiny, deterministic solve.
  - *Reachability filters:* Hamilton-Jacobi reachability safe sets precomputed offline (toolboxes such
    as `hj_reachability` / Level-Set / BEACLS) and looked up online; the online path is a fast,
    bounded value/gradient query, **not** an online PDE solve.
  - *Model-predictive shielding:* a short-horizon forward check that a safe recovery trajectory exists
    from the proposed next state, reusing [Sim](sim.md)/[Surrogate](surrogate.md) dynamics behind the
    `models` adapter.
  - *Backup controllers:* simple, analyzable verified controllers (e.g., proportional brake-to-stop,
    retreat-to-charging-pose, hold-attitude) — the simplex "safety controller."
  - *Spec & schema:* **JSON Schema + Pydantic v2** for authoring `SafetySpec`, with a canonical
    **Protobuf** wire form, exactly per conventions.md §3.
- **Runtime model.** Single-tick, deterministic, bounded-latency evaluation on the safety path. The
  Rust core runs with pre-allocated buffers (no allocation on the hot path), a fixed worst-case
  execution budget, and a watchdog that triggers the fallback on deadline miss. On the edge it runs as
  a small native binary; in cloud/sim it runs in-process under Python.
- **Build & packaging.** Python wheel `astro-mine-guard` (PyO3-built, bundling the Rust core); a
  standalone OCI image for the edge sidecar; the Rust core also published as a crate for embedding in
  constrained / flight-adjacent contexts (conventions.md §7, §2). SemVer; reproducible, pinned builds.

---

## 5. Data architecture

Guard is **stateless across runs** on the safety path — its guarantee derives from the spec and
models, not from accumulated history. It owns, produces, and consumes:

- **Owns:** the **`SafetySpec` schema** (versioned JSON Schema + Protobuf), the **`SafetyVerdict`**
  message schema, and the **safe-set / barrier model** interchange formats. These are registered in
  the [Core](core.md) message catalog (conventions.md §3); the `SafetySpec` schema is a *safety
  contract* and evolves only additively, RFC-gated.
- **Produces:** per-tick `SafetyVerdict` records and **intervention/certificate logs**. Verdict and
  telemetry streams are written to **MCAP** (timestamped, schema-tagged) per conventions.md §4/§5, so
  a shielded run's safety behavior is replayable channel-by-channel alongside [Sim](sim.md)/[Ops](ops.md)
  telemetry. Aggregate safety metrics land in **Parquet** for [Bench](bench.md) and analysis.
- **Consumes:** keep-out/terrain rasters and volumes from [Worlds](worlds.md) (COG/Zarr, in a planetary
  CRS — conventions.md §5; **no implicit Earth assumptions**); SADF power/thermal/torque budgets and
  geometry from [Fleet](fleet.md); comms-window/latency tables from [Link](link.md); and precomputed
  HJ reachability value functions / CBF parameters (N-D arrays in **Zarr/HDF5**, conventions.md §5).
- **Formats & schemas.** High-rate per-tick payloads (state in, action out, verdict) use the
  zero-copy **FlatBuffers/Cap'n Proto** encoding for hot-path messages (conventions.md §3) rather than
  Protobuf, to keep decode overhead negligible at swarm scale; everything non-hot-path is Protobuf.
- **Lifecycle, provenance & versioning.** Every verdict records the **spec version (content hash)**,
  the **model versions** (reachability sets, CBF params), the **Guard code version**, and the inputs'
  content hashes — so a safety claim is reproducible and a result can be tied to the exact constraints
  in force (conventions.md §5 provenance). Specs and safe-set models are **content-addressed** and
  published through [Hub](hub.md). Time and frames are SPICE-backed (conventions.md §5).

---

## 6. Integration architecture

Guard integrates **entirely through [Core](core.md)** contracts — it adds no private side-channels
(conventions.md §1).

- **Wrapping policies (the primary integration).** `PolicyShield` implements the [Core](core.md)
  Policy/Planner API and wraps the outputs of [Mind](mind.md), [Allocate](allocate.md), and learned
  policies from [Learn](learn.md). Because the wrapper *is* a Policy/Planner, it composes anywhere a
  policy is expected — no consumer needs Guard-specific code.
- **Position in both loops.** Guard sits **between policy and actuation** in:
  - the **design/training loop** — inside [Sim](sim.md), shielding policies during training and trade
    studies (so [Learn](learn.md) can train against the shield and [Studio](studio.md) can certify a
    candidate design as safe); and
  - the **operations loop** — between [Ops](ops.md)'s plan execution and [Bridge](bridge.md)'s
    hardware/flight-software adapters, so the same shield that validated a policy in sim is the one
    that protects it in the field (charter §6, "same components used in design… closing the loop in
    operations").
- **Constraint inputs.** Consumes keep-out volumes / terrain & slope limits from [Worlds](worlds.md);
  power-floor, thermal, torque, and kinematic limits from [Fleet](fleet.md) SADF; comms-window and
  latency geometry from [Link](link.md); reachability/dynamics models from [Sim](sim.md) /
  [Surrogate](surrogate.md).
- **Outputs / message flows.** `SafetyVerdict` and safety telemetry are surfaced to [Ops](ops.md)
  (operator awareness, replan triggers) and [View](view.md) (safety overlays, intervention timelines,
  plan explanations). A monitor firing or a sustained fallback is an **event** on the async plane
  (NATS/JetStream, conventions.md §4) that [Ops](ops.md) consumes to trigger replanning back through
  [Mind](mind.md)/[Allocate](allocate.md).
- **Protocols.** In-process library calls on the hot path; **gRPC** for the central Guard
  supervisor's service surface; events over **NATS/JetStream**; the real-time operations data plane
  reaches Guard via [Bridge](bridge.md) over **ROS 2/DDS** (conventions.md §4).
- **Benchmarking.** [Bench](bench.md) treats "safety violations per scenario" and "performance cost of
  shielding" as first-class scored metrics; Guard exposes its verdict stream for reproducible scoring.

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7), all three of which Guard must serve:
  1. **Local/dev & cloud sim/training** — Guard runs **in-process** inside [Sim](sim.md) workers
     (the Rust core called from Python). At training scale it fans out with the sim across **Ray/K8s**;
     it is stateless and adds bounded per-tick overhead.
  2. **Operations / ground** — Guard runs as an **edge sidecar** co-located with each controller (one
     small OCI container or embedded binary per agent), plus a **central Guard supervisor** Deployment
     for fleet-level coordination and verdict aggregation, near operators with the ROS 2/DDS plane.
  3. **Flight-adjacent (Phase 3, mostly out of open scope)** — the Rust core is embeddable as a crate
     in constrained environments behind [Bridge](bridge.md) adapters (cFS/F´); this is where the
     small-TCB, no-Python, no-allocation discipline pays off.
- **Compute.** The safety core is **CPU-only and lightweight** by design — small QP/monitor/lookup per
  tick, no GPU on the safety path. (Offline HJ-reachability *precomputation* can use GPU, but that is a
  design-time job, not a runtime dependency.) Memory footprint is small and statically bounded so it
  fits an edge controller alongside the primary autonomy.
- **Containerization & orchestration.** OCI image for the sidecar; Helm-deployed central supervisor on
  **Kubernetes**; in sim, co-scheduled with workers under **Ray/KubeRay** (conventions.md §7).
- **Scaling.** Per-agent shields scale linearly with fleet size (each agent carries its own local
  shield — there is no central bottleneck on the safety path). The central supervisor scales
  horizontally and is *not* on the critical safety path, so its unavailability degrades coordination
  optimality, never per-agent hard-constraint enforcement.

---

## 8. Performance & scalability

- **Targets.** The shield/monitor evaluation MUST fit inside the controller's tick budget on edge
  hardware — design target **≤ ~1 ms** for the CBF-QP + monitor path on a single agent, with a hard
  worst-case bound enforced by a watchdog. Overhead added to a [Sim](sim.md) step at training scale is
  budgeted to a small, measured fraction of the step cost.
- **Bottlenecks.** (1) The per-tick QP / reachability query; (2) multi-agent coupling, where the safe
  set depends on neighbor state; (3) staleness of neighbor information under comms delay.
- **Mitigations.**
  - *QP/query speed:* small, warm-started, deterministic solves (OSQP/Clarabel); HJ reachability is a
    table/value lookup at runtime, with the expensive PDE solve done **offline**; pre-allocated
    buffers and no hot-path allocation in the Rust core.
  - *Multi-agent coupling:* **responsibility partitioning** — decompose pairwise safety so each agent
    is responsible for its own half of a separation constraint, turning a joint problem into
    per-agent local solves (decentralized CBFs / reciprocal collision avoidance).
  - *Latency:* compute safe sets against **worst-case staleness** — pad margins by the maximum possible
    state drift over the comms delay window from [Link](link.md). The guarantee holds against the
    delayed-information adversary rather than assuming fresh state (charter §9).
- **Graceful degradation (conventions.md §8).** As comms degrade, margins grow and the reachable
  free-action set shrinks **conservatively**; in the limit Guard falls back to a verified safe state
  (hold/brake/retreat) rather than collapsing. Back-pressure on verdict/telemetry streams never blocks
  the safety path — telemetry is best-effort, the shield is not.
- **Measure before optimizing (conventions.md §8).** Guard ships representative benchmarks: shield
  latency distributions, intervention rates, and the *performance cost of shielding* (return with vs.
  without the shield) so the "without neutering performance" claim (charter §9) is reproducible.

---

## 9. Security, safety & compliance

This is Guard's central concern. Guard is a **safety-critical** component (conventions.md §9): the
correctness of its guarantee is the whole point of the package.

### 9.1 The safety guarantee and its trust model

- **Independence is the guarantee.** The hard-constraint guarantee derives **only** from the
  `SafetySpec`, the constraint/reachability models, and the verified backup controller — never from
  the wrapped policy. A learned policy is treated as an **untrusted, adversarial input** that proposes
  an action; Guard's job is to certify or correct it. Therefore a buggy, mistrained, or maliciously
  crafted policy can degrade mission performance but **cannot cause a hard-constraint violation**.
  This is what lets a learned controller be deployable in a no-recovery domain (charter §8, §9).
- **Minimal trusted computing base.** Only the Rust safety core (`arbiter`, `shields`, `monitors`,
  `backup`, `spec` evaluator) is trusted. It is small, deterministic, allocation-free on the hot path,
  and isolated from the Python orchestration and from the policy. The TCB's smallness is what makes
  the guarantee *analyzable* — the explicit answer to charter §8's "verifiable runtime assurance."
- **Fail-safe default.** No positive safety certificate ⇒ unsafe ⇒ fallback. Infeasible QP, stale
  model, missed deadline, monitor fault, lost neighbor state, or watchdog timeout all resolve to a
  verified safe action. Guard never fails open.

### 9.2 Layered assurance (defense in depth)

Guard composes complementary techniques because none alone is sufficient (charter §9):

1. **Runtime monitors (detect).** STL/MTL monitors evaluate temporal-logic properties online with
   robust semantics — including *predictive* monitoring that flags a property *about to* be violated
   in time to act, which matters under latency.
2. **Reachability/CBF filters (correct).** A CBF-QP minimally perturbs the proposed action to keep the
   state inside the safe set; an HJ-reachability filter provides the formally-backed safe set for
   nonlinear dynamics where a hand-designed barrier is hard. The filter *modifies* the action.
3. **Simplex backup (recover).** A verified backup controller and a library of safe states; when the
   filter cannot certify the next state, the **arbiter** switches control to the backup — the simplex
   architecture's "if uncertain, use the trusted simple controller."

The `arbiter` is the small decision core that combines monitor verdicts, the filter result, and backup
availability into a single certified action each tick, with a strict precedence: a fired hard-constraint
monitor or an infeasible/uncertifiable filter forces the backup.

### 9.3 Formal specification and verification

- Hard constraints are specified **formally and declaratively** in the `SafetySpec` (temporal logic +
  geometric/budget predicates), reviewed as a safety artifact, and **compiled** into monitors and
  shields — so the property that is enforced is exactly the property that was reviewed.
- The Rust safety core is validated with property-based testing (**proptest**, the Rust analogue of
  Hypothesis), seeded golden/determinism tests, and — for the smallest critical kernels — amenability
  to formal analysis (model checking / Kani-style verification) is a stated design goal of keeping the
  TCB tiny. Backup controllers carry explicit invariant proofs/arguments.

### 9.4 Latency and multi-agent safety

- Multi-agent guarantees are computed against **worst-case information staleness** from
  [Link](link.md), with **responsibility partitioning** so each agent enforces its share of a coupled
  constraint locally (§8). Under comms loss, agents fall back to conservative margins and, if needed,
  safe states — degrade, never collapse (charter §9; conventions.md §8). This is the explicit answer
  to charter §9's "verifiable safety… under latency."
- **Deep-space, one-shot assurance (RFC-0001).** Multi-regime missions push this regime to its
  extreme: at tens-of-minutes light-time ([Link](link.md)), worst-case-staleness margins grow
  accordingly and the **autonomous per-agent edge shield carries even more of the safety story**,
  because the central supervisor is off the critical path by light-time. Proximity ops,
  landing/anchoring, and maneuvers are **no-recovery, window-gated events** with no second attempt, so
  the certify-or-fall-safe verdict is the last line of defense; the per-phase posture
  ([mission model](mission-model.md)) lets each such phase carry its own margins and backup behaviors.

### 9.5 Conventional security & supply chain (conventions.md §9)

- **AuthN/AuthZ.** The central Guard supervisor and verdict APIs sit behind **OIDC** with **RBAC via
  OPA**; **mTLS** for service-to-service. Editing a `SafetySpec` in operations is a privileged,
  audited action.
- **Spec & model integrity.** `SafetySpec` documents and safe-set models are **content-addressed and
  signed (Sigstore/cosign)**; Guard **refuses to load an unsigned or tampered spec/model** — the
  shield's correctness depends on its inputs, so their integrity is part of the safety case.
- **Supply chain.** Signed artifacts, **SLSA** provenance, **SBOM** (Syft/CycloneDX); reproducible
  pinned builds; org defaults (Dependabot, secret scanning, push protection, read-only Actions).
- **Plugin isolation.** Third-party shields/monitors/backups are Core plugins; untrusted or non-Rust
  plugins run **out-of-process / sandboxed** (gVisor/WASM, conventions.md §9) and are **never** placed
  inside the TCB. A plugin can *propose* but only the trusted arbiter *certifies*.

### 9.6 Export control & dual use (conventions.md §12, charter §10.5)

- Generic safety-shielding mechanisms (CBF/HJ/monitoring against declared abstract constraints) are
  **default-open** science. Genuinely sensitive material — e.g., specific operational keep-out
  geometries, hardware-specific certified flight backup controllers, certification-grade flight
  assurance — is **partitioned** into access-controlled repos and gated via [Core](core.md) capability
  tags + OPA at load time. Guard documents an explicit EAR/ITAR posture per
  `astro-mine/.github` EXPORT_CONTROL.md, alongside [Bridge](bridge.md) and [Ops](ops.md). Open does
  not mean naive.

---

## 10. Observability & operability

- **Telemetry.** OpenTelemetry traces/metrics/logs (conventions.md §10). Key metrics: per-tick shield
  latency (with worst-case), intervention rate, fallback activations, monitor robustness margins,
  time-to-violation predictions, and the shielding performance cost. Structured JSON logs to **Loki**;
  metrics to **Prometheus/Grafana**; high-rate verdict streams to **MCAP** for replay.
- **Traceability.** A replan in [Ops](ops.md) is traceable through [Mind](mind.md)/[Allocate](allocate.md)/Guard
  (conventions.md §10): each verdict links the spec clause, inputs (content hashes), active layer, and
  the resulting action, so an operator (via [View](view.md)) can see *exactly why* Guard intervened.
- **Testing & validation (conventions.md §11).** Unit/property tests (`proptest`/Hypothesis) for
  monitor and filter invariants; **adversarial/falsification testing** — search for policy actions and
  disturbances that try to drive a violation and confirm the shield prevents them (the central
  validation strategy for an assurance component); seeded golden/determinism gates (CI fails on
  non-reproducibility); and consumer-driven **contract tests** proving Guard honors the [Core](core.md)
  Policy/Planner interface versions it claims. Reachability/CBF safe sets are regression-checked
  against [Sim](sim.md) ground-truth dynamics with explicit error budgets.
- **Health.** Standard liveness/readiness for the supervisor; the edge shield exposes a heartbeat and a
  watchdog whose expiry *is* a safe-mode trigger, not merely an alert.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Shielding/assurance method | CBF-QP filter; HJ-reachability filter; model-predictive shielding; simplex + verified backup; STL/MTL runtime monitors | **Layered combination**: STL/MTL monitors (detect) + CBF-QP / HJ-reachability filter (correct) + simplex backup (recover). No single method covers all constraints; charter §9 calls for verifiable, performant assurance, which only defense-in-depth delivers. |
| Where Guard runs | Edge, co-located per controller; centralized; hybrid | **Hybrid**: an autonomous **per-agent edge shield** owns hard-constraint enforcement (never network-dependent); a **central supervisor** (off the critical path) handles coordination and aggregation. |
| Implementation language / assurance level | Pure Python; pure Rust; Rust core + Python orchestration | **Rust verified core + Python orchestration** (conventions.md §2): tiny deterministic TCB for the guarantee, ergonomic Python wrapper for integration. |
| Constraint specification | Constraints in code; declarative safety-spec DSL/schema | **Declarative `SafetySpec`** (JSON Schema + Pydantic + Protobuf wire, conventions.md §3) compiled to monitors/shields — review the property once, enforce it everywhere; code is too easy to get subtly wrong for a safety contract. |
| Multi-agent latency handling | Assume fresh state; worst-case staleness margins + responsibility partitioning; central arbitration | **Worst-case staleness margins + decentralized responsibility partitioning** — guarantees hold against the delayed-information adversary and degrade gracefully (charter §9). |
| QP / reachability runtime | Online PDE/optimization; offline precompute + online lookup/solve | **Offline precompute (HJ value functions) + small online QP** (OSQP/Clarabel) — keeps the safety path within the tick budget. |
| Hot-path message encoding | Protobuf; FlatBuffers/Cap'n Proto | **FlatBuffers/Cap'n Proto** for per-tick state/action/verdict (conventions.md §3); Protobuf for everything else. |
| STL/MTL monitor engine | RTAMT; MoonLight; Reelay; custom Rust | **Rust monitor in the TCB** (RTAMT/MoonLight/Reelay-inspired), online robust semantics, bounded memory. |

**Open questions / research dependencies:**

- How to bound performance loss from shielding so it stays "without neutering performance" (charter §9)
  across diverse policies — co-designed with [Learn](learn.md) and scored by [Bench](bench.md).
- Compositional multi-agent guarantees: do per-agent responsibility-partitioned guarantees compose into
  a fleet-level guarantee under realistic [Link](link.md) latency models? (charter §8 open problem.)
- Where reachability sets / barriers come from for the hardest dynamics (granular excavation contact) —
  depends on [Sim](sim.md)/[Surrogate](surrogate.md) producing trustworthy, error-bounded models.
- How much of the TCB can be brought under machine-checked formal verification (Kani/model checking)
  while keeping it practical to evolve.
- **Deep-space, one-shot assurance (RFC-0001).** How to size worst-case-staleness margins and
  certify *single-shot, no-recovery* events (proximity ops, landing/anchoring, maneuvers) at
  tens-of-minutes light-time ([Link](link.md)), and how to author and validate **per-phase**
  `SafetySpec` profiles for the [mission model](mission-model.md)'s regimes — co-designed with
  [Mind](mind.md) and [Ops](ops.md). (Phase 3.)

---

## 12. Roadmap alignment

- **Phase 1 (this component).** Ship Guard alongside [Mind](mind.md), [Learn](learn.md),
  [Allocate](allocate.md), and [Studio](studio.md) (charter §11). **MVP:** the `SafetySpec` schema, the
  Rust safety core (CBF-QP shield + STL/MTL monitors + a simplex backup + arbiter), and the
  `PolicyShield` wrapper over the [Core](core.md) Policy/Planner API — enough to wrap a
  [Learn](learn.md) policy and run it shielded in [Sim](sim.md), with violations and shielding cost
  scored by [Bench](bench.md). This delivers the assurance story that makes Phase-1 learned methods
  publishable to [Hub](hub.md) and credible on the leaderboard.
- **Later in Phase 1 / Phase 2.** Multi-agent latency-aware shielding (`coord`); HJ-reachability
  filters for harder dynamics; the edge-sidecar deployment and central supervisor for [Ops](ops.md);
  verdict overlays in [View](view.md). The same shield that validated a policy in sim becomes the one
  that protects it in operations (charter §6) as Astro-Mine crosses the sim-to-operations threshold.
- **Phase 3 (mostly out of open scope).** The embeddable Rust core behind [Bridge](bridge.md)
  flight-software adapters; certification-grade flight assurance remains **partitioned and
  access-controlled**, not part of the open core (charter §2.2, §10.5).
- **Phase 3 — multi-regime assurance ([RFC-0001](../rfc/0001-multi-regime-missions.md)).** Per-phase
  assurance posture and deep-space, one-shot, window-gated shielding land in Phase 3; no Core schema
  hooks are reserved in Phase 1, since Guard consumes the [mission model](mission-model.md)'s `regime`
  / `PhaseTransition` contract rather than defining it.
