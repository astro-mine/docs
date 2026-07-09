# RFC 0008: Core artifact kinds for published designs and campaigns

- **Status:** draft
- **Author(s):** djankov
- **Created:** 2026-07-09
- **Affects Core:** yes — two **append-only** members added to the `PluginKind` vocabulary
  (`design`, `campaign`). String-enum additions with **no wire change**;
  `CORE_INTERFACE_VERSIONS` stays frozen at `0.1.0` ([VERSIONING.md §4](../VERSIONING.md)). Goes
  through the RFC process because it touches the Core narrow waist
  ([GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md)), and because
  `Astro-Mine-Hub` refuses to invent artifact kinds Core does not describe.

## Summary

Add `PluginKind.DESIGN = "design"` and `PluginKind.CAMPAIGN = "campaign"` to Core's closed artifact
vocabulary, and the matching `design` / `campaign` entries to Hub's `ARTIFACT_KINDS` (yielding the
OCI artifact types `application/vnd.astro-mine.design.v1` and `…campaign.v1`).

This unblocks **RM-P1-STUDIO-06** (astro-mine-studio#6), whose acceptance criteria require that a
validated design or campaign "**publishes to Hub as a content-addressed, signed artifact**" and that
"**published artifacts are indexed by the Core manifest (not a Studio-private schema)**". Today those
two criteria are jointly unsatisfiable: no Core `PluginKind` names a design or a campaign, so there
is nothing for Hub to index them as.

## Motivation

`studio.md` §6 states the contract: Studio "**can write back published designs/campaigns as
content-addressed, signed artifacts**", and `hub.md` §2 principle 2 states the rule that governs how:

> **The manifest is the index, not Hub's invention.** Hub indexes artifacts by the Core plugin
> manifest and refuses to invent its own parallel metadata schema for anything Core already
> describes. If discovery needs a field, the field belongs in the Core manifest (via RFC), not as a
> Hub-private extension.

Hub enforces this in code rather than prose. `astro_mine.hub.registry._oci.artifact_media_type`:

```python
def artifact_media_type(kind: str) -> str:
    """The ``application/vnd.astro-mine.<kind>.v1`` media type for a content ``kind``.

    ``kind`` must be one of :data:`ARTIFACT_KINDS`; an unknown kind raises ``ValueError`` (Hub
    stores only the content kinds Core describes — a new kind is a Core RFC, not a Hub extension).
    """
```

`ARTIFACT_KINDS` is `("policy", "world", "asset", "surrogate", "plugin", "schema")`. Core's
`PluginKind` has fourteen members — `regime_engine`, `sensor_model`, `coupling_scheme`,
`world_provider`, `body_pack`, `field_model`, `resource_field_backend`, `observation_model`,
`prior_recipe`, `info_gain_objective`, `comms_model`, `asset`, `policy`, `metric`. **None of them
describes a design study or a campaign.**

So a Phase-1 Studio has exactly three options, and two of them are forbidden by the documents that
created the requirement:

1. Publish under an existing kind (say `asset` or `schema`) and hide the campaign in
   `manifest.attributes`. This is a **Studio-private schema wearing a Core manifest** — precisely
   what `hub.md` §2 principle 2 and the STUDIO-06 acceptance criterion forbid. Discovery would key on
   fields Hub's catalog does not model, and `Astro-Mine-Ops` could not later resolve a campaign by
   kind.
2. Extend `ARTIFACT_KINDS` in Hub alone. Forbidden by the docstring above, in the same breath in
   which it is enforced.
3. Add the kinds to Core by RFC. That is this document.

The cost of not doing it is that RM-P1-STUDIO-06's publish half cannot ship, which in turn blocks the
Phase-1 Studio exit criterion ("goal-in → scored-design-out end-to-end on the anchor scenario,
producing a `Campaign`") from producing anything a second party can pull and verify — and it blocks
the Phase-2 `Ops` hand-off, which `studio.md` §2 principle 9 defines as consuming *the same artifact*
Studio produced, unchanged.

## Design

### The two kinds

**`design`** — a frozen, content-addressed **design study**: Studio's `TradeStudy` (its evaluated
candidates and the Pareto-ranked front they yield), or a single `EvaluatedCandidate` shared for
review. It is what a researcher publishes so a colleague can pull the front and reproduce it.

**`campaign`** — a frozen `Campaign`: a chosen design authored into a phased timeline with
contingency branches. It is the hand-off artifact. `studio.md` §2 principle 9 ("hand-off, don't
fork") requires that Ops consume it unchanged, and `hub.md` §6 already anticipates this: "Ops pulls a
validated, signed campaign bundle."

The pair mirrors the split Studio's own lifecycle already draws (`studio.md` §5): "intent → objective
spec → trade study → chosen candidate → campaign", where "once a study runs or a campaign is handed
off, **the artifact is frozen and content-addressed**". Publishing is exactly the moment of freezing,
so the vocabulary should name both frozen stages, not only the last one.

### A campaign is not a plugin — and neither is an asset

`PluginKind`'s docstring says each kind "implements a Core interface … and is discovered and
version-negotiated through `PluginRegistry`". Neither a design nor a campaign implements a Core
interface, and neither is executable.

That objection is already answered inside the enum. `PluginKind.ASSET` is carried with the note:

> An `asset` manifest in particular is *packaging metadata* — the SADF document is instantiated by
> Sim's loader, not by the registry.

`asset` establishes that the vocabulary names **the kinds of content Core describes for discovery**,
not solely the kinds Core executes. `design` and `campaign` join it on the same footing: packaging
metadata for content nobody loads as code. The same docstring already reserves the pattern for future
additions — "Mission-architecture kinds (RFC-0001 trajectory/mission/sizing) arrive by RFC in
Phase 3" — so an artifact-kind addition by RFC is the sanctioned path, not a novelty.

The one honest cost is that `PluginKind` is now unambiguously an *artifact*-kind vocabulary with a
legacy name. Renaming it is a breaking change for a cosmetic gain and is **not** proposed here.

### Manifest usage

A published campaign's `PluginManifest`:

| Field | Value |
|---|---|
| `name` | the `Campaign.id` (or `TradeStudy.id` for a design) |
| `version` | SemVer, chosen by the publisher; `name:version → digest` is immutable |
| `kind` | `campaign` / `design` |
| `core_interfaces` | `{}` — it implements none. (`world_provider` bundles carry `{"world_provider": "0.1.0"}`; a campaign has no interface to negotiate.) |
| `inputs` | the content hashes it was built from — objective, world, SADF assets, policies |
| `outputs` | the metric keys the campaign was scored on |
| `capability_tags` | copied from the chosen candidate's assets; **Studio honors, and never redefines, the export-control partition** (`studio.md` §9, `conventions.md` §13) |
| `provenance` | Core `Provenance`, projected from Studio's `ArtifactProvenance`: `input_hashes`, `seed`, `code_version`, `toolchain_version`, `env_lockfile` |
| `attributes` | `{"bundle_media_type": …, "objective_hash": …, "trade_study_ref": …}` |

The payload rides as an OCI layer, exactly as a world bundle does:

- `application/vnd.astro-mine.campaign.bundle.v1.json` — the canonical `Campaign` JSON.
- `application/vnd.astro-mine.design.bundle.v1.json` — the canonical `TradeStudy` JSON.

Publishing therefore requires no new Hub code path beyond the two vocabulary entries: Studio calls the
existing `HubClient.publish(name=…, version=…, kind="campaign", manifest=…, layers=[Blob(…)],
private_key_pem=…)`, which stores the config + layer, signs the manifest digest with ECDSA P-256, and
attaches the cosign signature, SLSA provenance, and CycloneDX SBOM as OCI referrers. A consumer's
`HubClient.pull(digest, verify=True)` re-verifies all three and **fails closed** — the verify-twice
guarantee of `RM-P1-HUB-03`.

### Reproducibility

`conventions.md` §5 requires that "every generated artifact records its inputs (content hashes), the
producing code version, the environment lockfile, and the random seed". Studio's `ArtifactProvenance`
already carries exactly these; this RFC only gives them a Core-described artifact to be stamped onto.
A puller who has the campaign's `inputs` hashes can re-pull each input by digest and re-run the study.

## Impact on Core

**Append-only, no wire change.**

- `astro_mine/core/registry/enums.py` — two members appended to `PluginKind`.
- `astro_mine/core/registry/schema/manifest.schema.json` — two values appended to the
  `$defs/PluginKind` enum (14 → 16).

There is no Protobuf or Cap'n Proto representation of `PluginKind` to change: the manifest is
JSON-Schema-validated, and the wire form of the kind is the string itself. `CORE_INTERFACE_VERSIONS`
stays `0.1.0`; a Core built before this RFC rejects a `campaign` manifest with a validation error
rather than misinterpreting it, which is the correct failure.

**Does this widen the narrow waist?** Marginally, and in the direction the waist already points. Core
does not gain a `Campaign` *schema* — the campaign's shape stays Studio-owned, carried in a layer
whose bytes Core never parses. Core gains only two names by which content can be *indexed*. The
alternative — a Core-owned `Campaign` message type — would widen the waist far more, and `studio.md`
§12 forbids it: "Studio adds no Core surface of its own."

**Downstream (not Core):** `astro-mine-hub` appends `"design"` and `"campaign"` to `ARTIFACT_KINDS`.
No other change: `artifact_media_type` derives the media string, and `ingest` already indexes any
`PluginManifest`.

## Alternatives considered

**Ride an existing `PluginKind`.** Publish the campaign as `kind="schema"` (or `asset`) with the
payload in `attributes`. Rejected: it is the Studio-private schema the STUDIO-06 acceptance criterion
and `hub.md` §2 principle 2 explicitly forbid. Catalog queries could not filter for campaigns; Ops
could not resolve one by kind; and the `attributes` blob would become an unversioned side-channel of
exactly the sort `hub.md` was written to prevent.

**Extend Hub's `ARTIFACT_KINDS` only.** Rejected by Hub's own docstring — "a new kind is a Core RFC,
not a Hub extension" — and on the merits: Hub's catalog is generated from the Core manifest, so a kind
Core cannot express is a kind the catalog cannot record.

**Wait for RFC-0001's Phase-3 mission kinds.** `hub.md` §3 reserves
`application/vnd.astro-mine.mission.v1` for the multi-regime `Mission` artifact. Rejected: a Phase-1
`Campaign` is not a `Mission` (RFC-0001 defines a single-`surface`-phase Mission as *exactly* today's
campaign, i.e. the campaign is the narrower, existing thing), and RM-P1-STUDIO-06 is a Phase-1
deliverable with a Phase-1 exit criterion. Deferring publish to Phase 3 would leave the Studio→Ops
hand-off undefined for two phases.

**Add a Core `Campaign` message schema.** Rejected: it widens the waist to hold an artifact only
Studio produces and only Ops consumes, and `studio.md` §12 states Studio adds no Core surface of its
own. Indexing by manifest gives Ops everything it needs to *find and verify* a campaign; parsing it is
a Studio-schema concern that Ops already accepts unchanged.

**Only add `campaign`.** Tempting — it is the artifact with a named downstream consumer. Rejected
because `studio.md` §5 freezes and content-addresses *both* stages ("once a study runs **or** a
campaign is handed off"), and the STUDIO-06 criterion says "designs/campaigns", plural and distinct. A
`TradeStudy` published as a `campaign` would be a lie about what it is. See "Unresolved questions".

## Unresolved questions

- **Is `design` needed in Phase 1?** The publish path that Phase-1 Studio must demonstrate is the
  campaign. `design` could be deferred to the first time someone actually shares a trade study.
  Adding both now costs two enum members and avoids a second RFC; adding only `campaign` keeps the
  vocabulary tighter. **Deferrable to implementation review.**
- **Does a `TradeStudy` publish as one artifact, or as a `design` manifest whose `inputs` reference
  each `EvaluatedCandidate` published separately?** The latter is more content-addressed in spirit
  (candidates dedupe across studies) and more expensive. Phase-1 proposal: one artifact, one layer.
- **Namespace and OPA gate.** `studio.md` §9 gates *who may publish to Hub* via OPA, and `hub.md`
  §5 partitions `open` / `verified` namespaces. Phase-1 tier-1 publishing is offline and
  accountless (`astro-mine-seal`'s keyed ECDSA path), so the gate is a Phase-2 concern tracked with
  Hub's trust-root policy (astro-mine-hub#14). This RFC does not change it.
- **Re-publish semantics.** Hub rejects re-publishing an existing `name:version` (digests are
  immutable). Studio must therefore choose a version per publish; whether that version is derived
  from the campaign's content hash or authored by the user is an implementation choice.
