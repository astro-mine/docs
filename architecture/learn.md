# Astro-Mine-Learn — Technology Architecture

> Layer: **Autonomy & coordination** · Phase: **1**
> The multi-agent RL engine: PettingZoo-style envs, baselines, curricula, and scale-out
> training for cooperation under partial observability and comms-limited links.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Learn` is the **multi-agent reinforcement-learning (MARL) toolkit** of the platform.
It turns a simulatable world into trainable RL problems and provides everything needed to train,
evaluate, and publish cooperative swarm policies at scale. Concretely, it provides:

- **Env wrappers** that present [Sim](sim.md) (and its [Surrogate](surrogate.md) fidelity tiers)
  as standard **Gymnasium** (single-agent) and **PettingZoo** (multi-agent) environments through
  the [Core](core.md) Environment API — with first-class **partial observability** and
  **intermittent, delayed communication** modeling;
- **Baselines** — reference algorithm implementations (MAPPO, IPPO, QMIX, plus comms-learning
  variants) that anyone can reproduce and try to beat;
- **Curricula & scenario generation** — staged difficulty and procedurally varied scenarios that
  make hard cooperation problems learnable;
- **Training infrastructure** — distributed, vectorized rollout + learner orchestration on
  **Ray** / **KubeRay**, with experiment tracking and reproducible run provenance;
- **Policy export** — trained policies emitted as portable **ONNX** artifacts plus metadata,
  ready for consumption by [Mind](mind.md), wrapping by [Guard](guard.md), and publication to
  [Hub](hub.md).

**Explicitly out of scope.** Learn does **not** simulate physics (that is [Sim](sim.md)), does
not learn surrogates of physics (that is [Surrogate](surrogate.md)), does not compose or execute
policies in a mission hierarchy at runtime (that is [Mind](mind.md)), does not provide the safety
shield that makes a learned policy deployable (that is [Guard](guard.md)), and does not solve the
combinatorial allocation problem with exact solvers (that is [Allocate](allocate.md), though Learn
may train heuristics it consumes). Learn defines **no new asset, world, or message schema** — it
is a *consumer* of Core contracts, never an extender of the waist. It also does not host a
leaderboard; it *produces* artifacts that [Bench](bench.md) scores and [Hub](hub.md) distributes.

**Primary users:** ML and RL researchers — the earliest and largest contributor base
(charter §3, §5.4). Secondarily, autonomy researchers and mission designers who consume trained
policies via [Mind](mind.md).

**Charter alignment:** §5.4 (the Learn package); §7 ("PyTorch and JAX; multi-agent RL via
PettingZoo, Gymnasium, and Ray RLlib"; "ONNX for portable policies"); §8 (the headline research
problem: *scalable cooperative multi-agent learning under partial observability and intermittent,
delayed communications*); §10.3 (the "academic flywheel" of benchmarks + leaderboards + hub that
Learn is the engine behind).

---

## 2. Architecture principles

1. **Library first, cluster second.** A researcher MUST be able to `pip install astro-mine-learn`,
   wrap a scenario, and train a baseline on a single GPU workstation before any cluster is
   involved (conventions.md §7, tier 1). The distributed path is the *same* code with a different
   executor, never a fork.
2. **The env is the only physics boundary.** Learn touches the world exclusively through the Core
   Environment API. Swapping [Sim](sim.md) for a [Surrogate](surrogate.md) tier, or one world for
   another, is a config change — never a code change in an algorithm. No private hooks into the
   engine.
3. **Comms-limitation and partial observability are modeled in the env, not bolted onto the
   algorithm.** Observation masks, message-channel budgets, drop/delay processes, and per-agent
   visibility live in a declarative **env wrapper** so that *every* algorithm — independent,
   CTDE, or comms-learning — sees the same constraint and results are comparable.
4. **Reproducibility is non-negotiable.** Same scenario + same seed + same pinned environment ⇒
   same learning curve (conventions.md §5, §11). Every run records its inputs, code version,
   lockfile, and seeds; results are content-addressed so [Bench](bench.md) can re-derive them.
5. **Portable policies, internal checkpoints.** The *only* artifact other components consume is
   **ONNX** + a typed metadata sidecar. Framework-specific checkpoints (PyTorch `state_dict`, JAX
   pytrees) stay internal to Learn (conventions.md §6).
6. **Algorithms are plugins.** A new MARL algorithm, a new curriculum, or a new scenario generator
   is contributed as a registered plugin against Learn's trainer/curriculum interfaces — not a
   patch to the core toolkit (conventions.md §1, charter §10.2).
7. **Throughput is multi-fidelity.** Training rollouts pick a fidelity tier per phase: cheap
   surrogate-accelerated or GPU-vectorized rollouts early, high-fidelity [Sim](sim.md) for
   final-policy validation. The fidelity dial is a curriculum axis, not an afterthought
   (conventions.md §8, charter §9).
8. **Honest evaluation.** Reported scores separate *training* envs from *held-out evaluation*
   envs; sample-efficiency, wall-clock, and seed-variance are all reported. A single lucky seed
   is an anti-pattern (charter §8 "evaluation science for swarm campaigns").
9. **Degrade, don't collapse.** Policies are trained and stressed against comms dropout so the
   learned behavior degrades gracefully — the property [Guard](guard.md) later enforces as a hard
   floor (conventions.md §8, charter §9).

---

## 3. Application architecture

Learn is an importable Python library plus an optional set of cluster-side services (rollout
workers, learners). Its modules:

```
astro_mine.learn
├── envs/           # Core Environment API → Gymnasium/PettingZoo adapters; vectorization
│   ├── adapter/    #   Core env ⇄ Gymnasium/PettingZoo (ParallelEnv) bridge
│   ├── comms/      #   comms-limited / partial-observability wrappers (masks, delay, drop, budget)
│   └── vector/     #   batched/vectorized env (GPU-vectorized + distributed CPU executors)
├── algos/          # MARL algorithm plugins: MAPPO, IPPO, QMIX, MADDPG, comms-learning (+JAX kernels)
├── models/         # policy/value nets: MLP/RNN/GNN/attention; centralized critics; comm modules
├── curriculum/     # staged difficulty, automatic curricula, scenario generators
├── train/          # trainer orchestration: rollout↔learner loop, Ray/KubeRay executors, sweeps
├── eval/           # evaluation harness: held-out envs, seed sweeps, metric aggregation
├── export/         # ONNX export + policy metadata sidecar; ONNX Runtime validation
├── track/          # experiment tracking (MLflow default / W&B option), provenance capture
└── registry/       # algorithm/curriculum/scenario plugin discovery (Core registry)
```

### Key abstractions exposed

- **`SwarmEnv` adapter** — wraps a Core Environment-API world as a PettingZoo `ParallelEnv`
  (multi-agent) or Gymnasium `Env` (single-agent / centralized control). It surfaces, as
  first-class structure: per-agent **observation spaces**, **action spaces**, an **observation
  mask** (what each agent can see this step), and a **comms channel** (who can message whom, at
  what budget/latency). Heterogeneous agents are supported via per-agent space dicts keyed by
  declared SADF capabilities (conventions.md §3).
- **`CommsModel`** — a declarative, composable wrapper describing the comms regime:
  line-of-sight/range gating (driven by [Link](link.md) when present), message bandwidth budget,
  stochastic **drop** probability, and fixed/sampled **delay** distributions. This is *the*
  knob that makes the charter §8 problem concrete and benchmark-comparable.
- **`Algorithm` / `Trainer`** — the plugin contract for a learning method: `act(obs)`,
  `learn(batch)`, checkpoint/restore, and an `export()` hook. CTDE algorithms additionally declare
  a centralized-critic input spec.
- **`Curriculum` / `ScenarioGenerator`** — produce a (possibly stateful) stream of env configs;
  `update(metrics)` advances staged or automatic curricula based on observed performance.
- **`PolicyPackage`** — the export unit: an ONNX graph + a typed metadata sidecar (obs/action
  spec, Core interface versions, training provenance, declared comms assumptions) — the contract
  with [Hub](hub.md), [Mind](mind.md), and [Guard](guard.md).

### Extension / plugin points

New **algorithms**, **curricula**, **scenario generators**, and **model architectures** register
through the Core plugin registry (conventions.md §1, §7). In-process plugins use Python entry
points; the trainer discovers them by capability tag. Reference baselines ship as *replaceable
examples*, not privileged internals (charter §10.2).

### Interaction patterns

- **In-process library** for single-workstation training and for embedding in [Studio](studio.md)
  / notebooks.
- **Distributed actor system** (Ray) for scale-out: a learner process owns the policy update; many
  **rollout workers** each hold a vectorized [Sim](sim.md)/[Surrogate](surrogate.md) env and stream
  experience back. Communication is Ray object-store / RPC internally; sim jobs and sweep
  lifecycle ride **NATS/JetStream** events (conventions.md §4) when orchestrated by
  [Cloud](cloud.md).
- **Producer** to [Bench](bench.md)/[Hub](hub.md): finished `PolicyPackage` artifacts are written
  to the content-addressed object store with provenance.

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.12+** for the entire public surface (conventions.md §2), type-checked
  with `mypy`/`pyright`. Performance-critical vectorized rollout kernels may drop to **JAX** (XLA)
  or, where a custom op is unavoidable, a C++/CUDA kernel behind a Python binding (conventions.md
  §2) — but these stay behind the same `Algorithm`/env interfaces.
- **ML frameworks:** **PyTorch** is the primary, default training framework (broadest community
  familiarity, the RLlib path). **JAX** (with **Brax**-style vectorized envs and `flax`/`optax`)
  is the recommended path for massively parallel, GPU-resident rollouts and differentiable
  pipelines (conventions.md §6, charter §7). Learn supports both; an algorithm declares which
  backend it uses.
- **RL framework:** **Ray RLlib** is the default multi-agent training framework and distributed
  executor (conventions.md §6, charter §7) — it gives multi-agent APIs, batteries-included
  baselines, and KubeRay scale-out for free. A **JAX-native** stack (PureJaxRL-style end-to-end
  GPU training) is offered as an alternative for throughput-bound research (see §11).
- **Env APIs:** **Gymnasium** + **PettingZoo** (`ParallelEnv`) (conventions.md §3). Vectorized
  envs follow the Gymnasium vector API and PettingZoo parallel conventions.
- **Config & scenarios:** **JSON Schema** + **Pydantic v2** for training configs, curricula, and
  scenario specs (conventions.md §3); Hydra-style composition is acceptable on top, but the
  validated schema is the source of truth.
- **Export & inference:** **ONNX** export; **ONNX Runtime** for the post-export equivalence check
  (conventions.md §6).
- **Experiment tracking:** **MLflow** (open-source default); **Weights & Biases** as a hosted
  option (conventions.md §6). Runs link to [Bench](bench.md) results and [Hub](hub.md) artifacts
  by content hash.
- **Build/packaging:** Python wheel `astro-mine-learn`; OCI images for the rollout-worker and
  learner roles (pinned base images, multi-arch where relevant) per conventions.md §7. SemVer;
  declares the Core interface major versions it supports (conventions.md §13).

---

## 5. Data architecture

Learn **owns no platform schema** — it consumes Core's Environment API and SADF, and produces
artifacts in shared formats (conventions.md §5).

| Data | Format / store | Notes |
|---|---|---|
| **Rollout experience** (transitions) | **Apache Arrow** in-memory; **Parquet** when spilled/replayed | Columnar, zero-copy across workers (conventions.md §5). Replay buffers are in Redis/Arrow. |
| **Training configs / curricula / scenario specs** | YAML/JSON validated by **JSON Schema** + Pydantic v2 | Versioned with the run; the reproducibility key. |
| **Internal checkpoints** | PyTorch `state_dict` / JAX pytree (framework-native) | **Internal only** — never the cross-component artifact (conventions.md §6). |
| **Exported policy** | **ONNX** graph + typed **metadata sidecar** (Protobuf/JSON) | The `PolicyPackage`; content-addressed in the object store. |
| **Metrics / learning curves** | **Parquet** + MLflow/W&B store; live via **Prometheus** | Aggregated reward, sample-efficiency, seed variance, comms-stress curves. |
| **Run recordings** (episode rollouts for debugging/replay) | **MCAP** | Heterogeneous timestamped channels (conventions.md §4); replayable in [View](view.md). |
| **Large artifacts** (datasets, policies) | **S3-compatible object store**, **content-addressed** | MinIO self-host / S3/GCS in cloud (conventions.md §5). |
| **Run metadata catalog** | **PostgreSQL** (via MLflow / [Hub](hub.md)) | Lineage, tags, leaderboard links. |

**Provenance & versioning.** Every `PolicyPackage` records: the scenario + world content hashes,
the Core interface versions used, the exact env-wrapper/comms-model config, the random seeds, the
code version, and the environment lockfile (conventions.md §5). This is what lets [Bench](bench.md)
reproduce a leaderboard entry exactly and what [Hub](hub.md) indexes. Policies and datasets are
**content-addressed**; the ONNX graph hash is part of the artifact identity.

**Coordinate frames & time.** Observations/actions inherit Core's SI-units, explicit-frame, and
SPICE-backed time conventions (conventions.md §5, core.md §2) — Learn never reinterprets them, it
only consumes the spaces the env declares.

---

## 6. Integration architecture

Learn sits in the design/training loop (charter §6) and connects only through Core contracts:

- **[Core](core.md) — Environment API & Policy API (consumes).** Learn's `envs/adapter`
  wraps any Core Environment-API world as Gymnasium/PettingZoo; exported policies implement the
  Core **Policy/Planner** contract (as ONNX + metadata) so [Mind](mind.md) can drop them in as
  controllers/planners. Learn declares the Core interface versions it supports and runs the Core
  consumer-driven contract tests in CI (conventions.md §11, core.md §6).
- **[Sim](sim.md) (consumes).** The high/medium-fidelity engine behind rollouts, reached through
  the Environment API. Sim implements the env; Learn wraps it. Sim job lifecycle (spawn, step,
  teardown) for distributed rollouts rides gRPC (control) and NATS/JetStream events when
  orchestrated by [Cloud](cloud.md) (conventions.md §4).
- **[Surrogate](surrogate.md) (consumes).** Learn requests cheaper fidelity tiers for fast
  rollouts and selects tiers as a curriculum/throughput axis. It honors the surrogate's tracked
  **error bounds** (conventions.md §8) — a policy trained mostly on surrogate fidelity is flagged
  in its metadata so [Bench](bench.md) can require a high-fidelity validation pass.
- **[Link](link.md) (consumes, optional).** When present, the `CommsModel` is driven by Link's
  line-of-sight/relay/latency/bandwidth model rather than a synthetic stand-in — making the
  comms-limitation realistic (charter §5.1).
- **[Mind](mind.md) (produces for).** Exported ONNX policies are consumed as controllers and
  pluggable planners inside Mind's hierarchy.
- **[Guard](guard.md) (produces for).** Learned policies are wrapped by Guard's safety shield;
  Learn surfaces the policy's declared comms/observability assumptions and action bounds in
  metadata so Guard knows what envelope to enforce.
- **[Allocate](allocate.md) (produces for, optional).** Learn can train learned heuristics that
  Allocate combines with CP-SAT/OR-Tools exact solvers (charter §5.4).
- **[Bench](bench.md) (produces for).** `PolicyPackage` artifacts are scored on named scenarios;
  Bench pins the Core interface versions and re-runs with recorded seeds for reproducibility.
- **[Hub](hub.md) (produces for / discovers from).** Policies (and baselines, curricula) are
  published to and discovered from Hub by content hash — the academic-flywheel network
  (charter §10.3).
- **[Cloud](cloud.md) (deploys on).** Distributed training runs as Ray jobs on KubeRay; large
  sweeps as Argo Workflows (conventions.md §7).

---

## 7. Infrastructure & deployment

- **Deployment tiers (conventions.md §7):**
  1. **Local/dev** — single workstation, one Python env, one GPU. A researcher clones, wraps a
     scenario, and trains a baseline. *This tier MUST always work* and is the default in docs and
     tutorials.
  2. **Cloud** — **Kubernetes** + **Ray** via **KubeRay**: a `RayJob`/`RayCluster` with one
     learner head and an autoscaling pool of rollout workers; GPU scheduling via the **NVIDIA GPU
     Operator** (MIG for sharing small policies); large hyperparameter sweeps as **Argo
     Workflows** DAGs. Orchestrated by [Cloud](cloud.md).
- **Compute profile:**
  - *Learner* — GPU-bound for the policy/value update (PyTorch CUDA or JAX/XLA). 1 GPU for small
    swarms; data-parallel multi-GPU for large nets.
  - *Rollout workers* — two regimes: **CPU-heavy** distributed rollouts against [Sim](sim.md)
    (many workers, modest memory each), or **GPU-vectorized** envs ([Surrogate](surrogate.md)/JAX/Brax)
    where thousands of envs share a GPU. The choice is a config/curriculum decision (see §8, §11).
  - *Memory* — replay buffers and rollout batches sized to the swarm count × horizon; spilled to
    Arrow/Parquet on the object store under pressure.
- **Containerization & orchestration:** OCI images per role (learner, rollout-worker), pinned base
  images; Ray for the actor system; KubeRay for K8s lifecycle; Argo for batch sweeps
  (conventions.md §7).
- **Scaling:** scale rollout workers horizontally behind the learner; learner scales with
  data-parallelism. State (buffers, run metadata) lives in Redis / object store / Postgres so
  workers stay stateless and preemptible (spot/preemptible nodes welcome).

---

## 8. Performance & scalability

**Targets (Phase 1, anchor scenario — lunar polar prospecting, tens of agents):**

- Single-GPU workstation: a documented baseline trains to a reported reference score within an
  overnight run on a surrogate/medium-fidelity tier (keeps tier 1 viable).
- Cloud: linear-ish scaling of environment-steps/sec with rollout-worker count up to the learner's
  ingest limit; sample-throughput, not just FLOPs, is the headline metric.

**Bottlenecks & mitigations:**

- **Simulation throughput is the dominant cost.** Three complementary strategies, selectable per
  run/curriculum stage (conventions.md §8):
  1. **GPU-vectorized envs** (JAX/Brax / Surrogate tiers) — thousands of envs resident on one GPU,
     best sample-throughput when a differentiable/fast surrogate exists.
  2. **Distributed CPU rollouts** (Ray workers each running [Sim](sim.md)) — required for
     high-fidelity physics that cannot be vectorized on-GPU.
  3. **Surrogate-accelerated rollouts** — [Surrogate](surrogate.md) tiers for the bulk of training,
     with periodic high-fidelity validation gates. *Recommended default: surrogate-accelerated +
     distributed CPU for fidelity-critical phases.*
- **Many small agents → tiny GPU kernels.** Batch across agents and envs; share encoders; use MIG
  to pack many small policies per GPU.
- **Replay/experience movement.** Apache **Arrow** zero-copy between workers; spill to **Parquet**
  on object storage; range-read only the slices a learner needs (conventions.md §8).
- **Back-pressure.** Rollout→learner queues are bounded; under load the system sheds rollouts
  rather than OOMing — and, deliberately, training under simulated comms dropout exercises the
  *graceful-degradation* property the policies themselves must have (conventions.md §8, charter §9).

**Scaling strategy:** horizontal rollout fan-out on Ray/K8s; data-parallel learner; multi-fidelity
dial as the primary cost lever; spot/preemptible workers for sweeps. Every baseline ships a
reproducible throughput benchmark (conventions.md §8 "measure before optimizing").

---

## 9. Security, safety & compliance

- **AuthN/AuthZ:** training services authenticate via **OIDC** and authorize via **RBAC/OPA**
  (conventions.md §9). Publishing to [Hub](hub.md) and submitting to [Bench](bench.md) require
  scoped credentials; service-to-service is **mTLS**.
- **Untrusted env/algorithm isolation.** Community-contributed scenario generators, env plugins,
  or algorithms run **out-of-process in sandboxed containers** (seccomp/gVisor; WASM where
  feasible) per conventions.md §7, §9 — Learn must execute third-party rollout code without
  trusting it. This matters because rollouts run arbitrary contributed env logic.
- **Supply chain.** Published policies are **signed (Sigstore/cosign)** with **SLSA provenance**
  and an **SBOM** (conventions.md §9). The `PolicyPackage` provenance record (§5) is part of the
  signed metadata so a Hub consumer can verify what a policy was trained on.
- **Safety boundary — explicit.** Learn produces policies; it provides **no runtime safety
  guarantee**. Hard constraints (collision, power floors, keep-out) are enforced independently by
  [Guard](guard.md) (conventions.md §9, charter §5.4). Learn's contribution to safety is *honest
  metadata* (declared comms/observability assumptions, action bounds, surrogate-fidelity caveats)
  so Guard and operators know the envelope. A learned policy is never trusted as the last line of
  defense.
- **Export control / dual use.** Learn trains *cooperative coordination under comms constraints*
  on *open scientific scenarios* — squarely inside the open commons (charter §2, §10.5,
  conventions.md §12). It generates no certification-grade flight targeting. Where a policy is
  trained against a capability-tagged sensitive scenario, that tag (from the Core manifest)
  propagates into the policy metadata and gates publication via OPA (conventions.md §12,
  core.md §9). Default-open; sensitive scenarios partitioned.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** traces/metrics/logs in every training service; structured JSON
  logs aggregated with **Loki**; metrics in **Prometheus** + **Grafana** dashboards
  (conventions.md §10). A distributed training run is traceable across learner and rollout workers.
- **Training metrics:** reward curves, KL/entropy/value-loss, env-steps/sec, sample-efficiency,
  per-agent contribution, and **comms-stress curves** (performance vs. drop/delay) — the headline
  diagnostic for the charter §8 problem.
- **Testing & validation strategy:**
  - *Unit/integration:* `pytest`; **Hypothesis** property tests for env-wrapper invariants
    (mask consistency, action-space conformance, comms-budget accounting) (conventions.md §11).
  - *Determinism gates:* seeded short-run golden tests; CI fails on non-reproducibility
    (conventions.md §11, §5).
  - *Contract tests:* consumer-driven tests proving Learn honors the [Core](core.md) Environment
    and Policy API versions it claims (conventions.md §11, core.md §10).
  - *Export equivalence:* every ONNX export is checked under **ONNX Runtime** for numerical
    equivalence to the source policy on a fixed observation batch before publish.
  - *Evaluation harness:* held-out evaluation envs, seed sweeps, and variance reporting baked into
    `eval/` so leaderboard numbers are statistically honest (charter §8).

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **MARL paradigm** | Fully independent learners (IPPO); centralized-training/decentralized-execution (CTDE: MAPPO/QMIX/MADDPG); explicit communication-learning methods | **CTDE (MAPPO + QMIX) as default baselines**, IPPO as the simple control, **comms-learning as a first-class research track** — because comms-limited cooperation *is* the charter §8 problem. Ship all three as plugins. |
| **RL framework / executor** | Ray RLlib; JAX-native (PureJaxRL/Brax-style end-to-end GPU); custom trainer | **Ray RLlib (PyTorch) as the default**, KubeRay for scale-out; **JAX-native offered as a high-throughput alternative** for vectorized-env research. Avoid a custom trainer except for kernels. |
| **Sim-throughput strategy** | GPU-vectorized envs; distributed CPU rollouts; surrogate-accelerated rollouts | **Surrogate-accelerated as the bulk-training default**, distributed CPU [Sim](sim.md) for fidelity-critical phases, **GPU-vectorized where a JAX/Brax env or surrogate exists** — selectable per curriculum stage. |
| **Partial-observability & comms modeling** | In-algorithm hacks; centralized super-observation; **declarative env-wrapper `CommsModel`** | **Declarative env-wrapper** (observation masks + drop/delay/budget channel), optionally driven by [Link](link.md) — keeps results comparable across algorithms. |
| **Curriculum / scenario generation** | Hand-authored stages; procedural/domain randomization; automatic curricula (PLR/teacher–student) | **Hand-authored staged curricula + domain randomization for the MVP**, with an **automatic-curriculum plugin interface** for research. |
| **Primary deep-learning framework** | PyTorch only; JAX only; **both, backend-declared** | **Both**, PyTorch primary/default, JAX for throughput — per algorithm declaration (conventions.md §6). |
| **Experiment tracking** | MLflow; Weights & Biases; both | **MLflow default** (OSS, self-host), **W&B optional** (conventions.md §6). |
| **Policy interchange** | ONNX; framework-native; TorchScript | **ONNX + metadata sidecar** is the only cross-component artifact (conventions.md §6). |

**Open questions / research dependencies:**

- The headline open problem (charter §8): *scalable cooperative learning under partial
  observability and intermittent, delayed comms.* The `CommsModel` makes it measurable; which
  algorithm family wins is unresolved and is a [Bench](bench.md) leaderboard, not a fixed choice.
- Exact boundary of the Core Environment API for **variable-fidelity** and **comms-masked**
  observation — co-designed with [Core](core.md), [Sim](sim.md), and [Surrogate](surrogate.md)
  (core.md §11).
- How much training can run on [Surrogate](surrogate.md) fidelity before high-fidelity validation
  is required — depends on Surrogate's tracked error bounds (conventions.md §8).
- Whether learned **allocation heuristics** belong in Learn or [Allocate](allocate.md), and the
  hand-off contract between them (charter §5.4).
- Sim-to-real / sim-to-sim transfer credibility for learned policies — tied to the platform-wide
  sim-to-real research thread (charter §8) and validated only on terrestrial analogs in Phase 2.

---

## 12. Roadmap alignment

- **Phase 1** is Learn's debut (charter §11): "become the MARL and planning commons for planetary
  swarms," shipping alongside [Mind](mind.md), [Allocate](allocate.md), [Guard](guard.md),
  [Studio](studio.md), and [Hub](hub.md), with the first public leaderboards.
- **MVP (Phase 1 entry):** Gymnasium/PettingZoo adapter over the Core Environment API; the
  `CommsModel` partial-observability/comms wrapper; **IPPO + MAPPO + QMIX baselines** on the
  anchor lunar-polar-prospecting scenario; single-GPU workstation training that *just works*;
  ONNX export + equivalence check; MLflow tracking; publish to [Hub](hub.md) and score on
  [Bench](bench.md).
- **Phase 1 build-out:** KubeRay distributed training on [Cloud](cloud.md); surrogate-accelerated
  and GPU-vectorized rollout paths; staged + domain-randomized curricula; comms-learning baselines;
  the comms-stress evaluation suite.
- **Later (Phase 2+):** automatic-curriculum plugins; learned allocation heuristics for
  [Allocate](allocate.md); transfer-learning and sim-to-real-aware training validated against the
  terrestrial analog field tests that [Ops](ops.md) introduces (charter §11, Phase 2). The success
  measure is the academic flywheel turning: external labs publishing policies to [Hub](hub.md) and
  beating the [Bench](bench.md) leaderboards (charter §10.3).
