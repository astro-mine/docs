# RFC 0005: `astro-mine-seal` — a shared artifact-integrity (signing / provenance / SBOM) companion package

- **Status:** proposed
- **Author(s):** djankov
- **Created:** 2026-07-06
- **Affects Core:** no — factors the platform's artifact-integrity facilities into a thin **Core
  companion package** (`astro-mine-seal`, import `astro_mine.seal`), built on Core's already-frozen
  `registry.Signature` / `Verifier` surface and `hashing` primitive. It makes **no** change to
  `astro-mine-core` — no new enum, message, schema, or wire type, and `CORE_INTERFACE_VERSIONS`
  stays `0.1.0`. Core stays crypto-free; the companion is the single home for the `cryptography`
  dependency and the supply-chain (SLSA/SBOM) helpers. It goes through the RFC process because it
  introduces a **new top-level package** and a cross-cutting convention (all signing / attestation
  consolidates onto it) —
  [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

## Summary

The platform already has a cohesive **artifact-integrity domain** — signing, verification, SLSA
provenance, SBOM, and the verify-twice orchestration — but it lives in one repo and one piece of it
has leaked. `astro-mine-hub`'s `supply_chain/` module is the de-facto home: `_signing.py`
(`generate_keypair` / `sign_digest` / `verify_signature` / `make_verifier`), `_attest.py`
(`build_slsa_provenance` / `build_cyclonedx_sbom` / `attest`), and `_supply_chain.py` (the
verify-twice `verify`, `DEFAULT_REQUIRED=(signature, slsa, sbom)`). Because Hub is a heavyweight
dependency (registry, index, FastAPI), the *signer alone* was re-implemented, byte-compatibly, in
`astro-mine-fleet` (`packaging/signing.py`) and `astro-mine-guard` (`spec/signing.py`, RM-P1-GUARD-05).

Factor that domain into a thin **Core companion package** — `astro-mine-seal`
(`import astro_mine.seal`) — that owns the single implementation of signing, verification, SLSA,
and SBOM, built on Core's frozen `registry.Signature` / `Verifier` surface, exactly as
[RFC-0002](0002-shared-spice-foundation.md) factored the shared SPICE foundation into
`astro-mine-spice` rather than re-deriving it per package. Hub, Fleet, and Guard depend on it; the
duplicated signer copies are deleted; and **Core stays crypto-free**.

Every producer signs and checks a **seal** on its artifacts, and the intactness of that seal is what
verification tests — hence the name.

## Motivation

Signatures and attestations only interoperate if every producer and verifier agrees, byte-for-byte,
on digest encoding, key format, signature encoding, and provenance/SBOM layout. Today the signing
half of that agreement is maintained **by hand across three copies**: a Fleet-signed SADF bundle, a
Hub-published artifact, and a Guard-loaded `SafetySpec` must all validate under identical rules. A
refactor in one copy — or divergent handling of a `cryptography` upgrade — produces a silent "valid
signature rejected" failure, in a security-critical path, with no single source of truth to audit.
The duplication also triples the maintenance and review surface for the most sensitive code the
platform ships.

And signing is not the last of it. SLSA provenance and SBOM generation exist today only on the Hub
*verify* side; as more producers publish to Hub — Learn's `PolicyPackage`s, Worlds/Prospect bundles,
Fleet SADF — they will need to *generate* attestations, not merely have Hub check them. `cryptography`
is imported by exactly three repos today (fleet, guard, hub); that set will grow along the producer
frontier. A per-package copy of the signer does not scale to that; a shared domain package does.

Core deliberately ships **no** crypto (`cryptography` is not a Core dependency): it owns the
`Signature` data envelope, the `Verifier` protocol, and the lightweight `hashing` primitive
(`content_hash` / `content_hash_json` / `canonical_json`), and delegates the actual signing to each
host. That decision is correct and stays — the narrow waist should not gain an EC library. A thin
companion package owns the *one* heavy implementation without widening Core.

## Design

### The routing rule this package makes explicit

Shared functionality sorts into exactly two homes, by **dependency weight and cohesion**, never by
"is it shared":

1. **Lightweight, dependency-free, broadly useful → `astro-mine-core`.** This is already where
   `hashing` (content-addressing), `canonical_json`, the provenance/run-context schema, and units
   live. Future non-crypto shared primitives go here too.
2. **Heavy or specialized, but a cohesive single-responsibility domain → a focused companion
   package** (the `astro-mine-spice` shape). Artifact integrity qualifies: it needs `cryptography`
   and it is one domain — *prove and check what an artifact is and who produced it*.

`astro-mine-seal` is bucket 2. There is deliberately **no** general-purpose `astro-mine-common` /
`utils` bucket (see Alternatives).

### The package

`astro-mine-seal` (import `astro_mine.seal`), Apache-2.0, private during incubation, generated from
`.repo-template`. Small and single-purpose; its only heavy dependency is `cryptography` (plus the
SBOM/SLSA serializers). It depends on `astro-mine-core` (for `registry.Signature` /
`SignatureScheme` / `SignatureKind`, the `Verifier` protocol, and `hashing`) and on nothing else in
the platform.

**Public surface** — the union of what already exists in Hub's `supply_chain/` and the leaked
signer copies, behavior unchanged:

- **Signing / verification** (from `_signing.py`):
  - `generate_keypair() -> (private_pem, public_pem)` — an ECDSA P-256 keypair.
  - `sign_digest(digest, private_pem) -> Signature` — a cosign-scheme Core `Signature` over a
    `sha256:<hex>` content digest.
  - `verify_signature(sig, digest, *, trusted_public_key_pem) -> None` — fail-closed.
  - `make_verifier(trusted_public_key_pem) -> Verifier` — a Core `Verifier` for the plugin
    registry's `require_signature` gate.
- **Attestation** (from `_attest.py`): `build_slsa_provenance(...)`, `build_cyclonedx_sbom(...)`,
  `attest(...)`.
- **Verify-twice orchestration** (from `_supply_chain.py`): `verify(...)` with the required-evidence
  policy (`signature` / `slsa` / `sbom`).

Scheme stays `SIGSTORE_COSIGN`, key-based ECDSA P-256 (the offline default). Keyless (Fulcio/Rekor)
is an additive future member behind the same surface, decided with the production trust-root work.

### Founding content: extract, don't invent

This is not new code — it **relocates** Hub's existing, cohesive `supply_chain/` module into the
shared package and **deletes** the two leaked signer copies. The migration is mechanical and
behavior-preserving (same function names and signatures; already byte-compatible, so existing
signatures continue to verify). A **cross-package conformance test** in `astro-mine-seal` pins the
signature bytes for a known digest+key and asserts round-trip + cross-verify, so any future drift
turns CI red.

### Sequencing (YAGNI-disciplined)

Additive and non-urgent — the mirrored copies interoperate today and nothing is blocked on this; it
must not gate any lunar-MVP milestone. Land it in the order the pain is real:

1. **Signer dedup first** — stand up `astro-mine-seal` with the signer + conformance test; migrate
   Guard, Hub, and Fleet to consume it and delete their local copies (small, independent PRs).
2. **Relocate attestation** — move Hub's `_attest.py` / `_supply_chain.py` (SLSA / SBOM /
   verify-twice) into `seal`; Hub imports them from there. No behavior change.
