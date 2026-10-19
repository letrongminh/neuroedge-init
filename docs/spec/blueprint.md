# NeuroEdge Blueprint — Software Requirements Specification

**Status:** approved for TSK-I2e-01 → I2e-09 (Q-86; current through Q-92). Structure follows ISO/IEC/IEEE
29148:2018 §9.6. This file is the one place for what a NeuroEdge Blueprint is and what `blueprint
pack`, `blueprint install` and the static index must do (CONTRIBUTING.md §8.1); PRD FR-BP-01 → 10,
FR-CLI-13 and NFR-SEC-14 state the product promise, this file states how each part of it is built
and verified. `python/tests/test_blueprint_srs.py` keeps §3 and §5 closed: every requirement has a
test case, every implemented test case names a test that exists, every planned one names a roadmap
task. The `blueprint.v1` schema itself is RFC work (CONTRIBUTING.md §3): this file says what the
schema must allow; the RFC of TSK-I2e-01 writes it.

---

## 1. Introduction

### 1.1 Purpose

A maker who has made a device work with NeuroEdge — an agent, its gates, its parts, a board, and
recordings that prove what it does — packs it once; someone else installs it with one command and
runs it on `sim` in under ten minutes (A14), then on the real kit. This specification states what
the package holds, what packing refuses, what installing checks before anything runs, and how the
static index lists packages, so that loop ③ of Q-72 can be built and measured: the install session
with three testers (A14, TSK-I2e-09) and, after the public launch, installs in its telemetry (Q-92).

### 1.2 Scope

In scope: the package (`blueprint.toml` manifest and the files it lists), the whole-package
digest, `neuroedge blueprint pack`, `neuroedge blueprint show`, `neuroedge blueprint install`,
evidence (recorded traces) and how they are checked, install parameters, the approval summary, the
kit and its bill of materials, the static index, and the first Blueprint (the fish tank).

Mission contracts and detectors inside a package are in scope from the public launch (Q-92 (7)): the
sections are accepted once the `mission.v1` RFC (TSK-I2d-04) and the detector work (TSK-I2d-09)
exist, and refused before (BL-FMT-05).

Out of scope until their own decisions: board profiles shipped inside a package (BL-FMT-04; they
wait for the conditional-safety RFC, TSK-I2d-02), signed evidence (`TODOS.md` #1, before the Hub
takes money), the paid Hub, payments and OCI distribution (FR-BP-10, when a maker asks to sell,
Q-92 (10)), consented data sharing (FR-BP-09). The Home Assistant add-on, the Pi SD image and the
affiliate page were cut by Q-92 (2).

### 1.3 Definitions

| Term | Meaning |
|:---|:---|
| **Blueprint** | A declarative package: `blueprint.toml` plus the files it lists — an agent project, its kit, its evidence, optional brain settings. Name kept through I2e and decided before the Hub is published (Q-85). |
| **Manifest** | `blueprint.toml` at the package root, valid against `schemas/blueprint.v1.json` (RFC, TSK-I2e-01). |
| **Package digest** | `sha256:` of the RFC 8785 canonical JSON of the manifest with every listed file's own SHA-256 (BL-PK-02). Independent of how the package travels (directory, git checkout, `.tar.gz`). |
| **Evidence** | `trace.v1` recordings shipped in the package, each with a tier (G1–G4 of PRD §13, or `hardware`) and a duration, that `replay` reproduces. **Unsigned** at MVP (FR-BP-04). |
| **Activation** | The step after the person has read the approval summary and said yes: only then does any code of the package run (BL-IN-05). |
| **Install parameter** | A value the installer is asked for (a threshold, quiet hours, a channel name) that the package writes into a fact, a sensor rule or a part — never into a gate (BL-IN-04). |
| **Reference board** | A board profile in `boards/` (`sim-default`, `sim-rpi5`, `linux-rpi5`, `esp32s3-box-3`) or `sim-virtual` (`virtual_parts.md`). |

### 1.4 References

