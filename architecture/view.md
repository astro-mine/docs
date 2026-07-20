# Astro-Mine-View — Technology Architecture

> Layer: **Design & operations (operations runtime, online mode)** · Phase: **2** · Extended for multi-regime missions ([RFC-0001](../rfc/0001-multi-regime-missions.md), Phase 3)
> (reused for design, demos, and teaching across all phases)
> The eyes of the swarm: see *what* it is doing — and a first-class account of *why*.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-View` is the **visualization, telemetry, and explanation** layer. It turns the
streams and artifacts produced everywhere else in the platform into something a human can watch,
inspect, and trust: a 3D geospatial picture of the swarm on the body, time-aligned dashboards of
fleet state, and — as a first-class feature, not a tooltip — **plan explanations** that answer
"why is the swarm doing this?" (charter §5.6, §8 "delay-tolerant supervisory autonomy").

It does, and only does:

- **3D geospatial rendering** — planetary terrain (from [Worlds](worlds.md)), assets, trajectories,
  keep-out zones, illumination/shadow, and resource-field overlays (from [Prospect](prospect.md)),
  rendered in the browser over **CesiumJS + 3D Tiles**.
- **Mission-control dashboards & telemetry** — per-asset and fleet-wide state, time-series plots,
  event/alarm tables, and comms-window timelines, built on **OpenMCT**.
- **Live streaming and replay** — the same views drive a live operations session (from
  [Ops](ops.md)) or replay a recorded **MCAP** log (from [Sim](sim.md) or an archived session),
  with a shared scrub/timeline control.
- **Plan & assignment explanation** — render the decision traces emitted by
  [Mind](mind.md)/[Allocate](allocate.md) and safety verdicts from [Guard](guard.md) as a timeline
  of decisions, alternatives, and the constraints that bound them.
- **An embeddable component library** — the same widgets host standalone, embed in
  [Studio](studio.md) for design-time visualization, and are reused by [Ops](ops.md).
- **Trajectory & mission-timeline views (RFC-0001).** For multi-regime missions, View also renders
  **multi-body / heliocentric trajectories** (transfer arcs, rendezvous geometry, porkchop /
  launch-window plots), a **mission timeline across regimes and phases**, and **cross-phase plan
  explanation**. It renders [Trajectory](trajectory.md)'s descriptive `TrajectoryRef` reference arcs
  and the multi-body geometry from [Transit](transit.md); it stays read-mostly and synthesizes no
  guidance, consistent with the dual-use boundary (RFC-0001 §6, [mission-model](mission-model.md) §4).

**Explicitly out of scope.** View is **read-mostly**: it computes no plans, runs no physics, owns
no fleet state, and commands no hardware. It does not *generate* explanations — it *renders* the
decision traces produced by the autonomy stack (View is a faithful viewer, not a second opinion).
This holds for trajectories too: View renders descriptive `TrajectoryRef` reference arcs but never
synthesizes guidance or operational maneuver targeting (RFC-0001 §6).
Command authority, supervisory override, and the human-in-the-loop control surface live in
[Ops](ops.md); View provides the picture Ops acts on. It is not a GIS/terrain authoring tool
(that is [Worlds](worlds.md)) nor a benchmark report generator (that is [Bench](bench.md)).

**Primary users:** operators and mission-ops teams (live supervision), stakeholders and reviewers
(demos, design walkthroughs), and educators/students (teaching). Secondarily every developer, who
uses View to debug a scenario by watching it.

**Charter alignment:** §5.6 (View — "see and understand what the swarm is doing and why"), §7
("OpenMCT for mission control, Cesium and 3D Tiles for geospatial rendering"), §8 (delay-tolerant
supervisory autonomy; trust models), §11 (Phase 2, with [Ops](ops.md)/[Bridge](bridge.md)).

---

## 2. Architecture principles

1. **Read-mostly, command-free.** View renders state and explanations; it never originates a
   command. Any control action a user takes is routed to [Ops](ops.md), which holds authority and
   does the safety gating. This keeps View safe to expose widely (demos, teaching) without it
   becoming an attack surface on the fleet.
2. **One viewer, two clocks — live and replay are the same code.** A live session and an MCAP
   replay differ only in the *source* behind a uniform time-indexed channel model. Every widget is
   driven by a shared timeline (wall-clock follow vs. scrub) so an operator and a student see the
   identical UI over different data.
3. **Render the explanation, don't invent it.** Explanations are decision traces authored upstream
   ([Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md)). View is a faithful renderer; it
   must never synthesize a plausible-but-wrong rationale. Honesty about provenance over polish.
4. **Embeddable first, app second — and, since [RFC-0010](../rfc/0010-console-surface-contract.md),
   embeddable only.** Every capability ships as a framed, dependency-light React component;
   [Studio](studio.md) and [Ops](ops.md) are peer consumers (library-first, conventions.md §1.4).
   View hosts no application of its own: the platform's standalone GUI is
   [`@astro-mine/console`](console.md), which sits above every surface, and View is the leaf those
   surfaces depend on (§3).
5. **Degrade, don't blank.** Tiles, telemetry, and traces arrive over flaky links and at scale.
   The client level-of-details, decimates, and back-pressures (conventions.md §8) — a stale or
   partial view is labelled stale, never a frozen or empty screen.
6. **Frames and units are explicit, always.** Every coordinate is shown in a declared planetary
   CRS resolved via SPICE/PROJ; every quantity carries SI units. No implicit Earth/WGS84 (charter
   anchor is the Moon) — conventions.md §5 and [Core](core.md) §2.
7. **Interop over bespoke.** Build on CesiumJS, OpenMCT, and the MCAP/Foxglove ecosystem; bridge
   to ROS 2/DDS rather than reinventing a telemetry transport (conventions.md §1.7, §4).
8. **Performance is a feature of correctness.** A view that can't keep up with hundreds of assets
   misleads the operator. Server-side aggregation and client LOD are first-order design concerns,
   not optimizations bolted on later.

---

## 3. Application architecture

View is a **TypeScript + React** front end (conventions.md §2) plus a thin **stateless backend**
("View Gateway") that fans telemetry and tiles into the browser and adapts upstream protocols. The
gateway holds no authoritative state — it is a translation and aggregation layer.

> **"Gateway" names two different things — this is View's.** The **View Gateway** below is View's
> *own* telemetry/tile fan-out backend. A **platform API gateway** — one unified REST edge in front
> of every component — is a separate idea, deferred to Phase 2 at the earliest and deliberately not
> built by the [console](console.md) ([RFC-0010](../rfc/0010-console-surface-contract.md)). Neither
> exists in Phase 1, and they are not the same future thing.

```
astro_mine.view
├── lib/                # embeddable component library (published npm package)
│   ├── globe/          # CesiumJS scene: terrain (3D Tiles), assets, trajectories, overlays
│   ├── dashboards/     # OpenMCT plugin + telemetry widgets, plots, alarm/event tables
│   ├── timeline/       # shared clock: live-follow / scrub, comms windows, eclipse/night bands
│   ├── explain/        # plan-explanation views: decision timeline, alternatives, constraints
│   ├── telemetry/      # channel model, streaming client (WS/SSE/Foxglove), decimation
│   ├── replay/         # MCAP reader (wasm), index/seek, channel mapping
│   └── frames/         # CRS/SPICE-time helpers, unit formatting, coordinate display
└── gateway/            # stateless backend (FastAPI):
    ├── tiles/          #   3D-Tiles / COG proxy + cache toward Worlds/Prospect
    ├── stream/         #   live telemetry fan-out (gRPC/ROS2 → WS/SSE/Foxglove), back-pressure
    ├── traces/         #   decision-trace ingest (MCAP) → explanation channels
    └── bff/            #   REST/GraphQL backend-for-frontend (session, layout, catalog)