3. **Grow along the producer frontier** — Learn / Worlds / Prospect adopt `seal` to *generate*
   attestations as they harden their Hub publish paths.

### Future members (charter, not scope-now)

The package's charter is the whole artifact-integrity domain, so these land here additively without a
rename or a second package: keyless cosign (Fulcio/Rekor), and the **production trust-root policy**
(cosign identities, key distribution, rotation/revocation) tracked in
[astro-mine-hub#14](https://github.com/astro-mine/astro-mine-hub/issues/14) — the mechanism lives in
`seal`, the org policy is decided with Hub.

## Impact on Core

**None to `astro-mine-core`.** No enum, message, schema, or wire form changes;
`CORE_INTERFACE_VERSIONS` stays `0.1.0`. The narrow waist does not widen — `astro-mine-seal` is a
companion built on Core's frozen `Signature` / `Verifier` surface and `hashing` primitive, exactly
as `astro-mine-spice` (RFC-0002) is a companion for SPICE resolution. Core remains crypto-free.

## Alternatives considered

1. **Promote signing/attestation into `astro-mine-core`.** Rejected: it adds a `cryptography`
   dependency and a supply-chain surface to the narrow waist that only the producer/verifier frontier
   needs, contradicting the thin-core principle. Core deliberately owns the `Signature` *shape*, the
   `Verifier` *protocol*, and the lightweight `hashing` primitive — and no crypto. A companion keeps
   that boundary intact.
2. **A general-purpose `astro-mine-common` / `utils` package.** Rejected — and worth stating
   explicitly, because it is the tempting shape. A grab-bag becomes a dependency magnet (every repo
   imports it for one function), accumulates unrelated transitive dependencies, and has no single
   reason to change, which is exactly what rots. It is also **unnecessary**: the platform already
   routes "shared but lightweight" into Core (bucket 1 above), so the only thing left to share is
   "heavy + cohesive," which belongs in *focused* domain companions. `astro-mine-seal` is defined by
   its dependency (`cryptography`) and its one domain (artifact integrity), not by "shared-ness" —
   that is what keeps it from becoming a junk drawer.
3. **Ship signing-only as `astro-mine-sign`.** Rejected as too narrow: SLSA/SBOM already exist in the
   same domain and dependency footprint (Hub's `_attest.py`), and the producer frontier will need
   them — a sign-only package would force a rename or a second package within a phase or two. The
   domain-scoped `seal` (with signing landing first) avoids that without over-building.
4. **Keep the mirrored copies; add only a cross-package drift test.** The cheapest option, adopted
   here as the *interim* guard during migration — but as the end state it still leaves three signer
   implementations to maintain and review, and no shared home for the growing attestation surface.
5. **Fold everything into Hub.** Rejected: Fleet and Guard would then depend on heavyweight Hub
   (registry, index, FastAPI) purely for a signer — the very reason the signer was copied in the
   first place. A dedicated thin package is the smaller dependency.

## Documentation impact

Adds `Seal` to the commons-backbone package vocabulary (Core · Spice · **Seal** · Bench · Hub ·
Cloud) in the architecture overview and this workspace's `CLAUDE.md`; a short `astro-mine-seal`
component note. No change to any accepted RFC's decision; RFC-0004's signer and the GUARD-05 load
gate, plus Hub's `supply_chain/`, migrate to consume it.

## Decision

**Proposed.** Pending steering-group acceptance per GOVERNANCE.md. On acceptance: create
`astro-mine-seal` from `.repo-template`; port the shared signer + conformance test and migrate
`guard` / `hub` / `fleet` off their copies (step 1); relocate Hub's SLSA/SBOM/verify-twice helpers
(step 2); grow adoption along the producer frontier (step 3) — all as small, independent PRs.

## Unresolved questions

- **Package name — RESOLVED: `astro-mine-seal`** (`import astro_mine.seal`), chosen over
  `astro-mine-sign` (too narrow), `astro-mine-supply-chain` / `astro-mine-attest` (accurate but drier).
- **Scope — RESOLVED:** the artifact-integrity domain (signing + verification + SLSA + SBOM +
  verify-twice), not signing-only and not a general utility package.
- **Core companion vs ordinary plugin** — whether to document `seal` as a formal "Core companion"
  (like `astro-mine-spice`) or just a plugin package. Cosmetic; it depends only on Core either way.
- **Keyless timing** — when to add the Fulcio/Rekor keyless path behind the same surface; tied to the
  production trust-root decision ([astro-mine-hub#14](https://github.com/astro-mine/astro-mine-hub/issues/14)).
