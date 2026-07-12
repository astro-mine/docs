# RFC 0009: Cross-package schema resolution — the `$id` contract and the downstream canary

- **Status:** accepted
- **Author(s):** djankov
- **Created:** 2026-07-12
- **Accepted:** 2026-07-12
- **Affects Core:** yes — adds a **public** `astro_mine.core.schema_registry()`; deprecates the
  private `units.schema_ref` plumbing five packages currently import; makes a Core schema's `$id`
  **public, append-only API**; and makes downstream schema resolution a **required Core CI check**.
  Additive: no wire change, no message-shape change, `CORE_INTERFACE_VERSIONS` stays frozen at
  `0.1.0` ([VERSIONING.md §4](../VERSIONING.md)). Goes through the RFC process because it touches
  the Core narrow waist and because it adds **normative** rules to
  [`conventions.md`](../architecture/conventions.md)
  ([GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)).

## Summary

Core owns JSON Schemas that other packages `$ref` across files — above all the shared units
vocabulary ([RFC-0007](0007-units-frames-wire-schema.md)). **Core never specified how they should do
that.** It solved only its own internal need, with a private module and a synthetic URI that is not
the schema's `$id`. Five packages import that private plumbing; three of them invented three
*different* workarounds to reach it. Nothing in any CI anywhere tests that they still resolve.

This RFC makes cross-package schema reference a first-class, owned contract:

1. **One name.** A Core schema is referenced by its absolute **`$id`**. The `$id` becomes public,
   append-only API.
2. **One mechanism.** Core exposes a public `schema_registry()` that resolves every Core schema by
   `$id`. It subsumes the private `units_registry()`, which becomes a deprecated alias.
3. **One guard.** A **downstream canary** in Core CI installs each consuming repo against
   Core@HEAD and runs its schema tests, so breaking a consumer fails the *Core* PR that breaks it.

Rule 3 is the load-bearing one. Rules 1 and 2 fix today's damage; rule 3 is why it does not recur.

## Motivation

### What actually happened

Six defects landed or were discovered in a single working session — a schema missing from the
published bundle, a stale schema inventory in a README, a cross-file `$ref` unresolvable for any
consumer of the published bundle, a schema digest that an installed Core could not report, an
unenforceable reproducibility pin, and a latent break in three downstream repos. They look
unrelated. They are one structure.

**Core has private conventions that other packages are forced to depend on, and nothing tests
them.**

### 1. The contract everyone needed was never written

[RFC-0007](0007-units-frames-wire-schema.md) established units/frames/epochs as a vocabulary
**shared across components**. Neither that RFC nor `conventions.md` — the normative document
governing *how* components are built — says how a non-Core package should reference a Core-owned
schema. So Core built what Core needed: `units_registry()` in
`astro_mine.core.units.schema_ref` — a module deliberately kept out of `units.__init__.__all__`
(so the package "stays import-light"), keyed on `_UNITS_REF_URI`, an **underscore-private constant
that is not the units schema's `$id`**. It was an artifact of Core authoring its own `$ref`s as
*filesystem-relative paths*, which happen to resolve — as URIs, against the consumer's `$id` base —
onto a path-shaped URI nobody serves and no schema declares.

**Five repos import that private module** (`allocate`, `guard`, `prospect`, `studio`, `worlds`), and
a sixth (`view`) vendors a byte-copy of the schema instead. Between them they invented **five
different techniques** to reference one schema:

| # | Technique | Who | Survives Core's `$id` moving? |
|---|---|---|---|
| 1 | **Path arithmetic** from the consumer's own `$id` — `"../../../core/units/schema/units.schema.json"` (6 `$ref`s across 2 schemas), reconstructing **Core's directory layout** from a repo that does not have it | `guard` | **No** — lands on the retired URI |
| 2 | **`$id` squatting** — declare a probe schema whose `$id` sits *inside Core's URI namespace* (`…/core/units/schema/studio.crs-probe.schema.json`) so a bare `"units.schema.json"` ref resolves onto the private URI. Its comment cites `schema_ref`'s `_UNITS_REF_URI` **by name** | `studio` | **No** |
| 3 | **Hardcoded absolute URI** — copy the private URI as a string literal | `prospect` | **No** |
| 4 | **Runtime derivation** — `units_schema()["$id"]`, never encoding a path | `worlds`, `allocate` | Yes |
| 5 | **Vendored byte-copy** of `units.schema.json` + codegen, resynced by hand | `view` (TS) | N/A — drifts silently instead |

Six consumers, five techniques, one schema. That is not six bugs. It is **one missing public
contract**, discovered six times — and only technique 4, which two repos arrived at independently,
is correct.

