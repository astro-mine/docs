# Astro-Mine-Hub — Technology Architecture

> Layer: **Commons backbone & platform infrastructure** · Phase: **1** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> The registry for sharing and discovering everything the community produces — plugins,
> worlds, assets, policies, and surrogate models — indexed by their [Core](core.md) manifest.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Hub` is the **artifact registry and discovery service** for the commons. It is the
place a contributor *publishes* a trained policy, a parameterized world, a SADF asset bundle, a
surrogate model, or any plugin — and the place every other component, tool, and human *finds,
verifies, and pulls* those artifacts. It is, in the spirit of a model hub (Hugging Face Hub,
PyPI, an OCI registry, the ROS package index), the network that compounds the project's value:
contribute once, and the contribution is discoverable, versioned, signed, and reusable across
design, training, operations, and benchmarks.

Hub does, and only does:

- **Stores** content as **content-addressed OCI artifacts** (plugins, worlds, assets, ONNX
  policies, surrogate models, schema bundles, datasets) — see conventions.md §7;
- **Indexes** every artifact by its [Core](core.md) **plugin manifest** (kind, the Core
  interface versions it implements, capability tags, inputs/outputs, provenance, signature);
- **Discovers** — faceted browse, full-text and **semantic** search, and **capability
  negotiation** against manifests ("find me an ONNX excavation policy compatible with Core
  policy-API v1 and these SADF capability tags");
- **Verifies** supply-chain integrity on the way in and on the way out: signature, SLSA
  provenance, and SBOM checks (conventions.md §9);
- **Resolves** dependencies and compatibility between artifacts via SemVer + Core interface
  ranges;
- **Gates** downloads by license and export-control/dual-use policy.

**Mission-architecture artifacts (RFC-0001).** When multi-regime missions land (Phase 3), the same
registry indexes new shareable artifact *types* by their [Core](core.md) manifest: **mission
templates / `MissionSpec`s** (see [mission-model](mission-model.md)), **`TrajectoryRef`/`ManeuverBudget`
libraries** ([Trajectory](trajectory.md) — *descriptive, design-time* reference arcs, **not**
executable guidance), **sized spacecraft designs** (SADF configs from [Sizing](sizing.md)), and
**open economics / value models** from [Ledger](ledger.md). They are stored, signed, indexed, and
served exactly like every other artifact — Hub still never executes them.

**Explicitly out of scope.** Hub does *not* execute, simulate, train, or score anything — it
**distributes the artifacts** that [Sim](sim.md), [Learn](learn.md), and [Bench](bench.md) act
on. It does **not** define the manifest or capability vocabulary — that is [Core](core.md)'s;
Hub is a *consumer* of the Core manifest schema, never its owner. It does **not** run the
leaderboard or reproducibility harness — that is [Bench](bench.md); Hub stores the artifacts a
submission references and links results back by content hash. It does **not** own the underlying
cluster — it is *deployed on* [Cloud](cloud.md). It is **not** a generic Docker registry for
runtime service images (those live in the org's CI registry); Hub curates *content* artifacts
described by Core manifests.

**Primary users:** **everyone** — researchers publishing and pulling policies/worlds/assets,
mission designers in [Studio](studio.md) pulling a fleet and a candidate policy, [Bench](bench.md)
resolving the exact artifacts behind a leaderboard entry, and any component that loads a plugin
through the Core registry.

**Charter alignment:** §5.7 (Hub: "registry for sharing and discovering ... in the spirit of a
model hub ... the network that compounds the project's value"), §10.2 (extension points
everywhere — every category of content is a plugin), §10.3 (the academic flywheel — Bench +
leaderboards + Hub are the growth engine), and §10.5 (interop-first; honest about dual use).

---

## 2. Architecture principles

1. **Content-addressed, immutable artifacts.** Every byte stored is addressed by its digest
   (sha256). A given `name:version` resolves to one immutable digest; tags are mutable pointers,
   digests are forever. This is what makes a [Bench](bench.md) result or a provenance chain
   exactly reproducible (conventions.md §5).
2. **The manifest is the index, not Hub's invention.** Hub indexes artifacts by the
   [Core](core.md) plugin manifest and refuses to invent its own parallel metadata schema for
   anything Core already describes. If discovery needs a field, the field belongs in the Core
   manifest (via RFC), not as a Hub-private extension.
   **The one thing Core does not describe is container shape**, and that is Hub's to name. An
   artifact's `artifact_kind` — the payload shape behind its `application/vnd.astro-mine.<kind>.v1`
   media type — is a *packaging* fact, whereas `PluginKind` enumerates the *interfaces* a plugin
   implements. The two overlap on four names and diverge elsewhere, and they cannot be collapsed:
   a served surrogate's Core kind is `field_model` or `regime_engine` depending on its physics
   domain, so no total map from container to interface exists. Widening Core to absorb container
   names would put a packaging concern in the narrow waist (core.md §2 principle 1). A catalog
   entry therefore carries **both, as separate queryable facets** — never one field holding two
   vocabularies — and Hub derives the container kind from the stored OCI `artifactType` rather
   than from a publisher's claim, so it cannot drift from the bytes.
3. **Verify before you trust — twice.** Signature, provenance, and SBOM are checked at
   **publish** (admission) *and* at **pull** (the client re-verifies). A compromised registry
   must not be able to serve an artifact a client accepts. Unsigned content is never promoted to
   a verified namespace — indeed it is never **admitted**: §9's tiers describe *open* as
   self-published and *signed*, so there is no tier for unsigned content and admission refuses
   it outright. Admission is **one gate** shared by the client library, the publish endpoint, and
   curation: three routes to the index is how a check ends up present on one path and missing
   from another, and a partially-admitted artifact — bytes stored, evidence absent, entry
   queryable — is the state the gate exists to prevent, so a failed check indexes nothing.
4. **Discovery is capability negotiation, not string matching.** Consumers ask "what satisfies
   *this* contract" (Core interface versions + capability tags + SADF/world constraints), and
   Hub answers from manifests — mirroring how Core itself negotiates at load time.
5. **Open to read, governed to write.** Anonymous discovery and pull of public, non-gated
   artifacts is frictionless; *publishing*, *verified-publisher* status, and *gated* downloads
   are authenticated and policy-controlled. **Shipped today:** download gating (OPA) and
   admission verification, which constrain *what* may be published regardless of who asks.
   **Deferred:** caller **authentication** on the write path — see §9.
6. **Standards in, standards out.** Hub speaks the **OCI Distribution Spec** so any
   `oci`/`oras`/`docker`/`cosign` client interoperates; there is no proprietary push/pull
   protocol. The value is in the *index and policy*, not in lock-in.
7. **Library first, service second.** A client SDK (`astro-mine-hub`) resolves, verifies, and
   caches artifacts on a single workstation against any OCI registry; the hosted service is a
   deployment of that capability, not a separate stack (conventions.md §1, tenet 4).
8. **Honest about dual use at the download boundary.** License and export-control gating
   (conventions.md §12) are first-class admission/egress decisions, evaluated against manifest
   capability tags — not an afterthought bolted onto a UI.
9. **Degrade, don't disappear.** Search may fall back to faceted/keyword when the embedding
   index is unavailable; pull must keep working from object storage + registry even if the
   metadata DB is degraded, because pull is reproducibility-critical.

---

## 3. Application architecture

Hub is a **service**: an OCI-compatible registry plus an index/discovery/policy plane in front
of it, plus a web UI and a client SDK. Its subsystems:

```
astro_mine.hub
├── registry/        # OCI Distribution Spec endpoint (blobs, manifests, tags, referrers)
├── index/           # manifest ingestion → Postgres catalog; faceted + semantic index
├── search/          # query planner: facets + full-text + pgvector semantic + capability match
├── resolve/         # SemVer + Core interface-range dependency & compatibility resolution
├── supply_chain/    # cosign verify, SLSA provenance, SBOM (Syft/CycloneDX), attestations
├── policy/          # OPA gate: authz, license & export-control download gating, namespace rules
├── curation/        # namespaces, verified publishers, review/moderation, deprecation/yank
├── api/             # REST + OpenAPI 3.1 (FastAPI) façade over the above
├── ui/              # TypeScript + React web front-end (browse, compare, artifact pages)
└── client/          # astro-mine-hub Python/CLI SDK: resolve, verify, pull, cache, publish
```

### Key abstractions exposed

- **Artifact** — an immutable, content-addressed OCI artifact with a typed
  `artifactType`/config (e.g. `application/vnd.astro-mine.policy.v1`,
  `…world.v1`, `…asset.v1` for SADF bundles, `…surrogate.v1`, `…plugin.v1`). Its OCI manifest
  layers carry the payload (an ONNX file, a USD/glTF + SADF bundle, a Zarr/COG world, a
  surrogate checkpoint) and reference the **Core plugin manifest** as a layer/config.
  **(RFC-0001)** The mission-architecture types add `…mission.v1` (a `MissionSpec`),
  `…trajectory.v1` (a descriptive `TrajectoryRef`/`ManeuverBudget`), `…asset.v1` for *sized* SADF
  designs, and `…economics.v1` (a [Ledger](ledger.md) value model) — each indexed by the same Core
  manifest, with the same content-addressing and attestations. Those are **container** kinds, so
  adding them is a Hub change (an append to its vocabulary) and not automatically a Core RFC —
  a Core RFC is needed only if they also introduce a new *interface* (principle 2).
- **Catalog record** — the indexed projection of an artifact's Core manifest into Postgres:
  `kind`, `core_interface_versions[]`, `capability_tags[]`, `inputs/outputs`, `license`,
  `provenance`, `signatures[]`, plus Hub-side facets (downloads, publisher, namespace, the
  container `artifact_kind`, semantic embedding vector). `kind` and `artifact_kind` are separate
  axes — the Core interface and the payload shape — and are queried independently.
- **Reference / attestation graph** — via the **OCI Referrers API**, signatures, SLSA
  provenance, and SBOMs attach to an artifact by digest; Hub exposes the full attestation set
  for any artifact.
- **Resolution request** — "give me the artifact(s) satisfying this constraint set
  (name/version range, Core interface range, required capability tags, target world/SADF)"; Hub
  returns pinned digests plus the transitive dependency closure.

### Extension / plugin points

- **Artifact-kind handlers** (plugins): per-`artifactType` validators and metadata extractors
  (e.g. an ONNX-policy handler that reads the model's I/O signature; a world handler that reads
  STAC/CRS metadata). New content kinds register a handler rather than patching Hub core
  (charter §10.2).
- **Policy bundles** (OPA): admission and download policies are data-driven Rego bundles, so
  governance/export-control rules evolve without code changes.
- **Search providers:** the semantic/full-text backend is swappable behind the `search/`
  interface (pgvector default; OpenSearch optional at scale).
- **Storage drivers:** the OCI registry's blob backend is any S3-compatible store.

### Interaction patterns

- **Publish:** client → `api/` (or direct OCI push via `oras`/`cosign`) → `supply_chain/`
  admission (verify signature/provenance/SBOM) → `curation/`/`policy/` namespace rules →
  `registry/` stores blobs → `index/` ingests the Core manifest into the catalog and computes
  the embedding. A NATS event (`hub.artifact.published`) is emitted (conventions.md §4).
- **Discover:** UI/SDK/[Studio](studio.md) → `api/` → `search/` (facets + full-text + pgvector
  + capability match) → ranked catalog records with attestation status.
- **Pull/resolve:** consumer → `resolve/` pins digests + dependency closure → `policy/` checks
  license/export gating → client downloads via OCI + **re-verifies** signatures/provenance
  locally before the [Core](core.md) registry loads the plugin.

---

## 4. Application programming & runtime platforms

- **Languages.** Control/API/index/policy planes in **Python 3.12+** (conventions.md §2); the
  **registry data path** (high-throughput blob/manifest serving) uses a mature OCI registry
  implementation rather than re-implementing the Distribution Spec (see §11). Performance- and
  safety-sensitive client tooling (content-addressed verification, resolution) MAY use **Rust**
  per conventions.md §2 ("content-addressed registry tooling"). The web UI is
  **TypeScript + React** (conventions.md §2).
- **Frameworks & libraries.** **FastAPI** + **Pydantic v2** for the REST/OpenAPI 3.1 façade
  (conventions.md §3); **ORAS** (OCI Registry As Storage) libraries for artifact push/pull of
  non-image content; **Sigstore `cosign`/`sigstore-python`** for signing/verification;
  **Syft + CycloneDX/SPDX** for SBOMs; **`in-toto`/SLSA** verifiers for provenance;
  **Open Policy Agent (OPA)** for authz + gating; **SQLAlchemy + Alembic** over PostgreSQL;
  **pgvector** for embeddings; **packaging`/`semver`** for version-range resolution.
