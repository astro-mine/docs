# Astro-Mine — Versioning & Release Policy

> **Status:** Phase-0 policy (adopted 2026-06-26). Normative for every `astro-mine-*` repository.
> Expands [`architecture/conventions.md`](architecture/conventions.md) §7 (packaging) and §13
> (naming & versioning). While the platform is in **private incubation**, the "incubation" rules
> here take precedence over any public-distribution language in the architecture docs.

## 1. Two version axes

Astro-Mine versions two different things on two independent SemVer axes. Conflating them is the
most common mistake.

| Axis | What it versions | Where it lives | Cadence |
|---|---|---|---|
| **Interface version** | a Core *contract* (`sadf`, `messages`, `objective`, `env`, `policy`, `registry`) | `astro_mine.core.compat.CORE_INTERFACE_VERSIONS` | only on a contract change — see §4 |
| **Package version** | a built *repository* artifact (the wheel) | each repo's `pyproject.toml [project] version` (and `__version__`) | per integration milestone — see §3 |

A repository's package version may advance (it ships more capability) while the Core contract it
speaks stays fixed. They are decoupled by design (`conventions.md §13`: "interface versions are
independent of implementation versions").

## 2. Package versions (per-repo SemVer)

- Every `astro-mine-*` package uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`), independently
  per repository (polyrepo; `conventions.md §7`).
- **Pre-1.0 for the whole private period.** Packages stay in the `0.y.z` range — honest
  signalling that the API is unstable and may break. **`1.0.0` is reserved for the
  public-stability commitment** (§7), not for "it works."
- **Initial assignment:**
  - A repo stays at **`0.0.0`** while it is scaffold-only (matches the
    `Development Status :: 1 - Planning` classifier).
  - It moves to **`0.1.0`** at its first runnable / consumable cut (the deliverable for its first
    integration milestone).
  - **`astro-mine-core` → `0.1.0` now:** its v0.1 narrow-waist interfaces (SADF, Environment /
    Policy APIs, message schemas, registry) are implemented and consumable — this is the
    "Core v0.1" the roadmap names as the Phase-0 backbone deliverable.
- **Cadence:** bump the **minor** (`0.1 → 0.2`) when a repo meaningfully advances at an
  integration milestone (M0.2, M1.1, …); bump the **patch** for fixes within a milestone. Do
  **not** churn versions between milestones.

### 2.1 Single source of truth: the Git tag

Because downstream repos install Core from source by Git ref (§5), the **Git tag is the real
version identity** — `uv` resolves the dependency by ref, not by the package's declared
`version`. Therefore:

- The version **MUST** be derived from the Git tag (`hatch-vcs` or equivalent), so
  `pyproject.toml`, `astro_mine.<pkg>.__version__`, and the tag cannot drift. "Bump a version"
  == "cut a tag."
- Tags are **annotated** and named `vMAJOR.MINOR.PATCH` (e.g. `v0.1.0`), one series per
  repository.

## 3. When versions are assigned — integration milestones

Versions are cut at the roadmap's **integration milestones** (`roadmap/`), giving stable
cross-repo pin targets and reproducible Bench inputs without per-commit churn.

| Milestone | Typical cut |
|---|---|
| Core v0.1 (Phase-0 backbone) | `astro-mine-core v0.1.0` |
| M0.1 / M0.2 first runnable slices | first `0.1.0` of each participating repo (worlds, prospect, fleet, sim, bench, link, cloud) |
| later milestones (M1.1, …) | minor bumps as each repo advances |

Between milestones, a downstream repo pins the last tag (or a specific commit) of its
dependencies.

## 4. The Core interface version is held at 0.1.0

**Policy (Phase 0–1, likely through Phase 3):** `CORE_INTERFACE_VERSIONS` stays at **`0.1.0` for
every interface**. No minor or major bump — even as the additive RFC-0001 schema hooks
(`MissionSpec`, `regime`, `PhaseTransition`, propulsion/return SADF, `operational_targeting`)
land in Phase 1. The **first interface bump happens at or after Phase 3.**

This is sound because the Core contract evolves under a strict **additive, append-only,
never-break** rule (`core.md`; `conventions.md §3`): proto fields are append-only, new fields are
additive (optional / default-valued), and `buf breaking` in Core CI **enforces** that every
change is wire-compatible. An old consumer and a newer Core therefore interoperate even though
both still report `0.1.0`.

**Consequence — version negotiation is a no-op while the version is frozen.**
`assert_core_compatible(...)` / `check_compatible(...)` (the `0.y` rule requires an *exact*-minor
match) return *compatible* for everything during Phases 0/1/2, because every party is `0.1.0`.
Compatibility and reproducibility are therefore guaranteed by **other** mechanisms, not by the
version number:

1. **Git-tag pin + `uv.lock`** — the exact Core commit a repo was built and tested against (§5).
   *Implemented.*
2. **Content-addressed schema digest** — the identity of the exact Core schema set, so a
   benchmark reproduces byte-for-byte (`RM-P0-BENCH-01/02`, CX-REPRO). **Partially implemented
   — see §4.1.**
3. **`buf breaking` (proto) + the model-drift check (JSON Schema ↔ Pydantic)** — keep every
   change additive, which is what makes the frozen version safe. *Implemented.*

The `compat` machinery still earns its place: it rejects unknown / misspelled interface names,
and it is the mechanism that will correctly refuse old consumers once the version is finally
bumped at Phase 3.

### 4.1 The schema digest — produced, not yet consumed

**Core produces it.** `astro_mine.core.SCHEMA_DIGEST` is the content address of the exact
schema set a given Core carries — a `sha256:` digest over the canonical sources (the JSON
Schemas, the Cap'n Proto hot path, the units conformance vectors, and the `.proto` sources).
It equals the published bundle's `schema_digest` for the same commit, and the bundle is
pullable from GHCR by digest (§5; `RM-P0-CORE-08`):

```python
from astro_mine.core import SCHEMA_DIGEST   # "sha256:…"
```

While the interface version is frozen, **this is the value that actually distinguishes one
Core schema set from another** — `__version__` and `CORE_INTERFACE_VERSIONS` cannot.

How a package *references* a Core schema — by absolute `$id`, resolved through
`astro_mine.core.schema_registry()` — is normative in
[`conventions.md` §3.1](architecture/conventions.md).

> **Note.** It is a *generated, committed constant*, not a runtime recompute, because the
> digest covers the `.proto` sources under `schemas/proto/` — which live at the Core repo root
> and are **not** in the wheel. An installed Core cannot see them, so it could not reproduce
> the digest from its own files; a filesystem walk relative to `__file__` would yield a
> plausible-but-wrong value in a wheel while looking correct in a source checkout. Core's CI
> fails if the constant goes stale, and the bundle builder refuses to publish a bundle whose
> digest no package claims.

**Nothing consumes it yet.** `ScenarioSpec` pins the Core *interface versions* (frozen, hence
constant across every Core revision through Phase 3) and its content inputs by hash — but not
the schema digest, and `resolve_scenario()` does not fold it into `scenario_hash`. So **today,
two Core revisions with materially different schemas satisfy the same `ScenarioSpec`**, and
mechanism 2 above is not yet doing the work this section credits it with. Reproducibility
currently rests on mechanism 1 — the `uv.lock` digest transitively pins the Core git rev — which
is real but is an *environment* pin, not a *contract* pin, and is unavailable to non-Python
bindings.

Closing that gap is tracked as **`astro-mine-bench#39`**. Until it lands, treat CX-REPRO's
byte-for-byte guarantee as resting on the lockfile, not on the schema digest.

## 5. How components depend on Core (private incubation)

While repos are private and nothing is published to a public index:

- A component declares Core as a **`uv` Git source pinned to a tag/commit**, recorded in
  `uv.lock`:

  ```toml
  # pyproject.toml
  dependencies = ["astro-mine-core"]

  [tool.uv.sources]
  astro-mine-core = { git = "https://github.com/astro-mine/astro-mine-core.git", tag = "v0.1.0" }
  ```

  Pin to a **tag** (or commit) — never `branch = "main"` — so `uv sync --locked` is reproducible.
- **CI auth:** the existing `uv sync --locked` step authenticates to the private
  `astro-mine-core` repo with a **PAT** (read scope) exposed to the job; `origin` remotes stay on
  HTTPS (the PAT is only for `uv`'s fetch, and does not affect GitHub Desktop).
- **OCI / schema-bundle artifacts** (e.g. the content-addressed schema bundle) publish to
  **private GHCR**, not a public registry. The bundle is self-describing: `bundle.json` carries
  its `schema_digest` (§4.1) and a `schema_index` mapping each schema's `$id` to its path, so a
  consumer can resolve the schemas' cross-file `$ref`s with a stock JSON Schema validator and
  no Core-specific code — which is what makes it usable from a non-Python binding.

This supersedes — *for the incubation period only* — the "Python wheels on an index" /
`pip install astro-mine-core` end-state described in `conventions.md §7`, `core.md §7`, and
`RM-P0-CORE-08`.

## 6. Git tags vs. GitHub Releases

- **Git tags: required.** They are the dependency pin target (§5) and the version source of truth
  (§2.1). Every milestone cut is a tag.
- **GitHub Release objects: deferred.** A full Release pays off when it carries published build
  artifacts (wheels) and changelogs for external consumers — none of which exist during private,
  source-installed incubation. A plain tag is sufficient to pin against.
  - *Optional:* cut a single milestone Release on **`astro-mine-core`** (e.g. "Core v0.1 — narrow
    waist frozen") with notes, to make the milestone legible — rather than a ceremonial Release
    per repo.

## 7. What changes at the public flip (future)

When the org makes repos public and stabilizes (per current intent, no earlier than the end of
Phase 1 — possibly later):

- Execute **`RM-P0-CORE-08`**: publish the `astro-mine-core` **wheel to a public index (PyPI)**
  via OIDC / Trusted Publishing, signed; switch downstream repos from the Git source to a normal
  version range (e.g. `astro-mine-core>=0.1,<0.2`).
- Turn on **full GitHub Releases** with signed wheel assets + SLSA provenance + SBOMs (CX-SEC).
- Reconcile `RM-P0-CORE-08`'s acceptance criteria (currently "`pip install astro-mine-core`" /
  "wheel on an index") with this document.

## 8. Summary

- Two axes: **package version** (per repo, moves per milestone) vs **Core interface version**
  (held at `0.1.0` until Phase 3).
- Packages stay **`0.y`**; `astro-mine-core` is **`0.1.0`** now; others `0.0.0` → `0.1.0` at
  first cut.
- The **Git tag is the version**; derive `__version__` from it.
- During incubation, depend on Core via a **tag-pinned `uv` Git source + PAT in CI**; **no public
  PyPI**, OCI to **private GHCR**.
- **Tags always; full GitHub Releases deferred** to the public flip.
- With the interface version frozen, **lockfiles + content hashes + `buf breaking`** — not
  version negotiation — guarantee compatibility and reproducibility.

---

*See also:* [`architecture/conventions.md`](architecture/conventions.md) (§7 packaging, §13
naming & versioning) · [`architecture/core.md`](architecture/core.md) (§7 distribution, §11
versioning model) · [`roadmap/`](roadmap/) (integration milestones, `RM-P0-CORE-08`).
