# Astro-Mine-Seal — Technology Architecture

> Layer: **Commons backbone** (a *Core companion*) · Phase: **1** · Added by [RFC-0005](../rfc/0005-seal-supply-chain-companion.md) (accepted)
> The single shared home for artifact integrity: signing, verification, SLSA provenance, and
> SBOM — built on [Core](core.md)'s frozen `Signature`/`Verifier` surface, so Core stays crypto-free.
> Cross-cutting standards: see [conventions.md](conventions.md).

---

## 1. Purpose & scope

`Astro-Mine-Seal` is the **single shared artifact-integrity implementation** for the platform.
[Core](core.md) owns the *shape* of integrity — the `Signature` data envelope, the `SignatureScheme`
/ `SignatureKind` enums, the `Verifier` protocol, and the lightweight `hashing` primitive
(`content_hash` / `content_hash_json` / `canonical_json`) — but deliberately ships **no crypto**:
`cryptography` is exactly the kind of heavy dependency the narrow waist must never carry (core.md
§2 principle 3). Seal is the crypto, factored into a thin package (`astro-mine-seal`, import `astro_mine.seal`)
that every producer and verifier depends on. Every producer signs a **seal** on its artifacts and the
intactness of that seal is what verification tests — hence the name.

Concretely, Seal:

- **signs and verifies** content digests — an ECDSA **P-256** keypair (`generate_keypair`), a
  cosign-scheme Core `Signature` over a `sha256:<hex>` digest (`sign_digest`), a **fail-closed**
  check (`verify_signature`), and a Core `Verifier` for the plugin registry's `require_signature`
  gate (`make_verifier`);
- **builds attestations** — SLSA provenance (`build_slsa_provenance`), a CycloneDX SBOM
  (`build_cyclonedx_sbom`), and the combined `attest`;
- **orchestrates verify-twice** — `verify(...)` against a required-evidence policy
  (`DEFAULT_REQUIRED = (signature, slsa, sbom)`), refusing an artifact that is missing or fails any
  required piece of evidence.

**The boundary (the invariant that keeps the waist thin).** Seal owns the *mechanism* of integrity —
key format, digest/signature encoding, provenance/SBOM layout, and the verify-twice policy — and
**stops there**. It does **not** own:

- **the `Signature` / `Verifier` vocabulary or `hashing`** — those are [Core](core.md)'s frozen
  surface; Seal is built *on* them, never a fork of them;