The consequence arrived on schedule. `astro-mine-core#54` corrected Core's own `$ref`s to name the
units schema by its real `$id` — semantically right, and required to make the published bundle
usable by any validator. It also retired the private URI. **`guard`, `prospect`, and `studio` now
resolve to a URI nobody registers** and will fail with `referencing.exceptions.Unresolvable` the
moment they re-pin Core. Nothing is broken today only because all sixteen repos are frozen on Core
`v0.2.0`, which predates the change.

Two further symptoms of the same missing contract, found in the same sweep:

- **`$id` namespaces are unowned.** `studio` publishes an `$id` under `/core/…`, and `worlds` ships
  byte-copies of two Surrogate schemas that **claim Surrogate's `$id`** — two repos publishing the
  same `$id`. If `$id` is the name a registry resolves by (§1), a colliding `$id` is a silent
  wrong-schema resolution waiting to happen.
- **Resolved `$id`s escape into published artifacts.** `worlds` writes the units `$id` and derived
  `$def` URIs into every `world.json` (`units_schema.id`, `crs`, `tiles_anchor_frame`). Core's `$id`
  is therefore not merely an internal name — it is already load-bearing in content-addressed output.

### 2. The check that should have caught it cannot fail

Core CI has three jobs. One is `consumer-smoke`, which reads as *"downstream consumption still
works"*. It resolves Core from **git tag `v0.1.0`** and asserts `core.__version__ == "0.1.0"`.

**It does not install the code under review.** It is structurally incapable of failing for any
change to Core. It went green on the three PRs described above while exercising a Core from two tags
earlier. No other Core job touches a consumer, and no consumer's CI tests Core at HEAD — all sixteen
test only their own frozen pin.

A green board therefore carries **no information** about downstream compatibility.

### 3. The pins convert invisible breakage into a flag day

Every repo pins Core at `v0.2.0`. `uv` requires a single git source for `astro-mine-core` across the
dependency graph, so bumping one repo drags its whole closure with it (bumping `guard` requires
`seal`, `mind`, `sim`, `hub`, `spice`, `bench`, `cloud` — eight repos). Nobody bumps casually, so
drift accumulates, so the next bump is a large coordinated event, which is expensive and frightening,
so nobody bumps.

The pin does its **reproducibility** job perfectly and its **compatibility** job not at all, because
nothing ever exercises the unpinned direction.

### The loop

> Core changes look safe (green CI) → breakage hides behind frozen pins → someone needs a new Core
> symbol → a re-pin is required → the re-pin detonates everything that accumulated → the cost pushes
> everyone back to the frozen pin.

`astro-mine-bench#39` is where the loop closed: it needs `SCHEMA_DIGEST`, which requires a re-pin,
which detonates the accumulated break. Fixing the six defects individually — each fix was correct —
touched nothing that generates them.

### Cost of not doing it

The org cannot move Core. Every Core change is a latent, unbounded liability discovered by whoever
re-pins first; the rational response is to never re-pin, which freezes the platform. `CX-REPRO`'s
reproducibility guarantee stays unenforceable, `M1.1`/`M1.2` cross-repo integration stays blocked,
and the next component that needs a Core schema invents a sixth workaround.

## Design

### 1. A Core schema is named by its `$id` — and the `$id` is public API

- Every Core JSON Schema **MUST** declare an absolute `$id` under `https://schemas.astro-mine.org/`.
  (All nine already do.)
- A schema in any other package **MUST** `$ref` a Core schema by that **absolute `$id`**, never by a
  relative path, never by a URI derived from Core's directory layout.

  ```json
  { "$ref": "https://schemas.astro-mine.org/core/units/v0.1/units.schema.json#/$defs/ReferenceFrame" }
  ```

- A published `$id` is **public, append-only API**. It **MUST NOT** be repurposed or removed; a new
  schema minor takes a new `$id` (`…/v0.2/…`). Changing a Core schema's `$id`, or the set of URIs its
  `$ref` graph resolves to, is a **breaking change** and is governed by §3. This is not a
  formality: `worlds` already writes resolved Core `$id`s into every published `world.json`.
- These URIs are **nominal**: nothing serves them, and resolution **MUST** work offline
  (`conventions.md`). Resolution is therefore by registry, never by network — see §2.

#### `$id` namespaces are owned

- A package **MUST** declare its schemas' `$id`s **only** under its own namespace
  (`https://schemas.astro-mine.org/<package>/…`). A package **MUST NOT** publish an `$id` under
  another package's namespace, and two packages **MUST NOT** publish the same `$id`.
