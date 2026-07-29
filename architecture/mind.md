# Astro-Mine-Mind — Technology Architecture

> Layer: **Autonomy & coordination** · Phase: **1** · Ships in: [`astro-mine-platform`](platform.md) · Extended for multi-regime missions (Phase 3)
> The hierarchical autonomy framework: mission planner → per-agent task-and-motion
> planner → local controller, composed from pluggable, swappable layers.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Mind` is the **autonomy composition framework** — the package that decides *how the
swarm decides and acts*. It does not invent one monolithic planner; it provides the **hierarchy,
the wiring, and the execution machinery** that turn a stated objective into actuator-level
commands across tens to hundreds of heterogeneous robots. The hierarchy has three tiers:

- a **mission planner** assigns roles and regions to agents and groups (the strategic tier);
- per-agent **task-and-motion planners (TAMP)** turn a role into a concrete sequence of
  parameterized actions and feasible motions (the tactical tier);
- **local controllers** execute those actions in closed loop against the environment (the
  reactive tier).

**Behavior trees and pluggable planners run throughout.** Every tier is an implementation of the
Policy/Planner contract that [Core](core.md) owns, so any layer can be swapped — a new global
planner, a learned TAMP backend, a different controller — **without rewriting the rest**. Mind is
the substrate where the genuine novelty of §5.4 is *composed*; the novel pieces themselves (the
allocator, the learned policies, the safety shield) live in sibling packages and plug in here.

**What Mind explicitly does NOT do:**

- It **does not own the Policy/Planner API.** [Core](core.md) defines the interfaces, message
  schemas, and composition contracts; Mind *implements and orchestrates* them. Mind never adds a
  private side-channel that bypasses Core (conventions.md §1).
- It **does not solve the combinatorial assignment problem itself.** The mission tier *delegates*
  heterogeneous task allocation and scheduling to [Allocate](allocate.md), the specialist engine.
- It **does not train policies.** Learned controllers and learned planner backends come from
  [Learn](learn.md) as portable artifacts; Mind only *embeds and invokes* them.
- It **does not provide safety guarantees.** Every action Mind emits is wrapped by
  [Guard](guard.md) before actuation; Mind treats Guard as a mandatory output filter, not an
  optional add-on.
- It **does not simulate, render, or command hardware.** It runs against the Environment API
  exposed by [Sim](sim.md) (design/training) or by [Ops](ops.md)/[Bridge](bridge.md) (operations).

**Primary users:** autonomy researchers (who author and benchmark new planner/controller layers)
and mission designers (who compose an autonomy stack for a campaign in [Studio](studio.md)).

**Charter alignment:** §5.4 (hierarchical autonomy framework — "where the genuine novelty
lives"), §6 (the design/training and operations loops both route replanning "back through
Astro-Mine-Mind"), §8 (cooperation under partial observability and intermittent/delayed comms),
§9 (robust coordination, "degrade gracefully rather than collapse"; verifiable safety of learned
policies under latency).

**Multi-regime, window-gated planning.** Mind extends the same three-tier hierarchy to
compose plans *across* mission **Phases/Regimes** ([mission-model](mission-model.md)) rather than
within a single surface campaign. Each Phase carries its own dynamics, comms, latency, and autonomy
posture, so Mind composes a per-phase decision stack and stitches them across `PhaseTransition`
handoffs. This is additive: a single-`surface`-phase mission is exactly today's campaign, so nothing
already built changes. The division of labour is deliberate: cross-phase replanning *policy* (phase
ordering, contingencies) is set in [Studio](studio.md) (design) and [Ops](ops.md) (operations);
Mind composes the per-phase stacks and honors the schedule it is given. The deep-space phases
demand a stronger delay-tolerant posture (tens-of-minutes light-time), reinforcing principle 5.

---

## 2. Architecture principles

1. **Compose, don't centralize.** Mind's value is the *wiring* between tiers, not a giant solver.
   Each tier is a thin orchestrator over a pluggable backend; the framework's job is to make
   heterogeneous backends interoperate through stable contracts, not to be smart itself.
2. **Every layer is a Core plugin.** Mission planners, TAMP backends, and controllers all
   implement the [Core](core.md) Policy/Planner interface and ship with a plugin manifest. "Add a
   new global planner" means writing a package and registering a manifest — never patching Mind
   (conventions.md §1, §7; charter §9.2).
3. **Hierarchy is the contract; the tiers are negotiable.** The mission → TAMP → control
   decomposition is the durable abstraction. Within it, a researcher MAY collapse tiers (a single
   end-to-end learned policy), insert tiers, or replace the representation (BT vs HTN vs FSM) so
   long as the inter-tier message schemas hold.
4. **Degrade, don't collapse.** Every tier has an explicit fallback path that is reachable with
   **stale or no fresh input** from the tier above. Loss of comms must downgrade autonomy
   gracefully — agents fall back to cached roles and conservative local behaviors, never to
   undefined behavior (charter §7/§9; conventions.md §8).
5. **Delay-tolerant by construction.** Plans carry validity horizons, assumptions, and
   contingency branches so an agent can act correctly on a *minutes-old* plan and reconcile when
   comms return. Decisions are time-stamped and idempotent; no tier assumes synchronous,
   reliable, low-latency exchange.
6. **Uncertainty- and partial-observability-first.** Tiers consume belief states (with explicit
   uncertainty, conventions.md §1.6), not point estimates, and can choose *information-gathering*
   actions (active perception) when belief is poor — directly serving the resource-uncertainty
   research problem (charter §7).
7. **Guard-wrapped output is the only output.** Mind never emits an action that has not passed
   through the [Guard](guard.md) shield. The safety boundary is architectural, not a convention a
   plugin author can forget.
8. **Same framework in design and ops.** The identical Mind stack runs offline against
   [Sim](sim.md) for training/validation and online inside [Ops](ops.md) for replanning. There is
   no separate "operations planner" to drift out of sync with the validated design (charter §5).
9. **Determinism on demand.** Given a seed, a pinned plugin set, and fixed inputs, a Mind stack
   produces identical decisions, so a [Bench](bench.md) result or an [Ops](ops.md) replan is
   reproducible and auditable (conventions.md §1.5, §11).

---

## 3. Application architecture

Mind is **library-first** (conventions.md §1.4): a researcher imports it, assembles a stack from
plugins, and runs it against a [Sim](sim.md) environment on one workstation. The same stack is
then deployed as a service inside [Ops](ops.md). Internal modules:

```
astro_mine.mind
├── mission/         # Mission-tier orchestrator: role/region assignment, group plans, contingencies
│   ├── planner/     #   pluggable mission-planner backends (PDDL/temporal, HTN, learned, scripted)
│   └── allocate/    #   thin adapter that delegates assignment to Astro-Mine-Allocate
├── tamp/            # Task-and-motion tier: per-agent symbolic+geometric planning
│   ├── task/        #   symbolic action planning (PDDL/temporal/HTN backends)
│   └── motion/      #   sampling-based & optimization-based motion planners (OMPL, TrajOpt)
├── control/         # Local-controller tier: closed-loop execution backends
│   └── policy/      #   learned-policy adapter (ONNX Runtime) + classical controllers (MPC/PID)
├── bt/              # Behavior-tree engine: execution glue across tiers (pure-Python Groot-v4 XML)
├── compose/         # The composer: builds/validates a hierarchy graph from a stack spec
├── exec/            # The executive: ticking, plan-validity tracking, replan triggers, fallbacks
├── belief/          # Belief-state assembly: fuses observations + comms state into tier inputs
├── coord/           # Decentralized coordination: gossip, consensus, conflict resolution
├── guardrail/       # Mandatory Guard binding: wraps every emitted action before it leaves Mind
└── registry/        # Discovery of planner/controller/BT plugins via the Core manifest
```

### Key abstractions exposed

- **Stack spec** — a declarative description (YAML, JSON-Schema-validated; conventions.md §3) of
  an autonomy stack: which plugin fills each tier, how they wire, fallback policies, replan
  triggers, and validity horizons. This is what [Studio](studio.md) authors and what
  [Bench](bench.md) pins. The composer turns a stack spec into a runnable, validated hierarchy.
- **Planner/Controller plugin** — any object implementing the [Core](core.md) Policy/Planner
  sub-interface for its tier (`MissionPlanner`, `TaskMotionPlanner`, `Controller`). The framework
  invokes it through that contract only; it never reaches inside.
- **Behavior tree** — the execution representation that sequences and guards actions within and
  across tiers. BT nodes can be *planner-invoking* (call a TAMP backend), *policy-invoking* (run
  an ONNX controller), or *primitive* (an SADF-declared action), giving a uniform reactive
  scaffold with explicit fallbacks (selector/decorator nodes ⇒ graceful degradation).
- **Plan + ContingentPlan** — a time-stamped, validity-horizoned artifact with assumptions and
  branch points, designed to be acted on while stale and reconciled on comms recovery.
- **Belief view** — the partial-observability-aware input each tier consumes: estimated state
  plus uncertainty plus comms/observation masks, assembled from the Environment API observation.

### Extension / plugin points

- **Mission-planner backend** (PDDL/temporal, HTN, learned, scripted) — pluggable.
- **TAMP task backend** and **TAMP motion backend** — independently pluggable (e.g., a learned
  task planner over an OMPL motion planner).
- **Controller backend** — classical (MPC/PID) or learned (ONNX), pluggable per asset class.
- **BT node libraries** — domain-specific actions/conditions as registered node packages.
- **Coordination strategy** — centralized, decentralized (gossip/consensus), or hybrid, selected
  per stack and per comms regime.

All discovered through the [Core](core.md) plugin registry; in-process via Python entry points,
or out-of-process (gRPC + sandbox) for untrusted/non-Python planners (conventions.md §7).

### Interaction patterns

The **executive** (`exec/`) ticks the active behavior tree. On each tick it (1) refreshes the
**belief view** from the Environment API observation; (2) checks **plan validity** and replan
triggers; (3) if the mission tier must re-decide, calls the mission planner, which delegates
assignment to [Allocate](allocate.md); (4) hands resulting roles to per-agent **TAMP**, which
produces actions + feasible motions; (5) the **control** tier closes the loop; (6) **every**
candidate action passes through `guardrail/` ([Guard](guard.md)) before it is returned as the
Environment API action. Under comms loss, `coord/` and the BT fallback branches keep agents
acting on cached plans (principle 4).

**Multi-regime composition.** Across a multi-phase mission the executive composes one
decision stack *per Phase*, reading the active phase's `regime` from the Environment API and
selecting the coordination strategy, fallback policy, and validity horizons appropriate to it
(e.g., a delay-tolerant supervisory stack for `interplanetary_transit`, a reactive surface stack
for `surface`). Hard **orbital-mechanics deadlines** — launch / transfer / return windows carried
on the `ManeuverBudget`s from [Trajectory](trajectory.md) — become first-class plan constraints
and replan triggers: a phase plan is invalid if it would miss its window. The joint
**asset↔target↔window↔trajectory** assignment is *not* solved in Mind; the mission tier hands it to
[Allocate](allocate.md) and consumes the returned trajectory feasibility / Δv as constraints
(see §6).

---

## 4. Application programming & runtime platforms

- **Languages:** **Python 3.12+** for the framework, orchestration, composition, and most planner
  glue (conventions.md §2), including the **pure-Python** behavior-tree engine. **C++20** enters only
  behind Python bindings for the native motion-planning libraries (OMPL, Drake, FCL). **Rust** is
  optional and reserved for the deterministic executive
  core where it abuts the [Guard](guard.md) boundary, if profiling justifies it.
- **Planning frameworks:**
  - *Behavior trees:* a **pure-Python** execution engine for the **Groot v4 XML dialect**
    (BehaviorTree.CPP's authoring format, charter §6) — parse / validate / round-trip plus a
    deterministic reactive tick engine. The native **BehaviorTree.CPP**/pybind11 runtime is
    deliberately **not** vendored: no Python binding is distributed, and a CMake+pybind11 build would
    breach the tier-1 local-install rule (conventions.md §7) for no gain over the XML dialect the
    engine already round-trips (astro-mine-mind#17).
  - *Symbolic / temporal planning:* PDDL2.1+ via the **unified-planning** library (a backend-
    agnostic façade over **Fast Downward**, **OPTIC**, **ENHSP**, etc.); HTN via **pyhop/SHOP**-
    style backends. These satisfy the "temporal/PDDL planners" requirement (charter §6).
  - *Task-and-motion planning:* a TAMP layer in the style of **PDDLStream** that interleaves the
    symbolic backend above with motion feasibility checks.
  - *Motion planning:* **OMPL** (sampling-based: RRT*, PRM*, BIT*) and optimization-based
    trajectory planners (Drake/TrajOpt); collision via **FCL**.
- **Learned components:** learned planners/controllers are invoked through **ONNX Runtime**
  (conventions.md §6) — the portable artifact format from [Learn](learn.md). Mind hosts inference,
  not training.
- **Solver delegation:** the mission tier calls [Allocate](allocate.md) (CP-SAT/OR-Tools + learned
  heuristics) over gRPC or in-process; Mind does not embed its own MILP/CP solver.
- **Runtime model:** an **event-driven executive loop** with a fixed maximum tick rate, bounded
  queues, and back-pressure (conventions.md §8). Library-first; the same code runs as a long-lived
  gRPC service in [Ops](ops.md) (one Mind instance per agent or per agent-group, plus a mission-
  tier coordinator).
- **Build/packaging:** ships in the [`astro-mine-platform`](platform.md) wheel (the behavior-tree
  engine is pure Python, no native build); the optional native planner deps (OMPL, FCL) sit behind
  `mind-*` extras and are vendored into the OCI image for the ops service (conventions.md §7.1).
  Declares the [Core](core.md) Policy/Planner interface major versions it supports
  (conventions.md §13).

---

## 5. Data architecture

Mind is compute-heavy and **owns little persistent data**; its artifacts are decisions and plan
provenance. It **produces, consumes, and stores** the following.

| Data | Role | Format / store |
|---|---|---|
| **Stack spec** | owned, authored | YAML + JSON Schema (conventions.md §3); content-addressed when pinned by [Bench](bench.md)/[Studio](studio.md) |
| **Behavior trees** | owned, authored | Groot-compatible BT XML; versioned with the stack |
| **PDDL domain/problem files** | produced/consumed | PDDL text; problem files generated per replan from belief state |
| **Plan / ContingentPlan** | produced | Canonical Protobuf message (a Core message schema), with validity horizon + assumptions + provenance |
| **Decision trace** | produced | **MCAP** stream of tier decisions, plan revisions, replan triggers, fallbacks (conventions.md §4) — replayable in [View](view.md) |
| **Belief view** | consumed | from the Environment API observation (Core message); uncertainty-tagged |
| **Asset capability declarations** | consumed | **SADF** from [Fleet](fleet.md) — what each asset *can* do bounds the action space |
| **Comms constraints** | consumed | from [Link](link.md) — line-of-sight/latency/bandwidth/Earth-link windows that gate coordination and set plan validity horizons |
| **Learned policy artifacts** | consumed | **ONNX** from [Learn](learn.md), referenced by content hash via [Hub](hub.md) |
| **Allocation results** | consumed | Arrow/Protobuf assignment messages from [Allocate](allocate.md) |

**Schemas:** the inter-tier vocabulary (Plan, Role, Action, BeliefView, ReplanTrigger) are
**Core-owned message schemas** (conventions.md §3); Mind generates its bindings from them and
never forks them. **Lifecycle:** belief views and plans are ephemeral (Redis for live ops state,
conventions.md §5); decision traces persist as MCAP in the object store for audit/replay.
**Provenance:** every emitted plan records the plugin set + versions, the [Core](core.md) interface
versions, the input content hashes (SADF, belief snapshot, comms model, policy artifacts), and the
seed — so a decision is reproducible and a [Bench](bench.md) submission is auditable
(conventions.md §5, §11).

---

## 6. Integration architecture

Mind sits at the center of both charter loops; **every arrow crosses a [Core](core.md) interface**
(charter §5; conventions.md §1).

- **[Core](core.md) (implements/composes):** Mind implements the **Policy/Planner API** at all
  three tiers and composes the sub-interfaces (`MissionPlanner`, `TaskMotionPlanner`, `Controller`)
  per §5.4. It consumes the **Environment API** (`reset/step`, multi-agent, comms-masked
  observations) and the **plugin registry/manifest**. It is a consumer of Core, never an extender
  of it.
- **[Sim](sim.md) (runs against, design/training):** Mind drives a [Sim](sim.md) environment via
  the Environment API for trade studies, training rollouts (with [Learn](learn.md)), and pre-flight
  validation. Multi-fidelity dial and [Surrogate](surrogate.md) acceleration are transparent to
  Mind behind the Environment API.
- **[Allocate](allocate.md) (delegates to):** the mission tier hands the heterogeneous
  task-allocation/scheduling problem (coupled power, comms-window, terrain constraints) to
  [Allocate](allocate.md) — over gRPC in ops, in-process in design — and turns the returned
  assignment into roles/regions. Mind owns *decomposition and execution*; Allocate owns *who does
  what, when, where*. **Multi-regime:** for multi-phase missions the delegated problem
  widens to the joint **asset↔target↔window↔trajectory** assignment; Mind passes the per-leg
  `ManeuverBudget`s and window constraints through and consumes the result as the per-phase plan.
- **[Learn](learn.md) (embeds from):** learned mission planners, TAMP heuristics, and controllers
  arrive as **ONNX** artifacts and slot into the matching tier through the Core contract, run via
  ONNX Runtime. Training is Learn's job; hosting/invoking is Mind's.
- **[Guard](guard.md) (wrapped by):** the final, mandatory stage. Every action — whether from a
  classical controller or a learned policy — is filtered by [Guard](guard.md)'s shield/monitor
  before becoming an Environment API action (charter §4.4, §8; conventions.md §9).
- **[Studio](studio.md) (orchestrated by, design):** Studio authors stack specs and BTs, runs
  Mind-driven trade studies, and captures intent into a campaign. The
  **cross-phase replanning policy** (phase ordering, contingencies, window-miss responses) is
  *Studio's* (design) concern, not Mind's; Mind composes the per-phase decision stack it implies.
- **[Ops](ops.md) (orchestrated by, online):** the same Mind stack runs inside Ops as a service;
  anomalies and monitor breaches trigger **online replanning** back through Mind →
  [Allocate](allocate.md) → [Guard](guard.md) (charter §5), with the digital-twin shadow vetting a
  replan before it commits. Ops owns the live cross-phase replanning *policy*;
  Mind executes the per-phase stack under the higher latency of deep-space phases.
- **[Trajectory](trajectory.md) (consumes, design-time):** descriptive `TrajectoryRef` /
  `ManeuverBudget` artifacts supply Δv and launch/transfer/return **window** feasibility that Mind
  treats as hard plan constraints and replan triggers ([mission-model.md](mission-model.md)) — never as executable
  guidance; converting them to flight guidance is gated out by the `operational_targeting` tag.
- **[Fleet](fleet.md) (consumes):** SADF capability declarations bound each agent's action space.
- **[Link](link.md) (consumes):** comms geometry/latency/windows set plan validity horizons and
  switch the coordination strategy between centralized and decentralized regimes.
- **[Bench](bench.md):** pins a Mind stack + Core interface versions per scenario for reproducible
  leaderboard evaluation. **[Hub](hub.md):** distributes shareable stack specs and BT packages.
  **[Bridge](bridge.md):** in Phase 2+, Mind's Guard-wrapped actions reach real assets via the ROS
  2/DDS data plane (conventions.md §4) — Mind itself never speaks DDS; Bridge is the boundary.

**Transport:** in-process library calls in design; **gRPC** for service-to-service in ops
(Mind↔Allocate↔Guard↔Ops); decision traces emitted as **MCAP** (conventions.md §3, §4).

---

## 7. Infrastructure & deployment

- **Tier 1 — Local/dev (MUST always work, conventions.md §7):** importable library; a researcher
  composes a stack and runs it against [Sim](sim.md) on a workstation, no services required.
- **Tier 2 — Cloud (training/eval):** during training and large sweeps, many Mind instances run as
  Gymnasium/PettingZoo agents inside **Ray** rollouts on **Kubernetes** (KubeRay), co-scheduled
  with [Sim](sim.md) and [Learn](learn.md); [Bench](bench.md) eval runs the same way.
- **Tier 3 — Operations/ground (charter §5):** Mind deployed as OCI containers in the [Ops](ops.md)
  cluster: a **mission-tier coordinator** service plus **per-agent (or per-group) executive**
  services, each pairing with a [Guard](guard.md) sidecar; ROS 2/DDS reached only through
  [Bridge](bridge.md).
- **Onboard-analog edge (Phase 2 analogs, Phase 3 flight-adjacent):** the per-agent executive +
  controller + Guard is designed to run on **resource-constrained edge** compute near the robot
  (the analog of onboard autonomy), while the mission tier stays ground-side — this placement is a
  key §11 decision (see below).
- **Compute:** mission/TAMP tiers are **CPU-bound** (search/solvers); learned controllers add
  **optional GPU** for ONNX inference (small models often run CPU at the edge). Memory is modest
  per agent (plan/belief state); scale is in instance *count*, not per-instance size.
- **Containerization/orchestration:** OCI images; **Kubernetes** substrate; **Ray** for
  distributed rollouts; **Argo Workflows** for batch trade-study sweeps (conventions.md §7).
- **Scaling:** horizontal — one executive per agent/group; mission tier scaled by region/group
  sharding. Stateless services with live state in **Redis** and durable traces in the object store
  (conventions.md §8).

---

## 8. Performance & scalability

**Targets (Phase-1 reference, lunar polar prospecting):**

- Control tier: closed-loop tick at the asset's control rate (10–100 Hz) per agent.
- TAMP replan: seconds to low tens of seconds per agent for a localized re-plan.
- Mission replan: tens of seconds to a few minutes for tens–hundreds of agents (delegated to
  [Allocate](allocate.md), which carries its own targets).
- Swarm scale: tens→hundreds of heterogeneous agents in training and ops.

**Bottlenecks & mitigations:**

- **Combinatorial blow-up at the mission tier.** Mitigation: delegate to [Allocate](allocate.md)
  (CP-SAT + learned heuristics), shard by region/group, and accept *good-enough* anytime
  solutions under a deadline rather than optimal ones.
- **TAMP search latency.** Mitigation: warm-start from cached motion plans; learned samplers/
  heuristics from [Learn](learn.md); fall back to a conservative BT branch if the deadline passes.
- **Per-agent inference cost at swarm scale.** Mitigation: ONNX Runtime with batched/edge
  inference; small distilled controllers; CPU inference where adequate (conventions.md §6).
- **Comms-bound coordination.** Mitigation: decentralized gossip/consensus in `coord/` so agents
  coordinate with neighbors when the global view is stale; validity-horizoned plans keep agents
  productive through blackouts (principles 4–5).

**Scaling strategy:** scale by **agent count** (horizontal executives) and by **rollout count**
(Ray fan-out). The mission tier is the lone semi-central component and is sharded; nothing forces
a single global synchronous decision. **Measure before optimizing:** Mind ships representative
multi-agent benchmarks whose results are reproducible (conventions.md §8).

---

## 9. Security, safety & compliance

- **Safety is the defining concern.** Mind's outputs drive (eventually) real hardware with no
  recovery and minutes of latency (charter §8). The architectural guarantee: **no action leaves
  Mind un-wrapped by [Guard](guard.md)** (principle 7). Hard constraints (collision, power floors,
  keep-out zones) are enforced by Guard *independently of any learned component* (conventions.md
  §9) — a learned controller cannot disable its own shield.
- **Degrade-not-collapse as a safety property.** Fallback BT branches and cached-plan execution
  are validated as safety behaviors, not best-effort niceties; loss of the mission tier must leave
  agents in a defined safe-productive or safe-idle state.
- **Plugin isolation:** untrusted/third-party planner or controller plugins run **out-of-process**
  in sandboxed containers (seccomp/gVisor; WASM forward-looking) per conventions.md §7/§9; only
  vetted plugins run in-process. Plan provenance records exactly which plugins decided what.
- **AuthN/AuthZ (ops):** OIDC + **OPA** RBAC on the Mind ops services; **mTLS** between
  Mind/Allocate/Guard/Ops (conventions.md §9). Replan commands are authenticated and audited.
- **Supply chain:** signed artifacts (Sigstore/cosign), SBOM, SLSA provenance; the embedded ONNX
  policies are content-addressed and signature-verified before load (conventions.md §9).
- **Export control / dual use:** parts of Mind are explicitly flagged in conventions.md §12 as
  dual-use-sensitive. Coordination logic for the **science/simulation commons is open**; any
  capability that drifts toward operational targeting is **capability-tagged** (via the
  [Core](core.md) manifest taxonomy) and partitioned/access-controlled. Mind documents an EAR/ITAR
  posture and gates sensitive planner backends at load via OPA (conventions.md §12; charter §9.5).

---

## 10. Observability & operability

- **Tracing:** **OpenTelemetry** spans across the full decision path so a replan in [Ops](ops.md)
  is traceable end-to-end through Mind → [Allocate](allocate.md) → [Guard](guard.md)
  (conventions.md §10) — the named cross-component trace.
- **Decision traces:** every tier decision, plan revision, replan trigger, Guard intervention, and
  fallback activation is logged to an **MCAP** stream, replayable in [View](view.md) and tied to
  the plan provenance — this is also the substrate for **plan explanations** to operators (charter
  §5.6).
- **Metrics:** Prometheus/Grafana — replan rate, tier latencies, deadline-miss rate, fallback
  activation rate, comms-degradation events, Guard-intervention rate (conventions.md §10).
- **Logs:** structured JSON via Loki; standard liveness/readiness; per-service SLOs.
- **Testing & validation:**
  - `pytest` + **Hypothesis** for inter-tier schema/protocol invariants; `gtest` for the C++/BT
    layer (conventions.md §11).
  - **Determinism gates:** seeded stacks compared to golden decision traces; CI fails on
    non-reproducibility (conventions.md §1.5, §11).
  - **Contract tests:** Mind proves it honors the [Core](core.md) Policy/Planner interface
    versions it declares (consumer-driven contract tests, conventions.md §11).
  - **Scenario validation:** Mind stacks are exercised against [Sim](sim.md) reference scenarios
    and scored on [Bench](bench.md); comms-degradation and partial-observability stress tests
    (injected blackouts, delayed/dropped messages) verify the degrade-not-collapse guarantee.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Coordination paradigm** | Centralized (one global planner); fully decentralized/distributed; hierarchical-hybrid | **Hierarchical-hybrid.** Centralized mission tier for global coherence + decentralized neighbor coordination at the agent tier for comms-robustness. Pure-central collapses under comms loss; pure-decentral can't reason globally about coupled ISRU goals. Hybrid degrades gracefully (charter §7/§9). |
| **Plan representation / execution** | Behavior trees; hierarchical state machines (HSM); HTN | **Behavior trees** as the execution scaffold (charter §6) for reactive fallbacks and composability — a **pure-Python engine for the Groot v4 XML dialect** (BehaviorTree.CPP's authoring format), the native BehaviorTree.CPP/pybind11 runtime re-scoped out to hold the tier-1 local-install rule (conventions.md §7; astro-mine-mind#17); **HTN available as a pluggable mission/TAMP backend** where hierarchical decomposition fits better than reactive BTs. HSMs are a weaker default (state explosion). |
| **Mission-planner backend** | PDDL/temporal; HTN; learned policy; scripted | **Pluggable, PDDL/temporal default** via unified-planning; HTN and learned backends as drop-in alternatives. The framework commits to *none* — it commits to the interface. |
| **TAMP backend** | Classical PDDL+motion (PDDLStream-style); sampling-based motion only; learned end-to-end; hybrid | **Hybrid:** symbolic task planning over **OMPL** sampling-based motion, with learned samplers/heuristics from [Learn](learn.md) slotted in. Pure-learned lacks guarantees; pure-classical is too slow at swarm scale. |
| **Controller backend** | Classical (MPC/PID); learned (ONNX); hybrid | **Pluggable per asset class:** classical MPC/PID baselines that always work + learned ONNX controllers where they win — all behind one Core Controller contract, all Guard-wrapped. |
| **Layer composition mechanism** | Hard-coded pipeline; Core-interface plugins + stack spec; full DSL | **Core-interface plugins + declarative stack spec.** Each tier implements a Core sub-interface; a JSON-Schema'd stack spec wires them. Composable and swappable without code change (principle 2). |
| **Where Mind runs in ops** | All ground-side; all onboard-analog edge; **split** (mission ground, executive/control edge) | **Split.** Mission tier ground-side (heavy search, human-in-loop); per-agent executive + controller + [Guard](guard.md) on onboard-analog edge so agents stay safe and productive through comms blackouts (charter §5/§8). |
| **Allocation** | Embed a solver in Mind; delegate to [Allocate](allocate.md) | **Delegate to [Allocate](allocate.md).** Mind owns decomposition/execution, not the combinatorial core (boundary; charter §4.4). For multi-regime missions the delegated problem widens to the joint asset↔target↔window↔trajectory assignment. |
| **Cross-phase planning** | One flat plan over all regimes; per-phase stacks composed across `PhaseTransition` handoffs | **Per-phase decision stacks, window-gated, composed across handoffs.** Each Phase gets the coordination/fallback/horizon posture its regime needs; cross-phase replanning *policy* lives in [Studio](studio.md)/[Ops](ops.md) (R2), Mind composes the stack. Orbital-mechanics windows from [Trajectory](trajectory.md) are hard constraints; outputs still pass [Guard](guard.md). |
| **Learned-policy runtime** | Framework-native (PyTorch); **ONNX Runtime** | **ONNX Runtime** — portable, edge-friendly, framework-neutral (conventions.md §6). |

**Open questions / research dependencies:**

- **Robust cooperation under partial observability + intermittent/delayed comms** is an open
  research problem (charter §7); Mind provides the *framework* (validity horizons, decentralized
  `coord/`, fallback BTs), but the *good policies* come from [Learn](learn.md) — co-designed.
- **TAMP at swarm scale within deadlines** (charter §8 "heterogeneous, tightly-coupled allocation"
  abutting continuous motion) — the symbolic↔motion↔allocation interleaving boundary is
  co-designed with [Allocate](allocate.md) and [Sim](sim.md).
- **Plan-to-belief interface for active perception** (decision-making under deep resource
  uncertainty, charter §7) — how belief views expose information value to the planner — co-designed
  with [Prospect](prospect.md) and [Core](core.md).
- **Exact split point for onboard-analog deployment** and the validity-horizon semantics for
  delay-tolerant supervisory autonomy (charter §7) — co-designed with [Ops](ops.md) and
  [Guard](guard.md).

---

## 12. Roadmap alignment

- **Phase 1 (this component, charter §10):** ship Mind alongside [Learn](learn.md),
  [Allocate](allocate.md), [Guard](guard.md), [Studio](studio.md), and [Hub](hub.md) to "become
  the MARL and planning commons for planetary swarms."
- **MVP:** the three-tier hierarchy over the [Core](core.md) Policy/Planner API; a **pure-Python
  Groot-v4 behavior-tree execution** scaffold (BehaviorTree.CPP re-scoped out, astro-mine-mind#17); a
  **PDDL/temporal mission backend** (unified-planning → Fast Downward); an **OMPL/FCL-based TAMP**; **classical + ONNX
  controllers**; mandatory [Guard](guard.md) wrapping; delegation to [Allocate](allocate.md);
  running against [Sim](sim.md) on the lunar-polar-prospecting reference scenario, scored on
  [Bench](bench.md), with the degrade-not-collapse fallback path validated under injected comms
  loss. Library-first (Tier 1 MUST work).
- **Later in Phase 1:** richer pluggable backends (HTN, learned planners), decentralized `coord/`
  strategies, stack specs shareable via [Hub](hub.md), and Studio-authored composition.
- **Phase 2:** online replanning inside [Ops](ops.md) with the digital-twin shadow; the split
  ground/edge deployment validated against terrestrial analog rover-swarm field tests
  (charter §10).
- **Phase 3:** Guard-wrapped actions reaching real flight hardware via [Bridge](bridge.md); new
  environments (asteroids, icy moons) handled purely by swapping [Worlds](worlds.md)/[Fleet](fleet.md)
  plugins — Mind unchanged, proving the abstraction held.
- **Phase 3 (multi-regime):** window-gated cross-phase composition over the Core
  `MissionSpec`/`PhaseTransition` schema (whose hooks are reserved in **Phase 1**), consuming
  [Trajectory](trajectory.md) feasibility/Δv via [Allocate](allocate.md), with cross-phase
  replanning policy in [Studio](studio.md)/[Ops](ops.md) and outputs still [Guard](guard.md)-wrapped
  ([mission-model](mission-model.md)).