```

> **There is no `app/`, by decision.** Earlier drafts reserved `app/` for a *"standalone hosted
> application (routing, layout, session shell)"*. [RFC-0010](../rfc/0010-console-surface-contract.md)
> **descopes it.** §6 below establishes that View's component library is embedded in
> [Studio](studio.md), and principle 4 makes Studio and [Ops](ops.md) peers consuming it — so
> `studio-ui → view` holds by View's own design, and a shell inside View that hosts Studio's surface
> closes the cycle `view → studio-ui → view`. The shell must sit **above** every surface, and every
> surface may use `view`, so it is a separate leaf package in a separate repo:
> [`@astro-mine/console`](console.md). **View stays a leaf that surfaces depend on — never the
> reverse.**
>
> The `lib/` demo harness is therefore a **developer component gallery** and a WebGL test surface:
> every scene is a committed fixture, and nothing loads user data. It is *not* the console, not an
> application, and not a way to view your own run — and it must not present itself as one. That it
> is currently the most immediately runnable front end in the platform is exactly why the
> distinction is worth stating.

### Key abstractions

- **Scene** — a CesiumJS `Viewer` with a **terrain provider** (3D Tiles / quantized-mesh from
  [Worlds](worlds.md)), an **imagery/overlay stack** (COG resource fields and uncertainty from
  [Prospect](prospect.md); illumination/PSR masks), and an **entity layer** (assets, trajectories,
  comms links, keep-out volumes) driven by the telemetry channel model.
- **Scene view modes (RFC-0001).** The Cesium globe handles **body-proximity / surface** rendering
  (terrain, assets, overlays); a complementary **heliocentric / multi-body view mode** handles the
  `interplanetary_transit` and `proximity_orbit` regimes — heliocentric transfer arcs, rendezvous
  geometry, and porkchop / launch-window plots from [Trajectory](trajectory.md) / [Transit](transit.md).
  The active view mode follows the phase's `regime` so the picture matches what the swarm is doing.
- **Channel model** — the uniform, time-indexed abstraction every widget reads from. A channel is
  `(id, schema, samples[t])`; it is fed identically by a live stream or an MCAP replay. Schemas are
  the [Core](core.md) message types (Protobuf / FlatBuffers, conventions.md §3).
- **Clock** — the single timeline. Modes: *live-follow* (track wall/mission time), *fixed-rate
  replay*, and *scrub*. All globe, dashboard, and explanation views subscribe to it, so the whole
  UI is time-coherent. For multi-regime missions (RFC-0001) the timeline also carries the
  **phase/regime banding** of the [MissionSpec](mission-model.md) — phases, `PhaseTransition`
  handoffs, and per-leg trajectory windows — so one scrub spans launch → transit → proximity →
  surface → return.
- **Explanation model** — a structured rendering of an upstream decision trace: the chosen plan,
  the assignment and its alternatives/scores, the active constraints (power floors, comms windows,
  keep-out), the trigger that caused a replan, and any [Guard](guard.md) intervention — laid out as
  a timeline and an inspectable "why this, not that" panel.
- **Layout/session** — a serializable description of which panels are shown, the layout, the active
  scenario/session, and the clock state; shareable and embeddable.

### Extension / plugin points

- **OpenMCT plugins** — telemetry adapters, view types, and time providers registered through
  OpenMCT's plugin API; this is how new dashboard widgets are added.
- **Cesium overlay providers** — new map/overlay layers (a new resource type, a new mask) register
  as imagery/3D-Tiles providers; no globe-core change.
- **Channel decoders** — new message schemas plug in via generated [Core](core.md) decoders; an
  unknown channel renders generically rather than failing.
- **Explanation renderers** — new decision-trace kinds (e.g., a new planner's rationale shape)
  register a renderer; unrecognized traces fall back to a raw structured view.
- **Embeddable widgets** — every `lib/` component is independently mountable with a documented
  props/context contract, so [Studio](studio.md) and [Ops](ops.md) compose only what they need.

### Interaction patterns

The browser holds a **subscription** to the gateway: it requests channels and a time window; the
gateway streams samples (WebSocket / Foxglove for high-rate, SSE for low-rate updates) with
server-side decimation and back-pressure. Terrain/overlay tiles are fetched directly over HTTP
(3D Tiles / COG) through a caching proxy. For replay, the browser reads an **MCAP** file (local or
range-requested from object storage) via a wasm reader and drives the same channel model. The BFF
serves session/layout/catalog over **REST + OpenAPI**, with **GraphQL** only where a panel's query
shape genuinely demands it (conventions.md §3).

---

## 4. Application programming & runtime platforms

- **Front end:** the platform front-end baseline (conventions.md §2.1) — TypeScript + React, Vite,
  pnpm, Vitest + Playwright.
  **Deviation: no Storybook.** Storybook caps at Vite <= 6 and Vite-version parity across the
  front ends was prioritized, so component docs and visual checks are served by the Playwright lane
  over the `lib/` demo harness until Storybook supports Vite 8.
- **3D geospatial:** **CesiumJS** + **3D Tiles** (charter §7) for planetary terrain and entities.
  **three.js / raw WebGL/WebGPU** is used *inside* Cesium (custom primitives / instanced draw) only
  where Cesium's entity API is too slow for very large swarms — not as a parallel renderer.
- **Mission control:** **OpenMCT** (charter §7) embedded as the dashboards/telemetry surface, wired
  to platform data through custom OpenMCT telemetry/time plugins.
- **Replay:** the **MCAP** TypeScript/wasm reader; **Foxglove**-compatible message schemas and
  panels reused where it saves work (conventions.md §4).
- **Gateway:** **Python 3.12+** with **FastAPI** (REST/OpenAPI, WebSocket, SSE) — same stack as the
  rest of the platform's edge services (conventions.md §2, §3). It speaks **gRPC** to internal
  services and reads **MCAP**/object storage. A **rosbridge/Foxglove WebSocket bridge** is the
  adapter for the ROS 2/DDS data plane when telemetry originates there.
- **Runtime model:** static front-end assets served from a CDN/object store; the gateway is a
  stateless, horizontally scalable service. No server-side application state — all session state is
  serialized client-side and (optionally) persisted via the BFF to Postgres.
- **Build/packaging:** the **`@astro-mine/view`** npm component library (SemVer, conventions.md §7,
  §13) and an OCI image for the gateway. There is no View-owned application artifact — the hosted
  GUI is [`@astro-mine/console`](console.md), which consumes this library (§3). Generated
  [Core](core.md) TS client libraries are a pinned dependency.

---

## 5. Data architecture

View **owns almost no data** — it is a viewer. It produces only UI-local artifacts and consumes the
platform's existing formats.

| Data | Direction | Format / store | Source / sink |
|---|---|---|---|
| Live telemetry / fleet state | consumed | [Core](core.md) message schemas (Protobuf; **FlatBuffers/Cap'n Proto** for per-tick channels) | [Ops](ops.md), [Sim](sim.md) live |
| Recorded sessions / replays | consumed | **MCAP** (heterogeneous timestamped channels, conventions.md §4) | [Sim](sim.md), archived [Ops](ops.md) sessions |
| Planetary terrain | consumed | **3D Tiles** (glTF tilesets) + quantized-mesh/heightfield over HTTP | [Worlds](worlds.md) |
| Resource fields & uncertainty overlays | consumed | **Cloud-Optimized GeoTIFF (COG)** via GDAL, cataloged with **STAC** | [Prospect](prospect.md) |
| Decision traces (explanations) | consumed | **MCAP** decision-trace streams | [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md) |
| Layouts / dashboards / saved views | **owned** | JSON (JSON-Schema-validated), persisted in **PostgreSQL** | View BFF |
| Annotations / bookmarks / shared scenes | **owned** | JSON in PostgreSQL; large captures (screenshots, exported clips) in **S3-compatible object store** | View BFF |

- **Schemas:** all consumed channels use [Core](core.md)-owned, versioned schemas; View declares
  the Core interface major versions it renders (conventions.md §3, §13) and degrades gracefully for
  unknown channels.
- **CRS & time:** spatial overlays carry an explicit planetary CRS (PROJ) and SPICE-backed epochs
  (TDB/ET, body-fixed/inertial); View resolves and displays them, never assuming WGS84
  (conventions.md §5).
- **Provenance:** a rendered explanation links back, by content hash, to the upstream decision trace
  and the plan/scenario that produced it (conventions.md §5), so "why" is auditable, not anecdotal.
- **Lifecycle:** live telemetry is transient (ring-buffered client-side and at the gateway);
  durable history lives in MCAP/TimescaleDB owned by [Ops](ops.md). View's own layouts/annotations
  are small, versioned, user-scoped records.

---

## 6. Integration architecture

View sits at the top of both charter loops, consuming from many siblings and integrating *through*
[Core](core.md) contracts — never via private side-channels (conventions.md §1).

- **← [Ops](ops.md).** The primary live source: fleet state estimates, plan-execution status,
  anomalies/alarms, and comms-window state, over **gRPC** server-streaming (control plane) bridged
  to **WebSocket/SSE** at the View gateway. User control intents (acknowledge, pause, override) are
  routed *to* Ops, which holds authority and gates them through [Guard](guard.md).
- **← [Sim](sim.md).** Live interactive runs stream frames over **gRPC** (server-streaming);
  finished or recorded runs are replayed from **MCAP** (conventions.md §4) — Sim explicitly
  "streams to View" and emits recorded MCAP for replay/explanation.
- **← [Worlds](worlds.md).** **3D Tiles** (LOD terrain) + quantized-mesh/heightfield and raster
  overlays over HTTP, feeding the Cesium terrain/imagery providers — Worlds emits geometry tiles,
  View renders them.
- **← [Prospect](prospect.md).** Resource-field expectations and **uncertainty** as **COG** overlays
  (cataloged via STAC), shown as map layers with explicit uncertainty (conventions.md §6, charter
  §5.1) rather than a single guess.
- **← [Mind](mind.md) / [Allocate](allocate.md) / [Guard](guard.md).** **MCAP** decision-trace
  streams — tier decisions, plan revisions, allocation alternatives/scores, replan triggers, Guard
  interventions/fallbacks — which View renders as the explanation timeline (Mind names these traces
  as "the substrate for plan explanations to operators").
- **→ [Studio](studio.md).** View's component library is **embedded in Studio** for design-time
  visualization — the same globe/dashboards/explanation widgets showing simulated rather than live
  data.
- **↔ [Bridge](bridge.md).** When telemetry originates on the **ROS 2/DDS** data plane, the
  rosbridge/Foxglove WebSocket bridge at View's gateway is the boundary into the browser (Bridge
  remains the platform's ROS 2/DDS boundary, conventions.md §4).
- **↔ [Hub](hub.md) / [Bench](bench.md).** View can open a published MCAP recording or scenario by
  content hash for replay and demos, and links from a [Bench](bench.md) result to its replay.

**Message flows.** Control plane in: **gRPC** server-streaming (Protobuf) from Ops/Sim. Browser
transport: **WebSocket/Foxglove** for high-rate channels, **SSE** for low-rate, **REST/OpenAPI**
(+ optional **GraphQL**) for BFF/session. Tiles/overlays: **HTTP** (3D Tiles, COG). Replay & traces:
**MCAP**. ROS 2/DDS telemetry: bridged via **rosbridge/Foxglove** at the gateway only.

---

## 7. Infrastructure & deployment

- **Deployment tiers** (conventions.md §7):
  1. **Local/dev** — `docker compose` (gateway + Sim/Ops mock), or a consuming static front end
     ([console](console.md), [Studio](studio.md)) pointed at a local Sim; a researcher watches a
     scenario in the browser with no cluster. *This tier MUST work.*
  2. **Operations / ground** — co-located near operators with [Ops](ops.md)/[Bridge](bridge.md);
     gateway on the ground K8s, static assets on a local CDN; consumes the ROS 2/DDS data plane via
     the bridge. This is View's home tier (Phase 2).
  3. **Cloud** — gateway behind an ingress/load balancer for demos, hosted replay, and embedding in
     a hosted [Studio](studio.md); tiles/overlays served from object storage + CDN.
- **Containerization:** an OCI image for the gateway; the front-end assets that embed this library
  are content-hashed and CDN-cached by whoever hosts them ([console](console.md),
  [Studio](studio.md), [Ops](ops.md)). Pinned, reproducible builds (conventions.md §7).
- **Orchestration:** **Kubernetes**; gateway runs as a stateless `Deployment` with an HPA;
  WebSocket/SSE connections handled by a sticky ingress (or NATS-fanned, see §8). No GPU on the
  server — rendering is in the client's GPU.
- **Compute profile.**
  - *Server (gateway):* CPU- and network-bound (proxy, decimation, fan-out). Modest CPU/mem per
    pod; scale by connection count and channel volume. No GPU.
  - *Client (browser):* needs a **WebGL2/WebGPU-capable GPU**; 8 GB+ RAM for large scenes. Tile
    streaming keeps VRAM bounded via Cesium LOD.
- **Scaling:** front end scales trivially (static + CDN). Gateway scales horizontally on
  connections; the tile/COG proxy is a cache tier (Redis index + object-store/CDN backing,
  conventions.md §5).

---

## 8. Performance & scalability

**Targets (Phase 2).** Smooth interactive globe (≥ 30 FPS) with **hundreds of assets** and live
trajectories; sub-second end-to-end telemetry latency on the ground tier for dashboard channels;
sub-second scrub/seek on MCAP replays of multi-hour sessions; first-meaningful-paint of a session
in a few seconds.

**Bottlenecks & mitigations.**

- **Too many entities on the globe.** A naïve Cesium entity per asset collapses at swarm scale.
  *Mitigation:* batched/instanced primitives, LOD/clustering (glyphs at distance), and
  server-side spatial aggregation for very large swarms — only entities in view, at the needed
  detail, reach the client.
- **High-rate telemetry firehose.** Per-tick state for hundreds of assets exceeds what a browser can
  plot. *Mitigation:* **server-side decimation and aggregation** at the gateway, FlatBuffers/Cap'n
  Proto for per-tick channels (conventions.md §3), and bounded client ring buffers with
  back-pressure (conventions.md §8) — load is shed and labelled, never queued unboundedly.
- **Terrain/overlay streaming.** *Mitigation:* 3D Tiles LOD + quantized-mesh from
  [Worlds](worlds.md), COG range reads for overlays, and a CDN-backed caching proxy.
- **WebSocket fan-out at many concurrent operators/viewers (demos).** *Mitigation:* stateless
  gateway pods behind sticky ingress; a shared **NATS** fan-out tier when one stream feeds many
  viewers (conventions.md §4) so upstream is read once.

**Client-side vs. server-side rendering.** Default is **client-side rendering** (Cesium in the
browser) — interactive, no server GPU, scales by user. For *very large* swarms or thin/embedded
clients, the gateway pre-aggregates entities server-side (down-sampled scene graph), with
**server-side pixel streaming (WebRTC, e.g. an Omniverse/Unreal render farm)** kept as a Phase-3
option for cinematic demos — explicitly not the default (see §11). Measure before optimizing
(conventions.md §8): View ships representative scene benchmarks.

---

## 9. Security, safety & compliance

- **AuthN/AuthZ:** OIDC at the gateway/BFF; RBAC enforced via **OPA** (conventions.md §9). View is
  read-mostly, so the dominant authorization concern is *what an identity may see* (which fleets,
  scenarios, resource layers) rather than what it may do.
- **Command safety.** View originates no fleet command. Any user control intent is forwarded to
  [Ops](ops.md), which is the sole authority and gates it through [Guard](guard.md). This is the
  central safety property: a compromised or buggy View cannot drive hardware. The UI clearly
  distinguishes *display* from *actionable control* and always shows the live constraint/safety
  state ([Guard](guard.md) verdicts) so an operator is never misled into an unsafe action.
- **Isolation:** stateless gateway; service-to-service **mTLS** inbound (conventions.md §9). The
  browser only ever talks to the gateway, never directly to internal services. Strict CSP, sanitized
  rendering of any user/annotation text, signed static assets (Sigstore/cosign), SBOM
  (conventions.md §9).
- **Supply chain:** signed OCI/npm artifacts, SLSA provenance, pinned dependencies; standard org
  defaults (Dependabot, secret scanning, push protection).
- **Export control / dual use (conventions.md §12).** View is a viewer, so the sensitive surface is
  *visibility of operational data*. The science/sim/teaching commons (replays, terrain, resource
  fields, simulated scenarios) is open; **live operational views and any genuinely sensitive
  targeting/positioning overlays are partitioned and access-gated** via the same capability tags
  [Core](core.md)/[Guard](guard.md) carry and OPA enforces. View renders only layers an identity is
  cleared for. "Open does not mean naive" — a public demo build serves only non-sensitive data.

---

## 10. Observability & operability

- **Telemetry:** **OpenTelemetry** in the gateway → traces, metrics, logs (conventions.md §10). A
  live replan is traceable end-to-end ([Mind](mind.md) → [Allocate](allocate.md) →
  [Guard](guard.md) → [Ops](ops.md)) and surfaces in View as the explanation timeline — the same
  trace, made human-readable.
- **Metrics:** **Prometheus** + **Grafana** for gateway/connection health (active connections,
  fan-out lag, decimation ratios, tile cache hit rate, dropped/late-channel counts). Client-side
  **real-user-monitoring** (FPS, frame budget, tile load time, channel staleness) reported back via
  the gateway so degraded views are visible to operators.
- **Logs:** structured JSON aggregated with **Loki**; standard liveness/readiness endpoints and
  per-view SLOs (e.g., telemetry-staleness budget).
- **Testing & validation:**
  - **Unit/component:** `pytest` for the gateway; **Vitest** + **React Testing Library** for the
    front end. **No Storybook** — see §4; the `lib/` developer gallery plus the Playwright lane
    serve widget documentation and visual checks instead.
  - **Replay-as-golden-test:** a pinned MCAP fixture renders to a stored snapshot; CI fails on
    regression — the same determinism discipline as the rest of the platform (conventions.md §11).
  - **Contract tests:** View asserts it renders the [Core](core.md) message and decision-trace
    interface versions it claims (consumer-driven, conventions.md §11, §13).
  - **End-to-end:** **Playwright** drives the `lib/` developer gallery against a mock gateway
    feeding a known scenario, checking globe entities, dashboard values, and explanation contents.
    (A consuming application's own shell is tested by that application — see
    [console.md](console.md) §10.)
  - **Performance:** scripted scene benchmarks (N assets × M channels) with frame-budget and
    latency assertions, run in CI on representative hardware.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Geospatial render engine** | **CesiumJS + 3D Tiles**; custom **three.js/WebGL(GPU)**; **Unreal/Omniverse pixel-streaming** | **CesiumJS + 3D Tiles** (charter §7; native planetary CRS, LOD terrain, aligns with [Worlds](worlds.md)). three.js/WebGPU only as in-Cesium primitives for very large swarms; Omniverse/Unreal streaming reserved for Phase-3 cinematic demos. |
| **Mission-control layer** | **OpenMCT embed**; fully custom React dashboards; **both** | **OpenMCT embed for telemetry dashboards** (charter §7, mature, plugin model) **+ custom React for globe, timeline, and explanation** views OpenMCT doesn't cover. |
| **Browser transport (high-rate)** | **WebSocket**; **SSE**; **WebRTC**; **Foxglove WS / rosbridge** | **WebSocket (+ Foxglove schemas)** for high-rate, **SSE** for low-rate/one-way updates; **rosbridge/Foxglove** when telemetry is on ROS 2/DDS; **WebRTC** only for server-side pixel streaming. |
| **Replay** | Custom log reader; **MCAP**; Foxglove Studio embed | **MCAP** (platform standard, conventions.md §4) via its TS/wasm reader, with Foxglove-compatible schemas/panels reused; not a separate format. |
| **Rendering site for huge swarms** | All client-side; **server-side aggregation**; server pixel-streaming | **Client-side by default**; **server-side entity aggregation** at the gateway above a swarm-size threshold; pixel-streaming only for thin clients / cinematic demos (Phase 3). |
| **Explanation representation** | Free-text from an LLM; **structured decision-trace rendering**; hybrid | **Render structured upstream decision traces** (MCAP from [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md)) as a timeline + "why this, not that" panel. **Optional LLM layer only to *narrate* the structured trace** ([Studio](studio.md)'s intent-LLM, charter §5.5) — never to invent rationale (principle §3). |
| **State transport: tiles** | Direct from [Worlds](worlds.md); gateway proxy/cache | **Gateway caching proxy** (CDN-backed) so the browser hits one origin and caches are shared. |
| **Front-end framework** | React + TS; Vue; Svelte | **React + TypeScript** (conventions.md §2 — non-negotiable platform standard). |
| **Multi-body / heliocentric view (RFC-0001)** | Extend the Cesium scene with a heliocentric mode; a separate astrodynamics plot widget; both | **Cesium for body-proximity / surface + a complementary heliocentric / multi-body mode** for transit and rendezvous, with a 2D **porkchop / launch-window** plot widget alongside; render [Trajectory](trajectory.md) `TrajectoryRef` arcs and [Transit](transit.md) geometry only — no guidance synthesis (dual-use boundary, RFC-0001 §6). |

**Open questions / research dependencies:**

- **Explanation UX for delay-tolerant supervision (charter §8).** What representation actually lets
  one operator trust and supervise hundreds of robots across minutes of latency? A View + human-
  factors research question, co-designed with [Ops](ops.md)/[Mind](mind.md) and validated in the
  Phase-2 terrestrial-analog field tests.
- **Decision-trace schema for explanations.** The exact, renderable shape of a decision trace
  (alternatives, scores, active constraints, triggers) is co-owned with [Mind](mind.md)/
  [Allocate](allocate.md)/[Guard](guard.md) and must be a stable [Core](core.md) message type.
- **Swarm-scale rendering threshold.** The asset count at which client-side rendering must hand off
  to server-side aggregation — to be measured with [Sim](sim.md) at scale, not guessed.
- **Uncertainty visualization.** How to render [Prospect](prospect.md)'s probabilistic resource
  fields honestly (not a false-precision heatmap) is partly a visualization-research problem.

---

## 12. Roadmap alignment

- **Pre-Phase-2 (reused early).** Because View is the natural way to *watch* a scenario, a thin
  slice — Cesium globe over [Worlds](worlds.md) tiles + MCAP replay from [Sim](sim.md) — is useful
  from Phase 0/1 for demos, debugging, and teaching, even though View formally ships in Phase 2.
  This early reuse is encouraged and keeps the component library honest.
- **Phase 2 (MVP, ships with [Ops](ops.md)/[Bridge](bridge.md)).** The full operations viewer: live
  fleet telemetry from [Ops](ops.md), OpenMCT dashboards, the 3D geospatial scene with
  [Prospect](prospect.md) overlays, the shared live/replay timeline, and the **plan-explanation**
  views rendering [Mind](mind.md)/[Allocate](allocate.md)/[Guard](guard.md) traces — validated
  against the terrestrial-analog rover-swarm field tests (charter §11). The embeddable library is
  consumed by [Studio](studio.md).
- **Phase 3+ (later).** Cinematic server-side pixel-streaming (Omniverse/Unreal) for stakeholder
  demos; richer LLM-narrated explanations; thin/mobile and AR/VR clients; flight-adjacent operations
  views as missions mature. All additive — the read-mostly, command-free core stays stable.
- **Multi-regime mission visualization (RFC-0001, Phase 3).** The heliocentric / multi-body view
  mode, mission timeline across regimes, and cross-phase plan explanation land in Phase 3 with
  [Trajectory](trajectory.md) / [Transit](transit.md); they consume the additive
  [MissionSpec](mission-model.md) / `TrajectoryRef` schemas whose Core hooks are reserved in Phase 1.
  Read-mostly and additive — no change to the command-free core.