- **Manifest handling.** Hub generates its catalog model from the [Core](core.md) plugin
  manifest schema (the same `buf`/`datamodel-code-generator` outputs Core publishes,
  conventions.md §3) — it does not hand-maintain a copy.
- **Runtime model.** Stateless API/index/search/policy services behind a load balancer; state
  in PostgreSQL, the OCI registry, S3-compatible object storage, and **Redis** (cache, rate
  limits, ephemeral resolution state) per conventions.md §5. Async work (embedding computation,
  SBOM scanning, mirror/replication) runs off a **NATS + JetStream** queue (conventions.md §4).
- **Build & packaging.** OCI service images, multi-arch, reproducible, pinned bases
  (conventions.md §7); the client ships as the `astro-mine-hub` Python wheel + CLI; SemVer
  throughout (conventions.md §13).

---

## 5. Data architecture

Hub **owns the distribution and index** of artifacts; it does **not** own their *schemas*
(Core) or their *semantics* (the producing component).

**Data produced / owned:**

- **Catalog metadata** in **PostgreSQL** (conventions.md §5): one row per artifact version with
  the indexed manifest projection (kind, Core interface versions, capability tags, license,
  provenance, publisher, namespace), download/usage counters, deprecation/yank status, and the
  **pgvector** embedding for semantic search. PostGIS is available where artifacts carry a
  spatial extent (e.g. a [Worlds](worlds.md) region).
