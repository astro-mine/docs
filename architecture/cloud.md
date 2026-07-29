# Astro-Mine-Cloud — Technology Architecture

> Layer: **Commons backbone & platform infrastructure** · Phase: **1** (but underpins
> scale-out from Phase 0 onward) · Extended for multi-regime missions (Phase 3)
> Ships in: [`astro-mine-platform`](platform.md) (engines, compilation, the local backend) · [`astro-mine-api`](api.md) (the submission service)
> The horizontal scale-out substrate: Kubernetes + Ray + Argo that runs thousands of
> simulations, training jobs, solves, and evaluations in parallel for the whole platform.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Cloud` is the **distributed-execution substrate** for the platform — the "how to
run lots of it" layer. It takes workloads *defined by other components* and runs them at scale
on a cluster: parameter sweeps, training runs, large solves, surrogate fitting, and benchmark
evaluation batches. **Mission-design sweep workloads.** It also schedules the design-time
batch workloads of the mission-architecture layer — embarrassingly-parallel trajectory window /
global-optimization sweeps from [Trajectory](trajectory.md) (e.g. pygmo island-model runs, porkchop
scans) and OpenMDAO design sweeps for [Sizing](sizing.md)/[Ledger](ledger.md) co-optimization. These
are additional workload *classes* on the existing substrate, not a new infra primitive. Concretely,
it provides:

- a **Kubernetes-based execution platform** with curated operators (KubeRay, Argo Workflows,
  the NVIDIA GPU Operator) and a hardened base for running the platform's OCI workloads
  (conventions.md §7);
- a **job & workflow API** — a small typed contract for "submit this containerized work, with
  these resources, against these content-addressed inputs, and put results here" — together with
  reference submission clients and a CLI;
- **two execution engines**, used per workload shape: **Ray/KubeRay** for tightly-coupled,
  stateful, gang-scheduled work (RL training, actor-based rollout fleets, distributed solves)
  and **Argo Workflows** for DAG-structured, loosely-coupled batch (large Cartesian/Sobol sweeps,
  fan-out/fan-in evaluation, ETL);
- **scheduling, queueing, autoscaling, and cost control** — fair-share queues with quotas, node
  autoscaling (Karpenter / cluster-autoscaler), spot/preemptible bidding with checkpoint-driven
  preemption recovery, and per-tenant budgets;
- **GPU scheduling and sharing** via the GPU Operator with **MIG** partitioning and
  time-slicing, so a 16-rollout-worker job and a single-GPU surrogate fit can co-reside;
- a **run/experiment integration layer** that wires every job to **MLflow** tracking and to
  content-addressed artifact storage (S3-compatible), so a scaled run is as reproducible as a
  laptop run (conventions.md §5, §6);
- **multi-tenancy and isolation** — namespaces, RBAC, network policy, and optional vClusters —
  so multiple users and organizations share one cluster safely.

**Explicitly out of scope.** Cloud contains **no** physics, **no** autonomy, **no** learning,
and **no** UI logic. It does not know what a rollout *is*; it knows how to schedule one. It does
not define asset, world, or message schemas — it is a *consumer* of [Core](core.md) contracts and
a *runner* of other components' containers, never an extender of the waist. It is **not** a hard
dependency: the **local/dev tier MUST remain fully functional without Cloud** (conventions.md
§7, tier 1). Cloud is an accelerator — it makes the same workloads bigger and faster, never the
only way to run them. It is also not the artifact registry ([Hub](hub.md)), not the leaderboard
([Bench](bench.md)), and not the design front door ([Studio](studio.md)); it hosts and executes
for all of them.

**Primary users:** power users and organizations running large design-optimization and
policy-training campaigns; platform operators who stand up and run a cluster; and, indirectly,
every researcher whose [Studio](studio.md) trade study or [Bench](bench.md) submission fans out
onto a cluster.

**Charter alignment:** §5.7 (the Cloud package — "distributed simulation orchestration on
Kubernetes and Ray … run thousands of simulations in parallel"); §7 ("Kubernetes, Ray, and
containerization for distributed simulation and training"); §6 ("the whole loop runs at scale on
Astro-Mine-Cloud"); §11 (Phase-1 autonomy & studio scale-out).

---

## 2. Architecture principles

1. **Infrastructure, not logic.** Cloud runs other people's code; it never embeds domain logic.
   If a behavior depends on what a simulation *means*, it belongs in [Sim](sim.md)/[Learn](learn.md),
   not here. The boundary is: Cloud schedules containers and moves bytes (conventions.md §1).
2. **Local-first, never a hard dependency.** Every workload Cloud runs MUST also run on a single
   workstation with `docker compose` or a Python env (conventions.md §7, tier 1). The cluster is
   *the same container with a bigger executor* — submitting to Cloud is a backend swap, not a
   code fork. This mirrors [Learn](learn.md)'s "library first, cluster second" tenet.
3. **The right engine for the workload shape.** Tightly-coupled stateful compute (RL, actor
   fleets, distributed solves) runs on **Ray**; embarrassingly-parallel DAG batch runs on **Argo
   Workflows**; trivial one-shot containers may run as plain **Kubernetes Jobs**. We do not force
   one engine onto every shape (see §11).
4. **Reproducible by construction.** A scaled job is pinned to an OCI image digest, a Core
   interface version, content-addressed inputs, and a recorded seed; it emits provenance
   identical to a laptop run (conventions.md §5, §11). "It only reproduces on the cluster" is a
   bug.
5. **Cost is a first-class constraint.** Spot/preemptible by default, checkpoint-to-resume on
   eviction, scale-to-zero idle pools, and hard per-tenant budgets. Compute that runs longer than
   it must, or that cannot survive a preemption, is treated as a defect, not a fact of life.
6. **Multi-tenant by default, isolated by policy.** The cluster assumes more than one tenant from
   day one: namespaces, quotas, RBAC (OPA), and network policy are the baseline; stronger
   isolation (vCluster, per-tenant node pools) is a configurable tier (conventions.md §9, §12).
7. **Data comes to compute, lazily.** Workers stream only the chunks they need from
   object storage over chunked, range-readable formats (Zarr/COG/Parquet), with locality caching —
   never bulk-copy a multi-terabyte dataset to every node (conventions.md §5, §8).
8. **Portable across substrates.** The platform targets *conformant Kubernetes*, not one cloud's
   proprietary API. The same Helm/Argo/Ray deployment runs on a laptop kind/k3s cluster, a managed
   cloud cluster (EKS/GKE/AKS), or an on-prem/HPC cluster — public-cloud lock-in is avoided by
   design (see §11).
9. **Degrade, don't collapse.** Queues shed and back-pressure under load; a node pool exhausted by
   spot reclamation drains gracefully and re-queues; one tenant cannot starve another
   (conventions.md §8).

---

## 3. Application architecture

Cloud is a **platform deployment plus a thin submission/control library**, not a monolith. Most
of it is curated upstream operators wired together by an opinionated layer; the code Cloud owns is
the job contract, the submission clients, the autoscaling/cost policies, and the tenancy controls.
Its modules:

```
astro_mine.cloud
├── jobspec/         # typed job/sweep/workflow contracts (Pydantic + proto wire form)
├── submit/          # submission clients + CLI: laptop ↔ cluster, same call site
├── engines/
│   ├── ray/         # KubeRay RayJob/RayCluster templates, gang scheduling, fault recovery
│   ├── argo/        # Argo Workflow/WorkflowTemplate generation for DAG sweeps
│   └── k8sjob/      # plain Kubernetes Job/Indexed-Job path for trivial one-shots
├── sched/           # priority/fair-share queues, quotas, gang scheduling integration
├── autoscale/       # Karpenter/cluster-autoscaler policies, spot bidding, scale-to-zero
├── gpu/             # GPU Operator config, MIG profiles, time-slicing, device requests
├── data/            # object-store I/O, chunk caching, dataset staging, locality hints
├── runs/            # MLflow wiring, provenance capture, artifact addressing
├── tenancy/         # namespaces, RBAC/OPA, network policy, vCluster provisioning, budgets
└── platform/        # Helm charts / operators bootstrap; observability stack install
```

### Key abstractions exposed

- **JobSpec** — the core contract: a containerized unit of work (image digest, command, resource
  request incl. GPU/MIG profile, content-addressed inputs, output URI, seed, tenant, priority,
  budget cap). Every higher construct compiles down to JobSpecs.
- **SweepSpec** — a parameter space (grid / random / Sobol / Optuna-driven) over a base JobSpec,
  compiled to an Argo fan-out (or a Ray Tune run for adaptive search).
- **WorkflowSpec** — an explicit DAG of JobSpecs with dependencies and fan-in (e.g. generate
  scenarios → run sims → aggregate → score), compiled to an Argo Workflow.
- **RayJob handle** — a tightly-coupled distributed job (a RayCluster lifecycle + entrypoint),
  for [Learn](learn.md) training, actor-based rollout fleets, and distributed [Allocate](allocate.md)
  solves.
- **RunContext** — the reproducibility envelope auto-attached to every execution: MLflow run id,
  input hashes, image digest, Core interface version, seed, lockfile reference.

### Extension / plugin points

- **Executor backends** behind the `engines/` interface (Ray, Argo, K8s Job today; Dask or a
  SLURM/HPC adapter pluggable for on-prem — see §11).
- **Scheduler plugins** (Kueue/Volcano/Yunikorn) selectable behind `sched/` for gang scheduling
  and fair-share.
- **Autoscaler/cost provider** behind `autoscale/` (Karpenter on AWS, cluster-autoscaler
  elsewhere, on-prem static pools).
- **Tenancy backend** behind `tenancy/` (namespace-per-tenant vs vCluster-per-tenant vs
  cluster-per-tenant).

Following conventions.md §1, none of these create side channels: a workload still reaches the rest
of the platform only through Core contracts and content-addressed artifacts.

### Interaction patterns

A submission flows: client builds a `JobSpec`/`SweepSpec` → `submit/` validates and resolves
inputs to content hashes → the chosen engine compiles it to Ray/Argo/K8s objects → `sched/`
admits it against the tenant's quota and queue → `autoscale/` provisions nodes (spot first) →
pods pull the pinned image, stream inputs from object store, run, checkpoint, and write
content-addressed outputs → `runs/` records provenance to MLflow and emits a completion event on
**NATS/JetStream** (conventions.md §4) that [Bench](bench.md), [Studio](studio.md), or [Hub](hub.md)
consume. The *exact same* `submit()` call, with a `local` backend, runs the job in-process or via
`docker compose` on a workstation.

**Mission-design sweeps.** The new design-time workloads compile onto the existing
abstractions with no new construct: a porkchop / launch-window scan or an OpenMDAO design sweep is a
`SweepSpec`/`WorkflowSpec` fanned out by **Argo** (embarrassingly-parallel, DAG); a pygmo
island-model global optimization, whose islands exchange candidates, maps onto a tightly-coupled
**RayJob** like a distributed [Allocate](allocate.md) solve. Both consume content-addressed
`MissionSpec`/`TrajectoryRef` inputs and emit content-addressed artifacts, so a mission trade study
reproduces exactly (see [mission-model](mission-model.md), conventions.md §5, §11).

---

## 4. Application programming & runtime platforms

- **Languages:** **Python 3.12+** for the submission library, CLI, sweep/workflow compilation,
  and control glue (conventions.md §2). Performance-sensitive controllers and CLIs MAY use
  **Rust** where it pays off (e.g. high-throughput artifact-staging tooling). YAML/Helm for
  declarative cluster config.
- **Substrate:** **Kubernetes** (conformant; v1.29+) is the only assumed substrate
  (conventions.md §7). All capability is delivered through operators and CRDs, not bespoke
  daemons where an upstream operator exists.
- **Execution engines / operators:**
  - **Ray + KubeRay** (RayCluster / RayJob / RayService CRDs) for distributed RL, Tune-driven
    sweeps, actor rollout fleets, and distributed solves (conventions.md §6).
  - **Argo Workflows** (Workflow / WorkflowTemplate / CronWorkflow) for DAG batch sweeps and
    fan-out/fan-in evaluation.
  - **Kubernetes Jobs / Indexed Jobs** for trivial one-shot containers.
  - **NVIDIA GPU Operator** (with the MIG manager and DCGM exporter) for GPU drivers,
    scheduling, MIG partitioning, and GPU telemetry.
- **Scheduling:** **Kueue** for job queueing, quotas, and fair-share is the recommendation;
  **Volcano** or **Apache YuniKorn** are alternatives where richer gang/batch scheduling is needed
  (see §11). KubeRay integrates with the chosen gang scheduler.
- **Autoscaling:** **Karpenter** (AWS) or **cluster-autoscaler** (portable) for nodes; the Ray
  autoscaler for in-cluster worker elasticity; KEDA for event-driven scale of queue consumers.
- **Packaging & runtime model:** every workload is an **OCI image** pinned by digest, built
  reproducibly on pinned bases (conventions.md §7). The platform itself ships as **Helm charts**
  (and an optional umbrella chart / GitOps repo for Argo CD or Flux). Cloud's own compilation and
  submission code ships in the [`astro-mine-platform`](platform.md) wheel; its submission *service*
  ships in [`astro-mine-api`](api.md). Runtime model is **stateless control + ephemeral
  workers**: durable state lives in PostgreSQL (catalog/metadata), object storage (artifacts),
  and Redis (queues/cache), per conventions.md §5.

---

## 5. Data architecture

Cloud **owns almost no domain data** — it moves and stages other components' data and owns only
execution metadata.

| Data | Format / store | Notes |
|---|---|---|
| Datasets consumed by jobs (DEMs, resource fields, sim outputs) | **Zarr**, **COG**, **Parquet**, **MCAP** in **S3-compatible object storage** | Read lazily, chunk-range from object store; never bulk-copied (conventions.md §5, §8). |
| Job outputs (sweep results, trained policies, eval batches) | **content-addressed** objects in the same S3-compatible store | Written by jobs, addressed by hash; ownership/indexing is [Hub](hub.md)'s, not Cloud's. |
| Run/experiment metadata | **MLflow** (backed by **PostgreSQL** + object store) | Every job is an MLflow run with params, metrics, and the `RunContext` envelope (conventions.md §6). |
| Job/workflow/queue state | **PostgreSQL** (Argo, Kueue) + Kubernetes etcd (CRDs) | Authoritative scheduling/lifecycle state. |
| Queues, locks, ephemeral cache | **Redis** | Submission queues, dedup, short-lived coordination (conventions.md §5). |
| Cluster & job metrics | **Prometheus** (+ **TimescaleDB** for high-rate/cost-accounting queries) | Drives autoscaling, cost reports, and dashboards (conventions.md §5, §10). |
| Lifecycle events | **NATS + JetStream** | Job submitted/started/checkpointed/completed/failed events (conventions.md §4). |

**Object storage portability:** S3-compatible everywhere — **MinIO** self-hosted/on-prem, native
**S3/GCS/Azure Blob** in cloud — accessed through one S3 client so workloads are storage-portable.

**Data locality strategy.** Large Zarr/COG datasets are *not* staged whole. The recommendation is a
**lazy chunk-streaming + caching** model: workers read chunks on demand; a node- or cluster-local
read cache (a pull-through cache layer such as JuiceFS/Alluxio, or a CSI-mounted cache, or simply a
warmed local-NVMe scratch tier) keeps hot chunks near compute. For sweeps that re-read the same
slices across thousands of jobs, Cloud can pre-warm a shared dataset cache and co-schedule jobs to
cache-warm nodes (locality hints in `data/`). Region/zone co-location of the cluster with the
object store is enforced to avoid cross-zone egress cost and latency. See §8 and §11.

**Lifecycle, provenance, versioning.** Inputs are resolved to content hashes at submit time;
outputs are content-addressed; every run records inputs, image digest, Core interface version,
lockfile, and seed (conventions.md §5, §11) — so a scaled result reproduces exactly. Object-store
**lifecycle policies** tier/expire scratch and intermediate artifacts; durable results graduate to
[Hub](hub.md). The `astro-mine-cloud` wheel and Helm charts are **SemVer**'d (conventions.md §7,
§13).

---

## 6. Integration architecture

Cloud sits *under* the platform: it executes workloads defined by siblings and connects through
Core contracts and content-addressed artifacts (conventions.md §1, §5). It defines **no new Core
schema** — it consumes them.

- **[Sim](sim.md)** — Cloud fans out scenario sweeps and digital-twin batches as Argo workflows or
  Ray jobs; Sim provides the scenario runtime image, Cloud the parallelism.
- **[Learn](learn.md)** — the headline tightly-coupled tenant: distributed MARL training runs as
  **RayJobs** on KubeRay (the exact integration Learn's docs assume); Cloud supplies gang
  scheduling, GPU/MIG, and spot+checkpoint resilience.
- **[Allocate](allocate.md)** — large CP-SAT/OR-Tools and learned-heuristic solves run as RayJobs or
  parallel K8s Jobs for portfolio/parameter solving at scale.
- **[Surrogate](surrogate.md)** — surrogate-fitting training jobs and bulk inference batches; GPU
  scheduling and MIG sharing are central here.
- **[Bench](bench.md)** — Cloud runs leaderboard evaluation batches as reproducible DAG workflows;
  Bench pins Core interface versions and seeds, Cloud guarantees the pinned, content-addressed
  execution environment. Completion events feed Bench's ingestion.
- **[Studio](studio.md)** — backs Studio's heavy design/trade-study jobs: a "goal-in, design-out"
  exploration becomes a sweep submitted to Cloud, results streamed back for ranking.
- **[Hub](hub.md)** — Cloud reads input artifacts (worlds, assets, policies, plugin OCI bundles)
  from and writes result artifacts to the content-addressed store that Hub indexes; Cloud also
  **hosts** Hub and other platform services as cluster deployments.
- **[Core](core.md)** — Cloud workloads carry a declared Core interface version; the `RunContext`
  records it; incompatible images are refused at admission.

**Protocols & flows.** Submission is **gRPC/REST** (FastAPI edge) into the control plane;
lifecycle eventing is **NATS/JetStream**; service-to-service is **gRPC over mTLS** (conventions.md
§3, §4, §9). Recorded outputs use **MCAP**/Parquet/Zarr per the data plane (conventions.md §4, §5).

---

## 7. Infrastructure & deployment

- **Deployment tier:** the **Cloud** tier (conventions.md §7, tier 2) — K8s + Ray scale-out — and
  Cloud *is* the implementation of that tier. It does **not** run in the local/dev tier; it makes
  that tier optional-to-exceed, never required.
- **Compute profile:** heterogeneous node pools. A **CPU pool** for control plane, Argo
  fan-out sweeps, and CPU-bound solves; one or more **GPU pools** (e.g. A100/H100/L4) for
  [Learn](learn.md), [Surrogate](surrogate.md), and GPU-accelerated [Sim](sim.md). Node sizing is
  workload-driven: RL learners want few large GPU nodes with high interconnect; rollout/sweep
  workers want many small spot nodes; memory-heavy solves want high-RAM CPU nodes. **MIG**
  partitions a single GPU (e.g. A100 → 7×10 GB slices) so small inference/fit jobs share one card.
- **Containerization:** all workloads are OCI images pinned by digest, multi-arch where relevant,
  reproducibly built on pinned bases (conventions.md §7). GPU images layer on the CUDA runtime via
  the GPU Operator's device plugin.
- **Orchestration:** Kubernetes + KubeRay + Argo + GPU Operator + the chosen queue (Kueue) and
  autoscaler (Karpenter/cluster-autoscaler). Installed via **Helm**, lifecycle-managed via **GitOps**
  (Argo CD or Flux) for reproducible, auditable cluster state.
- **Scaling:** three nested levels — (1) **node autoscaling** (Karpenter/cluster-autoscaler) adds/
  removes nodes per pending pods, spot-first, scale-to-zero idle GPU pools; (2) **job-level
  elasticity** (Ray autoscaler grows/shrinks worker counts mid-run; Argo parallelism caps); (3)
  **queue admission** (Kueue) holding work until quota/capacity is available so the cluster degrades
  gracefully under contention.
- **Substrate portability:** managed K8s (EKS/GKE/AKS) for the default cloud deployment; self-hosted
  or **on-prem/HPC** via conformant K8s; a tiny **kind/k3s** profile lets a developer exercise the
  *same* charts locally for testing the platform itself (distinct from the dependency-free local
  tier, which needs no K8s at all).

---

## 8. Performance & scalability

This is Cloud's reason to exist: turning a laptop-scale workload into thousands of parallel ones
without losing reproducibility or blowing the budget.

**Targets (Phase-1 working figures, to be made reproducible per conventions.md §8):**

- **Throughput:** schedule and run **10³–10⁴ concurrent sim/eval tasks** in a sweep; sustain a
  steady-state pipeline of thousands of short tasks with sub-minute scheduling latency at the
  queue.
- **Scaling efficiency:** ≥ **80–90 %** for embarrassingly-parallel Argo sweeps (near-linear with
  nodes); for tightly-coupled RL on Ray, near-linear rollout throughput with worker count until the
  learner/aggregation step becomes the bound.
- **GPU utilization:** keep allocated GPUs busy; MIG/time-slicing pushes effective utilization up
  for small jobs that would otherwise strand a whole card.
- **Cost:** majority of compute on **spot/preemptible**; checkpoint-to-resume keeps wasted work on
  eviction small (target: lose ≤ one checkpoint interval).

**Bottlenecks & mitigations:**

| Bottleneck | Mitigation |
|---|---|
| **Object-store I/O fan-in** (thousands of workers reading the same Zarr/COG) | Lazy chunk-range reads; pull-through/locality cache (JuiceFS/Alluxio or NVMe scratch); pre-warm + co-schedule to cache-warm nodes; co-locate cluster with store (§5). |
| **Scheduling latency / thundering herds** at sweep submit | Kueue admission + queue back-pressure; batch pod creation; Indexed Jobs / Argo `parallelism` caps instead of N independent pods. |
| **GPU stranding** (small jobs holding whole cards) | MIG partitioning + time-slicing; bin-pack small GPU jobs onto MIG slices; separate GPU pools by size class. |
| **Ray learner/aggregation as the serial bound** in RL | Scale rollout workers horizontally; keep learner on a high-interconnect node; async/decoupled learner where the algorithm allows (Learn's concern, Cloud provides topology). |
| **Spot reclamation** mid-run | Frequent, content-addressed checkpoints to object store; preemption-aware draining; automatic re-queue + resume; mixed spot/on-demand for the irreplaceable learner. |
| **Control-plane / etcd pressure** from huge fan-outs | Prefer Indexed Jobs and Argo over thousands of discrete objects; CRD/object TTL cleanup; archive completed workflows to Postgres+object store. |
| **Cross-zone egress cost/latency** | Zone-affinity scheduling; cluster and object store co-located; locality hints in `data/`. |

**Scaling strategy.** Horizontal at every level (conventions.md §8): stateless control plane
behind a load balancer with state in Postgres/Redis/object store; workers fan out across
spot-first autoscaled pools; data stays chunked and range-read so workers stream only their
slices. Multi-fidelity is exploited *for* cost — cheap surrogate/low-fidelity tiers run massively
parallel on cheap spot CPU, high-fidelity validation runs on fewer, reliable nodes. Every
performance claim ships with a reproducible benchmark (conventions.md §8).

**Mission-design sweeps.** The trajectory/sizing/ledger sweeps are largely **CPU-bound**
(vs the GPU sim/training workloads), so they fan out on the cheap spot CPU pools at the same
scaling-efficiency targets as Argo batch above. They follow the same **spot/preemptible +
checkpoint-to-resume** discipline: a porkchop scan check-points per-window and a pygmo island run
check-points per-generation, so an eviction loses at most one interval.

---

## 9. Security, safety & compliance

Multi-tenancy isolation is the central security concern: Cloud runs *others' code* for *multiple
tenants* on *shared hardware*.

- **AuthN/AuthZ:** OIDC (Keycloak/cloud IdP) for users; **RBAC enforced via OPA** for fine-grained,
  auditable authorization on submission, quota, and namespace access (conventions.md §9). Service
  accounts are least-privilege per workload.
- **Multi-tenancy isolation (tiered, see §11):**
  - *Baseline:* **namespace-per-tenant** with Kubernetes RBAC, **ResourceQuotas/LimitRanges**,
    **NetworkPolicies** (default-deny), and **Kueue** fair-share quotas.
  - *Stronger:* **vCluster-per-tenant** for control-plane isolation (each tenant sees its own API
    server) without full cluster duplication.
  - *Strongest:* **cluster-per-tenant** or dedicated node pools for organizations with hard
    isolation or compliance requirements.
- **Workload sandboxing:** untrusted/community workloads (plugin bundles, third-party policies) run
  with **seccomp**, dropped capabilities, read-only root FS, and **gVisor** (or Kata) runtime
  isolation; WASM (wasmtime) is the forward-looking sandbox for safe untrusted compute
  (conventions.md §9). Cloud never runs unsigned images in shared tenancy.
- **Service mesh / transport:** **mTLS** between services (Linkerd optional, conventions.md §9).
- **Secrets:** External Secrets Operator + Vault/cloud KMS; no secrets in images or charts
  (conventions.md §9).
- **Supply chain:** only **cosign-verified** images with **SLSA** provenance and an **SBOM**
  (Syft/CycloneDX) are admitted — enforced at the cluster boundary by an admission controller (OPA
  Gatekeeper / Kyverno) (conventions.md §9). Pinned, reproducible base images.
- **Export control / dual use:** Cloud is execution infrastructure and is open by default, but it is
  the **enforcement point** for capability gating: workloads carrying export-controlled capability
  tags (from Core manifests, charter §9.5) are admitted only into partitioned, access-controlled
  tenants/clusters, and such partitions can be operated separately (conventions.md §12). Cloud
  records who ran what, where, for audit.
- **Cost as a safety rail:** hard per-tenant **budget caps** and quota ceilings prevent a runaway
  sweep from exhausting shared capacity or spend — a denial-of-service and a financial control at
  once.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** SDK in the control plane and submission clients → traces,
  metrics, logs (conventions.md §10). A sweep is traceable end to end: submit → admit → schedule →
  per-task run → aggregate → result.
- **Metrics & dashboards:** **Prometheus** + **Grafana**; **DCGM** GPU metrics from the GPU
  Operator; Kueue/Argo/Ray exporters for queue depth, parallelism, and cluster-utilization
  dashboards. **TimescaleDB** backs high-rate cost-accounting and utilization queries.
- **Logs:** structured JSON aggregated with **Loki**; per-job logs addressable by run id and
  archived with the run's artifacts.
- **Cost observability:** per-tenant / per-job cost attribution (node-hours × instance price, spot
  vs on-demand, GPU-MIG fractions) surfaced as dashboards and enforced against budgets — operability
  for an org footing the bill.
- **Health & SLOs:** liveness/readiness on control-plane services; SLOs on scheduling latency, job
  success rate, and queue wait time (conventions.md §10).
- **Testing & validation:** `pytest` for the submission library and compilers; **ephemeral
  kind/k3s clusters in CI** to integration-test Helm charts, engine compilation, and the
  local↔cluster backend-equivalence guarantee; chaos/preemption tests that kill spot nodes mid-run
  and assert checkpoint-resume correctness; **golden-run determinism gates** asserting a cluster run
  reproduces the laptop run for the same inputs+seed (conventions.md §11). Load tests submit large
  synthetic sweeps to validate scheduling-latency and back-pressure targets.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Compute-orchestration engine** | Ray/KubeRay; Argo Workflows; plain K8s Jobs; Dask; SLURM/HPC | **Ray/KubeRay for tightly-coupled RL/actors/solves + Argo Workflows for DAG batch sweeps**; K8s Indexed Jobs for trivial one-shots. Dask as an optional backend for dataframe/array ETL; SLURM/HPC via a pluggable adapter for on-prem HPC tenants. |
| **Substrate** | Managed K8s (EKS/GKE/AKS); self-hosted K8s; on-prem/HPC | **Conformant Kubernetes, substrate-agnostic.** Default to managed in cloud for operability; self-host/on-prem supported via the same charts. Never depend on a single cloud's proprietary API. |
| **Job queue / gang scheduler** | Kueue; Volcano; Apache YuniKorn; default scheduler | **Kueue** for quotas + fair-share (clean, K8s-native, KubeRay integration); **Volcano** where heavy gang/HPC-style scheduling is needed. |
| **Node autoscaler** | Karpenter; cluster-autoscaler; static pools | **Karpenter on AWS** (fast, flexible, spot-savvy); **cluster-autoscaler** for portability/other clouds; static pools on-prem. |
| **Cost optimization** | On-demand only; spot/preemptible + checkpointing; reserved/committed | **Spot/preemptible-first with content-addressed checkpoint-resume**; on-demand only for the irreplaceable RL learner; reserved/committed for steady baseline. |
| **Multi-tenancy isolation** | Namespace-per-tenant; vCluster; cluster-per-tenant | **Namespace-per-tenant baseline**, **vCluster** for stronger control-plane isolation, **cluster-per-tenant** for hard-isolation/compliance orgs — tiered by need. |
| **Object storage** | MinIO (self-host); S3/GCS/Azure Blob | **S3-compatible abstraction** over MinIO (on-prem) and native cloud object stores; one client, storage-portable (conventions.md §5). |
| **Data locality for large Zarr/COG** | Stream-only; pull-through cache (JuiceFS/Alluxio); full pre-stage | **Lazy chunk-stream + pull-through/locality cache + pre-warm for hot shared datasets**; co-locate cluster with store. Full pre-stage only for small, repeatedly-scanned sets. |
| **Experiment tracking** | MLflow; Weights & Biases | **MLflow** (OSS default, self-hostable on-cluster); W&B as a hosted option (conventions.md §6). |
| **GitOps / install** | Helm only; Helm + Argo CD/Flux | **Helm packaging + GitOps (Argo CD or Flux)** for reproducible, auditable cluster state. |

**Mission-design sweeps.** No new decision row is needed: the design-time
trajectory/sizing/ledger sweeps reuse the existing **Ray (tightly-coupled) + Argo
(DAG/embarrassingly-parallel)** split — porkchop/window scans and OpenMDAO sweeps on Argo,
island-model global optimization on Ray — with the same spot/preemptible + checkpointing and
content-addressing recommendations above.

**Open questions / research dependencies:**

- **Tightly-coupled scaling limits for MARL** — where the Ray learner/aggregation step becomes the
  bound at swarm scale; co-designed with [Learn](learn.md) (async learners, sharded aggregation).
- **Optimal data-locality layer** — whether a pull-through FS (JuiceFS/Alluxio) beats CSI-cache or
  warmed-NVMe scratch for the platform's Zarr/COG access patterns; resolve empirically with
  [Worlds](worlds.md)/[Prospect](prospect.md) dataset profiles.
- **Spot interruption economics** — checkpoint cadence vs eviction-loss trade-off per workload
  class; needs measured eviction-rate data per region/instance.
- **HPC adapter scope** — how far to support SLURM/HPC tenants without forking the engine
  abstraction; depends on on-prem/academic uptake.
- **Capability-gating enforcement model** — how partitioned, export-controlled tenancy is operated
  and audited in practice; co-designed with governance/export-control (conventions.md §12).

---

## 12. Roadmap alignment

- **Phase 0 (underpinning):** Cloud is not a Phase-0 *deliverable*, but its principles shape Phase 0
  — every Phase-0 workload ([Sim](sim.md), [Bench](bench.md)) is built **container-first and
  cluster-ready** so it scales out later without rework. The dependency-free local tier
  (conventions.md §7) is what Phase 0 actually requires; Cloud must never compromise it.
- **Phase 1 (ship):** the MVP — a Helm-installable platform on conformant K8s with **KubeRay** for
  [Learn](learn.md) training, **Argo Workflows** for [Sim](sim.md)/[Bench](bench.md) sweeps,
  **K8s Jobs** for one-shots, **Kueue** queueing, spot+checkpoint cost optimization, the **GPU
  Operator + MIG**, S3-compatible artifact I/O, **MLflow** integration, and namespace-per-tenant
  isolation. This makes the design/training loop (charter §5) runnable "at scale on
  Astro-Mine-Cloud" and backs [Studio](studio.md)'s heavy jobs and first public
  [Bench](bench.md) leaderboards.
- **Phase 3 (multi-regime missions):** schedule the mission-design sweep workload classes
  ([Trajectory](trajectory.md)/[Sizing](sizing.md)/[Ledger](ledger.md)) as additional Ray/Argo
  workloads on the same substrate — no new infra primitive (Core schema hooks land Phase 1).
- **Phase 2+:** stronger multi-tenancy (vCluster / per-tenant clusters), on-prem/HPC adapters,
  advanced data-locality caching, refined cost/budget governance, and hosting the operations-tier
  services as the platform crosses into the operations loop. The measure of success: the *same*
  container that ran on a laptop runs unchanged across thousands of nodes — Cloud added scale, not
  a second codebase.
