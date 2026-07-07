# RFC 0005: `astro-mine-sign` — a shared signing/verification companion package

- **Status:** proposed
- **Author(s):** djankov
- **Created:** 2026-07-06
- **Affects Core:** no — factors the existing per-component cosign signer into a thin **Core
  companion package** (`astro-mine-sign`, import `astro_mine.sign`), built on Core's already-frozen
  `registry.Signature` / `Verifier` surface. It makes **no** change to `astro-mine-core` — no new
  enum, message, schema, or wire type, and `CORE_INTERFACE_VERSIONS` stays `0.1.0`. Core stays
  crypto-free; the companion is the single home for the `cryptography` dependency. It goes through
  the RFC process because it introduces a **new top-level package** and a cross-cutting convention
  (all signers consolidate onto it) —
  [GOVERNANCE.md](https://github.com/astro-mine/.github/blob/main/GOVERNANCE.md).

## Summary

Three producer packages now carry byte-compatible copies of the same ECDSA-P256, cosign-shaped
signer — `astro-mine-fleet` (`fleet/packaging/signing.py`), `astro-mine-hub`
(`hub/supply_chain/_signing.py`), and, as of **RM-P1-GUARD-05**, `astro-mine-guard`
(`guard/spec/signing.py`). Each is built on Core's `registry.Signature` envelope and `Verifier`
protocol and uses the `cryptography` library for the EC math. Factor the single implementation into
a thin **Core companion package** — `astro-mine-sign` (`import astro_mine.sign`) — that all three
depend on, exactly as [RFC-0002](0002-shared-spice-foundation.md) factored the shared SPICE
foundation into `astro-mine-spice` rather than re-deriving it per package. There is then **one**
signer, not N, and Core remains crypto-free.

## Motivation

Signatures only interoperate if every signer and verifier agrees, byte-for-byte, on the digest
encoding, key format, and signature encoding. Today that agreement is maintained by hand across
three copies: a Fleet-signed SADF bundle, a Hub-published artifact, and a Guard-loaded `SafetySpec`
must all validate under identical rules. A refactor in one copy — or divergent handling of a
`cryptography` upgrade — produces a silent "valid signature rejected" failure, in a
security-critical path, with no single source of truth to audit. The duplication also triples the
maintenance and review surface for the most sensitive code the platform ships.

Core deliberately ships **no** crypto (`cryptography` is not a Core dependency): it defines only the
`Signature` data envelope and the `Verifier` protocol and delegates the actual signing to each host.
That decision is correct and stays — the narrow waist should not gain an EC library. But "Core owns
the shapes, each package re-implements the crypto" is not the only way to honor it: a thin companion
package can own the *one* implementation without widening Core — the same shape as `astro-mine-spice`
(RFC-0002), a Core companion for the name→geometry resolution Core can't host.

## Design

### The package

`astro-mine-sign` (import `astro_mine.sign`), Apache-2.0, private during incubation, generated from
`.repo-template`. A small, dependency-light package whose only heavy dependency is `cryptography`.
It depends on `astro-mine-core` (for `registry.Signature` / `SignatureScheme` / `SignatureKind` and
the `Verifier` protocol) and on nothing else in the platform.

**Public surface** — the union of what the three copies already expose, behavior unchanged:

- `generate_keypair() -> (private_pem: bytes, public_pem: bytes)` — an ECDSA P-256 keypair.
- `sign_digest(digest: str, private_pem: bytes) -> Signature` — a cosign-scheme Core `Signature`
  over a `sha256:<hex>` content digest.
- `verify_signature(sig: Signature, digest: str, *, trusted_public_key_pem: bytes | None) -> None`
  — fail-closed; raises on scheme / key / digest mismatch.
- `make_verifier(trusted_public_key_pem: bytes) -> Verifier` — a Core `Verifier` for the plugin
  registry's `require_signature` gate.

Scheme stays `SIGSTORE_COSIGN`, key-based ECDSA P-256 (the offline default). Keyless (Fulcio/Rekor)
remains an additive future upgrade behind the same surface (see [RFC-0004](0004-safetyspec-safety-contract.md)
and the production trust-root follow-up).

### Migration

Mechanical and behavior-preserving. Each of `fleet/packaging/signing.py`,
`hub/supply_chain/_signing.py`, and `guard/spec/signing.py` is replaced by a dependency on
`astro_mine.sign` and its local copy deleted; call sites are unchanged (same names and signatures).
Because the implementations are already byte-compatible, existing signatures continue to verify. A
**cross-package conformance test** (fixture-based, in `astro-mine-sign`) pins the signature bytes for
a known digest+key and asserts round-trip + cross-verify, so any future drift turns CI red.

### Sequencing

Additive and non-urgent: the mirrored copies work and interoperate today. `astro-mine-sign` can be
stood up and adopted one consumer at a time (Guard, Hub, Fleet, in any order), each a small PR that
swaps the import and deletes the copy. No consumer is blocked on it, and it must not gate any
lunar-MVP milestone.

## Impact on Core

**None to `astro-mine-core`.** No enum, message, schema, or wire form changes;
`CORE_INTERFACE_VERSIONS` stays `0.1.0`. The narrow waist does not widen — `astro-mine-sign` is a
companion package built on Core's frozen `Signature` / `Verifier` surface, exactly as
`astro-mine-spice` (RFC-0002) is a companion for SPICE resolution. Core remains crypto-free.

## Alternatives considered

1. **Promote the signer into `astro-mine-core`.** Rejected: it adds a `cryptography` dependency and
   an EC-signing surface to the narrow waist that only a few producers need, contradicting the
   thin-core principle. Core deliberately owns the `Signature` *shape* and the `Verifier` *protocol*
   and no crypto; a companion package keeps that boundary intact.
2. **Keep the mirrored copies; add only a cross-package drift test.** The cheapest option, and it is
   adopted here as the *interim* guard during migration — but as the end state it still leaves three
   implementations to maintain and review. The companion package removes the duplication for good.
3. **Fold signing into an existing package (e.g. Hub).** Rejected: Fleet and Guard would then depend
   on Hub (a heavy package — registry, index, FastAPI) purely for a signer, violating the narrow
   waist. A dedicated thin package is the smaller dependency.

## Documentation impact

Adds `Sign` to the commons-backbone package vocabulary (Core · Spice · **Sign** · Bench · Hub ·
Cloud) in the architecture overview and this workspace's `CLAUDE.md`; a short `astro-mine-sign`
component note. No change to any accepted RFC's decision; RFC-0004's signer and the GUARD-05 load
gate migrate to consume it.

## Decision

**Proposed.** Pending steering-group acceptance per GOVERNANCE.md. On acceptance: create
`astro-mine-sign` from `.repo-template`, port the shared signer + conformance test, and migrate
`guard` / `hub` / `fleet` to depend on it (deleting their local copies) as small, independent PRs.

## Unresolved questions

- **Package name and scope** — `astro-mine-sign` vs a broader `astro-mine-supply-chain` that also
  hosts SLSA/SBOM helpers (currently Hub-local, RM-P1-HUB-03). Recommend starting signing-only.
- **Core companion vs ordinary plugin** — whether it is documented as a formal "Core companion"
  (like `astro-mine-spice`) or just a plugin package. Cosmetic; it depends only on Core either way.
- **Keyless timing** — when to add the Fulcio/Rekor keyless path behind the same surface; tied to
  the production trust-root decision (the GUARD-05 follow-up filed with Hub).