- **Supply-chain attestations** stored as OCI referrers alongside each artifact: cosign
  signatures, SLSA provenance, and SBOM (CycloneDX/SPDX).
- **Audit log** of publishes, yanks, gating decisions, and verified-publisher grants
  (append-only; structured JSON, conventions.md §10).

**Data stored / distributed (owned by producers, hosted by Hub):**

- **Artifact blobs** in an **S3-compatible object store** (MinIO self-host; S3/GCS in cloud),
  **content-addressed**, behind the OCI registry — the same large-binary tier conventions.md §5
  assigns to Hub/Cloud/Bench. Payloads: **ONNX** policies (conventions.md §6), **SADF**
  asset bundles with **USD/glTF** geometry (conventions.md §3), **Zarr/COG** world/resource
  fields (conventions.md §5), surrogate model checkpoints, plugin bundles, and Core **schema
  bundles**. **(RFC-0001)** plus **`MissionSpec`** documents, **`TrajectoryRef`/`ManeuverBudget`**
  libraries ([Trajectory](trajectory.md)), **sized SADF designs** ([Sizing](sizing.md)), and
  **open economics / value models** ([Ledger](ledger.md)) — content-addressed and provenance-
  tracked like everything else, so a mission trade study reproduces exactly.

**Formats & schemas:** OCI image-manifest + custom `artifactType` media types; the **Core plugin
manifest** as the index schema; OpenAPI 3.1 for the API; CycloneDX/SPDX for SBOMs;
in-toto/SLSA for provenance.