PRD §15 Q-45, Q-72, Q-81, Q-84, Q-85, Q-92; FR-BP-01 → 10, FR-CLI-13, FR-DX-09, FR-TEL-07, NFR-SEC-14,
A14 · `docs/spec/virtual_parts.md` (parts, `sim-virtual`, pin maps) ·
`docs/spec/deployment_profiles.md` (box + NeuroClaw, DP-COM-06 risk labels) ·
`docs/spec/core_contracts.md` (gate digests) · `python/neuroedge/engine/canonical.py` (RFC 8785) ·
`digests.lock` and `gate publish` (the digest discipline this package reuses) ·
`docs/business/brd-ambient-intelligence.md` BR-5 · `docs/business/product-proposal.md`.

---

## 2. Overall description

### 2.1 Product perspective

```
 maker's project                    package                           installer's machine
 ───────────────                    ───────                           ───────────────────
 agent.toml, actions/, gates/,      blueprint.toml  ─ digest ─┐       blueprint install <url|file|name>
 commands.toml, [sim.parts],  ──►   agent/ …                   │  ──►  1 fetch, verify digest (no file written on mismatch)
 traces/evidence/*.json             kit/bom.toml, wiring.svg   │       2 unpack into a new directory
 kit/                               evidence/*.json            │       3 approval summary  ── person says yes ──┐
        blueprint pack ─────────►   brain/ (optional)          │       4 parameters written                     │
        (refuses drafts, secrets,                               │       5 activation: evidence replay, build ◄───┘
         failing evidence)          index entry: url + digest ─┘         for sim → `neuroedge run` works
```

### 2.2 Code boundary

`python/neuroedge/blueprint/` (new unit): manifest model, digest, pack, show, install, index
client. It may import `engine` (canonical digest, build), `hal` (boards), `trace`, `paths`,
`errors`; replay and builds run through the CLI in a child process (BL-IN-05), so the unit never
imports a package's actions itself. The index is an external repository (TSK-I2e-04).

### 2.3 User classes

| Class | Uses |
|:---|:---|
| Maker (seller) | `pack`; publishes the package (GitHub release, any HTTPS host) and an index entry |
| Installer (maker or tester) | `show`, `install`, then `run` on `sim`; later builds for the kit |
| Family member (Q-85) | Reaches a Blueprint through a maker's product; never runs `pack` |
| Reviewer of an index entry | Reads the digest, license, evidence tier and the "unsigned" badge |

### 2.4 Constraints

1. Nothing from a package runs before the person approves (BL-IN-05); a digest mismatch writes
   nothing (BL-IN-02).
2. A package never carries a secret: keys, tokens, `.env`, `ui.json` (BL-SC-03).
3. Gates in a package are locked versions, never `-draft`, and an install parameter never edits a
   gate (BL-PK-03, BL-IN-04): the rules the evidence proves are the rules that run.
4. No server of NeuroEdge is in the path: packages are self-hosted, the index is a static
   repository (FR-BP-05).
5. No change to the rows of CONTRIBUTING.md §3 except the new `schemas/blueprint.v1.json`, which
   is the RFC of TSK-I2e-01.

### 2.5 Assumptions and dependencies

- The fish tank (`fixtures/agents/aquarium`, TSK-I2d-28) is the first Blueprint; its evidence is
  the recorded demo day on `sim` and the chip sessions from QEMU (tiers G1/G3 once G1 exists;
  `sim` traces are labelled `sim` until then).
- Mission contracts (I2d-04), detectors (I2d-09) and conditional safety (I2d-02) are not built yet;
  a Blueprint v1 works without them and carries contracts and detectors once they exist (BL-FMT-05,
  Q-92 (7)).

---

## 3. Specific requirements

Verification methods: **T** test, **I** inspection, **A** analysis, **D** demonstration.

