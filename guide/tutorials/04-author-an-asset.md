# Tutorial 04 — author an asset

**Persona:** P4 Roboticist / Asset Author · **Phase 0**
**Covers:** UC-C1 (scaffold) · UC-C2 (validate / lint) · UC-C3 (import a URDF) · UC-C4 (preview) ·
UC-G1 (publish signed)
**Time:** ~20 minutes. Entirely local — no content download, no account.

You will scaffold a SADF asset, validate it, import an existing URDF robot, preview its geometry,
and publish it signed to a local registry where it appears in the robot menu. This is the journey
that has always worked, and Fleet is the platform's **exemplar CLI** — 14 subcommands covering a
complete authoring lifecycle. What the rest of the platform's UX is aiming at looks like this.

---

## 1. Install

```bash
astro-mine fleet --help
```

```
    new           scaffold a minimal, valid SADF asset
    validate      validate one SADF document
    lint          lint one or more SADF documents
    resolve       emit a document's canonical JSON form
    package       write a content-addressed asset bundle
    verify        verify an OCI asset artifact's signature and that it loads
    publish       publish a signed SADF asset to a Hub registry
    catalog       list a Hub registry as the robot menu; preview one asset's geometry
    import        import a URDF/SDF description into SADF + USD/glTF geometry
    fidelity      list an asset's multi-fidelity profiles (coarse -> fine)
    families      list the parametric asset families + parameters
    resolve-family  resolve a parametric family to a concrete SADF document
    export        export a SADF asset to URDF/SDF (ROS) or a USD stage (Sim/Studio)
    render        render an asset preview/thumbnail (a composed, posed glTF/USD scene)
```

> The command is `astro-mine fleet <verb>`. A bare `fleet` binary once existed as a deprecated
> alias; it is gone (`conventions.md` §13). A couple of sub-command help strings still print the old
> bare form in prose — `resolve-family`'s *"see `fleet families`"*, for instance. `astro-mine fleet
> --help` itself is clean, and so is what `new` scaffolds.

## 2. Start from a shipped asset (recommended)

Fleet ships **six reference assets** as package data — the roster the anchor benchmark actually
uses:

```
src/astro_mine/fleet/library/
├── isru/isru-plant.sadf.yaml
├── logistics/hauler.sadf.yaml
├── manipulation/excavator.sadf.yaml
├── orbital/lander.sadf.yaml
├── orbital/relay-orbiter.sadf.yaml
└── surface/prospecting-rover.sadf.yaml
```

These are not toys. Packaged with `astro-mine fleet package`, they *are* six of the anchor's nine
pins ([tutorial 01](01-score-the-anchor.md) §6). Copying the one closest to your vehicle is
usually faster than starting from the scaffold:

```python
from importlib.resources import files
src = files("astro_mine.fleet").joinpath("library/surface/prospecting-rover.sadf.yaml")
print(src.read_text()[:400])
```

## 3. Scaffold a new one (UC-C1)

```bash
astro-mine fleet new rover my-rover.sadf.yaml --id example.my-rover --name "My Rover"
```

```
wrote my-rover.sadf.yaml
```

The scaffold is minimal and **valid on arrival**:

```yaml
sadf_version: "0.1"
asset:
  identity:
    id: "example.my-rover"
    name: "My Rover"
    version: "0.1.0"
    kind: "rover"
  core_interface_versions:
    sadf: "0.1.0"
  # root_frame must name a declared frame once `frames:` is non-empty.
  root_frame: "base"
  # frames:
  #   - {name: base}
  # capabilities: []          # Core-owned negotiation vocabulary (CapabilityTag)
  # bodies: []                # mass/inertia; add power:, thermal:, sensors:, comms: as needed
  # fidelity_profiles: []     # massmodel / kinematic / articulated
```

`capabilities` is the field that makes an asset *usable* by the rest of the platform: it is Core's
negotiation vocabulary, and it is how Mind and Allocate decide which robot can be given which task.
An asset with no capability tags will validate and publish, and nothing will ever assign it work.

## 4. Validate and lint (UC-C2)

```bash
astro-mine fleet validate my-rover.sadf.yaml
astro-mine fleet lint my-rover.sadf.yaml
```

```
OK: my-rover.sadf.yaml is valid SADF
OK: 1 file(s) passed lint
```

`validate` is schema conformance — is this a SADF document. `lint` is the judgement layer —
declared-but-unreferenced frames, mass without inertia, capability tags that no fidelity profile
supports. Run both; validate is necessary, lint is what stops your asset behaving strangely three
tutorials later.

Every Core-owned format has a validator, not just SADF:

```bash
astro-mine core validate my-rover.sadf.yaml     # dispatches on $id/$schema
astro-mine validate my-rover.sadf.yaml          # the umbrella routes to the owner
```

## 5. Import a URDF (UC-C3)

The bridge from the robotics world you already have. Given `mini.urdf`:

```xml
<?xml version="1.0"?>
<robot name="mini_rover">
  <link name="base_link">
    <inertial><mass value="120.0"/><origin xyz="0 0 0.3"/>
      <inertia ixx="8.0" ixy="0" ixz="0" iyy="12.0" iyz="0" izz="14.0"/></inertial>
  </link>
  <link name="mast_link">
    <inertial><mass value="6.0"/><origin xyz="0 0 0.5"/>
      <inertia ixx="0.2" ixy="0" ixz="0" iyy="0.2" iyz="0" izz="0.1"/></inertial>
  </link>
  <joint name="mast_joint" type="revolute">
    <parent link="base_link"/><child link="mast_link"/>
    <origin xyz="0 0 0.6"/><axis xyz="0 0 1"/>
    <limit lower="-3.14" upper="3.14" effort="20" velocity="1.0"/>
  </joint>
