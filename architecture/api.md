# Astro-Mine-API — the REST distribution

> Distribution: **`astro-mine-api`** (Python wheel + OCI image) · Repository: `astro-mine-api`
> Every REST surface the platform serves, as route modules over the library's public API.
> Depends on [`astro-mine-platform`](platform.md). Served to [`astro-mine-ui`](ui.md).
> Cross-cutting standards: see [conventions.md](conventions.md) §3 (where the REST layer lives).
>
> **Status: stood up.** The four route packages moved out of the component repositories, the
> excluded route tests run again under the routes they exercise, and the health-endpoint and error
> conventions §4 promised have converged. What is outstanding is `deploy/` — the container image,
> the compose file and the chart values (§3, §6). Tracked in the [roadmap](../roadmap/README.md).

## 1. Purpose

One deployable for the platform's hosted tier. Four components have a web face; each is a set of
FastAPI route modules built over that component's ordinary Python API, and none of them lives inside
the component.

That separation is what keeps tenet 4 of [conventions.md](conventions.md) §1 honest — *library first,
service second; the service is a deployment of the library, not a separate codebase.* When routes sit
inside a component, three things go wrong in practice, and all three did: the library acquires a web
framework as a base dependency for users who will never serve anything; REST conventions get decided
once per component; and behaviour starts to exist only in a route handler, where no library caller and
no test can reach it.

## 2. What is in it

| Surface | Owning component | Routes |
|---|---|---|
| **Hub registry API** | [Hub](hub.md) | `/publish` · `/resolve` · `/search` · `/artifacts/{name}/{version}` (+ `/download`) · `/healthz` (+ `/health`, deprecated) |
| **Studio API** | [Studio](studio.md) | `/intent` · `/studies` · `/studies/comparison` · `/catalog/assets` · `/catalog/worlds` · `/catalog/preview/{ref}` · `/worlds/{ref}` · `/campaigns/publish` · `/campaigns/{ref}` · `/healthz` |
| **Cloud submission service** | [Cloud](cloud.md) | `/jobs` · `/jobs/compile` · `/sweeps/compile` · `/sweeps/expand` · `/workflows/compile` · `/backends` · `/healthz` |
| **Bench leaderboard** | [Bench](bench.md) | `/submissions` (+ `/hub`, `/{id}`, `/{id}/replay`) · `/scenarios` · `/jobs/{id}` · `/audit` · `/metrics` · `/healthz` |

Roughly 1,200 lines of route code in total — small, which is the point. Everything these endpoints do
is a call into the platform.

**The library half stays in the platform.** The distinction matters most for Bench, whose leaderboard
is mostly *not* REST: the service layer, SQL, auth, authorization, evaluation, provenance and audit
modules are library code and live in `astro_mine.bench.leaderboard`. Only the route module is here.
The same rule applies everywhere: if it would still make sense with no HTTP in the picture, it is
library code.

**gRPC is not here.** Sim's and Prospect's gRPC services stay with their components — they serve a
component's own contract at high rate, are not a web edge, and have no cross-component conventions to
unify (`conventions.md` §3, §4).

## 3. Layout

```
src/astro_mine_api/<component>/    route modules, one package per owning component
src/astro_mine_api/_app.py         composition — mount the surfaces a deployment enables
tests/<component>/                 route tests, including the ones the consolidation could not keep
deploy/                            container image, compose file, chart values
```

Route modules import from `astro_mine.<component>` and from nothing else in this tree except shared
middleware. A route module MUST NOT import another surface's routes.

## 4. Conventions (normative)

The reason this distribution exists is that these are decided once.

- **REST + OpenAPI 3.1 via FastAPI.** The generated schema is the API's documentation; a surface
  MUST NOT maintain a second, hand-written description of its own routes.