### 3.1 Package format (BL-FMT)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-FMT-01 | A package shall be a directory tree with `blueprint.toml` at its root. The manifest shall name: `name` (lowercase, digits, `-`), `version` (SemVer), `author`, `license`, `summary`, the `agent` directory, every file of the package with its SHA-256, the `evidence` list, and optionally `kit`, `parameters`, `brain`. It shall be valid against `schemas/blueprint.v1.json`. | One declared shape, checked before anything else. | FR-BP-01 | T |
| BL-FMT-02 | A file in the package not listed in the manifest, a listed file that is missing, a path that is absolute, contains `..`, or is a symlink, device or hard link shall make the package invalid (three-part error naming the path). | Nothing rides along unseen; no path escapes the install directory. | FR-BP-01, NFR-SEC-14 | T |
| BL-FMT-03 | The `agent` directory shall be a NeuroEdge agent project (`agent.toml`, `commands.toml`, `actions/`, `gates/`, optional tests) that builds for `sim` on the board it declares (`[sim] board`, else `sim-default`). | The package is the maker's working project, not a new format to learn. | FR-BP-01, Q-72 | T |
| BL-FMT-04 | A package shall target reference boards only: its agent runs on `sim-default`, `sim-rpi5` or `sim-virtual` on `sim`, and names real boards through `[targets.<board>.pins]` (VP-PM-01). A package carrying a `board.v1` profile shall be refused until the conditional-safety RFC (TSK-I2d-02) says how a shipped profile declares `safe_state` and interlocks. | Bundled boards are where `safe_state ≠ off` lives (FR-BP-06); the pin map already covers wiring a reference board. | FR-BP-06, Q-84 | T |
| BL-FMT-05 | The manifest shall allow `contract` and `detectors` sections: they are validated against `mission.v1` (TSK-I2d-04) and the detector format (TSK-I2d-09), shown in the approval summary and locked only when the person approves (BL-IN-05); before those exist, a package that fills them is refused, naming what it waits for. | A maker shares the mission with the device, and nothing a stranger wrote runs or locks without approval (Q-92 (7)). | Q-72 | T |
| BL-FMT-06 | The optional `brain` section shall hold NeuroClaw settings that are text only (skills, the tested NeuroClaw version) and no secret, no tool switch that Q-80 labels as a risk turned on; install shows it and never installs or reconfigures NeuroClaw itself. | Box + NeuroClaw counts as a Blueprint (Q-81) without the package reaching into the brain's install. | Q-81, Q-83 | T |

### 3.2 Pack (BL-PK)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-PK-01 | `neuroedge blueprint pack [dir] [--out <dir>]` shall write the package (the listed files and `blueprint.toml`) and `<name>-<version>.tar.gz`, and print the package digest. | One command from a working project. | FR-CLI-13 | T |
| BL-PK-02 | The package digest shall be `sha256:` of the RFC 8785 canonical JSON of the manifest whose `files` table maps each path to its SHA-256; two packs of the same content shall give the same digest on any machine, and changing one byte of any file shall change it. The `.tar.gz` shall be reproducible (sorted entries, fixed mtime, uid/gid 0, no extended attributes). | One number identifies what was tested. | FR-BP-02 | T |
| BL-PK-03 | Pack shall refuse, with exit code 1 and nothing written: a gate whose version is `-draft` or that does not resolve; a gate whose digest differs from the one recorded in the manifest of an earlier pack of the same version; a failing `neuroedge gate lint` or `build --target sim`; missing evidence. | The package proves only locked rules. | FR-BP-02, CHANGELOG §3.3 #1 | T |
| BL-PK-04 | Pack shall replay every evidence trace against the packed agent and refuse when any verdict, reason or pin command differs from the recording (BL-EV-02). | No Blueprint without proof that reproduces. | FR-BP-04 | T |
| BL-PK-05 | Pack shall refuse a file that looks like a secret (BL-SC-03) and list the files it left out by rule (`build/`, `.venv/`, `__pycache__/`, `.git/`, `traces/` other than evidence). | A maker's working directory has keys in it; the package must not. | NFR-SEC-14 | T |

