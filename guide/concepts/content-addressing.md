# Content-addressing

**Content is named by what it is, not by what someone called it.**

Every artifact the platform exchanges — world bundles, SADF assets, resource priors, contact plans,
policy packages, surrogates, campaigns — is stored and referenced by the **SHA-256 digest of its
bytes**. A digest is not a label that points at content; it *is* the content's name.

## Why a name is not enough

A benchmark result means nothing unless everyone ran the same thing. If the anchor scenario said
*"the Shackleton world, version 0.4.0"*, then someone republishing 0.4.0 with a corrected PSR mask
would silently change every result derived from it — including results published before the change.
Nobody would notice, and every comparison across that boundary would be wrong.

With digests, that cannot happen. New bytes are a new digest, which is a different pin, which is a
different scenario. **Content cannot drift underneath a result.**

## The anchor is nine hashes

`lunar-polar-ice-prospecting-v1` pins nine artifacts: one world, six fleet assets, one resource
prior, one contact plan. Each pin carries the digest *and* a description of why that version:

> `astro-mine.fleet.excavator` 0.2.0 — the first excavator to declare a `tool` contact element,
> without which no library asset reaches the granular contact ladder.

> `astro-mine.fleet.isru-plant` 0.2.0 — the first plant to declare a `water_gauge`. Without it the
> plant filled a tank nothing could read: Bench scores `water_mass` by matching a reading's species
> and unit, so a full plant was indistinguishable from a swarm that produced nothing.

That is the audit trail a commons needs: not just *which* bytes, but *why these* bytes.

## Verify twice

Signatures are checked **at publish and again at admission**. Publishing with
`astro-mine fleet publish --pub <key>` pulls the artifact back and re-verifies it; pulling with
`astro-mine bench fetch` verifies every artifact fail-closed on arrival — the digest must match, and
a signature must be present, intact, and bound to the artifact.

Fail-closed means an unverifiable artifact is an error, never a warning. `--trusted-key` narrows it
further: pin *whose* signature you accept, not merely that one exists.

Signing lives in `astro-mine seal`, the one home for the `cryptography` dependency
([Seal](../../architecture/seal.md)), so Core stays crypto-free and every
producer shares one signer.

## It works offline

The tier-1 client is a local **OCI-layout** directory — `oci-layout`, `index.json`,
`blobs/sha256/…`. No server, no account, no Docker:

```bash
astro-mine bench fetch --registry ./my-store        # mirror by digest, verified
astro-mine fleet publish asset.yaml --registry ./my-store --sign --key ./keys/cosign.key
astro-mine fleet catalog --registry ./my-store
```

The same layout is what a remote registry serves, so a local store and `ghcr.io/astro-mine` are the
same thing at different addresses. Point `$ASTRO_MINE_HUB_REGISTRY` at your store and every
component finds it.

## What it buys each persona

- **P1** — your published result is reproducible by a stranger: same digests, same seeds, same
  runner.
- **P3, P4** — your world or asset can be depended on without you promising not to change it. You
  publish new bytes; existing pins keep working.
- **P7** — a leaderboard entry referencing a digest is verifiable without trusting the submitter.
  This is why `bench submit --hub-ref` is leaderboard-grade and `--policy-ref` is not: nothing pins
  what an importable reference resolves to.

See also: [determinism & provenance](determinism-and-provenance.md).