**Lifecycle:** publish → (optional review for verified/curated namespaces) → active →
deprecated (still pullable, flagged) → **yanked** (resolution refuses by default; bytes
retained for reproducibility/audit and pullable only by explicit digest). Garbage collection
reclaims unreferenced blobs but **never** a digest still referenced by a [Bench](bench.md)
result or a published provenance chain.

**Provenance & versioning:** every artifact records its inputs (content hashes), producing code
version, environment lockfile, and seed (conventions.md §5), so a pull reconstructs the exact
ancestry. Artifacts are **SemVer**'d; immutability of `name:version→digest` is enforced (a
re-publish to an existing version is rejected — publish a new version).

---

## 6. Integration architecture

Hub sits at the center of the **contribute-once-use-everywhere** flywheel (charter §6):

- **[Core](core.md)** — Hub indexes *everything* by the Core **plugin manifest** and validates
  the **Core interface versions** an artifact declares; capability negotiation and the
  capability-tag vocabulary used for dual-use gating are Core's, consumed here. Hub depends on
  `astro-mine-core` for the manifest model and version-range logic.
- **Producers (publish to Hub):** [Fleet](fleet.md) SADF assets; [Worlds](worlds.md) and
  [Prospect](prospect.md) world/resource-field content; [Learn](learn.md) **ONNX** policies;
  [Surrogate](surrogate.md) models; [Mind](mind.md)/[Allocate](allocate.md) planners; and
  arbitrary third-party plugins.