- **Every surface exposes `GET /healthz`** and the platform's standard liveness/readiness contract
  (`conventions.md` §10), answering **one body**: `{status, component, version}`. The deployment's
  own `/healthz` is that shape plus the list of surfaces it mounted. The spelling used to be
  inconsistent (`/health` vs `/healthz`) and converged on one during the move — a visible, low-cost
  example of what one home for the decision is for. `GET /hub/health` survives as a deprecated
  alias, marked `deprecated` in the document and carrying `Deprecation`/`Link` response headers,
  for one cycle.
- **Errors are typed and uniform**: one **problem document** (RFC 9457,
  `application/problem+json`) from every surface, carrying a stable machine-readable `code` and a
  human-readable `detail` that no client parses. The exception handlers are registered at
  composition, so they cover validation failures, `HTTPException`, and the unhandled case alike; a
  validation failure is **one object** whose field-level problems ride in an `errors` array, never
  the bare array a client would have to flatten. `code` is **append-only public API** — it is the
  thing a front end switches on, so removing or repurposing one is a breaking change. The codes are
  enumerated in the OpenAPI document, and a surface MUST NOT answer an error the enumeration does
  not name.
- **Units, frames and epochs on the wire follow Core's vocabulary** exactly as they do everywhere
  else (`conventions.md` §5). An API boundary is not a licence to invent a JSON shape; where a
  payload carries a Core type it carries Core's schema for it, referenced by `$id`.
- **AuthN is OIDC; AuthZ is enforced with OPA** (`conventions.md` §9). A surface MUST NOT implement
  its own authorization model.
- **Capability gating is enforced here for anything that leaves the commons.** Hub admission is one
  of the two boundaries where a capability tag is actually checked (`conventions.md` §12) — the
  registry endpoint is where an `operational_targeting`-tagged artifact is refused, and it must not be
  possible to publish past it.
- **Telemetry:** OpenTelemetry traces spanning a request into the library call it makes, so a Studio
  trade study is traceable from the HTTP request through Sim and Bench.

## 5. Interfaces

- **Inward:** `astro-mine-platform` only.
- **Outward:** HTTP, to [`astro-mine-ui`](ui.md), to third-party tools, and to the CLI in the one
  place it talks to a hosted service.
- **Not a Python API.** Nothing should import this distribution as a library. If code wants what an
  endpoint does, it wants the platform function the endpoint calls.

## 6. Deployment

Tier 2 of `conventions.md` §7.2 — the hosted tier. One image, with a deployment enabling the surfaces
it wants; Postgres, object storage, and Redis behind it per `conventions.md` §5. The **local tier does
not need this distribution at all**, and that is a requirement rather than an accident: Hub's tier-1
client, Bench's local scoring, Cloud's local backend and Studio's library API all work with no service
running, and a change that makes the API mandatory for a local workflow is a defect (CX-LOCAL).

## 7. Testing

Route tests live here, including the ones that could not move into the platform wheel — the
consolidation excluded roughly two dozen REST tests along with the routes, and covered the orphaned
library halves with characterization suites in the meantime. Bringing those tests back under the
routes they exercise was part of standing this repository up, and is done.

The **error contract and the health contract are asserted by tests that walk the routes**, not by a
sample: every route in the composed deployment is driven into a failure and the response validated
against the one problem schema, and the OpenAPI document is checked to declare that schema on every
operation. A surface added later that invents its own error shape or its own health spelling fails
those, which is the only thing that keeps "decided once" true a year from now.

The build MUST run against the platform at `HEAD`, not a released pin (`conventions.md` §3.1, §11).

## 8. Roadmap alignment

Standing up this repository was the first distribution-level task after the consolidation. Four of
the five pieces are done: the four route packages moved out of the component repositories, the
excluded route tests were restored, the health-endpoint spelling converged on `/healthz`, and the
error convention became one problem document with a named code. What remains is the tier's one
image and one chart (§3, §6).

The browser tier drove three further corrections here, all landed: cross-origin access, stable
operation ids, and typed responses — without them the front end cannot call this API at all, and a
client generated from the document types half its results as `unknown`. See the
[UI rebuild plan](../tpm/ui-rebuild-plan.md) §3. See the [roadmap](../roadmap/README.md).