</robot>
```

```bash
astro-mine fleet import mini.urdf -o mini-rover.sadf.yaml
```

```
imported imported.mini_rover -> mini-rover.sadf.yaml
  geometry: 0 ref(s) under mini-rover.sadf_assets
```

Kinematics, masses, and inertias come across; visual meshes are converted to USD/glTF under
`--assets-dir`. This URDF declares no meshes, hence `0 ref(s)`.

```bash
astro-mine fleet validate mini-rover.sadf.yaml
```

```
OK: mini-rover.sadf.yaml is valid SADF
```

**What import does not do:** it does not invent capability tags, power models, thermal models, or
sensors. URDF has no vocabulary for them. An imported asset is a valid *chassis*; making it a
participant in the swarm means adding `capabilities`, `power`, and `sensors` by hand. That is the
real work, and it is the part that makes SADF worth having.

## 6. Preview it (UC-C4)

```bash
astro-mine fleet render mini-rover.sadf.yaml -o mini-rover.glb
```

```
rendered imported.mini_rover -> mini-rover.glb
  lossy (2) — SADF stays authoritative:
    [render.proxy_geometry] asset.frames['base_link']: link 'base_link' declares mass but no visual
    mesh; the preview shows its inertia-equivalent box (same mass, same inertia tensor) — a derived
    proxy, not geometry the asset claims
    [render.proxy_geometry] asset.frames['mast_link']: link 'mast_link' declares mass but no visual
    mesh; the preview shows its inertia-equivalent box (same mass, same inertia tensor) — a derived
    proxy, not geometry the asset claims
```

`lossy (2)` is the header for exactly those two warnings, which is why they are nested beneath it.
The warnings go to stderr and the summary to stdout, so a redirect separates them.

**This is the honesty rule working.** The Phase-0 reference assets — and your freshly imported
robot — declare mass and inertia but no meshes. Rather than render nothing or invent a shape,
`render` draws each link's **inertia-equivalent box**: same mass, same inertia tensor, visibly a
proxy. It then tells you, per link, that this is what you are looking at, and stamps the output
`lossy`. A picture that quietly invented geometry would be worse than no picture.

`--format glb` (default) is the web/View form; `--format usd` is for Sim and Studio.
`--fidelity {massmodel,kinematic,articulated}` selects the LOD.

## 7. Publish it, signed (UC-G1)

Generate a signing key, then publish to a **local** OCI-layout registry — no server, no account:

```bash
astro-mine hub keygen --out ./keys
```

```
wrote keys/cosign.key and keys/cosign.pub
```

```bash
astro-mine fleet publish mini-rover.sadf.yaml \
  --registry ./myreg --sign --key ./keys/cosign.key --pub ./keys/cosign.pub
```

```
published imported.mini_rover:0.1.0 -> sha256:140919bddd4c430489700c95a52b480995c24a9cf2367eaa9791199d7a3793aa (signed) — round-trip verified
```

Three things happened. The asset was packaged into a content-addressed OCI artifact and got a
digest. It was signed with your key. And `--pub` made the client **pull it back and re-verify** —
the "verify twice" rule: verify at publish, verify again at admission, never trust a name.

`--registry` also accepts a remote (`ghcr.io/astro-mine`), and `--namespace` / `--publisher` set
where it lands. Local first: everything in this tutorial works with no network.

## 8. See it in the menu

```bash
astro-mine fleet catalog --registry ./myreg
```

```
1 asset(s) in ./myreg
  imported.mini_rover:0.1.0 [imported] — (no capability tags)
```

That is P4's success sentence — *"I imported my URDF and my excavator appears in the menu"* — and
also the reminder from §3: **no capability tags**, so nothing will ever task it.

Point `catalog` at the fetched anchor content and you see what a populated menu looks like:

```bash
astro-mine fleet catalog --registry ~/.cache/astro-mine/hub-registry
```

```
24 asset(s) in ~/.cache/astro-mine/hub-registry
  astro-mine.fleet.excavator:0.2.0 [excavator] — mobility.wheeled, excavation.bucket, sensing.imu, sensing.odometry, power.generation, power.storage
  astro-mine.fleet.prospecting-rover:0.1.0 [rover] — mobility.wheeled, prospecting.neutron, prospecting.nir, prospecting.gpr, prospecting.drill_assay, excavation.drill, sensing.imaging, sensing.imu, sensing.odometry, comms.relay, power.generation, power.storage
  ...
```

`--requires TAG[,TAG...]` filters to assets declaring all the given capability tags — the same
query Mind and Allocate run when they decide who can dig.

---

## 9. Where next

- **Put your asset in a swarm:** [02 — run it in the simulator](02-run-it-in-the-simulator.md).
- **See it in a GUI:** [07 — design a swarm in Studio](07-design-a-swarm-in-studio.md).
- **The SADF format itself:** [reference/file-formats.md](../reference/file-formats.md).
- **Every Fleet command:** [reference/cli.md](../reference/cli.md).