- **the production trust-root policy** — cosign identities, key distribution, rotation/revocation are
  org policy decided with [Hub](hub.md) ([astro-mine-hub#14](https://github.com/astro-mine/astro-mine-hub/issues/14)),
  even though the *mechanism* lives here;
- **the registry / index / publish plane** — storing and serving artifacts is [Hub](hub.md); Seal
  only proves and checks what an artifact is and who produced it.

**Explicitly out of scope.** Seal is not a registry, not a key-management service, and carries **no
operational-targeting** surface — it is integrity, not guidance (§9). Keyless cosign (Fulcio/Rekor)
is an additive future member behind the same surface, not a second package.

**Primary users:** the producer/verifier frontier — [Fleet](fleet.md) (signed SADF bundles),
[Hub](hub.md) (published artifacts + verify-twice), and [Guard](guard.md) (the fail-closed
`SafetySpec`/model load gate, guard.md §9.5) today; [Learn](learn.md), [Worlds](worlds.md), and
[Prospect](prospect.md) as they harden their Hub publish paths and need to *generate* attestations.

**Charter alignment:** the artifact-integrity domain realizes `conventions.md §9` (security & supply
chain — signed artifacts, SLSA provenance, SBOM) as one shared implementation rather than three
hand-maintained copies; `conventions.md §1.7` ("interop, don't reinvent") sanctions naming the
Sigstore/cosign bridge plainly.

---

## 2. Architecture principles

1. **A thin Core companion, not an edge.** Seal depends only on `astro-mine-core` (the `Signature` /
   `Verifier` types and `hashing`) plus `cryptography` and the SLSA/SBOM serializers. No other
   `astro-mine-*` package — deliberately, so [Fleet](fleet.md) and [Guard](guard.md) can sign without
   depending on heavyweight [Hub](hub.md) (registry, index, FastAPI), the very reason the signer was
   copied in the first place. Core depends on it not at all.
2. **The one home for `cryptography`.** Core stays crypto-free by design; Seal is the single place the
   EC library lives. New shared crypto / supply-chain code belongs here, never re-copied per package.
   This is the RFC-0005 routing rule made concrete: *lightweight+dependency-free → Core; heavy+cohesive
   → a focused companion* — never a general-purpose `common`/`utils` grab-bag.
3. **Byte-stable interoperation.** Signatures and attestations only interoperate if every producer and
   verifier agrees, byte-for-byte, on digest encoding, key format, signature encoding, and
   provenance/SBOM layout. One implementation means one agreement — a **cross-package conformance
   test** pins the signature bytes for a known digest+key so any drift turns CI red.
4. **Fail closed.** An unsigned, tampered, or under-attested artifact is **refused**, never trusted
   silently — verification raises rather than returning a soft "maybe". The correctness of every
   consumer (a Guard shield, a Hub pull, a Fleet load) depends on its inputs' integrity, so integrity
   is part of the safety case (guard.md §9.5).
5. **Extract, don't invent.** Seal's founding content is *relocated*, behavior-preserving, from
   [Hub](hub.md)'s `supply_chain/` module (same function names and signatures, already byte-compatible)
   — so existing signatures keep verifying and the two leaked signer copies (Fleet, Guard) are deleted,
   not re-derived.
6. **Keyed and offline by default.** The default scheme is `SIGSTORE_COSIGN`, key-based ECDSA P-256,
   with **no** Fulcio/Rekor network dependency — the local-tier reproducibility contract. Keyless is an
   additive path behind the same surface, decided with the production trust-root work.

---

## 3. Application architecture

Delivered **library-first** (importable, single-workstation usable per `conventions.md §1.4`); there
is no service wrapper — it is a dependency, not a process. Internal modules mirror the Hub
`supply_chain/` origin they are extracted from:

```
astro_mine.seal
├── _signing.py        # generate_keypair / sign_digest / verify_signature / make_verifier ; ECDSA P-256, cosign scheme
├── _attest.py         # build_slsa_provenance / build_cyclonedx_sbom / attest ; AttestationStore + AttestationSet + the OCI referrer constants
├── _supply_chain.py   # verify-twice: verify(...) + verify_slsa_document / verify_sbom_document ; DEFAULT_REQUIRED = (signature, slsa, sbom)
└── __init__.py        # facade: re-exports the public surface (and __version__)
```

### Key abstractions exposed

| Group | Names |
|---|---|
| Signing / verification | `generate_keypair`, `sign_digest`, `verify_signature` (fail-closed), `make_verifier` |
| Attestation | `build_slsa_provenance`, `build_cyclonedx_sbom`, `attest`; the `AttestationStore` / `AttestationSet` interchange (and the OCI referrer media-/artifact-type constants) |
| Verify-twice orchestration | `verify` (required-evidence policy) + the per-document `verify_slsa_document` / `verify_sbom_document` shape checks, `DEFAULT_REQUIRED = (signature, slsa, sbom)` |

Digests are `sha256:<hex>` strings; keys are PEM; signatures are Core `Signature` envelopes
(`scheme = SIGSTORE_COSIGN`, ECDSA P-256).

### Key abstractions consumed

- **[Core](core.md)** `registry`/`hashing`: the `Signature`, `SignatureScheme`, `SignatureKind`
  types, the `Verifier` protocol (for `require_signature`), and the `content_hash` /
  `canonical_json` primitives. This is Seal's *only* `astro-mine-*` dependency.
- **`cryptography`** — the ECDSA P-256 primitives (the single home for this dependency).
- **SLSA / CycloneDX serializers** — the provenance and SBOM document formats.

### Extension / plugin points

- **Keyless cosign (Fulcio/Rekor)** — an additive scheme behind the same `sign`/`verify` surface,
  landing with the production trust-root decision.
- **Additional attestation kinds** as the producer frontier grows (e.g. richer provenance predicates).

### Interaction patterns

A producer content-hashes its artifact (Core `hashing`), calls `sign_digest` with its private key,
and — as it hardens — `attest` to attach SLSA provenance and an SBOM; it publishes the artifact plus
its seal to [Hub](hub.md). A consumer resolves the artifact and calls `verify(...)`, which checks the
signature via a `Verifier` (`make_verifier`) **and** the required attestations, failing closed on any
gap. [Guard](guard.md) wires `make_verifier` into the plugin registry's `require_signature` gate so an
unsigned `SafetySpec`/model never loads.

---

## 4. Application programming & runtime platforms

- **Language:** **Python 3.12+** (conventions.md §2). The public surface is fully typed.
- **Crypto:** the **`cryptography`** library (ECDSA P-256) — the only heavy runtime dependency, plus
  the SLSA/SBOM serializers. No other geometry/ML/geospatial stack.
- **Config & schemas:** none of its own; it speaks Core's `Signature`/`Verifier` types and the
  standard SLSA/CycloneDX document shapes.
- **Runtime model:** in-process importable library only — no FastAPI/gRPC surface.
- **Build/packaging:** Python wheel `astro-mine-seal` (import `astro_mine.seal`); SemVer,
  version-from-Git-tag; depends on a pinned `astro-mine-core` interface major version (conventions.md
  §7, §13). `CORE_INTERFACE_VERSIONS` is **unchanged** by this package (stays `0.1.0`) — Seal adds no
  Core enum, message, schema, or wire form.

---

## 5. Data architecture

- **Inputs:** a content **digest** (`sha256:<hex>`, produced by Core `hashing`), a **private key**
  (PEM) to sign / a **trusted public key** (PEM) to verify, and the artifact metadata a provenance /
  SBOM describes.
- **Outputs:** a Core **`Signature`** envelope, an **SLSA provenance** document, and a **CycloneDX
  SBOM** — the *evidence* attached to an artifact.
- **No store of its own:** Seal holds no datasets and no key store — keys are supplied by the host and
  the evidence is persisted by the *producer* alongside the artifact in [Hub](hub.md) (conventions.md
  §5, §9). Provenance is a property of the artifact, recorded where the artifact lives.
- **Determinism:** the same digest + key ⇒ a byte-identical signature (the conformance-test invariant),
  which is what lets any verifier trust any producer.

---

## 6. Integration architecture

Seal sits on the **Commons backbone** as a Core companion and integrates through plain package
dependencies (no service plane, no side-channels — conventions.md §1.1):

- **← [Core](core.md).** Depends on `astro-mine-core` for the `Signature` / `Verifier` types and
  `hashing`. Core does **not** depend on Seal; the narrow waist stays crypto-free (core.md §2 principle 3).
- **→ [Fleet](fleet.md), [Hub](hub.md), [Guard](guard.md).** Each adopts `astro_mine.seal` and
  **deletes its local signer copy** — Fleet's `packaging/signing.py`, Hub's `supply_chain/_signing.py`,
  and Guard's `spec/signing.py` (RM-P1-GUARD-05). Hub additionally sources `_attest.py` /
  `_supply_chain.py` from Seal.
- **→ [Learn](learn.md), [Worlds](worlds.md), [Prospect](prospect.md).** The producer frontier adopts
  Seal to *generate* attestations as they harden their Hub publish paths — additive, no rework.

**This is the seam fix.** An ECDSA-P256 signer was byte-duplicated across three repos; a refactor in
one copy — or divergent handling of a `cryptography` upgrade — would produce a silent "valid signature
rejected" failure in a security-critical path, with no single source of truth to audit. By being the
one package every producer and verifier depends on, Seal removes that risk and shrinks the review
surface for the most sensitive code the platform ships.

---

## 7. Infrastructure & deployment

- **In-process library** — no cluster footprint; it is linked into whichever process signs or verifies
  (a research laptop, a Fleet authoring tool, a Hub verifier, a Guard load gate).
- **Keys at runtime:** supplied by the host — a developer key locally, an org signing identity in CI /
  Ops. The **production trust-root** (identities, distribution, rotation/revocation) is decided with
  Hub ([astro-mine-hub#14](https://github.com/astro-mine/astro-mine-hub/issues/14)); Seal provides the
  mechanism, not the policy.
- **Distribution:** pinned downstream via a `uv` Git source + CI token during private incubation,
  identical to the `astro-mine-core` / `astro-mine-spice` pattern. Public PyPI wheel and signed
  releases deferred to the public flip.

---

## 8. Performance & scalability

- A single ECDSA-P256 sign/verify is sub-millisecond; **verify-twice** cost is dominated by fetching
  and parsing the attestation evidence, not the crypto.
- No hot loop lives here — batch verification is embarrassingly parallel across artifacts.
- "Measure before optimizing" (conventions.md §8): a native fast path is unwarranted; integrity checks
  are not on any per-tick simulation path.

---

## 9. Security, safety & compliance

This is the component's *raison d'être* — it realizes `conventions.md §9` and the artifact-integrity
half of [guard.md §9.5](guard.md) as one shared implementation:

- **Fail-closed verification.** An unsigned, tampered, or under-attested artifact is **refused** — the
  registry gate (`require_signature`) and Guard's load gate both depend on this. Integrity is part of
  the safety case: a shield is only as trustworthy as the spec/model it loads (guard.md §9.5; LUNAR
  SR reqs).
- **Byte-stable, keyed, offline.** `SIGSTORE_COSIGN`, ECDSA **P-256**, key-based (no Fulcio/Rekor
  network path by default). The signature bytes for a known digest+key are pinned by the cross-package
  conformance test so all three producers stay interoperable.
- **Supply chain.** Seal *is* the platform's SLSA-provenance + CycloneDX-SBOM generator (Syft/CycloneDX
  lineage), plus pinned reproducible builds and the org security defaults (Dependabot, read-only
  Actions). `cryptography` is the one audited crypto dependency, pinned via `uv.lock`.
- **No operational-targeting capability.** Proving *what an artifact is and who produced it* is generic
  integrity, not guidance; Seal carries no guided-EDL / maneuver-targeting surface and is **not** gated
  by the `operational_targeting` capability tag (conventions.md §12; mirrors spice.md §9 and the
  [RFC-0001](../rfc/0001-multi-regime-missions.md) dual-use boundary).
- **Crypto stays out of any TCB.** Per guard.md §9.1, the signing/verification crypto lives in the
  untrusted load gate, **never** inside the Rust safety core — Seal is that untrusted, auditable gate,
  shared.

---

## 10. Observability & operability

- **Fail-loud, specific errors:** a verification failure names *which* evidence failed (bad signature,
  missing SLSA, absent SBOM, untrusted key) so a consumer surfaces a precise boundary failure rather
  than a silent default.
- **Conformance as a gate:** the cross-package conformance test (pinned signature bytes + round-trip +
  cross-verify) runs in CI, so a `cryptography` upgrade or an accidental encoding change is caught
  before it can reject a real production signature.

---

## 11. Technology options & recommendations

| Decision | Options | Recommendation |
|---|---|---|
| **Home for signing/attestation** | Promote into Core; a companion package; fold into Hub; a `common`/`utils` bag | **A focused companion (`astro-mine-seal`)** — keeps Core crypto-free, lets Fleet/Guard sign without heavyweight Hub, and avoids a dependency-magnet utils grab-bag (RFC-0005 Alternatives). |
| **Package scope** | Sign-only (`astro-mine-sign`); the full artifact-integrity domain | **Full domain** (sign + verify + SLSA + SBOM + verify-twice) — SLSA/SBOM share the domain and dependency footprint; sign-only would force a rename within a phase. |
| **Signing scheme** | Key-based cosign (offline); keyless Fulcio/Rekor | **Key-based ECDSA P-256, offline** now; keyless additive behind the same surface, with the trust-root decision. |
| **SBOM format** | CycloneDX; SPDX | **CycloneDX** — the existing Hub `_attest.py` lineage; one format, not two. |
| **Migration strategy** | Rewrite; extract-and-relocate from Hub | **Extract-and-relocate** — behavior-preserving, byte-compatible, existing signatures keep verifying; guarded by the conformance test. |

---

## 12. Roadmap alignment

Phase-1 deliverable, **additive and non-urgent** — the mirrored signer copies interoperate today, so
nothing is blocked and it **must not gate the lunar MVP** ([RFC-0005](../rfc/0005-seal-supply-chain-companion.md)
§Sequencing). Landed **signer-dedup-first**:

- **RM-P1-SEAL-01** — package scaffold (`astro_mine.seal`, Core-pinned wiring, the one `cryptography`
  home, CI).
- **RM-P1-SEAL-02** — the signer (`generate_keypair` / `sign_digest` / `verify_signature` /
  `make_verifier`) + the cross-package conformance test.
- **RM-P1-SEAL-03** — relocate SLSA / SBOM / verify-twice from Hub's `_attest.py` / `_supply_chain.py`.

**Consumer migrations** (each adopts `astro_mine.seal` and deletes its local copy): [Guard](guard.md),
[Fleet](fleet.md), and [Hub](hub.md) — Hub after SEAL-03. **Future members** (charter, additive, no
rename): keyless cosign (Fulcio/Rekor) and the production **trust-root policy** — cosign identities,
key distribution, rotation/revocation — tracked as
[astro-mine-hub#14](https://github.com/astro-mine/astro-mine-hub/issues/14) (Phase 2): the mechanism
lives in Seal, the org policy is decided with Hub.
