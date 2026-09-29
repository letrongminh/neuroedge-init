/* neuroedge studio — the page (docs/spec/studio.md).
 * Text from the server, an event or a trace is always set with textContent.
 * No framework, no external asset; every request goes to the same origin.
 */
"use strict";

(function () {
  const boot = JSON.parse(document.getElementById("ne-boot").textContent);
  const root = document.getElementById("studio");
  const VIEWS = ["live", "gate", "traces", "verify", "device", "mcp", "config"];

  // ---------------------------------------------------------------- state
  const S = {
    lang: "vi",
    view: "live",
    events: [],
    nowMs: 0,
    connected: false,
    everConnected: false,
    voice: null,
    agent: null,
    gates: null,
    gateName: null,
    gateInfo: {},
    whatifSeq: 0,
    traces: null,
    traceName: null,
    trace: null,
    traceNote: null,
    verify: { lint: null, test: null, verify: null },
    device: null,
    deviceNote: null,
    screenLang: null,
    mcp: null,
    reply: null,
    draft: "",
    answerError: null,
    openExplain: new Set()
  };
  try {
    const saved = localStorage.getItem("ne_studio_lang");
    if (saved === "vi" || saved === "en") S.lang = saved;
  } catch (e) { /* storage may be blocked */ }
  document.documentElement.lang = S.lang;

  // ---------------------------------------------------------------- helpers
  function t(key) {
    const dict = I18N[S.lang] || I18N.vi;
    return dict[key] !== undefined ? dict[key] : key;
  }

  function fill(text, vars) {
    return text.replace(/\{(\w+)\}/g, function (m, k) { return vars[k] !== undefined ? String(vars[k]) : m; });
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    const a = attrs || {};
    for (const k in a) {
      const v = a[k];
      if (v === null || v === undefined || v === false) continue;
      if (k === "text") node.textContent = String(v);
      else if (k === "class") node.className = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : String(v));
    }
    add(node, children);
    return node;
  }

  function add(node, children) {
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      node.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
    });
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs, children) {
    const node = document.createElementNS(SVG_NS, tag);
    const a = attrs || {};
    for (const k in a) {
      if (k === "text") node.textContent = String(a[k]);
      else node.setAttribute(k, String(a[k]));
    }
    add(node, children);
    return node;
  }

  function clear(node) { node.textContent = ""; }
  function short(data, n) {
    const text = JSON.stringify(data === undefined ? null : data);
    const cap = n || 140;
    return text.length > cap ? text.slice(0, cap - 1) + "…" : text;
  }
  function fmtMs(v) {
    const n = Number(v) || 0;
    return (n >= 100 ? String(Math.round(n)) : n >= 10 ? n.toFixed(1) : n.toFixed(2)) + " ms";
  }
  function chip(kind, text) { return el("span", { class: "st " + kind, text: text }); }
  function verdictChip(v) {
    return chip(v === "ALLOW" ? "allow" : "block", (v === "ALLOW" ? "✓ " : "✗ ") + v);
  }
  function codeBox(value) {
    return el("pre", { class: "code-box", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) });
  }
  function panel(titleKey, sub, extra, body) {
    return el("section", { class: "panel" }, [
      el("h2", {}, [el("span", { text: t(titleKey) }), sub ? el("span", { class: "sub", text: sub }) : null, extra]),
      body
    ]);
  }
  function whyOf(res) {
    const e = (res && res.error) || {};
    return (e.why || t("msg_not_available")) + (e.how ? " — " + e.how : "");
  }
  function naCard(res) {
    return el("div", { class: "not-available" }, [
      chip("warn", t("lbl_not_available")),
      el("span", { text: whyOf(res) })
    ]);
  }
  function loadingCard() { return el("div", { class: "hint", text: t("lbl_loading") }); }

  // GET/POST /api/<tail>: always resolves to an object with `ok`; 501 => `na`.
  function api(method, tail, body) {
    const opt = { method: method };
    if (body !== undefined) {
      opt.headers = { "Content-Type": "application/json" };
      opt.body = JSON.stringify(body);
    }
    return fetch("/api/" + tail, opt).then(function (r) {
      return r.json().then(function (j) {
        if (r.status === 501) j.na = true;
        return j;
      }, function () {
        return { ok: false, error: { why: "HTTP " + r.status } };
      });
    }).catch(function (e) {
      return { ok: false, error: { why: String(e) } };
    });
  }

  function enc(s) { return encodeURIComponent(s).replace(/%40/g, "@"); }

  // ---------------------------------------------------------------- events -> state
  function stateOf(evs, tMs) {
    const pins = {}, sensors = {}, asks = {};
    let frame = null;
    evs.forEach(function (e) {
      const d = e.data || {};
      if (e.type === "actuator_command") {
        const until = d.operation === "pulse" ? e.offset_ms + (d.duration_ms || 0)
          : d.operation === "on" ? Infinity : e.offset_ms;
        pins[d.pin] = { until: until, operation: d.operation };
      } else if (e.type === "actuator_aborted" && pins[d.pin]) {
        pins[d.pin].until = Math.min(pins[d.pin].until, e.offset_ms);
        pins[d.pin].aborted = d.reason;
      } else if (e.type === "sensor_read" || e.type === "sensor_set") {
        sensors[d.sensor] = { value: d.value, unit: d.unit || (sensors[d.sensor] && sensors[d.sensor].unit) };
      } else if (e.type === "display_frame") {
        frame = d;
      } else if (e.type === "tool_confirm_requested") {
        asks[d.id] = d;
      } else if (e.type === "tool_confirmed" || e.type === "tool_confirm_declined" || e.type === "tool_confirm_expired") {
        delete asks[d.id];
      }
    });
    Object.keys(pins).forEach(function (k) { pins[k].on = tMs < pins[k].until; });
    const pending = Object.keys(asks).map(function (k) { return asks[k]; }).filter(function (a) {
      return a.expires_ms > tMs;
    });
    return { pins: pins, sensors: sensors, frame: frame, pending: pending };
  }

  // Turns: from text_input / stt_result to the next one (docs/spec/studio.md §5).
  function groupTurns(evs) {
    const turns = [], gates = [];
    let cur = null, begin = null, facts = null;
    function open(e, d, kind, text) {
      cur = {
        idx: e.idx, offset: e.offset_ms, voice: kind === "stt_result", hasStt: kind === "stt_result",
        hasText: kind === "text_input", text: text, implicit: false, intents: [], notRecognized: null,
        s1: false, s2: false, knowledge: null, mcp: [], calls: [], gates: [], confirms: [], tts: [],
        latency: null
      };
      turns.push(cur);
    }
    evs.forEach(function (e, idx) {
      e.idx = idx;
      const d = e.data || {};
      const ty = e.type;
      if (ty === "stt_result" || ty === "text_input") {
        if (cur && cur.offset === e.offset_ms && cur.text === d.text &&
            ((ty === "text_input" && cur.hasStt && !cur.hasText) || (ty === "stt_result" && cur.hasText && !cur.hasStt))) {
          if (ty === "stt_result") { cur.voice = true; cur.hasStt = true; } else cur.hasText = true;
          return;
        }
        open(e, d, ty, d.text === undefined ? "—" : String(d.text));
        return;
      }
      if (ty === "tool_call" && d.source === "mcp" && (!cur || cur.calls.length > 0 || cur.gates.length > 0)) {
        open(e, d, "mcp", "MCP · " + d.name);
        cur.implicit = true;
      }
      if (ty === "gate_evaluation_begin") { begin = d; facts = null; }
      else if (ty === "gate_facts") facts = d;
      else if (ty === "gate_evaluation_result") {
        const g = {
          idx: idx, offset: e.offset_ms, gate: (begin && begin.gate) || d.blocked_by || "gate",
          digest: begin && begin.gate_digest, facts: facts || {}, result: d
        };
        gates.push(g);
        if (cur) cur.gates.push(g);
        begin = null; facts = null;
      }
      if (!cur) return;
      if (ty === "intent_extracted") cur.intents.push(d);
      else if (ty === "command_not_recognized") cur.notRecognized = d;
      else if (ty === "system_one_call" || ty === "system_one_fallback") cur.s1 = true;
      else if (ty === "system_two_call" || ty === "system_two_reply") cur.s2 = true;
      else if (ty === "knowledge_retrieved") cur.knowledge = d;
      else if (ty === "mcp_tool_result") cur.mcp.push(d);
      else if (ty === "tool_call") cur.calls.push(d);
      else if (ty === "tool_confirm_requested" || ty === "tool_confirmed" || ty === "tool_confirm_declined" || ty === "tool_confirm_expired") cur.confirms.push({ type: ty, data: d });
      else if (ty === "tts_stream_start") cur.tts.push(d.text);
      else if (ty === "turn_latency") cur.latency = d;
    });
    turns.forEach(function (tr) {
      const lat = tr.latency || {};
      const viaMcp = tr.mcp.length > 0 || tr.calls.some(function (c) { return c.source === "mcp"; });
      if (viaMcp) tr.route = "route_mcp";
      else if (tr.knowledge || lat.reply_source === "knowledge_rag") tr.route = "route_rag";
      else if (tr.s2 || lat.path === "system_2") tr.route = "route_s2";
      else if (tr.s1 || tr.calls.some(function (c) { return c.source === "system_one"; })) tr.route = "route_s1";
      else if (tr.intents.length > 0 || tr.calls.length > 0) tr.route = "route_grammar";
      else tr.route = null;
    });
    return { turns: turns, gates: gates };
  }

  // ---------------------------------------------------------------- icons (as in viz/assets/ui.js)
  function pinIcon(pin, on) {
    const c = on ? "var(--allow)" : "var(--dim)";
    if (/lock/.test(pin)) {
      return svg("svg", { viewBox: "0 0 64 64", "aria-hidden": "true" }, [
        svg("path", { d: on ? "M22 30 V20 a10 10 0 0 1 20 0" : "M22 30 V20 a10 10 0 0 1 20 0 V30", fill: "none", stroke: c, "stroke-width": "5" }),
        svg("rect", { x: 14, y: 30, width: 36, height: 26, rx: 4, fill: c }),
        svg("circle", { cx: 32, cy: 43, r: 4, fill: "var(--panel)" })
      ]);
    }
    if (/light|lamp|led/.test(pin)) {
      return svg("svg", { viewBox: "0 0 64 64", "aria-hidden": "true" }, [
        svg("circle", { cx: 32, cy: 26, r: 16, fill: on ? "#f2cc60" : "none", stroke: c, "stroke-width": 4 }),
        svg("rect", { x: 24, y: 44, width: 16, height: 10, rx: 2, fill: c })
      ]);
    }
    if (/relay|gate|vent|fan/.test(pin)) {
      return svg("svg", { viewBox: "0 0 64 64", "aria-hidden": "true" }, [
        svg("circle", { cx: 14, cy: 40, r: 5, fill: c }),
        svg("circle", { cx: 50, cy: 40, r: 5, fill: c }),
        svg("line", { x1: 14, y1: 40, x2: on ? 50 : 44, y2: on ? 40 : 18, stroke: c, "stroke-width": 5, "stroke-linecap": "round" })
      ]);
    }
    return svg("svg", { viewBox: "0 0 64 64", "aria-hidden": "true" }, [
      svg("circle", { cx: 32, cy: 32, r: 18, fill: on ? "var(--allow)" : "none", stroke: c, "stroke-width": 4 })
    ]);
  }

  const NAV_ICONS = {
    live: [["circle", { cx: 12, cy: 12, r: 10 }], ["circle", { cx: 12, cy: 12, r: 3 }]],
    gate: [["path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" }]],
    traces: [["polyline", { points: "22 12 18 12 15 21 9 3 6 12 2 12" }]],
    verify: [["path", { d: "M22 11.08V12a10 10 0 1 1-5.93-9.14" }], ["polyline", { points: "22 4 12 14.01 9 11.01" }]],
    device: [["rect", { x: 4, y: 4, width: 16, height: 16, rx: 2 }], ["rect", { x: 9, y: 9, width: 6, height: 6 }]],
    mcp: [["circle", { cx: 18, cy: 5, r: 3 }], ["circle", { cx: 6, cy: 12, r: 3 }], ["circle", { cx: 18, cy: 19, r: 3 }],
      ["line", { x1: 8.6, y1: 13.5, x2: 15.4, y2: 17.5 }], ["line", { x1: 15.4, y1: 6.5, x2: 8.6, y2: 10.5 }]],
    config: [["circle", { cx: 12, cy: 12, r: 3 }], ["path", { d: "M12 1v4M12 19v4M1 12h4M19 12h4M4.2 4.2l2.8 2.8M17 17l2.8 2.8M4.2 19.8L7 17M17 7l2.8-2.8" }]]
  };

  // ---------------------------------------------------------------- shell
  let refs = {};          // DOM handles of the current shell
  let regions = {};       // signature of what each live region shows

  function buildApp() {
    document.documentElement.lang = S.lang;
    regions = {};
    refs = { views: {}, nav: {} };

    refs.lost = el("div", { class: "banner lost", role: "status" }, [
      el("span", { text: "⚠ " + t("banner_lost_msg") })
    ]);
    refs.badge = el("span", { class: "live-badge", role: "status" });
    refs.providers = el("div", { class: "providers" });

    const langBtn = function (code) {
      return el("button", {
        type: "button", class: "lang-btn" + (S.lang === code ? " active" : ""), "aria-pressed": S.lang === code ? "true" : "false",
        text: code.toUpperCase(), onclick: function () { setLang(code); }
      });
    };

    const header = el("header", { class: "app-header" }, [
      el("div", { class: "header-left" }, [
        el("div", { class: "brand" }, [
          svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" }, [
            svg("polygon", { points: "12 2 2 7 12 12 22 7 12 2" }),
            svg("polyline", { points: "2 17 12 22 22 17" }),
            svg("polyline", { points: "2 12 12 17 22 12" })
          ]),
          el("span", { text: t("app_title") })
        ]),
        el("div", { class: "meta-chip" }, [el("span", { text: "agent" }), el("strong", { text: boot.agent })]),
        el("div", { class: "meta-chip" }, [el("span", { text: "target" }), el("strong", { text: boot.target })]),
        el("div", { class: "meta-chip" }, [el("span", { text: "board" }), el("strong", { text: boot.board })]),
        refs.badge
      ]),
      el("div", { class: "header-right" }, [
        refs.providers,
        el("div", { class: "lang-toggle", role: "group", "aria-label": "Language" }, [langBtn("vi"), langBtn("en")])
      ])
    ]);

    const nav = el("nav", { class: "studio-nav", "aria-label": t("nav_label") });
    VIEWS.forEach(function (v) {
      const b = el("button", {
        type: "button", class: "nav-item" + (v === S.view ? " active" : ""), "aria-current": v === S.view ? "page" : null,
        onclick: function () { switchView(v); }
      }, [
        svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" }, NAV_ICONS[v].map(function (p) { return svg(p[0], p[1]); })),
        el("span", { text: t("nav_" + v) })
      ]);
      refs.nav[v] = b;
      nav.appendChild(b);
    });

    const content = el("main", { class: "studio-content" });
    VIEWS.forEach(function (v) {
      refs.views[v] = el("section", { class: "studio-view" + (v === S.view ? " active" : ""), id: "view-" + v });
      content.appendChild(refs.views[v]);
    });

    clear(root);
    add(root, [refs.lost, header, el("div", { class: "studio-layout" }, [nav, content])]);
    paintBadge();
    paintProviders();
    renderView(S.view);
  }

  function paintBadge() {
    refs.badge.className = "live-badge" + (S.connected ? "" : " disconnected");
    clear(refs.badge);
    add(refs.badge, [el("span", { class: "live-dot" }), t(S.connected ? "live_badge" : "live_badge_lost")]);
    refs.lost.hidden = S.connected || !S.everConnected;
  }

  function paintProviders() {
    clear(refs.providers);
    const list = (S.agent && S.agent.ok && S.agent.providers) || [];
    list.forEach(function (p) {
      refs.providers.appendChild(el("div", { class: "provider-badge" }, [
        (p.label || p.role) + " ",
        el("span", { class: p.key_present ? "ok" : "missing", text: p.key_present ? t("val_key_present") : t("val_key_missing") })
      ]));
    });
  }

  function setLang(code) {
    S.lang = code;
    try { localStorage.setItem("ne_studio_lang", code); } catch (e) { /* ignore */ }
    S.draft = currentDraft();
    buildApp();
  }

  function switchView(v) {
    S.view = v;
    VIEWS.forEach(function (name) {
      refs.nav[name].classList.toggle("active", name === v);
      if (name === v) refs.nav[name].setAttribute("aria-current", "page");
      else refs.nav[name].removeAttribute("aria-current");
      refs.views[name].classList.toggle("active", name === v);
    });
    if (v === "gate") loadGates();
    else if (v === "traces") loadTraces();
    else if (v === "device") loadDevice();
    else if (v === "mcp") loadMcp();
    else if (v === "config") loadAgent();
    renderView(v);
  }

  function renderView(v) {
    if (v !== S.view) return;
    if (v === "live") renderLive();
    else if (v === "gate") renderGate();
    else if (v === "traces") renderTraces();
    else if (v === "verify") renderVerify();
    else if (v === "device") renderDevice();
    else if (v === "mcp") renderMcp();
    else renderConfig();
  }

  // ---------------------------------------------------------------- live session
  let liveRefs = null;

  function currentDraft() {
    return liveRefs && liveRefs.input && liveRefs.input.isConnected ? liveRefs.input.value : S.draft;
  }

  // Redraw a region only when what it shows changed, so focus and open <details> survive the 1 s tick.
  function region(key, sig, node, build) {
    if (regions[key] === sig) return;
    regions[key] = sig;
    clear(node);
    build(node);
  }

  function renderLive() {
    const c = refs.views.live;
    if (!liveRefs || !liveRefs.root.isConnected || liveRefs.root.parentNode !== c) {
      liveRefs = buildLiveShell();
      clear(c);
      c.appendChild(liveRefs.root);
      regions = {};
    }
    paintLive();
  }

  function buildLiveShell() {
    const r = {};
    r.devices = el("div", { class: "devices" });
    r.sensors = el("div");
    r.screen = el("div", { class: "screen-frame" });
    r.voice = el("div", { class: "voice-strip" });
    r.transcript = el("div", { class: "transcript", tabindex: "0", role: "log", "aria-label": t("title_assistant") });
    r.input = el("input", {
      class: "cmd-input", name: "cmd", autocomplete: "off", placeholder: t("cmd_placeholder"),
      "aria-label": t("cmd_placeholder"), value: S.draft
    });
    r.reply = el("div", { class: "cmd-reply", role: "status" });
    const form = el("form", { class: "cmd-form" }, [
      r.input, el("button", { type: "submit", class: "btn-primary", text: t("btn_send") })
    ]);
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      const line = r.input.value.trim();
      if (!line) return;
      r.input.value = "";
      S.draft = "";
      sendCommand(line);
    });
    r.ask = el("div");
    r.verdicts = el("div");
    r.stream = el("tbody");

    const left = el("div", { class: "col-left" }, [
      panel("title_devices", boot.board, null, r.devices),
      panel("title_sensors", null, null, r.sensors),
      panel("title_screen", null, null, r.screen)
    ]);
    const center = el("div", { class: "col-center" }, [
      el("section", { class: "panel" }, [
        el("h2", {}, [el("span", { text: t("title_assistant") })]),
        r.voice, r.transcript, form, r.reply
      ])
    ]);
    const right = el("div", { class: "col-right" }, [
      r.ask, panel("title_gate_verdicts", null, null, r.verdicts)
    ]);
    const table = el("table", { class: "data-table" }, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: t("th_time") }), el("th", { text: t("th_event") }), el("th", { text: t("th_payload") })
      ])]),
      r.stream
    ]);
    r.root = el("div", {}, [
      el("div", { class: "grid-3col" }, [left, center, right]),
      el("div", { class: "stream-panel" }, [panel("title_event_stream", null, null, el("div", { class: "table-wrap" }, [table]))])
    ]);
    return r;
  }

  function sendCommand(line) {
    S.reply = { pending: true, line: line };
    paintReply();
    fetch("/command", { method: "POST", body: line }).then(function (r) { return r.json(); }).then(function (j) {
      S.reply = { line: line, res: j };
      paintReply();
    }).catch(function (e) {
      S.reply = { line: line, res: { ok: false, error: { why: String(e) } } };
      paintReply();
    });
  }

  function paintReply() {
    if (!liveRefs) return;
    const node = liveRefs.reply;
    clear(node);
    const rp = S.reply;
    if (!rp) return;
    if (rp.pending) { node.textContent = t("lbl_running"); return; }
    const j = rp.res;
    if (!j.ok) { add(node, [chip("block", "✗"), " " + whyOf(j)]); return; }
    if (j.recognised === undefined) { add(node, [chip("allow", "✓"), " " + rp.line]); return; }
    if (!j.recognised) { add(node, [chip("warn", t("chip_not_recognized")), " " + rp.line]); return; }
    add(node, [
      chip("accent", "intent " + j.intent),
      j.verdict ? verdictChip(j.verdict) : null,
      j.action ? el("span", { class: "mono", text: " → " + j.action }) : null
    ]);
  }

  function paintLive() {
    const R = liveRefs;
    const st = stateOf(S.events, S.nowMs);
    const grouped = groupTurns(S.events);

    // devices
    const pins = boot.pins.slice();
    Object.keys(st.pins).forEach(function (p) { if (pins.indexOf(p) < 0) pins.push(p); });
    const pinRows = pins.map(function (p) {
      const s = st.pins[p];
      const on = !!(s && s.on);
      const label = !s ? "LOW" : on ? (s.operation === "pulse" ? "PULSE" : "HIGH") : (s.aborted ? "ABORTED" : "LOW");
      return { pin: p, on: on, label: label };
    });
    region("devices", JSON.stringify(pinRows), R.devices, function (n) {
      if (pinRows.length === 0) { n.appendChild(el("div", { class: "hint", text: t("lbl_no_devices") })); return; }
      pinRows.forEach(function (row) {
        n.appendChild(el("div", { class: "device" + (row.on ? " on" : "") }, [
          pinIcon(row.pin, row.on), el("div", { class: "mono", text: row.pin }), el("div", { class: "state", text: row.label })
        ]));
      });
    });

    // sensors
    const names = boot.sensors.slice();
    Object.keys(st.sensors).forEach(function (s) { if (names.indexOf(s) < 0) names.push(s); });
    const sensorRows = names.map(function (n) {
      const r = st.sensors[n];
      return { name: n, text: r && r.value !== undefined ? String(r.value) + (r.unit ? " " + r.unit : "") : "—" };
    });
    region("sensors", JSON.stringify(sensorRows), R.sensors, function (n) {
      if (sensorRows.length === 0) { n.appendChild(el("div", { class: "hint", text: t("lbl_no_sensors") })); return; }
      sensorRows.forEach(function (row) {
        n.appendChild(el("div", { class: "sensor-row" }, [
          el("span", { class: "mono", text: row.name }), el("span", { class: "sensor-val", text: row.text })
        ]));
      });
    });

    // screen
    region("screen", JSON.stringify(st.frame), R.screen, function (n) {
      const f = st.frame;
      if (!f) { n.appendChild(el("div", { class: "screen-text hint", text: t("lbl_no_frame") })); return; }
      const text = f.text !== undefined ? String(f.text)
        : [f.format, f.width && f.height ? f.width + "×" + f.height : "", f.sha256 ? String(f.sha256).slice(0, 23) + "…" : ""].join(" ");
      n.appendChild(el("div", { class: "screen-text", text: text }));
    });

    paintVoiceStrip();

    // transcript
    const last = S.events.length ? S.events[S.events.length - 1] : null;
    region("transcript", S.events.length + ":" + (last ? last.type + last.offset_ms : "") + ":" + S.lang, R.transcript, function (n) {
      const atBottom = R.transcript.scrollHeight - R.transcript.scrollTop - R.transcript.clientHeight < 40;
      if (grouped.turns.length === 0) n.appendChild(el("div", { class: "hint", text: t("lbl_no_turns") }));
      grouped.turns.forEach(function (tr) { n.appendChild(turnCard(tr)); });
      if (atBottom) R.transcript.scrollTop = R.transcript.scrollHeight;
    });

    // confirmation: redraw only when the set of open questions or the connection changes
    const askSig = st.pending.map(function (a) { return a.id; }).join(",") + ":" + S.connected + ":" + (S.answerError || "");
    const changed = regions.ask !== askSig;
    region("ask", askSig, R.ask, function (n) {
      st.pending.forEach(function (a) { n.appendChild(askCard(a)); });
      if (S.answerError) n.appendChild(el("div", { class: "hint err", text: S.answerError }));
    });
    if (changed && st.pending.length > 0 && R.ask.querySelector(".ask-btn.no")) R.ask.querySelector(".ask-btn.no").focus();
    st.pending.forEach(function (a) {
      const timer = R.ask.querySelector('[data-ask="' + String(a.id).replace(/"/g, "") + '"]');
      if (timer) timer.textContent = fill(t("confirm_time_left"), { s: Math.max(0, Math.ceil((a.expires_ms - S.nowMs) / 1000)) }) + " · " + t("confirm_source");
    });

    // verdict cards, newest first
    region("verdicts", grouped.gates.length + ":" + S.lang, R.verdicts, function (n) {
      if (grouped.gates.length === 0) { n.appendChild(el("div", { class: "hint", text: t("lbl_no_verdicts") })); return; }
      grouped.gates.slice(-20).reverse().forEach(function (g) { n.appendChild(verdictCard(g)); });
    });

    // event stream
    region("stream", S.events.length + ":" + (last ? last.type : ""), R.stream, function (n) {
      if (S.events.length === 0) {
        n.appendChild(el("tr", {}, [el("td", { colspan: "3", class: "hint", text: t("lbl_no_events") })]));
        return;
      }
      S.events.slice(-15).reverse().forEach(function (e) {
        n.appendChild(el("tr", {}, [
          el("td", { class: "mono", text: e.offset_ms + " ms" }),
          el("td", {}, [el("code", { text: e.type })]),
          el("td", { class: "mono dim", text: short(e.data, 200) })
        ]));
      });
    });
  }

  function askCard(a) {
    const no = el("button", { type: "button", class: "ask-btn no", text: t("btn_cancel"), disabled: !S.connected,
      onclick: function () { answerConfirm(a.id, "no"); } });
    const yes = el("button", { type: "button", class: "ask-btn yes", text: t("btn_agree"), disabled: !S.connected,
      onclick: function () { answerConfirm(a.id, "yes"); } });
    return el("section", { class: "panel ask-panel", role: "alertdialog", "aria-label": t("title_confirm") }, [
      el("h2", {}, [el("span", { text: t("title_confirm") }), el("span", { class: "sub", text: "RFC-0006" })]),
      el("div", { class: "ask-title", text: String(a.message || "") + (a.action ? " (" + a.action + ")" : "") }),
      el("div", { class: "ask-timer", "data-ask": String(a.id).replace(/"/g, ""), text: "" }),
      el("div", { class: "ask-btns" }, [yes, no]),
      el("div", { class: "ask-note", text: t("confirm_note") })
    ]);
  }

  function answerConfirm(id, answer) {
    S.answerError = null;
    fetch("/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: id, answer: answer }) })
      .then(function (r) { return r.json(); }).then(function (j) {
        if (!j.ok) { S.answerError = whyOf(j); regions.ask = null; paintLive(); }
      }).catch(function (e) { S.answerError = String(e); regions.ask = null; paintLive(); });
  }

  function turnCard(tr) {
    const blocked = tr.gates.some(function (g) { return g.result.verdict === "BLOCK"; });
    const card = el("div", { class: "turn" + (blocked ? " blocked" : "") });
    card.appendChild(el("div", { class: "turn-header" }, [
      el("span", { class: "speaker", text: (tr.voice ? "🎤 " : tr.implicit ? "⚙ " : "⌨ ") + (tr.implicit ? "MCP" : t("spk_you")) }),
      el("span", { class: "mono dim", text: tr.offset + " ms" })
    ]));
    card.appendChild(el("div", { class: "turn-text", text: tr.text }));

    const meta = el("div", { class: "turn-meta" });
    if (tr.route) meta.appendChild(el("span", { class: "route-badge", text: t(tr.route) }));
    tr.intents.forEach(function (it) {
      meta.appendChild(el("span", { class: "mono", text: "intent " + it.intent + (typeof it.confidence === "number" ? " (" + it.confidence.toFixed(2) + ")" : "") }));
    });
    if (tr.notRecognized) {
      meta.appendChild(chip("warn", t("chip_not_recognized") + (typeof tr.notRecognized.confidence === "number" ? " " + tr.notRecognized.confidence.toFixed(2) : "")));
    }
    tr.calls.forEach(function (cl) {
      meta.appendChild(el("span", { class: "mono", text: cl.name + "() · " + (cl.source || "?") }));
    });
    tr.gates.forEach(function (g) {
      meta.appendChild(verdictChip(g.result.verdict));
      meta.appendChild(el("span", { class: "mono", text: g.gate }));
      if (g.result.failed_criterion) {
        meta.appendChild(el("span", { class: "mono err", text: (g.result.reason || "") + " " + g.result.failed_criterion }));
      }
    });
    tr.confirms.forEach(function (cf) {
      if (cf.type === "tool_confirm_requested") meta.appendChild(chip("warn", t("chip_asked")));
      else if (cf.type === "tool_confirmed") meta.appendChild(chip("allow", t("chip_confirmed")));
      else if (cf.type === "tool_confirm_declined") meta.appendChild(chip("block", t("chip_declined")));
      else meta.appendChild(chip("warn", t("chip_expired")));
    });
    card.appendChild(meta);

    tr.tts.forEach(function (line) {
      card.appendChild(el("div", { class: "turn-reply", text: "🗣 “" + line + "”" }));
    });

    const lat = tr.latency;
    if (lat && lat.stages_ms) {
      const stages = [["p", "perception"], ["s2", "system_two"], ["g", "gate"], ["a", "action"], ["other", "other"]];
      const bar = el("div", { class: "latency-bar", role: "img", "aria-label": t("lbl_latency") + " " + fmtMs(lat.total_ms) });
      const legend = el("div", { class: "latency-legend" });
      stages.forEach(function (s) {
        const ms = Number(lat.stages_ms[s[1]]) || 0;
        if (ms <= 0) return;
        bar.appendChild(el("div", { class: "lat-seg " + s[0], style: "flex:" + ms + " 1 0" }));
        legend.appendChild(el("span", { class: "lat-key" }, [el("i", { class: "lat-dot " + s[0] }), s[1] + " " + fmtMs(ms)]));
      });
      if (bar.children.length > 0) card.appendChild(bar);
      legend.appendChild(el("span", { class: "lat-key", text: "Σ " + fmtMs(lat.total_ms) }));
      card.appendChild(legend);
    }
    return card;
  }

  function verdictCard(g) {
    const d = g.result;
    const details = el("details", { class: "verdict-details" }, [el("summary", { text: t("lbl_explain") })]);
    const body = el("div", { class: "explain" });
    details.appendChild(body);
    details.open = S.openExplain.has(g.idx);
    if (details.open) explainBody(body, g);
    details.addEventListener("toggle", function () {
      if (details.open) { S.openExplain.add(g.idx); explainBody(body, g); }
      else S.openExplain.delete(g.idx);
    });
    return el("div", { class: "verdict-card " + d.verdict }, [
      el("div", { class: "verdict-summary" }, [
        el("span", {}, [verdictChip(d.verdict), " ", el("span", { class: "mono", text: g.gate })]),
        el("span", { class: "mono dim", text: g.offset + " ms" })
      ]),
      el("div", { class: "hint", text: d.verdict === "BLOCK"
        ? [d.reason, d.failed_criterion, d.action ? "→ " + d.action : ""].filter(Boolean).join(" · ")
        : (d.action ? "→ " + d.action : "") }),
      details
    ]);
  }

  function gateBase(name) { return String(name || "").split("@")[0]; }

  function fetchGateInfo(base, done) {
    if (S.gateInfo[base]) { done(S.gateInfo[base]); return; }
    api("GET", "gates/" + enc(base)).then(function (j) {
      S.gateInfo[base] = j;
      done(j);
    });
  }

  function explainBody(body, g) {
    clear(body);
    const d = g.result;
    const crit = Object.keys(g.facts).concat(Object.keys(d.evaluations || {}).filter(function (k) { return !(k in g.facts); }));
    if (crit.length > 0) {
      const rows = crit.map(function (k) {
        const f = g.facts[k] || {};
        const ev = d.evaluations ? d.evaluations[k] : undefined;
        const value = f.value !== undefined ? f.value : ev;
        const fail = k === d.failed_criterion || ev === false;
        return el("tr", {}, [
          el("td", { class: "mono", text: k }),
          el("td", { class: "mono", text: value === undefined ? "—" : typeof value === "object" ? short(value, 60) : String(value) }),
          el("td", { text: f.source || "—" }),
          el("td", { text: f.confidence === null || f.confidence === undefined ? "—" : String(f.confidence) }),
          el("td", { class: fail ? "err" : "ok", text: fail ? "✗" : "✓" })
        ]);
      });
      body.appendChild(el("div", { class: "table-wrap" }, [el("table", { class: "crit-table" }, [
        el("thead", {}, [el("tr", {}, ["th_criterion", "th_val", "th_src", "th_conf", "th_res"].map(function (k) { return el("th", { text: t(k) }); }))]),
        el("tbody", {}, rows)
      ])]));
    }
    if (d.failed_criterion) body.appendChild(kv(t("lbl_failed_rule"), d.failed_criterion + (d.reason ? " (" + d.reason + ")" : "")));
    if (d.action) body.appendChild(kv("on_block:", d.action + (d.escalated_to ? " → " + d.escalated_to : "")));
    if (d.message) body.appendChild(kv(t("lbl_message"), d.message));
    if (g.digest) body.appendChild(kv("gate_digest:", g.digest));
    const extra = el("div", {}, [el("span", { class: "hint", text: t("lbl_loading") })]);
    body.appendChild(extra);
    fetchGateInfo(gateBase(g.gate), function (info) {
      clear(extra);
      if (!info.ok) { extra.appendChild(naCard(info)); return; }
      if (info.chain && info.chain.length) extra.appendChild(kv(t("lbl_inherit"), info.chain.join(" → ")));
      extra.appendChild(el("div", { class: "kv-key", text: "allow_when:" }));
      extra.appendChild(codeBox(info.allow_when || {}));
      extra.appendChild(el("div", { class: "kv-key", text: "on_block:" }));
      extra.appendChild(codeBox(info.on_block || {}));
    });
  }

  function kv(k, v) {
    return el("div", { class: "kv" }, [el("strong", { text: k + " " }), el("span", { class: "mono", text: String(v) })]);
  }

  // ---- voice strip
  function paintVoiceStrip() {
    const v = S.voice;
    let evState = null;
    S.events.forEach(function (e) { if (e.type === "voice_state_changed") evState = e.data && e.data.to; });
    const sig = JSON.stringify([v, evState, S.lang]);
    region("voice", sig, liveRefs.voice, function (n) {
      if (!v || !v.ok || !v.enabled) {
        n.appendChild(el("div", { class: "hint" }, ["ℹ " + t("voice_not_enabled") + " ", el("code", { text: "neuroedge studio --mic" })]));
        return;
      }
      const state = String(v.state || evState || "IDLE").toUpperCase();
      const chips = el("div", { class: "fsm-chips" });
      ["IDLE", "LISTENING", "THINKING", "SPEAKING"].forEach(function (s, i) {
        if (i > 0) chips.appendChild(el("span", { class: "dim", text: "→" }));
        chips.appendChild(el("span", { class: "fsm-chip" + (state === s ? " active" : ""), text: s }));
      });
      const c = v.counters || {};
      const mute = el("button", { type: "button", class: "btn-sm" + (v.muted ? "" : " active"), "aria-pressed": v.muted ? "true" : "false",
        text: (v.muted ? "🔇 " : "🎤 ") + t(v.muted ? "btn_unmute" : "btn_mute"), onclick: toggleMute });
      n.appendChild(el("div", { class: "voice-strip-top" }, [chips]));
      n.appendChild(el("div", { class: "voice-actions" }, [
        el("div", { class: "voice-btn-group" }, [
          v.running ? mute : null,
          el("span", { class: "counters-chip", text: t(v.half_duplex ? "audio_half_duplex" : "audio_full_duplex") })
        ]),
        el("span", { class: "counters-chip", text: fill(t("counters_voice"), { turns: c.turns || 0, barge: c.barge_in || 0, stt: c.stt_unavailable || 0, cancel: c.cancelled || 0 }) })
      ]));
    });
  }

  function toggleMute() {
    api("POST", "voice/mute", { muted: !(S.voice && S.voice.muted) }).then(function (j) {
      if (j.ok) { S.voice = j; if (liveRefs) paintVoiceStrip(); }
    });
  }

  let voiceTimer = null;
  function pollVoice() {
    if (S.view !== "live" || document.hidden) return;
    api("GET", "voice").then(function (j) {
      S.voice = j;
      if (S.view === "live" && liveRefs && liveRefs.root.isConnected) paintVoiceStrip();
    });
  }

  // ---------------------------------------------------------------- gates
  function loadGates() {
    api("GET", "gates").then(function (j) {
      S.gates = j;
      if (j.ok && j.gates.length && !j.gates.some(function (g) { return g.name === S.gateName; })) S.gateName = j.gates[0].name;
      renderView("gate");
    });
  }

  function renderGate() {
    const c = refs.views.gate;
    clear(c);
    const g = S.gates;
    if (!g) { c.appendChild(loadingCard()); return; }
    if (!g.ok) { c.appendChild(naCard(g)); return; }
    const lintBox = el("div", { class: "result-box", hidden: true });
    const lintBtn = runButton("btn_lint", "gate-lint", function (done) {
      api("POST", "lint").then(function (j) {
        done();
        clear(lintBox);
        lintBox.hidden = false;
        renderLint(lintBox, j);
      });
    });
    const rows = g.gates.map(function (x) {
      const sel = x.name === S.gateName;
      return el("tr", { class: sel ? "sel" : "" }, [
        el("td", {}, [el("button", { type: "button", class: "link-btn mono", "aria-pressed": sel ? "true" : "false",
          text: x.name + (x.version ? "@" + x.version : ""), onclick: function () { S.gateName = x.name; delete S.gateInfo[x.name]; renderGate(); } })]),
        el("td", { text: Array.isArray(x.levels) ? x.levels.join(" / ") : x.levels === undefined ? "—" : String(x.levels) }),
        el("td", {}, [el("code", { text: x.fail || "—" })]),
        el("td", {}, [chip(x.status === "OK" ? "allow" : "block", x.status || "?")]),
        el("td", { class: "mono dim", text: x.digest ? String(x.digest).slice(0, 19) + "…" : "—" })
      ]);
    });
    const registry = panel("title_gate_registry", g.lint ? g.lint.resolved + "/" + g.lint.total : null, lintBtn, el("div", {}, [
      lintBox,
      el("div", { class: "table-wrap" }, [el("table", { class: "data-table" }, [
        el("thead", {}, [el("tr", {}, ["nav_gate", "th_level", "th_fail", "th_status", "th_digest"].map(function (k) { return el("th", { text: t(k) }); }))]),
        el("tbody", {}, rows.length ? rows : [el("tr", {}, [el("td", { colspan: "5", class: "hint", text: t("lbl_no_gates") })])])
      ])])
    ]));
    const detail = el("section", { class: "panel" });
    const what = el("section", { class: "panel" });
    c.appendChild(el("div", { class: "grid-2col" }, [el("div", { class: "col" }, [registry, detail]), el("div", { class: "col" }, [what])]));
    if (!S.gateName) { detail.appendChild(el("div", { class: "hint", text: t("lbl_no_gates") })); return; }
    const info = S.gateInfo[S.gateName];
    if (!info) { detail.appendChild(loadingCard()); fetchGateInfo(S.gateName, function () { renderView("gate"); }); return; }
    renderGateDetail(detail, what, info);
  }

  function renderLint(box, j) {
    if (!j.ok) { box.appendChild(naCard(j)); return; }
    box.appendChild(el("div", {}, [chip(j.resolved === j.total ? "allow" : "block", j.resolved + "/" + j.total), " " + t("lbl_gates_resolved")]));
    (j.gates || []).forEach(function (x) {
      if (x && (x.status === "FAIL" || x.error)) box.appendChild(el("div", { class: "mono err", text: (x.name || "") + " — " + (x.error || x.status) }));
    });
  }

  function runButton(labelKey, key, fn) {
    const b = el("button", { type: "button", class: "btn-sm", text: t(labelKey) });
    b.addEventListener("click", function () {
      if (b.disabled) return;
      b.disabled = true;
      clear(b);
      add(b, [el("span", { class: "spinner", "aria-hidden": "true" }), " " + t("lbl_running")]);
      fn(function () { b.disabled = false; b.textContent = t(labelKey); });
    });
    return b;
  }

  function renderGateDetail(detail, what, info) {
    if (!info.ok) { detail.appendChild(naCard(info)); what.appendChild(naCard(info)); return; }
    const label = info.name + (info.version ? "@" + info.version : "");
    detail.appendChild(el("h2", {}, [el("span", { text: t("title_gate_spec") }), el("span", { class: "sub mono", text: label })]));
    if (info.chain && info.chain.length) detail.appendChild(kv(t("lbl_chain"), info.chain.join(" → ")));
    const spec = info.evaluate || {};
    const crit = Object.keys(spec).map(function (k) {
      const s = spec[k] || {};
      const opts = s.levels || s.options;
      return el("tr", {}, [
        el("td", { class: "mono", text: k }),
        el("td", {}, [el("code", { text: (s.type || "?") + (opts ? " [" + opts.join(", ") + "]" : "") })]),
        el("td", { text: s.instructions || "—" })
      ]);
    });
    detail.appendChild(el("div", { class: "table-wrap" }, [el("table", { class: "crit-table" }, [
      el("thead", {}, [el("tr", {}, ["th_criterion", "th_type", "th_desc"].map(function (k) { return el("th", { text: t(k) }); }))]),
      el("tbody", {}, crit)
    ])]));
    ["allow_when", "on_block", "budget"].forEach(function (k) {
      if (info[k] && Object.keys(info[k]).length) {
        detail.appendChild(el("div", { class: "kv-key", text: k + ":" }));
        detail.appendChild(codeBox(info[k]));
      }
    });
    if (info.explanation && Object.keys(info.explanation).length) {
      detail.appendChild(el("div", { class: "kv-key", text: t("lbl_explain") + ":" }));
      detail.appendChild(codeBox(info.explanation));
    }
    renderWhatIf(what, info, label);
  }

  function renderWhatIf(what, info, label) {
    what.appendChild(el("h2", {}, [el("span", { text: t("title_whatif") }), el("span", { class: "sub mono", text: label })]));
    what.appendChild(el("p", { class: "hint", text: t("desc_whatif") }));
    const out = el("div", { class: "whatif-out", role: "status" });
    const inputs = {};
    const form = el("div", { class: "whatif-form" });
    const spec = info.evaluate || {};
    Object.keys(spec).forEach(function (k) {
      const s = spec[k] || {};
      const opts = s.levels || s.options;
      let ctl, read;
      if (opts && opts.length) {
        ctl = el("select", { class: "ctrl-select", "aria-label": k }, opts.map(function (o) { return el("option", { value: o, text: o }); }));
        read = function () { return ctl.value; };
      } else if (s.type === "bool" || s.type === "boolean") {
        ctl = el("input", { type: "checkbox", checked: true, "aria-label": k });
        read = function () { return ctl.checked; };
      } else if (s.type === "number" || s.type === "int" || s.type === "float" || s.type === "integer") {
        ctl = el("input", { type: "number", class: "ctrl-input", value: "0", "aria-label": k });
        read = function () { return Number(ctl.value); };
      } else {
        ctl = el("input", { type: "text", class: "ctrl-input", "aria-label": k });
        read = function () { return ctl.value; };
      }
      const unset = el("input", { type: "checkbox", "aria-label": k + " " + t("lbl_unset") });
      inputs[k] = { read: read, unset: unset };
      const refresh = function () { ctl.disabled = unset.checked; runWhatIf(info.name, inputs, out); };
      ctl.addEventListener("change", refresh);
      ctl.addEventListener("input", refresh);
      unset.addEventListener("change", refresh);
      form.appendChild(el("div", { class: "whatif-row" }, [
        el("label", { class: "ctrl-label" }, [ctl, el("code", { text: k })]),
        el("label", { class: "ctrl-label dim" }, [unset, t("lbl_unset")])
      ]));
    });
    what.appendChild(form);
    what.appendChild(el("div", { class: "kv-key", text: t("lbl_preview_verdict") }));
    what.appendChild(out);
    runWhatIf(info.name, inputs, out);
  }

  function runWhatIf(name, inputs, out) {
    const facts = {};
    Object.keys(inputs).forEach(function (k) { if (!inputs[k].unset.checked) facts[k] = inputs[k].read(); });
    const seq = ++S.whatifSeq;
    api("POST", "gates/" + enc(name) + "/whatif", { facts: facts }).then(function (j) {
      if (seq !== S.whatifSeq) return;
      clear(out);
      if (!j.ok) { out.appendChild(naCard(j)); return; }
      out.appendChild(el("div", {}, [
        verdictChip(j.verdict),
        j.reason ? el("span", { class: "mono", text: " " + j.reason + (j.failed_criterion ? " (" + j.failed_criterion + ")" : "") }) : null
      ]));
      if (j.action) out.appendChild(kv("on_block:", j.action));
      if (j.evaluations) out.appendChild(codeBox(j.evaluations));
    });
  }

  // ---------------------------------------------------------------- traces
  let blobUrl = null;

  function loadTraces() {
    api("GET", "traces").then(function (j) {
      S.traces = j;
      if (j.ok && !j.traces.some(function (x) { return x.name === S.traceName && x.valid !== false; })) {
        const first = j.traces.filter(function (x) { return x.valid !== false; })[0];
        S.traceName = first ? first.name : null;
        S.trace = null;
      }
      if (S.traceName && !S.trace) loadTrace(S.traceName);
      renderView("traces");
    });
  }

  function loadTrace(name) {
    S.trace = null;
    S.traceNote = null;
    api("GET", "traces/" + enc(name)).then(function (j) {
      if (S.traceName !== name) return;
      S.trace = j;
      renderView("traces");
    });
    renderView("traces");
  }

  function renderTraces() {
    const c = refs.views.traces;
    clear(c);
    const tr = S.traces;
    if (!tr) { c.appendChild(loadingCard()); return; }
    if (!tr.ok) { c.appendChild(naCard(tr)); return; }
    const save = runButton("btn_record", "record", function (done) {
      api("POST", "record").then(function (j) {
        done();
        S.traceNote = j.ok ? { ok: true, text: t("lbl_saved") + " " + j.name + " (" + j.events + ")" } : { ok: false, res: j };
        if (j.ok) S.traceName = j.name;
        S.trace = null;
        loadTraces();
      });
    });
    const rows = tr.traces.map(function (x) {
      const sel = x.name === S.traceName;
      const bad = x.valid === false;
      return el("tr", { class: sel ? "sel" : "" }, [
        el("td", {}, [bad ? el("span", { class: "mono", text: x.name }) : el("button", { type: "button", class: "link-btn mono", "aria-pressed": sel ? "true" : "false", text: x.name,
          onclick: function () { S.traceName = x.name; loadTrace(x.name); } })]),
        el("td", { text: bad || x.events === null || x.events === undefined ? "—" : String(x.events) }),
        el("td", { text: [x.target, x.board].filter(Boolean).join(" · ") || "—" }),
        el("td", {}, [bad ? el("span", { class: "st block", title: x.error || "", text: t("chip_invalid") + (x.error ? " · " + String(x.error).slice(0, 80) : "") })
          : chip(x.anonymized === false ? "warn" : "allow", x.anonymized === false ? "raw" : "sha256")]),
        el("td", { class: "mono", text: x.recorded_at || "—" })
      ]);
    });
    const list = panel("title_traces_list", null, save, el("div", {}, [
      el("div", { class: "notice", text: "🔒 " + t("privacy_note") }),
      S.traceNote ? (S.traceNote.ok ? el("div", { class: "result-box", text: S.traceNote.text }) : naCard(S.traceNote.res)) : null,
      el("div", { class: "table-wrap" }, [el("table", { class: "data-table" }, [
        el("thead", {}, [el("tr", {}, ["th_session", "th_events_count", "th_target", "th_anonymized", "th_recorded_at"].map(function (k) { return el("th", { text: t(k) }); }))]),
        el("tbody", {}, rows.length ? rows : [el("tr", {}, [el("td", { colspan: "5", class: "hint", text: t("lbl_no_traces") })])])
      ])])
    ]));
    c.appendChild(list);
    if (S.traceName) {
      const box = el("section", { class: "panel" });
      c.appendChild(box);
      renderTimeline(box);
    }
  }

  function renderTimeline(box) {
    const j = S.trace;
    const replayOut = el("div", { class: "whatif-out", role: "status" });
    const replay = runButton("btn_replay", "replay", function (done) {
      api("POST", "traces/" + enc(S.traceName) + "/replay").then(function (r) {
        done();
        clear(replayOut);
        if (!r.ok) { replayOut.appendChild(naCard(r)); return; }
        replayOut.appendChild(el("div", {}, [chip(r.match ? "allow" : "block", r.match ? "✓ match" : "✗ mismatch"),
          " " + (r.verdicts ? r.verdicts.length + " " + t("th_verdict") : "") + (r.detail ? " — " + r.detail : "")]));
      });
    });
    const tools = el("span", { class: "row-actions" }, [replay]);
    if (j && j.events) {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      blobUrl = URL.createObjectURL(new Blob([JSON.stringify(j, null, 2)], { type: "application/json" }));
      tools.appendChild(el("a", { class: "btn-sm", href: blobUrl, download: S.traceName + ".json", text: "⬇ " + t("btn_json") }));
    }
    box.appendChild(el("h2", {}, [el("span", { text: t("title_timeline") }), el("span", { class: "sub mono", text: S.traceName }), tools]));
    box.appendChild(replayOut);
    if (!j) { box.appendChild(loadingCard()); return; }
    if (!j.events) { box.appendChild(naCard(j)); return; }

    const evs = j.events;
    let maxMs = 1;
    evs.forEach(function (e) { if (e.offset_ms > maxMs) maxMs = e.offset_ms; });
    const pct = function (ms) { return Math.max(0, Math.min(100, (ms / maxMs) * 100)); };
    const lane = function (name, track, tail) {
      return el("div", { class: "timeline-lane" }, [el("span", { class: "mono lane-name", text: name }), track, el("span", { class: "dim lane-tail", text: tail })]);
    };

    const gateHits = [];
    evs.forEach(function (e) {
      if (e.type !== "gate_evaluation_result") return;
      const v = (e.data && e.data.verdict) || "?";
      const left = pct(e.offset_ms);
      gateHits.push(el("div", { class: "timeline-hit " + (v === "ALLOW" ? "allow" : "block") + (left > 70 ? " flip" : ""), style: left > 70 ? "right:" + (100 - left) + "%" : "left:" + left + "%", title: v + " @ " + e.offset_ms + " ms" }, [
        el("span", { class: "hit-label", text: v })
      ]));
    });
    box.appendChild(lane(t("lbl_gate_lane"), el("div", { class: "timeline-track" }, gateHits), String(gateHits.length)));

    const pins = [];
    evs.forEach(function (e) { if (e.type === "actuator_command" && e.data && pins.indexOf(e.data.pin) < 0) pins.push(e.data.pin); });
    pins.forEach(function (pin) {
      const cmds = evs.filter(function (e) { return e.type === "actuator_command" && e.data.pin === pin; });
      const bars = cmds.map(function (e, i) {
        const op = e.data.operation;
        let end = e.offset_ms;
        if (op === "pulse") end = e.offset_ms + (e.data.duration_ms || 0);
        else if (op === "on") end = i + 1 < cmds.length ? cmds[i + 1].offset_ms : Infinity;
        const left = pct(e.offset_ms);
        const endP = pct(Math.min(end, maxMs));
        const width = Math.max(2, endP - left);
        return el("div", { class: "timeline-hit pulse" + (left > 70 ? " flip" : ""), style: (left > 70 ? "right:" + (100 - endP) + "%" : "left:" + left + "%") + ";width:" + width + "%", title: pin + " " + op + " @ " + e.offset_ms + " ms" }, [
          el("span", { class: "hit-label", text: op.toUpperCase() })
        ]);
      });
      box.appendChild(lane(pin, el("div", { class: "timeline-track" }, bars), cmds.length ? cmds[cmds.length - 1].data.operation : ""));
    });

    const axis = el("div", { class: "timeline-axis" });
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) { axis.appendChild(el("span", { class: "mono", text: Math.round(maxMs * f) + " ms" })); });
    box.appendChild(axis);
  }

  // ---------------------------------------------------------------- verify
  function renderVerify() {
    const c = refs.views.verify;
    clear(c);
    const V = S.verify;
    const out = { lint: el("div"), test: el("div"), verify: el("div") };
    const btn = function (key, labelKey, path) {
      return runButton(labelKey, key, function (done) {
        api("POST", path).then(function (j) { done(); V[key] = j; renderVerifyResults(out, V); });
      });
    };
    c.appendChild(el("section", { class: "panel" }, [
      el("h2", {}, [el("span", { text: t("title_matrix") }), el("span", { class: "row-actions" }, [btn("lint", "btn_lint", "lint"), btn("test", "btn_test", "test"), btn("verify", "btn_verify", "verify")])]),
      out.lint, out.test, out.verify
    ]));
    renderVerifyResults(out, V);
    const notYet = el("ul", { class: "plain-list" }, ["ny_board", "ny_secure_boot", "ny_wifi", "ny_timing"].map(function (k) { return el("li", { text: t(k) }); }));
    c.appendChild(panel("title_not_yet", "CHANGELOG §3.7", null, notYet));
  }

  function cell(v) {
    if (v === true) return chip("allow", "✓");
    if (v === false) return chip("block", "✗");
    if (v && typeof v === "object") return el("span", { class: "st accent", text: (v.source === "ci" ? "CI" : String(v.source || "")) + (v.job ? " · " + v.job : "") });
    return el("span", { text: v === undefined || v === null ? "—" : String(v) });
  }

  function renderVerifyResults(out, V) {
    clear(out.lint); clear(out.test); clear(out.verify);
    if (V.lint) { const b = el("div", { class: "result-box" }); renderLint(b, V.lint); out.lint.appendChild(b); }
    if (V.test) {
      const b = el("div", { class: "result-box" });
      if (!V.test.ok) b.appendChild(naCard(V.test));
      else {
        b.appendChild(el("div", {}, [chip(V.test.failed ? "block" : "allow", "Passed: " + V.test.passed + " · Failed: " + V.test.failed)]));
        if (V.test.output_tail) b.appendChild(codeBox(V.test.output_tail));
      }
      out.test.appendChild(b);
    }
    const vr = V.verify;
    if (!vr) { out.verify.appendChild(el("div", { class: "hint", text: t("lbl_verify_hint") })); return; }
    if (!vr.ok) { out.verify.appendChild(naCard(vr)); return; }
    const rows = (vr.matrix || []).map(function (r) {
      return el("tr", {}, [el("td", {}, [el("strong", { text: r.item })]), el("td", {}, [cell(r.sim)]), el("td", {}, [cell(r.linux)]), el("td", {}, [cell(r.esp32s3)])]);
    });
    out.verify.appendChild(el("div", { class: "table-wrap" }, [el("table", { class: "data-table" }, [
      el("thead", {}, [el("tr", {}, [el("th", { text: t("th_artifact") }), el("th", { text: "sim" }), el("th", { text: "linux" }), el("th", { text: "esp32s3" })])]),
      el("tbody", {}, rows)
    ])]));
    out.verify.appendChild(el("div", { class: "result-box" }, [
      el("div", {}, [chip(vr.passed ? "allow" : "block", vr.summary || (vr.passed ? "Passed" : "Failed"))]),
      vr.compared ? el("div", { class: "hint", text: "Compared: " + vr.compared }) : null
    ]));
  }

  // ---------------------------------------------------------------- device
  function loadDevice() {
    api("GET", "device").then(function (j) {
      S.device = j;
      renderView("device");
    });
  }

  function renderDevice() {
    const c = refs.views.device;
    clear(c);
    c.appendChild(el("div", { class: "banner", role: "note" }, [el("strong", { class: "warn-text", text: t("banner_qemu") })]));
    const d = S.device;
    if (!d) { c.appendChild(loadingCard()); return; }
    if (!d.ok) { c.appendChild(naCard(d)); return; }

    const buildOut = el("div", { class: "whatif-out", role: "status" });
    const build = runButton("btn_build", "build", function (done) {
      api("POST", "device/build").then(function (j) {
        done();
        clear(buildOut);
        if (!j.ok) { buildOut.appendChild(naCard(j)); return; }
        buildOut.appendChild(kv(t("lbl_built"), (j.dir || "") + " · " + (j.files ? (Array.isArray(j.files) ? j.files.length : j.files) : 0) + " " + t("lbl_files") + (j.checked ? " · " + j.checked : "")));
        loadDevice();
      });
    });
    const fw = d.firmware || {};
    const golden = d.golden || {};
    const fwPanel = panel("title_build_firmware", null, build, el("div", {}, [
      codeBox("neuroedge build --target esp32s3 --board esp32s3-box-3"),
      kv(t("lbl_firmware"), fw.built ? (t("lbl_built") + (fw.dir ? " · " + fw.dir : "")) : t("lbl_not_built")),
      fw.files ? kv(t("lbl_files"), Array.isArray(fw.files) ? fw.files.length : fw.files) : null,
      golden.checked ? kv(t("lbl_golden"), golden.checked) : null,
      buildOut
    ]));

    const q = d.qemu;
    const qBody = el("div", {});
    if (!q) qBody.appendChild(el("div", { class: "hint", text: t("lbl_no_qemu") }));
    else {
      if (q.selftest !== undefined) qBody.appendChild(kv("NE_SELFTEST", String(q.selftest)));
      if (q.trace_done !== undefined) qBody.appendChild(kv("NE_TRACE DONE", String(q.trace_done)));
      if (q.log) qBody.appendChild(codeBox(q.log));
    }
    qBody.appendChild(el("div", { class: "hint", text: t("qemu_note") }));
    c.appendChild(el("div", { class: "grid-2col" }, [fwPanel, panel("title_qemu_boot", "UART", null, qBody)]));

    // screen gallery
    const screens = d.screens || [];
    if (!S.screenLang) S.screenLang = S.lang;
    const grid = el("div", { class: "gallery-grid" });
    const langBtn = function (code) {
      return el("button", { type: "button", class: "btn-sm" + (S.screenLang === code ? " active" : ""), "aria-pressed": S.screenLang === code ? "true" : "false",
        text: code.toUpperCase(), onclick: function () { S.screenLang = code; renderView("device"); } });
    };
    screens.forEach(function (s) {
      const lang = s.langs && s.langs.indexOf(S.screenLang) >= 0 ? S.screenLang : (s.langs && s.langs[0]) || S.screenLang;
      const img = el("img", { src: "/api/device/golden/" + lang + "/" + enc(s.name) + ".png", alt: s.name, loading: "lazy" });
      const card = el("div", { class: "gallery-card" }, [img, el("div", { class: "card-title" }, [el("span", { text: s.name }), el("span", { class: "mono dim", text: lang })])]);
      img.addEventListener("error", function () { img.replaceWith(el("div", { class: "hint img-missing", text: t("lbl_img_missing") })); });
      grid.appendChild(card);
    });
    if (screens.length === 0) grid.appendChild(el("div", { class: "hint", text: t("lbl_no_screens") }));
    c.appendChild(panel("title_ui_gallery", golden.checked || null, el("span", { class: "row-actions" }, [langBtn("vi"), langBtn("en")]), grid));

    // OTA phases
    const ota = d.ota && d.ota.phases;
    const stepper = el("div", { class: "stepper" });
    if (!ota || ota.length === 0) stepper.appendChild(el("div", { class: "hint", text: t("lbl_no_ota") }));
    else ota.forEach(function (p) {
      stepper.appendChild(el("div", { class: "step-item " + (p.ok ? "valid" : "reject") }, [
        el("div", { class: "step-phase", text: p.phase }),
        el("div", {}, [chip(p.ok ? "allow" : "block", p.ok ? "✓" : "✗"), el("div", { class: "mono", text: (p.markers || []).join("\n") })])
      ]));
    });
    c.appendChild(panel("title_ota_stepper", "qemu_ota.sh", null, stepper));
    if (d.hint) c.appendChild(el("div", { class: "notice", text: String(d.hint) }));
  }

  // ---------------------------------------------------------------- MCP
  function loadMcp() {
    api("GET", "mcp").then(function (j) { S.mcp = j; renderView("mcp"); });
  }

  function renderMcp() {
    const c = refs.views.mcp;
    clear(c);
    const m = S.mcp;
    if (!m) { c.appendChild(loadingCard()); }
    else if (!m.ok) { c.appendChild(naCard(m)); }
    else {
      const tools = (m.tools || []).map(function (x) {
        return el("details", { class: "tool" }, [
          el("summary", {}, [el("code", { text: x.name }), " ", el("span", { class: "dim", text: x.description || "" })]),
          codeBox(x.input_schema || {})
        ]);
      });
      c.appendChild(el("div", { class: "grid-2col" }, [
        panel("title_mcp_tools", String((m.tools || []).length), null, el("div", {}, [el("p", { class: "hint", text: t("mcp_tools_desc") })].concat(tools.length ? tools : [el("div", { class: "hint", text: t("lbl_no_tools") })]))),
        el("div", { class: "col" }, [
          panel("title_desktop_cfg", null, null, el("div", {}, [codeBox(m.desktop_config || ""), el("p", { class: "hint", text: t("mcp_desktop_note") })])),
          panel("title_ext_mcp", t("note_data_not_cmd"), null, el("div", {}, (m.servers || []).length
            ? m.servers.map(function (s) { return kv(s.name, (s.tools || []).join(", ")); })
            : [el("div", { class: "hint", text: t("lbl_no_servers") })]))
        ])
      ]));
    }
    const feed = [];
    groupTurns(S.events).turns.forEach(function (tr) {
      tr.calls.filter(function (cl) { return cl.source === "mcp"; }).forEach(function (cl) {
        const g = tr.gates[0];
        feed.push(el("tr", {}, [
          el("td", { class: "mono", text: tr.offset + " ms" }),
          el("td", {}, [el("code", { text: cl.name })]),
          el("td", { class: "mono dim", text: short(cl.arguments, 100) }),
          el("td", {}, [g ? verdictChip(g.result.verdict) : el("span", { class: "dim", text: "—" })])
        ]));
      });
    });
    c.appendChild(panel("title_mcp_feed", "tool_call · source=mcp", null, el("div", { class: "table-wrap" }, [el("table", { class: "data-table" }, [
      el("thead", {}, [el("tr", {}, ["th_time", "th_func", "th_args", "th_verdict"].map(function (k) { return el("th", { text: t(k) }); }))]),
      el("tbody", {}, feed.length ? feed : [el("tr", {}, [el("td", { colspan: "4", class: "hint", text: t("lbl_no_mcp_calls") })])])
    ])])));
  }

  // ---------------------------------------------------------------- config
  function loadAgent() {
    api("GET", "agent").then(function (j) {
      S.agent = j;
      paintProviders();
      renderView("config");
    });
  }

  function renderConfig() {
    const c = refs.views.config;
    clear(c);
    const a = S.agent;
    if (!a) { c.appendChild(loadingCard()); return; }
    if (!a.ok) { c.appendChild(naCard(a)); return; }
    const req = Object.keys(a.requires || {}).map(function (k) {
      return el("tr", {}, [el("td", { class: "mono", text: k }), el("td", { class: "mono", text: short(a.requires[k], 120) })]);
    });
    const caps = Object.keys((a.board && a.board.capabilities) || {}).map(function (k) {
      return el("tr", {}, [el("td", { class: "mono", text: k }), el("td", { class: "mono", text: short(a.board.capabilities[k], 120) })]);
    });
    const table = function (head, rows) {
      return el("div", { class: "table-wrap" }, [el("table", { class: "data-table" }, [
        el("thead", {}, [el("tr", {}, head.map(function (k) { return el("th", { text: t(k) }); }))]), el("tbody", {}, rows)
      ])]);
    };
    const provs = (a.providers || []).map(function (p) {
      return el("tr", {}, [
        el("td", { text: p.label || p.role }),
        el("td", { class: "mono", text: p.role }),
        el("td", { class: "mono", text: p.key_env || "—" }),
        el("td", {}, [chip(p.key_present ? "allow" : "block", p.key_present ? t("val_key_present") : t("val_key_missing"))])
      ]);
    });
    c.appendChild(el("div", { class: "grid-2col" }, [
      el("div", { class: "col" }, [
        panel("title_agent_decl", a.label, null, el("div", {}, [
          kv("root", a.root || "—"),
          kv("targets", (a.targets || []).join(", ") || "—"),
          el("div", { class: "kv-key", text: t("sec_requires") }), table(["th_name", "th_params"], req),
          el("div", { class: "kv-key", text: t("sec_board_caps") + " " + ((a.board && a.board.id) || "") }), table(["th_name", "th_params"], caps)
        ])),
        panel("title_templates", null, null, el("ul", { class: "plain-list" }, (a.templates || []).map(function (x) { return el("li", { class: "mono", text: String(x) }); })))
      ]),
      panel("title_providers", null, null, el("div", {}, [table(["th_provider", "th_role", "th_key_env", "th_key"], provs), el("p", { class: "hint", text: t("note_api_keys") })]))
    ]));
  }

  // ---------------------------------------------------------------- live connection
  function connect() {
    const es = new EventSource("/events");
    es.onopen = function () { S.connected = true; S.everConnected = true; paintBadge(); if (liveRefs) { regions.ask = null; if (S.view === "live") paintLive(); } };
    es.onmessage = function (m) {
      let d;
      try { d = JSON.parse(m.data); } catch (e) { return; }
      S.events = d.events || [];
      S.nowMs = d.now_ms || 0;
      if (!S.connected) { S.connected = true; S.everConnected = true; paintBadge(); }
      if (S.view === "live") paintLive();
      else if (S.view === "mcp") renderMcp();
    };
    es.onerror = function () { S.connected = false; paintBadge(); if (S.view === "live" && liveRefs) { regions.ask = null; paintLive(); } };
  }

  buildApp();
  loadAgent();
  connect();
  pollVoice();
  voiceTimer = setInterval(pollVoice, 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) pollVoice(); });
  window.addEventListener("beforeunload", function () { clearInterval(voiceTimer); });
})();