- If `$id` is the name a registry resolves by, a colliding or squatted `$id` is a silent
  wrong-schema resolution. Both exist today (`studio` squats `/core/…`; `worlds` ships copies of
  Surrogate schemas bearing Surrogate's `$id`) and are fixed as part of the convergence (§4).

#### Cross-language and vendored consumers

- A package that cannot import Core (a non-Python binding — e.g. `view`) **MUST** resolve Core
  schemas from the **published bundle**, using the `schema_index` (`$id` → path) that
  `astro-mine-core#54` added for exactly this purpose. That is the language-neutral twin of §2.
- A package that nonetheless **vendors** a copy of a Core schema **MUST** guard it against drift by
  pinning `astro_mine.core.SCHEMA_DIGEST` (or the bundle's `schema_digest`) and failing CI when the
  copy no longer matches. A hand-resynced copy with only a comment to remind you — `view`'s
  situation today — is drift with extra steps.

### 2. One public mechanism: `astro_mine.core.schema_registry()`

Core exposes, in `astro_mine.core.__all__`:

```python
def schema_registry(*extra: Mapping[str, Any]) -> referencing.Registry:
    """Resolve any Core schema `$ref` offline.

    Registers every Core schema under its own `$id`, plus each schema in `extra` under
    its own `$id` (a consumer's schemas, which its own `$ref`s resolve against).
    """
```

A consumer needs exactly this, and nothing else:

```python
from jsonschema import Draft202012Validator
from astro_mine.core import schema_registry

validator = Draft202012Validator(my_schema, registry=schema_registry(my_schema))
```

- It generalizes `units_registry()`: the next component that must `$ref` `messages`, `mission`, or
  `sadf` uses the same call, rather than inventing a sixth technique. `allocate` already needs this
  — it reaches Core's `messages` catalog *and* units through it, and today has to extend Core's
  units-only registry by hand
  (`units_registry(schema).with_resource(messages["$id"], …)`). The variadic `extra` makes that the
  supported path rather than a workaround.
- It is the in-process twin of the bundle's `schema_index` (`$id` → path), which
  `astro-mine-core#54` added so **non-Python** consumers can build the same registry from the
  published artifact. One naming scheme, two carriers.
- **Deprecation.** `astro_mine.core.units.schema_ref.units_registry()` survives as a thin alias that
  emits `DeprecationWarning`. During the migration window the registry **also** registers the units
  schema under the retired path-shaped URI, so `guard` / `prospect` / `studio` keep resolving
  **unchanged** — restoring the *additive, append-only, never-break* rule that `VERSIONING.md` §4
  depends on and that `#54` violated. Both the alias and the legacy URI are removed once all
  consumers have migrated (§4), and **MUST NOT** be relied on by new code.
- Other packages **MUST NOT** import Core modules that are underscore-private or absent from a
  package's `__all__`. Correspondingly, Core **MUST** provide a public, documented equivalent for any
  capability a consumer legitimately needs — the absence of one is what produced the workarounds.

### 3. The downstream canary — breakage fails the Core PR that causes it

`consumer-smoke` is replaced. Its tag-pinned form is a false green and **MUST NOT** be trusted as
evidence of anything; it is repointed at the checkout under review.

Core CI gains a **required** `downstream-canary` job:

- A matrix over the repos that resolve Core schemas — initially `allocate`, `guard`, `prospect`,
  `studio`, `worlds`; extended as consumers appear. (`view` is TypeScript and vendors its copy, so
  it is covered by the digest drift-guard of §1 rather than by this matrix.)
- For each: check out its default branch, install its environment, then **replace `astro-mine-core`
  with the checkout under review** (overriding the repo's pin), and run its schema/contract tests.
- A consumer whose schemas no longer resolve against Core@HEAD **fails the Core PR**.

This is the whole point. It moves the discovery of a break from *"whoever re-pins first, months
later, in a repo they may not own"* to *"the author of the change, in the PR that causes it, while
the context is in their head."* It is what turns a re-pin from a landmine into a formality — and it
would have caught `#54` in minutes.

The canary tests **compatibility**; the pins continue to provide **reproducibility**. They are
different jobs and both are needed. Consumers keep pinning Core by tag (`VERSIONING.md` §5); no
consumer builds against a moving Core.

*Implementation note (non-normative):* the override is most simply done by syncing the consumer's
locked environment and then force-installing Core from the PR checkout over it. The exact mechanism
is an implementation detail; the requirement is that the consumer's tests run against Core@HEAD.

### 4. One-time convergence, then the alias dies

The alias exists so repos can migrate **independently** rather than in a lockstep flag day.

1. Core PR: §1–§3 (public `schema_registry()`, legacy alias, canary, `consumer-smoke` repaired).
2. Tag Core **`v0.3.0`** — a minor bump (additive; interface version stays `0.1.0`,
   `VERSIONING.md` §4). Publishing the tag ships the corrected, self-sufficient schema bundle.
3. Re-pin org-wide in dependency order — `seal`/`spice`/`mind`/`cloud` → `hub`/`allocate` →
   `bench`/`prospect`/`studio`/`worlds` → `sim` → `guard`/`link`/`fleet`/`surrogate` — migrating
   each consumer onto `$id` + `schema_registry()` as it moves. The canary confirms each repo the
   moment it lands, rather than at some later re-pin. Specifically:
   - `guard` — replace 6 path-arithmetic `$ref`s with the absolute `$id`;
   - `prospect` — replace the hardcoded stale URI with the absolute `$id`;
   - `studio` — delete the `$id`-squatting probe; `$ref` the `$id` from its own namespace;
   - `allocate`, `worlds` — already correct (technique 4); swap the hand-extended registry for
     `schema_registry(...)`;
   - `worlds` — stop publishing schemas that claim Surrogate's `$id`;
   - `view` — resolve from the bundle's `schema_index`, or pin `SCHEMA_DIGEST` and fail CI on drift.
4. Land the §1/§2 MUSTs in `conventions.md` (per precedent — RFC-0007's MUSTs landed separately).
5. Remove the alias and the legacy URI, and drop the deprecation shim.

Unblocks `astro-mine-bench#39` (the `ScenarioSpec` schema-digest pin), which is what exposed the loop.

## Impact on Core

**Does this widen the narrow waist?** Marginally, and correctly. `schema_registry()` is a small,
dependency-light function over schemas Core already ships. Core is the *only* package that can own
it: the schemas are Core's, their `$id`s are Core's, and a resolution contract owned by any consumer
is by definition a private convention — which is the failure this RFC exists to end. It cannot live
in a plugin.

**Breaking changes.** `#54` already made one, silently: it retired the URI three consumers depend
on. This RFC *repairs* that — the legacy alias restores resolution for every existing consumer, so
`v0.3.0` is additive for them. The genuinely breaking step is the eventual removal of the alias
(§4.5), which happens only after every consumer has migrated and the canary is green.

**Wire / interface.** None. No message shape, proto, or Cap'n Proto schema changes.
`CORE_INTERFACE_VERSIONS` stays `0.1.0`.

**Schema digest.** Re-registering the legacy URI does not alter any schema file, so the bundle's
`schema_digest` is unchanged by this RFC.

## Alternatives considered

**Migrate the three consumers; leave Core alone.** Rejected. Because `uv` requires one Core source
across the graph, a consumer cannot adopt the new `$id` without re-pinning Core, which drags its
whole closure — ten repos for these three, serialized. It is a flag day rather than a migration, and
it retires nothing: the next component to reach for a Core schema finds the same missing contract and
invents the same class of workaround. It also leaves the false green in place, so the next break is
equally silent.

**Revert `#54`.** Rejected. The old `$ref`s were unresolvable for *any* consumer of the published
bundle — a language-neutral artifact that no non-Python binding could validate against. Reverting
restores a worse contract to fix a compatibility break that an alias fixes at a fraction of the cost.

**Serve the `$id` URIs (a real schema registry over HTTP).** Rejected for now. Resolution must work
offline and hermetically (`conventions.md`); network resolution during validation is exactly what the
model-drift check had to be hardened *against*. The bundle's `schema_index` already gives non-Python
consumers what a served registry would, without the availability dependency.

**Keep `units_registry()` and merely make it public.** Rejected. It is units-specific, and the
problem is general: `messages` and `mission` are equally `$ref`-able, and a consumer needing them
would face the identical gap. Publishing the specific case would ratify the accident.

**Vendor Core's schemas into each consumer.** Rejected: it duplicates the source of truth, which is
the disease (four hand-maintained schema inventories drifted this session alone), and it defeats the
content-addressed digest that `CX-REPRO` depends on.

## Unresolved questions

- **Canary scope.** Start with the five schema-consuming repos, or all sixteen? Five buys the
  protection cheaply; sixteen also catches non-schema API breaks. Deferred to implementation —
  the matrix is trivially extended.
- **Canary cost and flakiness.** Cloning and installing N consumers on every Core PR has a runtime
  cost, and a consumer whose `main` is red would block Core. Mitigation (deferred): run the full
  matrix on merge-to-`main` and a reduced set on PRs, or allow an explicit, time-boxed
  quarantine label for a consumer that is red for unrelated reasons — never a silent skip, which is
  how `consumer-smoke` became decorative.
- **`$id` versioning policy.** When a Core schema takes a breaking change, it takes a new `$id`
  (`…/v0.2/…`). Whether Core then serves both `$id`s from one registry for a deprecation window, and
  for how long, is left to the first case that needs it.
- **Enforcing "no private imports" mechanically.** A lint (import-linter or a ruff rule) could fail a
  consumer that imports an underscore-private Core module, rather than relying on review. Worth doing;
  not required by this RFC.