- **Consumers (pull from Hub):** [Studio](studio.md) pulls assets, worlds, and candidate
  policies into a design; [Sim](sim.md) and any component **loading a plugin via the Core
  registry** resolves it through Hub; [Learn](learn.md) pulls baselines/curricula and publishes
  trained policies back; [Ops](ops.md) pulls a validated, signed campaign bundle.
- **[Bench](bench.md)** — the tightest coupling and the other half of the academic flywheel
  (charter §10.3): a leaderboard submission *references Hub artifacts by digest*; Bench resolves
  and verifies them through Hub, and Bench results link back to the exact artifact digests they
  scored. Hub never scores; Bench never stores artifacts.
- **[Cloud](cloud.md)** — Hub is *deployed on* Cloud's Kubernetes substrate; large training/sweep
  workers pull artifacts from Hub's object tier with range reads (conventions.md §8).
- **Experiment tracking** — **MLflow** runs (conventions.md §6) link to Hub artifacts by
  content hash, closing the loop from training run → published policy → Bench result.

**Protocols & message flows:** **OCI Distribution Spec** (HTTP) for blob/manifest/tag/referrer
traffic; **REST/OpenAPI** (FastAPI) for discovery, resolution, and admin; **gRPC** for
internal service-to-service calls (conventions.md §3); **NATS + JetStream** events
(`hub.artifact.published`, `…yanked`, `…verified`) consumed by [Bench](bench.md),
[Studio](studio.md), and notifications (conventions.md §4). Recorded streams are not Hub's
concern (that's MCAP, owned by Sim/Ops).

---

## 7. Infrastructure & deployment

- **Deployment tier:** **Cloud** (conventions.md §7, tier 2) — Kubernetes on [Cloud](cloud.md).
  A **local/dev** tier (tier 1, which MUST always work) runs the registry + Postgres + MinIO via
  `docker compose`, and the `astro-mine-hub` client resolves/pulls against **any** OCI registry
  (including `ghcr.io` or a private Harbor/Zot) so a researcher needs no hosted Hub to be
  productive.
- **Containerization & orchestration:** OCI images for every service; deployed via Helm/Argo CD
  on K8s; the registry data path scales as a StatefulSet/Deployment with object-storage backend;
  API/search/policy services are stateless **HorizontalPodAutoscaler** deployments.
- **Compute profile:** **CPU + memory bound**, *not* GPU. The registry path is I/O- and
  bandwidth-bound (large blob transfer); the index/search path is DB- and (modestly)
  embedding-bound. Embedding computation for semantic search is the only place a small GPU or
  CPU inference pool helps; everything else is CPU. Storage is the dominant resource — plan for
  multi-TB→PB object storage with lifecycle tiering (hot for popular artifacts, cold/archive for
  yanked-but-retained bytes).
- **Scaling building blocks:** a **CDN / pull-through cache** in front of blob egress (the hot
  path); read replicas for Postgres; Redis for hot catalog/resolution caching and rate limiting;
  **registry mirroring/replication** (Harbor/Zot support this natively) for multi-region and for
  air-gapped/offline mirrors.

---

## 8. Performance & scalability

**Targets (order-of-magnitude design goals):**

- **Pull throughput:** saturate available bandwidth for large blobs; multi-GB ONNX/world
  artifacts stream from object storage / CDN, not the API tier.
- **Resolution latency:** dependency + compatibility resolution for a typical artifact closure
  in well under a second (cached interface-version graph in Redis/Postgres).
- **Search latency:** sub-second faceted + full-text + top-k semantic queries at catalog sizes
  of 10^5–10^6 artifact versions.
- **Concurrent pulls:** scale to large [Bench](bench.md)/[Cloud](cloud.md) fan-out where
  thousands of workers pull the same few artifacts simultaneously.

**Bottlenecks & mitigations:**

- **Blob egress (the hot path).** Mitigate with a **CDN/pull-through cache** and content
  addressing (identical layers dedup; popular artifacts cache once, serve many). This is the
  single most important scaling lever for the thundering-herd pull pattern.
- **Admission cost (sign/SBOM/provenance verification + embedding).** Done **asynchronously**
  off the NATS queue so publish acknowledges fast and verification/indexing complete behind it;
  an artifact is "verified/searchable" only once that completes.
- **Semantic search at scale.** pgvector with an HNSW/IVFFlat index is the default; if recall or
  latency at large catalog sizes regresses, the `search/` interface lets OpenSearch take over
  vectors + full-text without touching callers (§11).
- **Metadata DB.** Stateless services + Postgres read replicas + Redis caching; the catalog is
  read-heavy. Pull remains available from registry+object-store even if the catalog is degraded
  (principle §9).

**Scaling strategy:** horizontal, stateless services behind load balancers with state in
Postgres/Redis/object store (conventions.md §8); object storage and CDN absorb the data-volume
growth; registry replication handles geo/offline scale-out.

---

## 9. Security, safety & compliance

Hub is the platform's **supply-chain trust boundary** — the place a hostile artifact would most
want to enter and the place reproducibility lives or dies. This section is central.

- **Artifact integrity & provenance (the core of Hub).** Every artifact is
  **content-addressed** (sha256) and **signed with Sigstore/cosign** (keyless, OIDC-bound, or
  KMS keys), carries **SLSA provenance** (which builder/CI produced it, from which inputs), and
  ships an **SBOM** (Syft → CycloneDX/SPDX) — exactly the supply-chain stack mandated by
  conventions.md §9. Verification happens **at admission** and **at pull** (the client
  re-verifies before [Core](core.md) loads the plugin — defense in depth: a compromised Hub
  cannot make a client accept tampered bytes). Attestations are stored via the OCI Referrers
  API and are independently fetchable/auditable.
  **Admission applies to every publish, not only the curated tiers**: it proves the digest exists
  and its bytes are its content address, that the manifest offered for indexing is the one
  actually stored (otherwise the index describes something other than what a consumer pulls),
  that the artifact is signed at all, and that the signature/SLSA/SBOM chain verifies. A trust
  tier above `open` is granted only by an **audited promotion that re-runs those checks** — never
  claimed by the publisher, and never inherited from publish time.
  **Shipped today:** the keyed **ECDSA (`sigstore_cosign` scheme)** path, which works offline with
  no account — the local tier's default. **Deferred:** keyless Sigstore (Fulcio/Rekor, OIDC-bound)
  and KMS keys, additive behind the same scheme, decided with the trust-root policy
  ([astro-mine-hub#14](https://github.com/astro-mine/astro-mine-hub/issues/14), Phase 2).
- **AuthN/AuthZ.** **OIDC** (Keycloak self-host or cloud IdP); **RBAC enforced via OPA**
  (conventions.md §9). Anonymous read of public, non-gated artifacts; authenticated publish;
  namespace-scoped write; **verified-publisher** is a granted, audited role. Service-to-service
  is **mTLS** (conventions.md §9).
  **Status — read this as design intent, not shipped behaviour.** What ships today is the **OPA
  download gate** and **admission verification**. The write path has **no caller authentication**:
  `POST /publish` identifies nobody, and `publisher` is a self-declared label, not an
  authenticated identity. That is tolerable only because admission constrains *what* may be
  indexed regardless of who asks — a caller cannot forge content provenance, claim a trust tier,
  or index an artifact it did not store — but it is **not** the "governed to write" posture
  principle 5 describes, and the gap is deliberate and tracked, not an oversight. Whether writes
  are fronted by a gateway or gain in-process authn is an open Phase-2 question alongside the
  trust-root policy (astro-mine-hub#14).
- **Curation & moderation (trust model).** Tiered namespaces: **open** (community,
  self-published, signed but unreviewed) and **curated/verified** (reviewed, verified-publisher,
  promoted only after admission checks pass). The trust tier is a first-class facet so consumers
  and [Bench](bench.md) can require, e.g., "verified-publisher + valid SLSA provenance." Yank
  and deprecation are auditable governance actions (charter §10.4 RFC/governance posture).
- **Plugin execution isolation.** Hub **never executes** artifact code — it stores, indexes,
  verifies, and serves. Untrusted-plugin sandboxing (seccomp/gVisor, out-of-process gRPC, the
  forward-looking WASM path) is the *consuming* component's responsibility (conventions.md §9,
  core.md §9). Hub's job is to ensure what you pulled is exactly what was signed.
- **Export control & dual use (download gating).** Per conventions.md §12 and charter §10.5,
  Hub evaluates **license + export-control policy at the download boundary** against manifest
  **capability tags** (Core's dual-use taxonomy). Genuinely sensitive operational capability is
  partitioned into **access-controlled/gated namespaces**; license compatibility (Apache-2.0
  default, charter §10.4) and export posture are checked before resolution returns bytes.
  "Open does not mean naive." **(RFC-0001)** The supply-chain stack (signing, SLSA provenance,
  SBOM) and these gates apply unchanged to the mission-architecture artifacts: the reserved
  `operational_targeting` capability tag plus license/export gating (OPA) govern downloads of
  `TrajectoryRef`/`MissionSpec`/sized-SADF artifacts at the boundary — keeping descriptive,
  design-time trajectory work in the open commons while partitioning operational maneuver targeting
  and guided EDL out. **Proprietary cost-data plugins** (the commercial layer above the open
  [Ledger](ledger.md) framework) are access-gated, **not** part of the open commons.
- **Org/CI supply-chain defaults** (conventions.md §9) apply: Dependabot, secret scanning, push
  protection, read-only default Actions permissions; secrets via External Secrets Operator +
  Vault/KMS — none in images or repos.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** SDK in every service → traces, metrics, logs
  (conventions.md §10). A publish is traceable end-to-end (admission → verify → index → embed →
  event), as is a resolution+pull (resolve → gate → egress).
- **Metrics & dashboards:** **Prometheus + Grafana** — pull bandwidth and cache-hit ratio,
  resolution/search latency, admission queue depth, verification pass/fail rates, storage growth
  and dedup ratio, per-namespace download counts.
- **Logs:** structured JSON aggregated with **Loki**; the **audit log** (publishes, yanks,
  gating/verification decisions, role grants) is retained separately for compliance.
- **Health:** standard liveness/readiness endpoints and per-service SLOs (conventions.md §10);
  the **pull/resolve** path carries the strictest availability SLO because it is
  reproducibility-critical.
- **Testing & validation:** `pytest` + **Hypothesis** for resolver/SemVer/version-range
  invariants (conventions.md §11); **consumer-driven contract tests** proving Hub honors the
  [Core](core.md) manifest interface versions it claims (conventions.md §11); golden tests for
  search ranking and resolution determinism; integration tests against a real OCI registry
  (Zot/Harbor in CI) and `cosign`/SLSA/SBOM verification fixtures, including **negative tests**
  (tampered blob, bad signature, missing provenance, gated-download denial) that MUST fail
  closed. Release artifacts are signed (conventions.md §11).

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| Artifact-store backbone | **OCI registry** (Harbor / Zot / ghcr); DVC/Git-LFS; HF-Hub-style custom store; raw S3 + custom index | **OCI registry** — content-addressed, signed, standard clients, Referrers API for attestations; aligns with conventions.md §7 |
| OCI registry implementation | **Harbor**; **Zot**; ghcr (hosted) | **Zot** for the lean OCI-native self-host (built-in cosign/Referrers/sync); **Harbor** if richer RBAC/replication/UI is wanted; ghcr for dev convenience |
| Metadata & search store | **PostgreSQL + pgvector**; OpenSearch/Elasticsearch | **Postgres + pgvector** (one store for catalog + facets + semantic vectors, conventions.md §5); **OpenSearch** only if vector/full-text scale outgrows it |
| Discovery approach | Keyword only; faceted only; **faceted + full-text + semantic embeddings + capability match** | **All combined** — facets/full-text for precision, embeddings for "find something like this," capability match against manifests for correctness |
| Curation / moderation | Fully open; reviewed-only; **tiered (open + curated/verified namespaces)** | **Tiered** — frictionless open publish (signed, unreviewed) plus curated/verified-publisher namespaces; trust tier is a queryable facet |
| Dependency & compat resolution | Pin-only (no resolution); **SemVer + Core interface-range solver** | **SemVer + Core interface ranges** — resolve closures, refuse incompatible Core interface majors, pin to digests |
| Artifact push/pull client | docker CLI; **ORAS + cosign**; bespoke protocol | **ORAS + cosign** (standard OCI tooling) wrapped by the `astro-mine-hub` SDK; no bespoke protocol |
| Blob egress scaling | Direct from registry; **CDN / pull-through cache** | **CDN / pull-through cache** — the dominant hot-path lever for fan-out pulls |
| License / export gating | None; post-hoc; **policy-gated at download (OPA + capability tags)** | **OPA at the download boundary** against Core capability tags (conventions.md §12) |

**Open questions / research dependencies:**

- **Capability-tag taxonomy for gating** — depends on [Core](core.md)'s dual-use vocabulary,
  co-designed with governance/export-control (core.md §11). Hub's gating is only as good as that
  taxonomy.
- **Compatibility resolution semantics** — how to express and resolve compatibility among an
  ONNX policy, a SADF asset, and a world (e.g. observation/action shape and CRS compatibility),
  beyond Core interface majors. Co-designed with [Learn](learn.md), [Fleet](fleet.md), and
  [Worlds](worlds.md).
- **Semantic-search corpus & embedding model** — what text/metadata to embed (manifest +
  README + capability tags) and which embedding model, to make "find a policy like X" actually
  useful; validated against curated relevance sets.
- **Reproducibility ↔ storage cost** of never deleting referenced digests — retention/tiering
  policy for yanked-but-referenced artifacts, co-designed with [Bench](bench.md).
- **(RFC-0001) Mission-architecture artifact handlers & gating** — per-`artifactType` validators
  for `MissionSpec`/`TrajectoryRef`/sized-SADF/economics artifacts, and the OPA gating that ties
  `TrajectoryRef` downloads to the `operational_targeting` tag — co-designed with
  [Trajectory](trajectory.md), [Sizing](sizing.md), [Ledger](ledger.md), and the
  [mission-model](mission-model.md) schema.

---

## 12. Roadmap alignment

- **Phase 1 (ships).** Hub launches in Phase 1 (charter §11) alongside the autonomy/studio
  wave, as the second half of the academic flywheel with [Bench](bench.md): an OCI-backed
  registry that **stores, signs, indexes (by Core manifest), and serves** worlds, SADF assets,
  ONNX policies, surrogate models, and plugins; faceted + full-text + semantic discovery; SemVer
  + Core-interface resolution; cosign/SLSA/SBOM verification at publish and pull; the REST API,
  web UI, and `astro-mine-hub` client; tiered namespaces with verified publishers; and license/
  export-control download gating. This is the **MVP** that lets the first public leaderboards and
  community plugins (charter §11, Phase 1) circulate.
- **Phase 0 (pre-Hub).** Before Hub exists, content is content-addressed and consumable from a
  plain OCI registry (ghcr/Zot) via the client SDK and the [Core](core.md) registry — the
  local/dev tier that MUST always work. Phase 0 deliberately ships *without* a hosted Hub
  (charter §11 lists Hub in Phase 1), so Phase-0 artifacts are forward-compatible by being OCI +
  signed from day one.
- **Phase 2+ (later).** Multi-region replication and offline/air-gapped mirrors for
  [Ops](ops.md) (charter §11, Phase 2); richer curation/review workflows; deeper [Bench](bench.md)
  integration (submission-by-reference, result↔artifact linking) and recommendation/discovery
  ranking; ecosystem features (third-party verified publishers, commercial layers) as the
  cislunar ecosystem matures (charter §11, Phase 3). The measure of success is the same as the
  commons itself: how readily a contribution published once becomes usable everywhere.
- **Phase 3 (multi-regime missions, RFC-0001).** Hub indexes and serves the new
  mission-architecture artifact types — `MissionSpec`s, `TrajectoryRef`/`ManeuverBudget` libraries,
  sized SADF designs, and open economics models — with `operational_targeting`-aware gating. No
  earlier Hub work is required since these reuse the existing artifact/manifest machinery; the
  enabling [Core](core.md) manifest hooks are reserved in Phase 1 ([mission-model](mission-model.md)).
