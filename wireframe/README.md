# wireframe/

HTML reference wireframes for the user interface. Open directly in a browser; no internet required.

**Not source code and not packaged.** Each file embeds a **snapshot**
of `python/neuroedge/viz/assets/ui.css` at the time it was authored. The actual CSS for the sim page
resides only in `python/neuroedge/viz/assets/`. When the two differ, `viz/assets/` is authoritative.

| File | Content | Plan |
|:---|:---|:---|
| [`studio-v1.html`](studio-v1.html) | **Reference design.** NeuroEdge Studio: seven screens (live session, gates, traces, verification, ESP32-S3 device, MCP, configuration), bilingual, approved 2026-09-29 | TSK-I1-04, `docs/spec/studio.md` (Q-51) |
| [`lab-monitor-v2.html`](lab-monitor-v2.html) | **Reference design.** Lab Monitor panel in sim page, updated per design review 2026-09-24 | `docs/spec/lab_mcp.md` §11 (Block N5b) |
| [`lab-monitor-v1.html`](lab-monitor-v1.html) | Two initial layout variants (A: panel within page, **selected**; B: separate tab) | historical, non-normative |

IBM Plex font is **not yet** embedded in wireframes (pending TSK-N0-06). Wireframes use system fonts.
