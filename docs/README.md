# NeuroEdge documentation

Start from the row that describes you. Each topic has one home (`CONTRIBUTING.md` §8.1); the
other pages link to it instead of repeating it.

| You are | Start here | Then |
|:---|:---|:---|
| **Trying it** (maker, family) | [`../README.md`](../README.md) quickstart · [`user/bat-dau.md`](user/bat-dau.md) | [`user/huong-dan.md`](user/huong-dan.md) guide · [`user/an-toan.md`](user/an-toan.md) safety in plain words · [`user/trang-thai.md`](user/trang-thai.md) what works today |
| **Integrating** (partner, product team) | [`user/doi-tac/README.md`](user/doi-tac/README.md) | [`spec/extension_sdk.md`](spec/extension_sdk.md) · [`spec/tool_calling.md`](spec/tool_calling.md) · [`spec/python_api.md`](spec/python_api.md) |
| **Contributing** (developer, coding agent) | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) · [`../CHANGELOG.md`](../CHANGELOG.md) §3 handoff | [`reference/cli.md`](reference/cli.md) commands · [`architecture/README.md`](architecture/README.md) · [`../roadmap/neuroedge-roadmap.md`](../roadmap/neuroedge-roadmap.md) §0 |
| **Evaluating the business** (investor, partner) | [`business/README.md`](business/README.md) | [`business/product-proposal.md`](business/product-proposal.md) · [`business/kien-truc-tong-the.html`](business/kien-truc-tong-the.html) |

## What lives where

| Folder | Contents |
|:---|:---|
| [`user/`](user/README.md) | Guides for people using the product: install, run, kits, firmware, glossary ([`thuat-ngu.md`](user/thuat-ngu.md)) |
| [`reference/`](reference/cli.md) | Every command, its expected output, exit codes, error messages and CI jobs |
| [`architecture/`](architecture/README.md) | How the system is built: C4 chapters `00`–`16` and generated posters |
| `spec/` | Normative specifications, listed below |
| [`rfc/`](rfc/README.md) | Approved changes to contracts and formats |
| [`business/`](business/README.md) | Proposal, business requirements, home web and app, partner sessions |
| [`reports/`](reports/README.md) | Dated spikes and studies; evidence behind decisions |
| [`release.md`](release.md) | How a release is cut (used by `release-pypi.yml`) |

Decisions are in [`roadmap/neuroedge-prd.md`](../roadmap/neuroedge-prd.md) §15 (`Q-N`); progress and
tasks are in [`roadmap/neuroedge-roadmap.md`](../roadmap/neuroedge-roadmap.md) §0.

## Specifications

| Spec | Defines |
|:---|:---|
| [`core_contracts.md`](spec/core_contracts.md) | API, `board.toml`, `agent.toml`, gates, HAL and traces |
| [`tool_calling.md`](spec/tool_calling.md) | The path from language to a physical action; MCP |
| [`threat_model.md`](spec/threat_model.md) | Every path from a verdict to a pin, and what is out of scope |
| [`deployment_profiles.md`](spec/deployment_profiles.md) | Profile A (separate brain) and Profile B (one chip, all-in-one) |
| [`missions.md`](spec/missions.md) | Missions and the operator runtime |
| [`blueprint.md`](spec/blueprint.md) | NeuroEdge Blueprint packaging and install |
| [`virtual_parts.md`](spec/virtual_parts.md) | Virtual parts and pin maps |
| [`extension_sdk.md`](spec/extension_sdk.md) | `neuroedge.guard` and the Extension SDK |
| [`python_api.md`](spec/python_api.md) | Public Python API and CLI surface |
| [`simulation_coverage.md`](spec/simulation_coverage.md) | Primitives × targets coverage |
| [`vision.md`](spec/vision.md) · [`camera.md`](spec/camera.md) | Vision facts and camera modes |
| [`voice_fsm.md`](spec/voice_fsm.md) | Conversation state machine (voice) |
| [`ui.md`](spec/ui.md) · [`studio.md`](spec/studio.md) | Device screens; the local web app |
| [`hal_mcu_review.md`](spec/hal_mcu_review.md) | HAL review under microcontroller limits |
| [`lab_mcp.md`](spec/lab_mcp.md) | NeuroEdge Lab, trimmed to the sections still cited |