### 3.3 Evidence (BL-EV)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-EV-01 | Each evidence entry shall name a `trace.v1` file, its tier (`sim`, `G1`, `G2`, `G3`, `G4`, `hardware`), its duration as recorded, and the board it ran on; a trace recorded on `sim-virtual` carries `risk=virtual_board` into the summary. | The reader knows what kind of proof it is. | FR-BP-04, VP-VB-05 | T |
| BL-EV-02 | Evidence passes when `replay` on the packed agent reaches the recorded verdicts and pin commands; a chip trace (NE1 sessions) replays on the host as `record`/`replay` already do (TC-B-12-1). | One meaning of "proof" everywhere. | FR-BP-04 | T |
| BL-EV-03 | `show`, `install` and the index shall say **"unsigned"** next to every piece of evidence until signed traces exist (`TODOS.md` #1). | The seller can edit a trace; the reader must know. | FR-BP-04 | T |

### 3.4 Show and install (BL-IN)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-IN-01 | `neuroedge blueprint install <source> [--digest sha256:…] [--into <dir>]` and `neuroedge blueprint show <source>` shall accept, as `<source>`, a local package (`.tar.gz` or directory), an HTTPS archive, a git URL at a tag or commit, or an index name; plain `http://` shall be refused. | Self-hosted packages, no account. | FR-BP-03, FR-BP-05 | T |
| BL-IN-02 | Before writing any file, install shall verify the package digest against `--digest`, else against the index entry, else print it and ask the person to confirm it; on mismatch it shall exit 1 and leave the file system unchanged. | Zero files on a bad package. | FR-BP-03, NFR-SEC-14 | T |
| BL-IN-03 | The approval summary (printed by `show`, and by `install` before activation) shall list: name, version, author, license (FR-BP-08); what the agent requires (primitives, pins, sensors, parts by kind) and on which board; each action with its gate and what the gate checks, in the gate's own words; whether a person is asked and for what; network destinations the agent or brain settings name; risk labels (`virtual_board`, and any of DP-COM-06); every evidence entry with tier, duration and **unsigned**; files the package contains by kind. | The person approves knowing what will run and what it can move. | FR-BP-03, FR-BP-06, NFR-SEC-14 | T |
| BL-IN-04 | Install parameters declared in the manifest (name, type, default, range, where written: a `[sim.facts]` key, a `[sim.sensor_facts]` threshold, a part attribute) shall be asked for, validated, and written into the installed copy; a parameter that targets a gate file shall make the package invalid. | Tune the device without changing the proven rules. | FR-BP-03 | T |
| BL-IN-05 | No file of the package shall be imported or executed before the person approves the summary (`--yes` only with `--digest`, for scripts); activation then builds for `sim` and replays the evidence in a child process, and refuses activation (files kept, agent marked not activated) when replay fails. | FR-BP-01 forbids code during install, FR-BP-03 asks for replay: replay is code (`@action` bodies), so it runs after consent, not before. | FR-BP-01, FR-BP-03 | T |
| BL-IN-06 | Install shall write into a new directory (`--into`, else `./<name>`), never into an existing non-empty one, and print the next command (`cd <name> && neuroedge run --ui`). | No overwrite; a first run in one line. | FR-BP-03 | T |
| BL-IN-07 | From a clean machine with the wheel installed, `blueprint install` of the fish tank followed by `neuroedge run` on `sim` shall take under 10 minutes with no account (A14). | The install session with three testers measures it (TSK-I2e-09). | A14 | D |

### 3.5 Index (BL-IX)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-IX-01 | The index shall be a static repository of one TOML file per Blueprint version: name, version, URL, package digest, author, license, evidence tiers and durations, `unsigned = true`, summary; no server, no account, no counts, no paid ranking. | Hub without a server until the gate. | FR-BP-05 | I |
| BL-IX-02 | `install <name>[@version]` shall read the index (a configured git URL or a local checkout), take the entry's URL and digest, and verify the downloaded package against that digest (BL-IN-02). | The index's digest is the promise. | FR-BP-05 | T |
| BL-IX-03 | `neuroedge blueprint index-entry <package>` shall print the entry a maker commits to the index, from the package itself. | The entry cannot drift from the package. | FR-BP-05 | T |

### 3.6 Kit (BL-KT)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-KT-01 | The optional `kit` section shall hold `kit/bom.toml` (each item: part name of `[sim.parts]` or a board, quantity, part number, at least one purchase link) and a wiring drawing; every output, input and sensor the agent's parts declare shall have a BOM item, and every BOM item a part or the board. | A buyer gets what the agent needs, nothing it does not. | FR-BP-07, FR-DX-09 | T |
| BL-KT-02 | `bom.toml` shall hold plain links with no affiliate tag; `show` prints them. Q-92 (2) cut the affiliate page. | Commissions never sit on the safety path (Q-72). | FR-BP-07 | I |
| BL-KT-03 | The fish tank Blueprint shall ship with kit, BOM, wiring, its agent on parts (VP-PT-08), its demo-day `sim` trace and chip sessions as evidence, and pass BL-PK-01 → 05. | The first Blueprint is the reference. | FR-DX-09, TSK-I2d-28 | T |

### 3.7 Security (BL-SC)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-SC-01 | Unpacking shall refuse archive entries that are absolute, contain `..`, are links or devices, exceed 50 MB in total or 2 000 files, and shall unpack into a temporary directory moved into place only after BL-IN-02 passes. | No tar-slip, no zip bomb, no half-written install. | NFR-SEC-14 | T |
| BL-SC-02 | Fetching shall use HTTPS with certificate checks (or git over HTTPS), follow at most 5 redirects, and stop at the size limit of BL-SC-01. | Self-hosted does not mean unauthenticated transport. | NFR-SEC-14 | T |
| BL-SC-03 | A secret shall never enter a package: pack refuses files named or shaped like keys and tokens (`*.key`, `*.pem` private keys, `.env*`, `nao.token`, `ui.json`, `revoked.txt`, `jwks.json` private parts, NeuroClaw `config.json`), and values that match a secret pattern in `agent.toml` or brain settings (the rules of `plugins/actuators.py` `secret_fields`). | A maker's directory holds the box's keys (`neuroedge pair`). | DP-A-04, NFR-SEC-14 | T |
| BL-SC-04 | Install shall run no hook, script or entry point of the package, and add nothing to the Python path except the installed agent's own directory when the person runs it. | Declarative only. | FR-BP-01 | T |

### 3.8 Non-functional requirements (BL-NF)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| BL-NF-01 | Pack and install shall work offline for a local package; only fetching needs the network. | `sim` needs no account or network (FR-DX-02). | FR-DX-02 | T |
| BL-NF-02 | Install shall record the "installed a Blueprint" milestone only under the opt-out policy of FR-TEL-01 (no package name, no digest, no URL). | Launch telemetry counts installs without tracking anyone (Q-92 (1)). | FR-TEL-07 | T |

---

## 4. Interfaces

### 4.1 `blueprint.toml` (illustrative; the RFC of TSK-I2e-01 writes the schema)

```toml
schema  = "neuroedge.blueprint/v1"
name    = "be-ca-nhiet-doi"
version = "1.0.0"
author  = "@maker"
license = "PolyForm-Noncommercial-1.0.0; commercial use under the NeuroEdge commercial licence"
summary = "Bể cá nhiệt đới: sưởi, sục khí, đèn; không sưởi khi nước ấm, tắt sục khí phải hỏi chủ nhà"
agent   = "agent"

[[evidence]]
trace    = "evidence/mot-ngay.json"
tier     = "sim"
board    = "sim-default"
duration = "25 s"

[[evidence]]
trace    = "evidence/chip-sess-1.json"
tier     = "G3"
board    = "esp32s3-box-3"

[[parameters]]
name    = "warm_from"
type    = "number"
default = 29
range   = [24, 32]
writes  = "sim.sensor_facts.water_hot.gte"

[kit]
bom     = "kit/bom.toml"
wiring  = "kit/wiring.svg"

[files]   # path -> sha256, written by `pack`
"agent/agent.toml" = "sha256:…"
```

### 4.2 Command line

```
neuroedge blueprint pack [dir] [--out dist/]
neuroedge blueprint show <file|dir|url|name>
neuroedge blueprint install <file|dir|url|name> [--digest sha256:…] [--into dir] [--yes]
neuroedge blueprint index-entry <package>
```

Exit codes: `0` done; `1` refused (invalid package, digest mismatch, failing evidence, secret
found); `2` a `contract` or `detectors` section whose format does not exist yet (BL-FMT-05).

---

## 5. Verification

Status `implemented — <file>::<test>` names a test in this repository; `planned — <TSK>` names
the roadmap task that adds the test with the code. No test is skipped in the meantime
(CONTRIBUTING.md §5).

| TC | Verifies | Level | Procedure → expected | Status |
|:---|:---|:---|:---|:---|
| TC-FMT-01-1 | BL-FMT-01 | unit | Valid manifests load; each missing required field, a bad name or version → error naming the field | planned — TSK-I2e-01 |
| TC-FMT-02-1 | BL-FMT-02 | unit | Unlisted file, missing file, absolute path, `..`, symlink → each refused naming the path | planned — TSK-I2e-01 |
| TC-FMT-03-1 | BL-FMT-03 | integration | Package whose agent does not build for `sim` → refused with the build's problems | planned — TSK-I2e-02 |
| TC-FMT-04-1 | BL-FMT-04 | unit | Agent on `sim-virtual` with a pin map for `esp32s3-box-3` → accepted; package with a `board.v1` file → refused naming TSK-I2d-02 | planned — TSK-I2e-01 |
| TC-FMT-05-1 | BL-FMT-05 | unit | `contract` filled with a valid `mission.v1` contract → listed in the approval summary and locked only on approval; before the format exists → exit 2 naming what it waits for | planned — TSK-I2e-01 |
| TC-FMT-06-1 | BL-FMT-06 | unit | Brain section with a secret or a Q-80 risk tool on → refused; text-only settings shown in the summary | planned — TSK-I2e-03 |
| TC-PK-01-1 | BL-PK-01 | integration | `pack` of the fish tank → package directory, `.tar.gz`, printed digest | planned — TSK-I2e-02 |
| TC-PK-02-1 | BL-PK-02 | unit | Two packs → same digest and identical `.tar.gz` bytes; one byte changed in any file → different digest | planned — TSK-I2e-02 |
| TC-PK-03-1 | BL-PK-03 | integration | `-draft` gate, unresolved gate, changed gate at same version, failing lint or build, no evidence → each exit 1, nothing written | planned — TSK-I2e-02 |
| TC-PK-04-1 | BL-PK-04 | integration | An evidence trace edited to another verdict → pack refuses naming the trace and the step | planned — TSK-I2e-02 |
| TC-PK-05-1 | BL-PK-05 | unit | Project with `build/`, `.venv/`, a `nao.token` → the token refused, the rest left out and listed | planned — TSK-I2e-02 |
| TC-EV-01-1 | BL-EV-01 | unit | Evidence entries without tier, duration or board → refused; a `sim-virtual` trace → summary shows `risk=virtual_board` | planned — TSK-I2e-01 |
| TC-EV-02-1 | BL-EV-02 | integration | The fish tank's demo-day trace and a chip NE1 session replay to their verdicts from the package | planned — TSK-I2e-05 |
| TC-EV-03-1 | BL-EV-03 | unit | `show`, `install` summary and `index-entry` output each carry "unsigned" for every evidence entry | planned — TSK-I2e-03 |
| TC-IN-01-1 | BL-IN-01 | integration | Install from a local `.tar.gz`, a directory, a local git repository at a tag, a local HTTPS test server; `http://` → refused | planned — TSK-I2e-03 |
| TC-IN-02-1 | BL-IN-02 | integration | Wrong `--digest`, index digest mismatch → exit 1 and the target directory and temp space unchanged | planned — TSK-I2e-03 |
| TC-IN-03-1 | BL-IN-03 | unit | Summary of the fish tank lists license, parts, each action with its gate words, the question for the air pump, evidence with "unsigned" | planned — TSK-I2e-03 |
| TC-IN-04-1 | BL-IN-04 | unit | Parameter out of range → asked again / refused with `--yes`; written into the installed `agent.toml`; a parameter writing into `gates/` → package invalid | planned — TSK-I2e-03 |
| TC-IN-05-1 | BL-IN-05 | integration | A package whose action module writes a marker file at import → no marker after `show` or before approval; activation runs replay in a child process; failing replay → not activated | planned — TSK-I2e-03 |
| TC-IN-06-1 | BL-IN-06 | unit | Install into an existing non-empty directory → refused, nothing written | planned — TSK-I2e-03 |
| TC-IN-07-1 | BL-IN-07 | demonstration | Measured A14 session: clean machine, wheel, install, `run` on `sim`, timestamps per step, < 10 min | planned — TSK-I2e-09 |
| TC-IX-01-1 | BL-IX-01 | inspection | The index repository holds TOML entries only and no server code | planned — TSK-I2e-04 |
| TC-IX-02-1 | BL-IX-02 | integration | Install by name from a local index checkout verifies the entry's digest; tampered package → refused | planned — TSK-I2e-04 |
| TC-IX-03-1 | BL-IX-03 | unit | `index-entry` of a package → entry whose digest, license, evidence and `unsigned` match the package | planned — TSK-I2e-04 |
| TC-KT-01-1 | BL-KT-01 | unit | BOM missing an item for a part, or an item with no part and no link → refused naming it | planned — TSK-I2e-05 |
| TC-KT-02-1 | BL-KT-02 | inspection | `bom.toml` links carry no affiliate tag | planned — TSK-I2e-05 |
| TC-KT-03-1 | BL-KT-03 | integration | The fish tank Blueprint packs, shows and installs, and its evidence replays | planned — TSK-I2e-05 |
| TC-SC-01-1 | BL-SC-01 | unit | Archives with `../x`, `/etc/x`, a symlink, a device, 51 MB, 2 001 files → each refused, nothing outside the temp directory | planned — TSK-I2e-03 |
| TC-SC-02-1 | BL-SC-02 | integration | Self-signed HTTPS → refused; 6 redirects → refused; body over the limit → stopped | planned — TSK-I2e-03 |
| TC-SC-03-1 | BL-SC-03 | unit | Each secret file name and a secret value in `agent.toml` → pack refuses naming it | planned — TSK-I2e-02 |
| TC-SC-04-1 | BL-SC-04 | integration | Package with `setup.py`, a `.pth` file and a console entry point → none runs or is installed | planned — TSK-I2e-03 |
| TC-BNF-01-1 | BL-NF-01 | integration | Pack and install of a local package with the network blocked | planned — TSK-I2e-08 |
| TC-BNF-02-1 | BL-NF-02 | unit | Install records one milestone event with no name, digest or URL; opt-out → none | planned — TSK-I2e-07 |

---

## 6. Traceability

| PRD | Requirements |
|:---|:---|
| FR-BP-01 | BL-FMT-01 → 06, BL-IN-05, BL-SC-04 |
| FR-BP-02 | BL-PK-01 → 05 |
| FR-BP-03 | BL-IN-01 → 07 |
| FR-BP-04 | BL-PK-04, BL-EV-01 → 03 |
| FR-BP-05 | BL-IN-01, BL-IX-01 → 03 |
| FR-BP-06 | BL-FMT-04, BL-IN-03 |
| FR-BP-07 | BL-KT-01, BL-KT-02 |
| FR-BP-08 | BL-IN-03 |
| FR-CLI-13 | BL-PK-01, BL-IN-01, §4.2 |
| NFR-SEC-14 | BL-FMT-02, BL-IN-02, BL-IN-03, BL-SC-01 → 04 |
| FR-TEL-07 | BL-NF-02 |
| A14 | BL-IN-07, BL-KT-03 |
| FR-BP-09, FR-BP-10 | out of scope (§1.2) |

## 7. Decisions this specification takes (Q-86, product owner, 2026-10-16)

| ID | Decision | Why | Alternative |
|:---|:---|:---|:---|
| BL-D-01 | Package code runs only after approval; replay is part of activation (BL-IN-05) | FR-BP-01 and FR-BP-03 conflict: replay executes `@action` bodies | Replay before approval in a sandbox (a sandbox per OS is new work and still runs seller code) |
| BL-D-02 | Blueprints v1 target reference boards and use pin maps; no shipped board profiles (BL-FMT-04) | Shipped profiles carry `safe_state ≠ off`, which waits for the conditional-safety RFC | Allow shipped profiles now with `safe_state = off` only |
| BL-D-03 | Mission contracts and detectors are accepted in a package once their formats exist, shown and locked only on approval (BL-FMT-05; reserved and refused under Q-86, amended by Q-92 (7)) | The mission core ships with the public launch, so the fish tank can share its mission | Keep them refused in v1 and open them in a `blueprint.v2` |
| BL-D-04 | Manifest in TOML (`blueprint.toml`); digest over files, not over the archive (BL-PK-02) | Same language as `agent.toml`; git and `.tar.gz` give the same digest | YAML like gates; digest of the archive bytes |
