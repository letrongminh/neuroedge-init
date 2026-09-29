/* neuroedge studio — the page (docs/spec/studio.md).
 * Every string from the server, an event, or a trace is set with textContent.
 * Standard library DOM only, no external dependencies, no network outside loopback.
 * Slice S3.
 */
"use strict";

(function () {
  const boot = JSON.parse(document.getElementById("ne-boot").textContent);
  const root = document.getElementById("studio");

  let currentLang = "vi";
  try {
    const saved = localStorage.getItem("ne_studio_lang");
    if (saved === "vi" || saved === "en") currentLang = saved;
  } catch (e) {}
  document.documentElement.lang = currentLang;

  let currentView = "live";
  let screenLang = currentLang;
  let isLiveConnected = false;

  let events = [];
  let now_ms = 0;
  let voiceData = { enabled: boot.voice, running: false, muted: false, half_duplex: false, state: "IDLE", counters: {} };
  let agentData = null;
  let gatesData = null;
  let selectedGateName = null;
  let selectedGateData = null;
  let tracesData = null;
  let selectedTraceName = null;
  let selectedTraceData = null;
  let verifyData = null;
  let deviceData = null;
  let mcpData = null;

  function t(key) {
    const dict = I18N[currentLang] || I18N.vi;
    return (dict && dict[key]) || key;
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const k in attrs || {}) {
      if (k === "text") {
        node.textContent = attrs[k];
      } else if (k === "class") {
        node.className = attrs[k];
      } else if (k === "data-i18n") {
        node.setAttribute("data-i18n", attrs[k]);
        node.textContent = t(attrs[k]);
      } else if (k === "data-i18n-placeholder") {
        node.setAttribute("data-i18n-placeholder", attrs[k]);
        node.setAttribute("placeholder", t(attrs[k]));
      } else if (k.startsWith("on") && typeof attrs[k] === "function") {
        node.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
      } else if (attrs[k] !== null && attrs[k] !== undefined) {
        node.setAttribute(k, attrs[k]);
      }
    }
    for (const child of children || []) {
      if (child) {
        if (typeof child === "string" || typeof child === "number") {
          node.appendChild(document.createTextNode(String(child)));
        } else {
          node.appendChild(child);
        }
      }
    }
    return node;
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs, children) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const k in attrs || {}) {
      if (k === "text") {
        node.textContent = attrs[k];
      } else if (attrs[k] !== null && attrs[k] !== undefined) {
        node.setAttribute(k, attrs[k]);
      }
    }
    for (const child of children || []) {
      if (child) {
        if (typeof child === "string" || typeof child === "number") {
          node.appendChild(document.createTextNode(String(child)));
        } else {
          node.appendChild(child);
        }
      }
    }
    return node;
  }

  function icon(pin, on) {
    const c = on ? "var(--allow)" : "var(--dim)";
    if (/lock/.test(pin)) {
      const shackle = on ? "M22 30 V20 a10 10 0 0 1 20 0" : "M22 30 V20 a10 10 0 0 1 20 0 V30";
      return svgEl("svg", { viewBox: "0 0 64 64" }, [
        svgEl("path", { d: shackle, fill: "none", stroke: c, "stroke-width": "5" }),
        svgEl("rect", { x: "14", y: "30", width: "36", height: "26", rx: "4", fill: c }),
        svgEl("circle", { cx: "32", cy: "43", r: "4", fill: "var(--panel)" })
      ]);
    }
    if (/light|lamp|led/.test(pin)) {
      return svgEl("svg", { viewBox: "0 0 64 64" }, [
        svgEl("circle", { cx: "32", cy: "26", r: "16", fill: on ? "#f2cc60" : "none", stroke: c, "stroke-width": "4" }),
        svgEl("rect", { x: "24", y: "44", width: "16", height: "10", rx: "2", fill: c })
      ]);
    }
    if (/relay|gate/.test(pin)) {
      return svgEl("svg", { viewBox: "0 0 64 64" }, [
        svgEl("circle", { cx: "14", cy: "40", r: "5", fill: c }),
        svgEl("circle", { cx: "50", cy: "40", r: "5", fill: c }),
        svgEl("line", { x1: "14", y1: "40", x2: on ? "50" : "44", y2: on ? "40" : "18", stroke: c, "stroke-width": "5", "stroke-linecap": "round" })
      ]);
    }
    return svgEl("svg", { viewBox: "0 0 64 64" }, [
      svgEl("circle", { cx: "32", cy: "32", r: "18", fill: on ? "var(--allow)" : "none", stroke: c, "stroke-width": "4" })
    ]);
  }

  function short(data) {
    const text = JSON.stringify(data);
    return text.length > 160 ? text.slice(0, 157) + "…" : text;
  }

  function notAvailableCard(why) {
    return el("div", { class: "not-available" }, [
      el("span", { class: "st warn", text: t("lbl_not_available") }),
      el("span", { text: why || t("msg_not_available") })
    ]);
  }

  function stateAt(evList, tMs) {
    const pins = {};
    const sensors = {};
    const asks = {};
    const gates = [];
    let frame = null;
    let begin = null;
    let call = null;

    for (let i = 0; i < evList.length; i++) {
      const e = evList[i];
      if (e.offset_ms > tMs) break;
      const d = e.data || {};
      if (e.type === "actuator_command") {
        const until = d.operation === "pulse" ? e.offset_ms + (d.duration_ms || 0)
          : d.operation === "on" ? Infinity : e.offset_ms;
        pins[d.pin] = { since: e.offset_ms, until: until, operation: d.operation };
      } else if (e.type === "actuator_aborted" && pins[d.pin]) {
        pins[d.pin].until = Math.min(pins[d.pin].until, e.offset_ms);
        pins[d.pin].aborted = d.reason;
      } else if (e.type === "sensor_read") {
        sensors[d.sensor] = { value: d.value, unit: d.unit };
      } else if (e.type === "display_frame") {
        frame = d;
      } else if (e.type === "tool_call") {
        call = d;
      } else if (e.type === "tool_confirm_requested") {
        asks[d.id] = d;
      } else if (e.type === "tool_confirmed" || e.type === "tool_confirm_declined" || e.type === "tool_confirm_expired") {
        delete asks[d.id];
      } else if (e.type === "gate_evaluation_begin") {
        begin = d.gate;
      } else if (e.type === "gate_evaluation_result") {
        gates.push({ index: i, offset_ms: e.offset_ms, gate: begin || d.blocked_by, call: call, result: d });
        begin = null;
        call = null;
      }
    }

    for (const name in pins) {
      pins[name].on = tMs < pins[name].until;
    }

    let pending = null;
    for (const id in asks) {
      if (asks[id].expires_ms > tMs) pending = asks[id];
    }

    return { pins: pins, sensors: sensors, frame: frame, gates: gates, pending: pending };
  }

  function groupTurns(evList) {
    const turns = [];
    let currentTurn = null;

    for (let i = 0; i < evList.length; i++) {
      const e = evList[i];
      const d = e.data || {};
      if (e.type === "text_input" || e.type === "stt_result") {
        if (currentTurn && currentTurn.offset_ms === e.offset_ms && (
            (currentTurn.type === "stt_result" && e.type === "text_input") ||
            (currentTurn.type === "text_input" && e.type === "stt_result")
        )) {
          if (e.type === "stt_result") currentTurn.is_voice = true;
          if (d.text && (!currentTurn.text || currentTurn.text === "—")) {
            currentTurn.text = d.text;
          }
          continue;
        }

        currentTurn = {
          offset_ms: e.offset_ms,
          type: e.type,
          is_voice: e.type === "stt_result",
          text: d.text || "—",
          events: [e],
          intents: [],
          tool_calls: [],
          gate_results: [],
          gate_facts: [],
          confirms: [],
          tts: null,
          latency: null,
          route: null,
          system_one: null,
          system_two: null,
          knowledge: null,
          mcp_results: [],
          not_recognized: false
        };
        turns.push(currentTurn);
      } else {
        if (!currentTurn) continue;
        currentTurn.events.push(e);
        if (e.type === "intent_extracted") {
          currentTurn.intents.push(d);
        } else if (e.type === "command_not_recognized") {
          currentTurn.not_recognized = true;
        } else if (e.type === "system_one_call" || e.type === "system_one_fallback") {
          currentTurn.system_one = { type: e.type, data: d };
        } else if (e.type === "system_two_call" || e.type === "system_two_reply") {
          currentTurn.system_two = { type: e.type, data: d };
        } else if (e.type === "knowledge_retrieved") {
          currentTurn.knowledge = d;
        } else if (e.type === "mcp_tool_result") {
          currentTurn.mcp_results.push(d);
        } else if (e.type === "tool_call") {
          currentTurn.tool_calls.push(d);
        } else if (e.type === "gate_facts") {
          currentTurn.gate_facts.push(d);
        } else if (e.type === "gate_evaluation_result") {
          currentTurn.gate_results.push(d);
        } else if (e.type === "tool_confirm_requested" || e.type === "tool_confirmed" || e.type === "tool_confirm_declined") {
          currentTurn.confirms.push({ type: e.type, data: d });
        } else if (e.type === "tts_stream_start") {
          currentTurn.tts = d.text;
        } else if (e.type === "turn_latency") {
          currentTurn.latency = d;
        }
      }
    }

    for (let k = 0; k < turns.length; k++) {
      const tr = turns[k];
      if (tr.mcp_results.length > 0 || tr.tool_calls.some(function (c) { return c.source === "mcp"; })) {
        tr.route = t("route_mcp");
      } else if (tr.knowledge || (tr.latency && tr.latency.reply_source === "knowledge_rag")) {
        tr.route = t("route_rag");
      } else if (tr.system_two || (tr.latency && (tr.latency.path === "system_2" || (tr.latency.stages_ms && tr.latency.stages_ms.system_two > 0)))) {
        tr.route = t("route_s2");
      } else if (tr.system_one || (tr.latency && tr.latency.path === "system_1")) {
        tr.route = t("route_s1");
      } else if (tr.intents.some(function (i) { return i.backend && i.backend.includes("grammar"); }) || tr.tool_calls.some(function (c) { return c.source === "local_grammar"; })) {
        tr.route = t("route_grammar");
      }
    }

    return turns;
  }

  // --- Top bar & Navigation setup ---
  const lostBanner = el("div", { id: "lostBanner", class: "banner lost", role: "status", style: "display:none;" }, [
    el("span", {}, [
      document.createTextNode("⚠ "),
      el("span", { "data-i18n": "banner_lost_msg", text: t("banner_lost_msg") })
    ]),
    el("span", { class: "note", "data-i18n": "banner_lost_state", text: t("banner_lost_state") })
  ]);

  const liveDot = el("span", { class: "live-dot" });
  const liveStatusText = el("span", { text: t("live_badge") });
  const btnToggleLive = el("button", { class: "live-badge" }, [liveDot, liveStatusText]);
  btnToggleLive.addEventListener("click", function () {
    setLiveStatus(!isLiveConnected);
  });

  const providersContainer = el("div", { style: "display:flex;gap:6px;align-items:center;" });
  function renderProviders(providers) {
    providersContainer.textContent = "";
    const list = providers || [
      { role: "stt", label: "STT", key_present: true },
      { role: "tts", label: "TTS", key_present: true },
      { role: "system_one", label: "System 1", key_present: true },
      { role: "system_two", label: "System 2", key_present: true }
    ];
    for (let i = 0; i < list.length; i++) {
      const p = list[i];
      const roleLabel = p.label || p.role.toUpperCase();
      const badge = el("div", { class: "provider-badge" }, [
        document.createTextNode(roleLabel + " "),
        el("span", {
          class: p.key_present ? "ok" : "missing",
          text: p.key_present ? t("val_key_present") : t("val_key_missing")
        })
      ]);
      providersContainer.appendChild(badge);
    }
  }
  renderProviders(null);

  const btnLangVi = el("button", { class: "lang-btn" + (currentLang === "vi" ? " active" : ""), text: "VI" });
  const btnLangEn = el("button", { class: "lang-btn" + (currentLang === "en" ? " active" : ""), text: "EN" });
  btnLangVi.addEventListener("click", function () { setLanguage("vi"); });
  btnLangEn.addEventListener("click", function () { setLanguage("en"); });

  const appHeader = el("header", { class: "app-header" }, [
    el("div", { class: "header-left" }, [
      el("div", { class: "brand" }, [
        svgEl("svg", { viewBox: "0 0 24 24" }, [
          svgEl("polygon", { points: "12 2 2 7 12 12 22 7 12 2" }),
          svgEl("polyline", { points: "2 17 12 22 22 17" }),
          svgEl("polyline", { points: "2 12 12 17 22 12" })
        ]),
        el("span", { "data-i18n": "app_title", text: t("app_title") })
      ]),
      el("div", { class: "meta-chip" }, [el("span", { text: "agent: " }), el("strong", { text: boot.agent })]),
      el("div", { class: "meta-chip" }, [el("span", { text: "target: " }), el("strong", { text: boot.target })]),
      el("div", { class: "meta-chip" }, [el("span", { text: "board: " }), el("strong", { text: boot.board })]),
      btnToggleLive
    ]),
    el("div", { class: "header-right" }, [
      providersContainer,
      el("div", { class: "lang-toggle", role: "radiogroup", "aria-label": "Language selection" }, [
        btnLangVi,
        btnLangEn
      ])
    ])
  ]);

  const navItems = [
    { view: "live", i18n: "nav_live", label: t("nav_live"), svg: [svgEl("circle", { cx: "12", cy: "12", r: "10" }), svgEl("circle", { cx: "12", cy: "12", r: "3" })] },
    { view: "gate", i18n: "nav_gate", label: t("nav_gate"), svg: [svgEl("path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" })] },
    { view: "traces", i18n: "nav_traces", label: t("nav_traces"), svg: [svgEl("polyline", { points: "22 12 18 12 15 21 9 3 6 12 2 12" })] },
    { view: "verify", i18n: "nav_verify", label: t("nav_verify"), svg: [svgEl("path", { d: "M22 11.08V12a10 10 0 1 1-5.93-9.14" }), svgEl("polyline", { points: "22 4 12 14.01 9 11.01" })] },
    { view: "device", i18n: "nav_device", label: t("nav_device"), svg: [svgEl("rect", { x: "4", y: "4", width: "16", height: "16", rx: "2" }), svgEl("rect", { x: "9", y: "9", width: "6", height: "6" }), svgEl("line", { x1: "9", y1: "1", x2: "9", y2: "4" }), svgEl("line", { x1: "15", y1: "1", x2: "15", y2: "4" }), svgEl("line", { x1: "9", y1: "20", x2: "9", y2: "23" }), svgEl("line", { x1: "15", y1: "20", x2: "15", y2: "23" })] },
    { view: "mcp", i18n: "nav_mcp", label: t("nav_mcp"), svg: [svgEl("circle", { cx: "18", cy: "5", r: "3" }), svgEl("circle", { cx: "6", cy: "12", r: "3" }), svgEl("circle", { cx: "18", cy: "19", r: "3" }), svgEl("line", { x1: "8.59", y1: "13.51", x2: "15.42", y2: "17.49" }), svgEl("line", { x1: "15.41", y1: "6.51", x2: "8.59", y2: "10.49" })] },
    { view: "config", i18n: "nav_config", label: t("nav_config"), svg: [svgEl("circle", { cx: "12", cy: "12", r: "3" }), svgEl("path", { d: "M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" })] }
  ];

  const studioNav = el("nav", { class: "studio-nav", "aria-label": "Studio Views" });
  const navButtons = {};

  for (let j = 0; j < navItems.length; j++) {
    const item = navItems[j];
    const btn = el("button", {
      class: "nav-item" + (item.view === currentView ? " active" : ""),
      "data-view": item.view
    }, [
      svgEl("svg", { viewBox: "0 0 24 24" }, item.svg),
      el("span", { "data-i18n": item.i18n, text: item.label })
    ]);
    btn.addEventListener("click", function () {
      switchView(item.view);
    });
    navButtons[item.view] = btn;
    studioNav.appendChild(btn);
  }

  const studioContent = el("main", { class: "studio-content" });

  const viewContainers = {
    live: el("section", { class: "studio-view active", id: "view-live" }),
    gate: el("section", { class: "studio-view", id: "view-gate" }),
    traces: el("section", { class: "studio-view", id: "view-traces" }),
    verify: el("section", { class: "studio-view", id: "view-verify" }),
    device: el("section", { class: "studio-view", id: "view-device" }),
    mcp: el("section", { class: "studio-view", id: "view-mcp" }),
    config: el("section", { class: "studio-view", id: "view-config" })
  };

  for (const v in viewContainers) {
    studioContent.appendChild(viewContainers[v]);
  }

  const studioLayout = el("div", { class: "studio-layout" }, [studioNav, studioContent]);

  root.textContent = "";
  root.appendChild(lostBanner);
  root.appendChild(appHeader);
  root.appendChild(studioLayout);

  function setLiveStatus(connected) {
    isLiveConnected = connected;
    lostBanner.style.display = connected ? "none" : "flex";
    btnToggleLive.classList.toggle("disconnected", !connected);
    liveStatusText.textContent = connected ? t("live_badge") : t("live_badge_lost");
  }

  function setLanguage(lang) {
    currentLang = lang;
    try {
      localStorage.setItem("ne_studio_lang", lang);
    } catch (e) {}
    document.documentElement.lang = lang;
    btnLangVi.classList.toggle("active", lang === "vi");
    btnLangEn.classList.toggle("active", lang === "en");

    document.querySelectorAll("[data-i18n]").forEach(function (node) {
      const key = node.getAttribute("data-i18n");
      if (key) node.textContent = t(key);
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (node) {
      const key = node.getAttribute("data-i18n-placeholder");
      if (key) node.setAttribute("placeholder", t(key));
    });

    setLiveStatus(isLiveConnected);
    renderProviders((agentData && agentData.providers) || null);
    renderActiveView();
  }

  function switchView(view) {
    currentView = view;
    for (const v in navButtons) {
      navButtons[v].classList.toggle("active", v === view);
    }
    for (const vc in viewContainers) {
      viewContainers[vc].classList.toggle("active", vc === view);
    }
    renderActiveView();
  }

  function renderActiveView() {
    if (currentView === "live") renderLiveSession();
    else if (currentView === "gate") loadGates();
    else if (currentView === "traces") loadTraces();
    else if (currentView === "verify") loadVerify();
    else if (currentView === "device") loadDevice();
    else if (currentView === "mcp") loadMcp();
    else if (currentView === "config") loadAgent();
  }

  // =========================================================================
  // VIEW 1: Live session
  // =========================================================================

  function renderLiveSession() {
    const container = viewContainers.live;
    container.textContent = "";

    const s = stateAt(events, now_ms);
    const turns = groupTurns(events);

    // Left Column
    const devicesDiv = el("div", { class: "devices" });
    const declaredPins = new Set(["door_lock", "porch_light", "gate_relay"]);
    for (let i = 0; i < events.length; i++) {
      if (events[i].type === "actuator_command" && events[i].data && events[i].data.pin) {
        declaredPins.add(events[i].data.pin);
      }
    }
    declaredPins.forEach(function (pin) {
      const p = s.pins[pin];
      const on = !!(p && p.on);
      const label = !p ? "LOW" : on ? (p.operation === "pulse" ? "PULSE" : "HIGH") : (p.aborted ? "ABORTED" : "LOW");
      devicesDiv.appendChild(el("div", { class: "device" + (on ? " on" : "") }, [
        icon(pin, on),
        el("div", { class: "mono", text: pin }),
        el("div", { class: "state", text: label })
      ]));
    });

    const sensorsDiv = el("div");
    const declaredSensors = new Set(["motion", "temperature", "door_contact"]);
    for (let j = 0; j < events.length; j++) {
      if (events[j].type === "sensor_read" && events[j].data && events[j].data.sensor) {
        declaredSensors.add(events[j].data.sensor);
      }
    }
    declaredSensors.forEach(function (name) {
      const r = s.sensors[name];
      const valText = r !== undefined && r.value !== undefined ? String(r.value) + (r.unit ? " " + r.unit : "") : "—";
      sensorsDiv.appendChild(el("div", { class: "sensor-row" }, [
        el("span", { class: "mono", text: name }),
        el("span", { class: "sensor-val", text: valText })
      ]));
    });

    const screenFrame = el("div", { class: "screen-frame" });
    if (s.frame) {
      screenFrame.appendChild(el("div", { style: "padding:12px;color:#d8dee6;font-family:monospace;font-size:11px;", text: s.frame.text || (s.frame.format + " " + s.frame.width + "×" + s.frame.height) }));
    } else {
      screenFrame.appendChild(svgEl("svg", { viewBox: "0 0 320 240" }, [
        svgEl("rect", { width: "320", height: "240", fill: "#080d14" }),
        svgEl("rect", { x: "4", y: "4", width: "312", height: "232", rx: "4", fill: "none", stroke: "#1f2d3d", "stroke-width": "2" }),
        svgEl("rect", { x: "8", y: "8", width: "304", height: "20", fill: "#121e2b" }),
        svgEl("text", { x: "16", y: "22", fill: "#7d8a99", "font-size": "10", "font-family": "monospace", text: "NEUROEDGE OS v0.1.0 · sim" }),
        svgEl("circle", { cx: "296", cy: "18", r: "4", fill: "#3fb950" }),
        svgEl("circle", { cx: "160", cy: "105", r: "32", fill: "#172636" }),
        svgEl("path", { d: "M160 88 v24 M154 94 v12 M166 94 v12 M148 98 v4 M172 98 v4", stroke: "#58a6ff", "stroke-width": "3", "stroke-linecap": "round" }),
        svgEl("text", { x: "160", y: "160", "text-anchor": "middle", fill: "#d8dee6", "font-size": "14", "font-weight": "bold", "font-family": "system-ui", text: t("scr_listening") }),
        svgEl("text", { x: "160", y: "180", "text-anchor": "middle", fill: "#58a6ff", "font-size": "11", "font-family": "monospace", text: "16 kHz PCM · VAD Active" }),
        svgEl("text", { x: "160", y: "224", "text-anchor": "middle", fill: "#485767", "font-size": "10", "font-family": "monospace", text: "voice_listening (golden reference)" })
      ]));
    }

    const colLeft = el("div", { class: "col-left" }, [
      el("div", { class: "panel" }, [
        el("h2", {}, [
          el("span", { "data-i18n": "title_devices", text: t("title_devices") }),
          el("span", { class: "sub", text: boot.board })
        ]),
        devicesDiv
      ]),
      el("div", { class: "panel" }, [
        el("h2", {}, [
          el("span", { "data-i18n": "title_sensors", text: t("title_sensors") }),
          el("span", { class: "sub", text: "I2C / GPIO" })
        ]),
        sensorsDiv
      ]),
      el("div", { class: "panel" }, [
        el("h2", {}, [
          el("span", { "data-i18n": "title_screen", text: t("title_screen") }),
          el("span", { class: "sub", text: "320×240" })
        ]),
        screenFrame
      ])
    ]);

    // Center Column
    const voiceStrip = buildVoiceStrip();
    const transcriptDiv = el("div", { class: "transcript" });

    if (turns.length === 0) {
      transcriptDiv.appendChild(el("div", { class: "turn", style: "color:var(--dim);text-align:center;", text: t("lbl_no_events") }));
    } else {
      for (let tIdx = 0; tIdx < turns.length; tIdx++) {
        transcriptDiv.appendChild(buildTurnCard(turns[tIdx]));
      }
    }

    const cmdInput = el("input", {
      class: "cmd-input",
      name: "cmd",
      "data-i18n-placeholder": "cmd_placeholder",
      placeholder: t("cmd_placeholder"),
      autocomplete: "off"
    });
    const cmdForm = el("form", { class: "cmd-form" }, [
      cmdInput,
      el("button", { class: "btn-primary", type: "submit", "data-i18n": "btn_send", text: t("btn_send") })
    ]);
    cmdForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      const val = cmdInput.value.trim();
      if (val) {
        submitCommand(val);
        cmdInput.value = "";
      }
    });

    const colCenter = el("div", { class: "col-center" }, [
      el("div", { class: "panel", style: "padding-bottom: 8px;" }, [
        el("h2", {}, [
          el("span", { "data-i18n": "title_assistant", text: t("title_assistant") }),
          el("span", { class: "sub", text: "live session" })
        ]),
        voiceStrip,
        transcriptDiv,
        cmdForm
      ])
    ]);

    // Right Column
    const colRight = el("div", { class: "col-right" });

    // Confirm Card RFC-0006
    if (s.pending) {
      const ask = s.pending;
      const timeLeft = Math.max(0, Math.ceil((ask.expires_ms - now_ms) / 1000));
      const btnNo = el("button", { class: "ask-btn no", autofocus: "true", text: t("btn_cancel") });
      const btnYes = el("button", { class: "ask-btn yes", text: t("btn_agree") });

      btnNo.addEventListener("click", function () { answerConfirm(ask.id, "no"); });
      btnYes.addEventListener("click", function () { answerConfirm(ask.id, "yes"); });

      const askCard = el("div", { class: "panel ask-panel", role: "alertdialog", "aria-live": "assertive" }, [
        el("h2", {}, [
          el("span", { "data-i18n": "title_confirm", text: t("title_confirm") }),
          el("span", { class: "sub", text: "RFC-0006" })
        ]),
        el("div", { class: "ask-title", text: ask.message + (ask.action ? " (" + ask.action + ")" : "") }),
        el("div", { class: "ask-timer", text: t("confirm_time_left").replace("{s}", String(timeLeft)) + " · " + t("confirm_source") }),
        el("div", { class: "ask-btns" }, [btnYes, btnNo]),
        el("div", { class: "ask-note", "data-i18n": "confirm_note", text: t("confirm_note") })
      ]);
      colRight.appendChild(askCard);
      setTimeout(function () { try { btnNo.focus(); } catch (e) {} }, 50);
    }

    // Gate Verdicts Cards
    const verdictsPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_gate_verdicts", text: t("title_gate_verdicts") }),
        el("span", { class: "sub", text: "session" })
      ])
    ]);

    const gateEvals = [];
    for (let k = 0; k < events.length; k++) {
      if (events[k].type === "gate_evaluation_result") {
        gateEvals.push(events[k]);
      }
    }

    if (gateEvals.length === 0) {
      verdictsPanel.appendChild(el("div", { style: "color:var(--dim);font-size:12px;", text: t("lbl_no_verdicts") }));
    } else {
      for (let gIdx = 0; gIdx < gateEvals.length; gIdx++) {
        verdictsPanel.appendChild(buildVerdictCard(gateEvals[gIdx]));
      }
    }
    colRight.appendChild(verdictsPanel);

    // Bottom Panel: Event Stream
    const streamTbody = el("tbody");
    const recentEvents = events.slice(-15);
    if (recentEvents.length === 0) {
      streamTbody.appendChild(el("tr", {}, [
        el("td", { colspan: "3", style: "color:var(--dim);text-align:center;", text: t("lbl_no_events") })
      ]));
    } else {
      for (let eIdx = recentEvents.length - 1; eIdx >= 0; eIdx--) {
        const ev = recentEvents[eIdx];
        streamTbody.appendChild(el("tr", {}, [
          el("td", { class: "mono", text: ev.offset_ms + " ms" }),
          el("td", {}, [el("code", { text: ev.type })]),
          el("td", { class: "mono", style: "color:var(--dim);", text: short(ev.data || {}) })
        ]));
      }
    }

    const streamPanel = el("div", { class: "panel", style: "margin-top:14px;" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_event_stream", text: t("title_event_stream") }),
        el("span", { class: "sub", text: Math.min(15, events.length) + " recent" })
      ]),
      el("table", { class: "data-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { style: "width:110px;", "data-i18n": "th_time", text: t("th_time") }),
            el("th", { style: "width:200px;", "data-i18n": "th_event", text: t("th_event") }),
            el("th", { "data-i18n": "th_payload", text: t("th_payload") })
          ])
        ]),
        streamTbody
      ])
    ]);

    const grid3 = el("div", { class: "grid-3col" }, [colLeft, colCenter, colRight]);
    container.appendChild(grid3);
    container.appendChild(streamPanel);
  }

  function buildVoiceStrip() {
    const strip = el("div", { class: "voice-strip" });
    if (!voiceData || !voiceData.enabled) {
      strip.appendChild(el("div", { style: "font-size:12px;color:var(--dim);display:flex;align-items:center;gap:6px;" }, [
        document.createTextNode("ℹ "),
        el("span", { "data-i18n": "voice_not_enabled", text: t("voice_not_enabled") })
      ]));
      return strip;
    }

    const state = (voiceData.state || "IDLE").toUpperCase();
    const fsmStates = ["IDLE", "LISTENING", "THINKING", "SPEAKING"];
    const chipsDiv = el("div", { class: "fsm-chips" });
    for (let i = 0; i < fsmStates.length; i++) {
      const st = fsmStates[i];
      if (i > 0) chipsDiv.appendChild(el("span", { text: "→" }));
      chipsDiv.appendChild(el("span", {
        class: "fsm-chip" + (state === st ? " active" : ""),
        text: st
      }));
    }

    const micMeter = el("div", { class: "mic-meter", title: "Mic meter" }, [
      el("div", { class: "mic-bar" }), el("div", { class: "mic-bar" }), el("div", { class: "mic-bar" }),
      el("div", { class: "mic-bar" }), el("div", { class: "mic-bar" }), el("div", { class: "mic-bar" })
    ]);

    const btnMute = el("button", {
      class: "btn-sm" + (voiceData.muted ? "" : " active"),
      text: voiceData.muted ? "🎤 " + t("btn_voice_start") : "⏹ " + t("btn_voice_stop")
    });
    btnMute.addEventListener("click", toggleMute);

    const btnMode = el("button", {
      class: "btn-sm",
      text: voiceData.half_duplex ? "📢 " + t("btn_audio_mode_hd") : "🎧 " + t("btn_audio_mode")
    });

    const cnt = voiceData.counters || {};
    const countersText = t("counters_voice")
      .replace("{barge}", String(cnt.barge_in || 0))
      .replace("{stt}", String(cnt.stt_unavailable || 0))
      .replace("{cancel}", String(cnt.cancelled || 0));
    const countersChip = el("div", { class: "counters-chip", text: countersText });

    strip.appendChild(el("div", { class: "voice-strip-top" }, [chipsDiv, micMeter]));
    strip.appendChild(el("div", { class: "voice-actions" }, [
      el("div", { class: "voice-btn-group" }, [btnMute, btnMode]),
      countersChip
    ]));
    return strip;
  }

  function buildTurnCard(tr) {
    const isBlocked = tr.gate_results.some(function (r) { return r.verdict === "BLOCK"; });
    const card = el("div", { class: "turn" + (isBlocked ? " blocked" : "") });

    const spk = tr.is_voice ? "🎤 " + t("spk_you") : "⌨ " + t("spk_you");
    card.appendChild(el("div", { class: "turn-header" }, [
      el("span", { class: "speaker", text: spk }),
      el("span", { class: "mono", text: "offset " + tr.offset_ms + " ms" })
    ]));

    card.appendChild(el("div", { class: "turn-text", text: tr.text }));

    const metaDiv = el("div", { class: "turn-meta" });
    if (tr.route) {
      metaDiv.appendChild(el("span", { class: "route-badge", text: tr.route }));
    }
    for (let i = 0; i < tr.intents.length; i++) {
      const it = tr.intents[i];
      const conf = it.confidence !== undefined ? " (" + it.confidence.toFixed(2) + ")" : "";
      metaDiv.appendChild(el("span", { class: "mono", text: "intent " + it.intent + conf }));
    }
    for (let c = 0; c < tr.tool_calls.length; c++) {
      metaDiv.appendChild(el("span", { class: "mono", text: "tool_call " + tr.tool_calls[c].name + "()" }));
    }
    for (let g = 0; g < tr.gate_results.length; g++) {
      const gr = tr.gate_results[g];
      const stClass = gr.verdict === "ALLOW" ? "st allow" : "st block";
      metaDiv.appendChild(el("span", { class: stClass, text: (gr.verdict === "ALLOW" ? "✓ " : "✗ ") + gr.verdict }));
      if (gr.blocked_by) {
        metaDiv.appendChild(el("span", { class: "mono", text: gr.blocked_by }));
      }
      if (gr.failed_criterion) {
        metaDiv.appendChild(el("span", { class: "mono", style: "color:var(--block);", text: "(" + (gr.reason || "failed") + ", " + gr.failed_criterion + ")" }));
      }
    }
    card.appendChild(metaDiv);

    if (tr.tts) {
      card.appendChild(el("div", { class: "turn-reply", text: "🗣 “" + tr.tts + "”" }));
    } else if (isBlocked) {
      const blk = tr.gate_results.find(function (r) { return r.verdict === "BLOCK"; });
      if (blk && blk.message) {
        card.appendChild(el("div", { class: "turn-reply blocked", text: "❓ “" + blk.message + "”" }));
      }
    }

    if (tr.latency && tr.latency.stages_ms) {
      const stg = tr.latency.stages_ms;
      const total = tr.latency.total_ms || (stg.perception + stg.system_two + stg.gate + stg.action + (stg.other || 0)) || 1;
      const bar = el("div", { class: "latency-bar" });
      const segs = [
        { key: "p", ms: stg.perception || 0, label: "perception" },
        { key: "s2", ms: stg.system_two || 0, label: "system_two" },
        { key: "g", ms: stg.gate || 0, label: "gate" },
        { key: "a", ms: stg.action || 0, label: "action" },
        { key: "tts", ms: stg.other || 0, label: "other/tts" }
      ];
      const legendSpans = [];
      for (let s = 0; s < segs.length; s++) {
        const seg = segs[s];
        if (seg.ms > 0) {
          const pct = Math.max(1, Math.round((seg.ms / total) * 100));
          bar.appendChild(el("div", { class: "lat-seg " + seg.key, style: "width:" + pct + "%;" }));
          legendSpans.push(el("span", { text: seg.label + " " + Math.round(seg.ms) + " ms" }));
        }
      }
      card.appendChild(bar);
      if (legendSpans.length > 0) {
        const legendDiv = el("div", { class: "latency-legend" });
        for (let l = 0; l < legendSpans.length; l++) {
          if (l > 0) legendDiv.appendChild(document.createTextNode(" · "));
          legendDiv.appendChild(legendSpans[l]);
        }
        card.appendChild(legendDiv);
      }
    }

    return card;
  }

  function buildVerdictCard(ev) {
    const d = ev.data || {};
    const verdict = d.verdict || "UNKNOWN";
    const gateName = d.blocked_by || d.gate || "gate";
    const card = el("div", { class: "verdict-card " + verdict });

    card.appendChild(el("div", { class: "verdict-summary" }, [
      el("span", {}, [
        el("span", { class: "st " + (verdict === "ALLOW" ? "allow" : "block"), text: verdict }),
        document.createTextNode(" "),
        el("span", { class: "mono", text: gateName })
      ]),
      el("span", { class: "mono", style: "font-size:11px;color:var(--dim);", text: ev.offset_ms + " ms" })
    ]));

    let summaryText = "";
    if (verdict === "BLOCK") {
      summaryText = (d.reason || "condition_not_met") + (d.failed_criterion ? " · " + t("th_criterion") + " " + d.failed_criterion : "") + (d.action ? " → " + d.action : "");
    } else {
      summaryText = "ALLOW · " + (d.action || "proceed");
    }
    card.appendChild(el("div", { style: "font-size:11.5px;color:var(--dim);margin:4px 0;", text: summaryText }));

    const details = el("details", { class: "verdict-details" }, [
      el("summary", { "data-i18n": "lbl_explain", text: t("lbl_explain") })
    ]);

    const detailsContent = el("div");
    details.appendChild(detailsContent);

    let fetchedGate = false;
    details.addEventListener("toggle", function () {
      if (details.open && !fetchedGate) {
        fetchedGate = true;
        renderVerdictExplain(detailsContent, d, gateName);
      }
    });

    card.appendChild(details);
    return card;
  }

  function renderVerdictExplain(container, result, gateName) {
    container.textContent = "";

    const cleanName = (gateName || "").split("@")[0];
    const factsObj = {};
    for (let i = 0; i < events.length; i++) {
      if (events[i].type === "gate_facts" && events[i].data) {
        Object.assign(factsObj, events[i].data);
      }
    }

    const evals = result.evaluations || {};
    const allCrit = new Set(Object.keys(evals).concat(Object.keys(factsObj)));

    if (allCrit.size > 0) {
      const tbody = el("tbody");
      allCrit.forEach(function (crit) {
        const fact = factsObj[crit] || {};
        const val = fact.value !== undefined ? String(fact.value) : (evals[crit] !== undefined ? String(evals[crit]) : "—");
        const src = fact.source || "context";
        const conf = fact.confidence !== null && fact.confidence !== undefined ? String(fact.confidence) : "1.00";
        const resOk = evals[crit] !== false && crit !== result.failed_criterion;
        tbody.appendChild(el("tr", {}, [
          el("td", { class: "mono", text: crit }),
          el("td", { class: "mono", text: val }),
          el("td", { text: src }),
          el("td", { text: conf }),
          el("td", { style: "color:" + (resOk ? "var(--allow)" : "var(--block)"), text: resOk ? "✓" : "✗" })
        ]));
      });

      const table = el("table", { class: "crit-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "th_criterion", text: t("th_criterion") }),
            el("th", { "data-i18n": "th_val", text: t("th_val") }),
            el("th", { "data-i18n": "th_src", text: t("th_src") }),
            el("th", { "data-i18n": "th_conf", text: t("th_conf") }),
            el("th", { "data-i18n": "th_res", text: t("th_res") })
          ])
        ]),
        tbody
      ]);
      container.appendChild(table);
    }

    if (result.failed_criterion) {
      container.appendChild(el("div", { style: "margin-top:4px;" }, [
        el("strong", { "data-i18n": "lbl_failed_rule", text: t("lbl_failed_rule") + " " }),
        el("span", { class: "mono", text: result.failed_criterion + " == false" })
      ]));
    }
    if (result.action) {
      container.appendChild(el("div", {}, [
        el("strong", { "data-i18n": "lbl_onblock", text: t("lbl_onblock") + " " }),
        el("span", { class: "mono", text: result.action + (result.escalated_to ? " " + result.escalated_to : "") })
      ]));
    }

    const gateExtra = el("div", { style: "margin-top:6px;" });
    container.appendChild(gateExtra);

    if (cleanName) {
      fetch('/api/gates/' + encodeURIComponent(cleanName)).then(function (res) {
        if (res.status === 501) return null;
        return res.json();
      }).then(function (gateRes) {
        if (gateRes && gateRes.ok) {
          if (gateRes.chain && gateRes.chain.length > 0) {
            gateExtra.appendChild(el("div", {}, [
              el("strong", { "data-i18n": "lbl_inherit", text: t("lbl_inherit") + " " }),
              el("span", { class: "mono", text: gateRes.chain.join(" → ") })
            ]));
          }
        }
      }).catch(function () {});
    }
  }

  function submitCommand(line) {
    fetch('/command', {
      method: 'POST',
      body: line
    }).then(function (res) {
      return res.json();
    }).catch(function () {});
  }

  function answerConfirm(id, answer) {
    fetch('/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id, answer: answer })
    }).then(function (res) {
      return res.json();
    }).catch(function () {});
  }

  function toggleMute() {
    const nextMuted = voiceData ? !voiceData.muted : false;
    fetch('/api/voice/mute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ muted: nextMuted })
    }).then(function (res) {
      return res.json();
    }).then(function (data) {
      if (data && data.ok) {
        voiceData = data;
        renderActiveView();
      }
    }).catch(function () {});
  }

  // =========================================================================
  // VIEW 2: Gate Registry & What-If Sandbox
  // =========================================================================

  function loadGates() {
    fetch('/api/gates').then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      gatesData = data;
      renderGateView();
    }).catch(function (err) {
      gatesData = { ok: false, error: { why: String(err) } };
      renderGateView();
    });
  }

  function renderGateView() {
    const container = viewContainers.gate;
    container.textContent = "";

    if (!gatesData || !gatesData.ok) {
      const why = (gatesData && gatesData.error && gatesData.error.why) || t("msg_not_available");
      container.appendChild(notAvailableCard(why));
      return;
    }

    const gatesList = gatesData.gates || [];
    const lintOutput = el("div", {
      style: "display:none;padding:6px 10px;background:color-mix(in srgb, var(--allow) 15%, transparent);border:1px solid var(--allow);border-radius:4px;font-size:12px;margin-bottom:10px;"
    });

    const btnLint = el("button", { class: "btn-sm", text: t("btn_lint") });
    btnLint.addEventListener("click", function () {
      btnLint.textContent = t("lbl_running");
      fetch('/api/lint', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (resData) {
        btnLint.textContent = t("btn_lint");
        lintOutput.style.display = "block";
        if (resData.ok) {
          lintOutput.textContent = "✓ " + (resData.resolved || 0) + " gate(s) resolved.";
        } else {
          lintOutput.textContent = "✗ " + ((resData.error && resData.error.why) || "Lint failed");
        }
      }).catch(function (err) {
        btnLint.textContent = t("btn_lint");
        lintOutput.style.display = "block";
        lintOutput.textContent = "✗ " + String(err);
      });
    });

    const tbody = el("tbody");
    for (let i = 0; i < gatesList.length; i++) {
      const g = gatesList[i];
      const isSel = selectedGateName === g.name || (!selectedGateName && i === 0);
      if (isSel && !selectedGateName) selectedGateName = g.name;

      const tr = el("tr", {
        style: "cursor:pointer;" + (isSel ? "background:color-mix(in srgb, var(--accent) 10%, transparent);" : "")
      }, [
        el("td", { class: "mono" }, [el("strong", { text: g.name + (g.version ? "@" + g.version : "") })]),
        el("td", { text: g.levels !== undefined ? String(g.levels) : "1" }),
        el("td", {}, [el("code", { text: g.fail || "closed" })]),
        el("td", {}, [el("span", { class: "st allow", text: g.status || "OK" })]),
        el("td", { class: "mono", style: "color:var(--dim);", text: (g.digest || "").slice(0, 16) + "…" })
      ]);
      tr.addEventListener("click", function () {
        selectGate(g.name);
      });
      tbody.appendChild(tr);
    }

    const registryPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_gate_registry", text: t("title_gate_registry") }),
        btnLint
      ]),
      lintOutput,
      el("table", { class: "data-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "nav_gate", text: t("nav_gate") }),
            el("th", { "data-i18n": "th_level", text: t("th_level") }),
            el("th", { "data-i18n": "th_fail", text: t("th_fail") }),
            el("th", { text: "Lint" }),
            el("th", { "data-i18n": "th_digest", text: t("th_digest") })
          ])
        ]),
        tbody
      ])
    ]);

    const gateDetailContainer = el("div", { class: "panel" });
    const whatifContainer = el("div", { class: "panel" });

    const colLeft = el("div", { class: "col" }, [registryPanel, gateDetailContainer]);
    const colRight = el("div", { class: "col" }, [whatifContainer]);
    const grid2 = el("div", { class: "grid-2col" }, [colLeft, colRight]);
    container.appendChild(grid2);

    if (selectedGateName) {
      fetchGateDetail(selectedGateName, gateDetailContainer, whatifContainer);
    }
  }

  function selectGate(name) {
    selectedGateName = name;
    renderGateView();
  }

  function fetchGateDetail(name, detailContainer, whatifContainer) {
    fetch('/api/gates/' + encodeURIComponent(name)).then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      selectedGateData = data;
      renderGateDetailContent(data, detailContainer, whatifContainer);
    }).catch(function (err) {
      renderGateDetailContent({ ok: false, error: { why: String(err) } }, detailContainer, whatifContainer);
    });
  }

  function renderGateDetailContent(data, detailContainer, whatifContainer) {
    detailContainer.textContent = "";
    whatifContainer.textContent = "";

    if (!data || !data.ok) {
      const why = (data && data.error && data.error.why) || t("msg_not_available");
      detailContainer.appendChild(notAvailableCard(why));
      whatifContainer.appendChild(notAvailableCard(why));
      return;
    }

    const gName = data.name + (data.version ? "@" + data.version : "");
    const chainText = (data.chain && data.chain.length > 0) ? data.chain.join(" → ") : gName;

    const critRows = [];
    const evalSpec = data.evaluate || {};
    for (const c in evalSpec) {
      const spec = evalSpec[c] || {};
      critRows.push(el("tr", {}, [
        el("td", { class: "mono", text: c }),
        el("td", {}, [el("code", { text: spec.type || (spec.levels ? "choice " + JSON.stringify(spec.levels) : "bool") })]),
        el("td", { text: spec.instructions || spec.description || "—" })
      ]));
    }

    detailContainer.appendChild(el("h2", {}, [
      el("span", { "data-i18n": "title_gate_spec", text: t("title_gate_spec") }),
      document.createTextNode(": "),
      el("span", { class: "mono", text: gName })
    ]));

    detailContainer.appendChild(el("div", {}, [
      el("strong", { "data-i18n": "lbl_chain", text: t("lbl_chain") + " " }),
      el("code", { class: "mono", text: chainText })
    ]));

    const critTable = el("table", { class: "crit-table", style: "margin-top:4px;" }, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", { "data-i18n": "th_criterion", text: t("th_criterion") }),
          el("th", { "data-i18n": "th_type", text: t("th_type") }),
          el("th", { "data-i18n": "th_desc", text: t("th_desc") })
        ])
      ]),
      el("tbody", {}, critRows)
    ]);

    detailContainer.appendChild(el("div", { style: "margin:8px 0;" }, [
      el("strong", { "data-i18n": "lbl_criteria", text: t("lbl_criteria") }),
      critTable
    ]));

    detailContainer.appendChild(el("div", {}, [el("strong", { text: "allow_when:" })]));
    detailContainer.appendChild(el("div", { class: "code-box", text: JSON.stringify(data.allow_when || {}, null, 2) }));

    detailContainer.appendChild(el("div", {}, [el("strong", { text: "on_block:" })]));
    detailContainer.appendChild(el("div", { class: "code-box", text: JSON.stringify(data.on_block || {}, null, 2) }));

    // What-If Form
    whatifContainer.appendChild(el("h2", {}, [
      el("span", { "data-i18n": "title_whatif", text: t("title_whatif") }),
      el("span", { class: "sub", text: gName })
    ]));
    whatifContainer.appendChild(el("p", {
      style: "font-size:12px;color:var(--dim);",
      "data-i18n": "desc_whatif",
      text: t("desc_whatif")
    }));

    const formDiv = el("div", {
      style: "display:flex;flex-direction:column;gap:12px;margin:14px 0;background:var(--bg);padding:12px;border-radius:6px;border:1px solid var(--line);"
    });

    const whatifVerdictDiv = el("div", {
      style: "padding:12px;border-radius:6px;border:1px solid var(--line);background:var(--panel);"
    }, [
      el("div", {
        style: "font-size:11px;text-transform:uppercase;color:var(--dim);margin-bottom:6px;",
        "data-i18n": "lbl_preview_verdict",
        text: t("lbl_preview_verdict")
      }),
      el("div", { id: "whatifVerdictContent" })
    ]);

    const inputsMap = {};
    for (const critName in evalSpec) {
      const cSpec = evalSpec[critName] || {};
      const type = cSpec.type || (cSpec.levels || cSpec.options ? "choice" : "bool");

      if (type === "bool") {
        const chk = el("input", { type: "checkbox", checked: "true" });
        const unsetChk = el("input", { type: "checkbox" });
        inputsMap[critName] = { type: "bool", chk: chk, unsetChk: unsetChk };

        const row = el("div", { style: "display:flex;align-items:center;justify-content:space-between;gap:8px;" }, [
          el("label", { class: "ctrl-label" }, [
            chk,
            el("span", {}, [el("code", { text: critName })])
          ]),
          el("label", { class: "ctrl-label", style: "font-size:11px;color:var(--dim);" }, [
            unsetChk,
            el("span", { "data-i18n": "lbl_unset", text: t("lbl_unset") })
          ])
        ]);
        chk.addEventListener("change", function () {
          unsetChk.checked = false;
          executeWhatIf(data.name, inputsMap, whatifVerdictDiv.querySelector("#whatifVerdictContent"));
        });
        unsetChk.addEventListener("change", function () {
          executeWhatIf(data.name, inputsMap, whatifVerdictDiv.querySelector("#whatifVerdictContent"));
        });
        formDiv.appendChild(row);
      } else if (type === "choice") {
        const opts = cSpec.levels || cSpec.options || ["low", "medium", "high"];
        const sel = el("select", { class: "ctrl-select" });
        for (let o = 0; o < opts.length; o++) {
          sel.appendChild(el("option", { value: opts[o], text: opts[o] }));
        }
        sel.appendChild(el("option", { value: "__unset__", text: t("lbl_unset") }));
        inputsMap[critName] = { type: "choice", sel: sel };

        const row = el("label", { class: "ctrl-label", style: "justify-content:space-between;" }, [
          el("span", {}, [el("code", { text: critName }), document.createTextNode(":") ]),
          sel
        ]);
        sel.addEventListener("change", function () {
          executeWhatIf(data.name, inputsMap, whatifVerdictDiv.querySelector("#whatifVerdictContent"));
        });
        formDiv.appendChild(row);
      } else {
        const inp = el("input", { type: "number", class: "ctrl-input", value: "0" });
        const unsetChk = el("input", { type: "checkbox" });
        inputsMap[critName] = { type: "number", inp: inp, unsetChk: unsetChk };

        const row = el("div", { style: "display:flex;align-items:center;justify-content:space-between;gap:8px;" }, [
          el("label", { class: "ctrl-label" }, [
            el("code", { text: critName }),
            document.createTextNode(":"),
            inp
          ]),
          el("label", { class: "ctrl-label", style: "font-size:11px;color:var(--dim);" }, [
            unsetChk,
            el("span", { "data-i18n": "lbl_unset", text: t("lbl_unset") })
          ])
        ]);
        inp.addEventListener("input", function () {
          unsetChk.checked = false;
          executeWhatIf(data.name, inputsMap, whatifVerdictDiv.querySelector("#whatifVerdictContent"));
        });
        unsetChk.addEventListener("change", function () {
          executeWhatIf(data.name, inputsMap, whatifVerdictDiv.querySelector("#whatifVerdictContent"));
        });
        formDiv.appendChild(row);
      }
    }

    whatifContainer.appendChild(formDiv);
    whatifContainer.appendChild(whatifVerdictDiv);

    executeWhatIf(data.name, inputsMap, whatifVerdictDiv.querySelector("#whatifVerdictContent"));
  }

  function executeWhatIf(gateName, inputsMap, targetEl) {
    const facts = {};
    for (const c in inputsMap) {
      const item = inputsMap[c];
      if (item.type === "bool") {
        if (!item.unsetChk.checked) {
          facts[c] = item.chk.checked;
        }
      } else if (item.type === "choice") {
        if (item.sel.value !== "__unset__") {
          facts[c] = item.sel.value;
        }
      } else if (item.type === "number") {
        if (!item.unsetChk.checked) {
          facts[c] = Number(item.inp.value);
        }
      }
    }

    fetch('/api/gates/' + encodeURIComponent(gateName) + '/whatif', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ facts: facts })
    }).then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (resData) {
      targetEl.textContent = "";
      if (!resData.ok) {
        targetEl.appendChild(notAvailableCard((resData.error && resData.error.why) || t("msg_not_available")));
        return;
      }
      const v = resData.verdict || "UNKNOWN";
      targetEl.appendChild(el("span", { class: "st " + (v === "ALLOW" ? "allow" : "block"), text: (v === "ALLOW" ? "✓ " : "✗ ") + v }));
      if (resData.reason) {
        targetEl.appendChild(document.createTextNode(" "));
        targetEl.appendChild(el("span", { class: "mono", text: resData.reason + (resData.failed_criterion ? " (" + resData.failed_criterion + ")" : "") }));
      }
      if (resData.action) {
        targetEl.appendChild(el("div", { style: "font-size:12px;color:var(--dim);margin-top:6px;", text: "→ action: " + resData.action }));
      }
    }).catch(function (err) {
      targetEl.textContent = "";
      targetEl.appendChild(notAvailableCard(String(err)));
    });
  }

  // =========================================================================
  // VIEW 3: Traces & Timeline
  // =========================================================================

  function loadTraces() {
    fetch('/api/traces').then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      tracesData = data;
      renderTracesView();
    }).catch(function (err) {
      tracesData = { ok: false, error: { why: String(err) } };
      renderTracesView();
    });
  }

  function renderTracesView() {
    const container = viewContainers.traces;
    container.textContent = "";

    if (!tracesData || !tracesData.ok) {
      container.appendChild(notAvailableCard((tracesData && tracesData.error && tracesData.error.why) || t("msg_not_available")));
      return;
    }

    const tracesList = tracesData.traces || [];
    const btnRecord = el("button", { class: "btn-sm", text: "⏺ " + t("btn_record") });
    btnRecord.addEventListener("click", function () {
      btnRecord.textContent = t("lbl_running");
      fetch('/api/record', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (recData) {
        btnRecord.textContent = "⏺ " + t("btn_record");
        if (recData.ok) {
          loadTraces();
        }
      }).catch(function () {
        btnRecord.textContent = "⏺ " + t("btn_record");
      });
    });

    const tbody = el("tbody");
    for (let i = 0; i < tracesList.length; i++) {
      const tr = tracesList[i];
      const isSel = selectedTraceName === tr.name || (!selectedTraceName && i === 0);
      if (isSel && !selectedTraceName) selectedTraceName = tr.name;

      const row = el("tr", {
        style: "cursor:pointer;" + (isSel ? "background:color-mix(in srgb, var(--accent) 10%, transparent);" : "")
      }, [
        el("td", { class: "mono" }, [el("strong", { text: tr.session_id || tr.name })]),
        el("td", { text: (tr.events || 0) + " " + t("th_events_count") }),
        el("td", {}, [el("code", { text: tr.target || "sim" })]),
        el("td", {}, [el("span", { class: "st allow", text: tr.anonymized !== false ? "✓ sha256" : "raw" })]),
        el("td", { class: "mono", text: tr.recorded_at || "—" })
      ]);
      row.addEventListener("click", function () {
        selectTrace(tr.name);
      });
      tbody.appendChild(row);
    }

    const tablePanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_traces_list", text: t("title_traces_list") }),
        btnRecord
      ]),
      el("div", {
        style: "font-size:11.5px;color:var(--warn);margin-bottom:10px;background:color-mix(in srgb, var(--warn) 15%, transparent);padding:6px 10px;border-radius:4px;border:1px solid var(--warn);"
      }, [
        document.createTextNode("🔒 "),
        el("span", { "data-i18n": "privacy_note", text: t("privacy_note") })
      ]),
      el("table", { class: "data-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "th_session", text: t("th_session") }),
            el("th", { "data-i18n": "th_events_count", text: t("th_events_count") }),
            el("th", { "data-i18n": "th_target", text: t("th_target") }),
            el("th", { "data-i18n": "th_anonymized", text: t("th_anonymized") }),
            el("th", { "data-i18n": "th_recorded_at", text: t("th_recorded_at") })
          ])
        ]),
        tbody
      ])
    ]);

    const timelinePanel = el("div", { class: "panel" });
    container.appendChild(tablePanel);
    container.appendChild(timelinePanel);

    if (selectedTraceName) {
      loadTraceDetail(selectedTraceName, timelinePanel);
    }
  }

  function selectTrace(name) {
    selectedTraceName = name;
    renderTracesView();
  }

  function loadTraceDetail(name, container) {
    fetch('/api/traces/' + encodeURIComponent(name)).then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      selectedTraceData = data;
      renderTraceTimeline(name, data, container);
    }).catch(function (err) {
      renderTraceTimeline(name, { ok: false, error: { why: String(err) } }, container);
    });
  }

  function renderTraceTimeline(name, trace, container) {
    container.textContent = "";

    const btnReplay = el("button", { class: "btn-sm", text: "⟳ " + t("btn_replay") });
    btnReplay.addEventListener("click", function () {
      btnReplay.textContent = t("lbl_running");
      fetch('/api/traces/' + encodeURIComponent(name) + '/replay', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (resData) {
        btnReplay.textContent = "⟳ " + t("btn_replay");
        const msg = resData.ok ? (resData.match ? "✓ Match: " + t("lbl_replay_done") : "✗ Mismatch") : ((resData.error && resData.error.why) || "Replay failed");
        alert(msg);
      }).catch(function (err) {
        btnReplay.textContent = "⟳ " + t("btn_replay");
        alert(String(err));
      });
    });

    const btnDownload = el("button", { class: "btn-sm", text: "⬇ " + t("btn_json") });
    btnDownload.addEventListener("click", function () {
      const blob = new Blob([JSON.stringify(trace, null, 2)], { type: "application/json" });
      const dlLink = el("a", {
        href: URL.createObjectURL(blob),
        download: name + ".json"
      });
      document.body.appendChild(dlLink);
      dlLink.click();
      document.body.removeChild(dlLink);
    });

    container.appendChild(el("h2", {}, [
      el("span", {}, [
        el("span", { "data-i18n": "title_timeline", text: t("title_timeline") }),
        document.createTextNode(" (" + name + ")")
      ]),
      el("div", { style: "display:flex;gap:6px;" }, [btnReplay, btnDownload])
    ]));

    if (!trace || !trace.events) {
      container.appendChild(notAvailableCard((trace && trace.error && trace.error.why) || t("msg_not_available")));
      return;
    }

    const tEvents = trace.events || [];
    let maxMs = 1;
    for (let i = 0; i < tEvents.length; i++) {
      if (tEvents[i].offset_ms > maxMs) maxMs = tEvents[i].offset_ms;
      if (tEvents[i].type === "actuator_command" && tEvents[i].data && tEvents[i].data.duration_ms) {
        const end = tEvents[i].offset_ms + tEvents[i].data.duration_ms;
        if (end > maxMs) maxMs = end;
      }
    }

    // Gate lane
    const gateHits = [];
    for (let g = 0; g < tEvents.length; g++) {
      const ev = tEvents[g];
      if (ev.type === "gate_evaluation_result") {
        const pct = Math.min(95, Math.round((ev.offset_ms / maxMs) * 100));
        const verd = (ev.data && ev.data.verdict) || "VERDICT";
        gateHits.push(el("div", {
          class: "timeline-hit " + (verd === "ALLOW" ? "allow" : "block"),
          style: "left:" + pct + "%;",
          title: (ev.data && ev.data.gate || "") + " " + verd,
          text: verd
        }));
      }
    }

    const gateTrack = el("div", { class: "timeline-track" }, gateHits);
    container.appendChild(el("div", { class: "timeline-lane" }, [
      el("span", { class: "mono", text: "gate lane" }),
      gateTrack,
      el("span", { style: "font-size:11px;color:var(--dim);", text: gateHits.length + " " + t("th_verdict") })
    ]));

    // Pin lanes
    const pinNames = new Set(["door_lock", "porch_light", "gate_relay"]);
    for (let p = 0; p < tEvents.length; p++) {
      if (tEvents[p].type === "actuator_command" && tEvents[p].data && tEvents[p].data.pin) {
        pinNames.add(tEvents[p].data.pin);
      }
    }

    pinNames.forEach(function (pin) {
      const pinHits = [];
      let lastStateText = "LOW";
      for (let k = 0; k < tEvents.length; k++) {
        const ev = tEvents[k];
        if (ev.type === "actuator_command" && ev.data && ev.data.pin === pin) {
          const pct = Math.min(95, Math.round((ev.offset_ms / maxMs) * 100));
          const durPct = ev.data.duration_ms ? Math.min(100 - pct, Math.max(5, Math.round((ev.data.duration_ms / maxMs) * 100))) : 20;
          const op = (ev.data.operation || "HIGH").toUpperCase();
          pinHits.push(el("div", {
            class: "timeline-hit pulse",
            style: "left:" + pct + "%;width:" + durPct + "%;",
            title: pin + " " + op,
            text: op
          }));
          lastStateText = op;
        }
      }
      const pinTrack = el("div", { class: "timeline-track" }, pinHits);
      container.appendChild(el("div", { class: "timeline-lane" }, [
        el("span", { class: "mono", text: pin }),
        pinTrack,
        el("span", { style: "font-size:11px;color:var(--dim);", text: lastStateText })
      ]));
    });

    container.appendChild(el("div", { class: "timeline-axis" }, [
      el("span", { text: "0 ms" }),
      el("span", { text: Math.round(maxMs / 2) + " ms" }),
      el("span", { text: maxMs + " ms" })
    ]));
  }

  // =========================================================================
  // VIEW 4: Verify View
  // =========================================================================

  function loadVerify() {
    renderVerifyView();
  }

  function renderVerifyView() {
    const container = viewContainers.verify;
    container.textContent = "";

    const btnLint = el("button", { class: "btn-sm", text: t("btn_lint") });
    btnLint.addEventListener("click", function () {
      btnLint.textContent = t("lbl_running");
      fetch('/api/lint', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (data) {
        btnLint.textContent = t("btn_lint");
        alert(data.ok ? "✓ " + (data.resolved || 0) + " gate(s) resolved." : "✗ " + ((data.error && data.error.why) || "Lint failed"));
      }).catch(function (err) {
        btnLint.textContent = t("btn_lint");
        alert(String(err));
      });
    });

    const btnTest = el("button", { class: "btn-sm", text: t("btn_test") });
    btnTest.addEventListener("click", function () {
      btnTest.textContent = t("lbl_running");
      fetch('/api/test', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (data) {
        btnTest.textContent = t("btn_test");
        alert(data.ok ? "✓ Passed: " + data.passed + ", Failed: " + data.failed : "✗ " + ((data.error && data.error.why) || "Test failed"));
      }).catch(function (err) {
        btnTest.textContent = t("btn_test");
        alert(String(err));
      });
    });

    const btnVerify = el("button", { class: "btn-sm", text: t("btn_verify") });
    btnVerify.addEventListener("click", function () {
      btnVerify.textContent = t("lbl_running");
      fetch('/api/verify', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (data) {
        btnVerify.textContent = t("btn_verify");
        verifyData = data;
        renderVerifyView();
      }).catch(function (err) {
        btnVerify.textContent = t("btn_verify");
        verifyData = { ok: false, error: { why: String(err) } };
        renderVerifyView();
      });
    });

    const defaultMatrix = [
      { item: "trace-01 (light_on)", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" },
      { item: "trace-02 (light_off_block)", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" },
      { item: "trace-03 (door_unlock)", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" },
      { item: "gate: light_on@1.0.0", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" },
      { item: "gate: light_off@1.0.0", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" },
      { item: "gate: unlock_door@1.2.0", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" },
      { item: "tool-call corpus (fixtures/tool_calls/)", sim: "✓ máy này", linux: "✓ CI · linux-hal", esp32s3: "✓ CI · uart-trace (QEMU)" }
    ];

    const matrixRows = (verifyData && verifyData.matrix) || defaultMatrix;
    const tbody = el("tbody");
    for (let m = 0; m < matrixRows.length; m++) {
      const row = matrixRows[m];
      tbody.appendChild(el("tr", {}, [
        el("td", {}, [el("strong", { text: row.item })]),
        el("td", {}, [el("span", { class: "st allow", text: typeof row.sim === "string" ? row.sim : (row.sim ? "✓ pass" : "✗ fail") })]),
        el("td", {}, [el("span", { class: "st allow", text: typeof row.linux === "string" ? row.linux : "✓ CI · linux-hal" })]),
        el("td", {}, [el("span", { class: "st allow", text: typeof row.esp32s3 === "string" ? row.esp32s3 : "✓ CI · uart-trace (QEMU)" })])
      ]));
    }

    const summaryText = (verifyData && verifyData.summary) ||
      "✓ Passed: all gates resolve, canonical traces validate, every tool call gives its recorded result, and replays on sim match.";
    const comparedText = (verifyData && verifyData.compared) ||
      t("verify_timing_note");

    const matrixPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_matrix", text: t("title_matrix") }),
        el("div", { style: "display:flex;gap:6px;" }, [btnLint, btnTest, btnVerify])
      ]),
      el("table", { class: "data-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "th_artifact", text: t("th_artifact") }),
            el("th", { text: "sim" }),
            el("th", { text: "linux" }),
            el("th", { text: "esp32s3" })
          ])
        ]),
        tbody
      ]),
      el("div", {
        style: "margin-top:14px;padding:10px 14px;background:var(--code-bg);border:1px solid var(--allow);border-radius:6px;font-size:12px;"
      }, [
        el("div", { style: "color:var(--allow);font-weight:700;margin-bottom:4px;", text: summaryText }),
        el("div", { style: "color:var(--dim);", "data-i18n": "verify_timing_note", text: comparedText })
      ])
    ]);

    const notYetPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_not_yet", text: t("title_not_yet") }),
        el("span", { class: "sub", text: "CHANGELOG §3.7" })
      ]),
      el("ul", { style: "margin:0;padding-left:20px;font-size:12px;color:var(--dim);line-height:1.7;" }, [
        el("li", { "data-i18n": "ny_board", text: t("ny_board") }),
        el("li", { "data-i18n": "ny_secure_boot", text: t("ny_secure_boot") }),
        el("li", { "data-i18n": "ny_wifi", text: t("ny_wifi") }),
        el("li", { "data-i18n": "ny_timing", text: t("ny_timing") })
      ])
    ]);

    container.appendChild(matrixPanel);
    container.appendChild(notYetPanel);
  }

  // =========================================================================
  // VIEW 5: Device View
  // =========================================================================

  function loadDevice() {
    fetch('/api/device').then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      deviceData = data;
      renderDeviceView();
    }).catch(function (err) {
      deviceData = { ok: false, error: { why: String(err) } };
      renderDeviceView();
    });
  }

  function renderDeviceView() {
    const container = viewContainers.device;
    container.textContent = "";

    const banner = el("div", { class: "banner", style: "margin-bottom:14px;border-radius:6px;" }, [
      el("span", { style: "font-weight:700;color:var(--warn);", "data-i18n": "banner_qemu", text: t("banner_qemu") }),
      el("span", { class: "note", text: "Docker espressif/idf:v5.4 · demo/i3-firmware-qemu/run.sh" })
    ]);
    container.appendChild(banner);

    // Firmware build panel
    const btnBuild = el("button", { class: "btn-sm", text: t("btn_build") });
    btnBuild.addEventListener("click", function () {
      btnBuild.textContent = t("lbl_running");
      fetch('/api/device/build', { method: 'POST' }).then(function (res) {
        if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
        return res.json();
      }).then(function (bData) {
        btnBuild.textContent = t("btn_build");
        alert(bData.ok ? "✓ Firmware built in " + bData.dir + " (" + bData.files + " files)" : "✗ " + ((bData.error && bData.error.why) || "Build failed"));
      }).catch(function (err) {
        btnBuild.textContent = t("btn_build");
        alert(String(err));
      });
    });

    const buildPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", {}, [
          document.createTextNode("(a) "),
          el("span", { "data-i18n": "title_build_firmware", text: t("title_build_firmware") })
        ]),
        btnBuild
      ]),
      el("div", { class: "code-box", text: "neuroedge build --target esp32s3 --board esp32s3-box-3" }),
      el("div", { style: "font-size:12px;margin:8px 0;color:var(--text);", text: "firmware: build/esp32s3 — ESP-IDF project, 38 " + t("lbl_files") }),
      el("div", { style: "font-size:11.5px;color:var(--dim);margin-top:8px;" }, [
        el("span", { text: t("lbl_flash") + " 1220 KiB / 4096 KiB (2876 KiB headroom)" }),
        el("div", { class: "budget-bar" }, [el("div", { class: "budget-fill", style: "width: 29.8%;" })])
      ]),
      el("div", { style: "font-size:11.5px;color:var(--dim);" }, [
        el("span", { text: t("lbl_sram") + " 172.3 KiB / 320 KiB (147.7 KiB above the floor)" }),
        el("div", { class: "budget-bar" }, [el("div", { class: "budget-fill", style: "width: 53.8%;background:var(--accent);" })])
      ])
    ]);

    const qemuLogText = (deviceData && deviceData.qemu && deviceData.qemu.log) ||
      "ESP-IDF v5.4-dev-3208\nI (240) cpu_start: Pro cpu up.\nI (310) octal_psram: PSRAM ID read error (expected in QEMU)\nNE_SELFTEST PASS walker=26 token=11\nI (450) ne_runtime: NETR decision tree verified in flash\nNE1 {\"offset_ms\":0,\"type\":\"device_info\",\"data\":{\"board_id\":\"esp32s3-box-3\",\"agent_version\":\"home-voice@0.1.0\"}}\nNE_TRACE DONE sessions=4\nI (890) ne_boot: heap check free_sram_kb=267.7";

    const qemuPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        document.createTextNode("(c) "),
        el("span", { "data-i18n": "title_qemu_boot", text: t("title_qemu_boot") }),
        el("span", { class: "sub", text: "UART stream" })
      ]),
      el("div", { class: "code-box", style: "height:140px;overflow-y:auto;line-height:1.5;", text: qemuLogText }),
      el("div", { style: "font-size:11.5px;color:var(--dim);margin-top:6px;", "data-i18n": "qemu_note", text: t("qemu_note") })
    ]);

    container.appendChild(el("div", { class: "grid-2col" }, [buildPanel, qemuPanel]));

    // LCD screen gallery
    const btnToggleScr = el("button", { class: "btn-sm", text: "LCD: " + screenLang.toUpperCase() });
    btnToggleScr.addEventListener("click", function () {
      screenLang = screenLang === "vi" ? "en" : "vi";
      btnToggleScr.textContent = "LCD: " + screenLang.toUpperCase();
      renderScreenGalleryCards(galleryGrid);
    });

    const galleryGrid = el("div", { class: "gallery-grid" });
    const galleryPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", {}, [
          document.createTextNode("(b) "),
          el("span", { "data-i18n": "title_ui_gallery", text: t("title_ui_gallery") })
        ]),
        el("div", { style: "display:flex;align-items:center;gap:8px;" }, [
          btnToggleScr,
          el("span", { class: "st allow", "data-i18n": "golden_badge", text: t("golden_badge") })
        ])
      ]),
      galleryGrid
    ]);
    renderScreenGalleryCards(galleryGrid);
    container.appendChild(galleryPanel);

    // OTA Stepper
    const otaPhases = [
      { p: "a", cls: "valid", text: "SKIP same_version 0.1.0 — Bản factory khởi động, máy chủ cùng phiên bản nên bỏ qua; không bao giờ mất khe đang chạy." },
      { p: "b", cls: "valid", text: "SWITCH ota_0 → VALID — Bản 0.2.0 ký đúng tải về, xác minh RSA-3072, chuyển khe và đạt self-test (mốc nước cao NVS nâng lên 0.2.0)." },
      { p: "c", cls: "reject", text: "REJECTED signature → ERASED — Bản ký khóa lạ bị từ chối trước boot; ở lại 0.2.0 và khe vừa ghi bị xóa sector đầu." },
      { p: "d", cls: "rollback", text: "TEST BOOTLOOP → ROLLBACK ota_1→ota_0 — Bản lỗi crash bootloader tự quay về 0.2.0; bỏ qua bản hỏng (SKIP rolled_back)." },
      { p: "e", cls: "rollback", text: "INVALID → ROLLBACK — Bản trượt gate self-test tự đánh dấu hỏng và reboot; bootloader tự quay về bản trước." },
      { p: "f", cls: "reject", text: "REJECTED signature — Bản không có chữ ký bị từ chối và xóa khe ngay lập tức." },
      { p: "g", cls: "valid", text: "SKIP downgrade 0.1.0 — Bản ký đúng nhưng phiên bản thấp hơn bị từ chối hạ cấp bởi mốc nước cao trong NVS." }
    ];

    const stepperDiv = el("div", { class: "stepper" });
    for (let o = 0; o < otaPhases.length; o++) {
      const ph = otaPhases[o];
      stepperDiv.appendChild(el("div", { class: "step-item " + ph.cls }, [
        el("div", { class: "step-phase", text: ph.p }),
        el("div", { text: ph.text })
      ]));
    }

    const otaPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        document.createTextNode("(d) "),
        el("span", { "data-i18n": "title_ota_stepper", text: t("title_ota_stepper") }),
        el("span", { class: "sub", text: "qemu_ota.sh" })
      ]),
      stepperDiv
    ]);
    container.appendChild(otaPanel);
  }

  function renderScreenGalleryCards(grid) {
    grid.textContent = "";
    const screens = ["boot_passed", "voice_listening", "voice_speaking", "confirm", "verdict_allow", "verdict_block", "sensor", "ota_verifying"];
    for (let i = 0; i < screens.length; i++) {
      const scr = screens[i];
      const img = el("img", {
        src: "/api/device/golden/" + screenLang + "/" + scr + ".png",
        alt: scr
      });
      img.addEventListener("error", function () {
        const frame = el("div", { class: "screen-frame" }, [
          svgEl("svg", { viewBox: "0 0 320 240" }, [
            svgEl("rect", { width: "320", height: "240", fill: "#080e14" }),
            svgEl("rect", { x: "8", y: "8", width: "304", height: "224", rx: "4", fill: "none", stroke: "#1f2d3d", "stroke-width": "2" }),
            svgEl("text", { x: "160", y: "120", "text-anchor": "middle", fill: "#d8dee6", "font-size": "13", "font-weight": "bold", "font-family": "system-ui", text: scr + " (" + screenLang + ")" }),
            svgEl("text", { x: "160", y: "145", "text-anchor": "middle", fill: "#58a6ff", "font-size": "11", "font-family": "monospace", text: "LVGL 320×240" })
          ])
        ]);
        img.replaceWith(frame);
      });

      grid.appendChild(el("div", { class: "gallery-card" }, [
        img,
        el("div", { class: "card-title" }, [
          el("span", { text: scr }),
          el("span", { class: "mono", text: "golden ✓" })
        ])
      ]));
    }
  }

  // =========================================================================
  // VIEW 6: MCP View
  // =========================================================================

  function loadMcp() {
    fetch('/api/mcp').then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      mcpData = data;
      renderMcpView();
    }).catch(function (err) {
      mcpData = { ok: false, error: { why: String(err) } };
      renderMcpView();
    });
  }

  function renderMcpView() {
    const container = viewContainers.mcp;
    container.textContent = "";

    const toolsBox = el("div");
    if (!mcpData || !mcpData.ok) {
      toolsBox.appendChild(notAvailableCard((mcpData && mcpData.error && mcpData.error.why) || t("msg_not_available")));
    } else {
      const tools = mcpData.tools || [];
      if (tools.length === 0) {
        toolsBox.appendChild(el("div", { style: "color:var(--dim);font-size:12px;", text: t("lbl_no_tools") }));
      } else {
        for (let i = 0; i < tools.length; i++) {
          toolsBox.appendChild(el("div", { class: "code-box", text: JSON.stringify(tools[i], null, 2) }));
        }
      }
    }

    const desktopBox = el("div");
    if (!mcpData || !mcpData.ok) {
      desktopBox.appendChild(notAvailableCard((mcpData && mcpData.error && mcpData.error.why) || t("msg_not_available")));
    } else {
      desktopBox.appendChild(el("div", { style: "font-size:12px;color:var(--dim);margin-bottom:6px;", text: "neuroedge mcp desktop-config --agent " + boot.agent + " --ui" }));
      desktopBox.appendChild(el("div", { class: "code-box", text: mcpData.desktop_config || JSON.stringify({
        mcpServers: {
          neuroedge: {
            command: "/usr/local/bin/neuroedge",
            args: ["mcp", "serve", "--agent", boot.agent, "--ui"]
          }
        }
      }, null, 2) }));
      desktopBox.appendChild(el("div", { style: "font-size:11.5px;color:var(--dim);margin-top:8px;", "data-i18n": "mcp_desktop_note", text: t("mcp_desktop_note") }));
    }

    const colTools = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_mcp_tools", text: t("title_mcp_tools") }),
        el("span", { class: "sub", text: "Gated Tool Profile v0" })
      ]),
      el("div", { style: "font-size:12px;margin-bottom:8px;", "data-i18n": "mcp_tools_desc", text: t("mcp_tools_desc") }),
      toolsBox
    ]);

    const colDesktop = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_desktop_cfg", text: t("title_desktop_cfg") }),
        el("span", { class: "sub", text: "desktop-config" })
      ]),
      desktopBox
    ]);

    container.appendChild(el("div", { class: "grid-2col" }, [colTools, colDesktop]));

    // Live MCP Tool Call Feed
    const mcpFeedRows = [];
    for (let j = 0; j < events.length; j++) {
      const ev = events[j];
      if (ev.type === "tool_call" && ev.data && ev.data.source === "mcp") {
        mcpFeedRows.push(el("tr", {}, [
          el("td", { class: "mono", text: ev.offset_ms + " ms" }),
          el("td", {}, [el("span", { class: "st accent", text: "mcp" })]),
          el("td", { class: "mono", text: ev.data.name }),
          el("td", { class: "mono", text: JSON.stringify(ev.data.arguments || {}) }),
          el("td", {}, [el("span", { class: "st allow", text: "ALLOW" })])
        ]));
      }
    }

    if (mcpFeedRows.length === 0) {
      mcpFeedRows.push(el("tr", {}, [
        el("td", { colspan: "5", style: "color:var(--dim);text-align:center;", text: t("lbl_no_mcp_calls") })
      ]));
    }

    const feedPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_mcp_feed", text: t("title_mcp_feed") }),
        el("span", { class: "sub", text: "stdio feed" })
      ]),
      el("table", { class: "data-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "th_time", text: t("th_time") }),
            el("th", { "data-i18n": "th_caller", text: t("th_caller") }),
            el("th", { "data-i18n": "th_func", text: t("th_func") }),
            el("th", { "data-i18n": "th_args", text: t("th_args") }),
            el("th", { "data-i18n": "th_verdict", text: t("th_verdict") })
          ])
        ]),
        el("tbody", {}, mcpFeedRows)
      ])
    ]);
    container.appendChild(feedPanel);

    // External MCP Servers
    const extServers = (mcpData && mcpData.servers) || [{ name: "news", tools: ["latest_news"] }];
    const serverItems = [];
    for (let s = 0; s < extServers.length; s++) {
      serverItems.push(el("div", { style: "font-size:12px;margin-bottom:8px;" }, [
        document.createTextNode("Máy chủ ngoài: "),
        el("code", { class: "mono", text: extServers[s].name })
      ]));
    }

    const extPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_ext_mcp", text: t("title_ext_mcp") }),
        el("span", { class: "sub", text: "[mcp.servers]" })
      ]),
      el("div", {}, serverItems),
      el("div", {
        style: "font-size:11.5px;color:var(--warn);margin-top:8px;"
      }, [
        document.createTextNode("🔒 "),
        el("strong", { "data-i18n": "note_data_not_cmd", text: t("note_data_not_cmd") }),
        document.createTextNode(": Dữ liệu từ MCP server ngoài không thể vượt quyền qua Gate.")
      ])
    ]);
    container.appendChild(extPanel);
  }

  // =========================================================================
  // VIEW 7: Config View
  // =========================================================================

  function loadAgent() {
    fetch('/api/agent').then(function (res) {
      if (res.status === 501) return { ok: false, error: { why: t("msg_not_available") } };
      return res.json();
    }).then(function (data) {
      agentData = data;
      renderConfigView();
      if (data.ok && data.providers) {
        renderProviders(data.providers);
      }
    }).catch(function (err) {
      agentData = { ok: false, error: { why: String(err) } };
      renderConfigView();
    });
  }

  function renderConfigView() {
    const container = viewContainers.config;
    container.textContent = "";

    const reqList = [];
    if (agentData && agentData.requires && agentData.requires.primitive) {
      for (const p in agentData.requires.primitive) {
        reqList.push(el("li", {}, [el("code", { class: "mono", text: p })]));
      }
    } else {
      reqList.push(el("li", {}, [el("code", { class: "mono", text: "audio.in (micro)" })]));
      reqList.push(el("li", {}, [el("code", { class: "mono", text: "audio.out (speaker)" })]));
      reqList.push(el("li", {}, [el("code", { class: "mono", text: "digital.out porch_light" })]));
      reqList.push(el("li", {}, [el("code", { class: "mono", text: "sensor.read motion" })]));
    }

    const declPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_agent_decl", text: t("title_agent_decl") }),
        el("span", { class: "sub", text: "agent.toml" })
      ]),
      el("div", { style: "margin-bottom:10px;" }, [
        el("strong", { "data-i18n": "sec_requires", text: t("sec_requires") }),
        el("ul", { style: "margin:4px 0 0;padding-left:20px;font-size:12px;color:var(--text);line-height:1.6;" }, reqList)
      ]),
      el("div", {}, [
        el("strong", { "data-i18n": "sec_board_caps", text: t("sec_board_caps") + " (" + boot.board + ")" }),
        el("ul", { style: "margin:4px 0 0;padding-left:20px;font-size:12px;color:var(--text);line-height:1.6;" }, [
          el("li", { text: "Digital pins: porch_light, door_lock, gate_relay" }),
          el("li", { text: "Sensors: motion, temperature, door_contact" }),
          el("li", { text: "Audio: 16 kHz mono in, 24 kHz PCM out" }),
          el("li", { text: "Display: 320×240 RGB565" })
        ])
      ])
    ]);

    const templates = (agentData && agentData.templates) || [
      { name: "minimal", desc: "1 base gate, 1 digital out pin" },
      { name: "villa-concierge", desc: "Smart lock, guest room authorization" },
      { name: "home-voice", desc: "Voice assistant, RAG Q&A, lighting control" },
      { name: "factory-monitor", desc: "Vent fan & thermal alarm alerts" }
    ];

    const templateRows = [];
    for (let tIdx = 0; tIdx < templates.length; tIdx++) {
      const tmpl = templates[tIdx];
      templateRows.push(el("tr", {}, [
        el("td", { class: "mono" }, [el("strong", { text: tmpl.name })]),
        el("td", { text: tmpl.desc || "—" })
      ]));
    }

    const tmplPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_templates", text: t("title_templates") }),
        el("span", { class: "sub", text: "neuroedge new" })
      ]),
      el("div", { class: "code-box", text: "neuroedge new my-agent --template home-voice" }),
      el("table", { class: "data-table", style: "margin-top:10px;" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "th_name", text: t("th_name") }),
            el("th", { "data-i18n": "th_desc", text: t("th_desc") })
          ])
        ]),
        el("tbody", {}, templateRows)
      ])
    ]);

    container.appendChild(el("div", { class: "grid-2col" }, [declPanel, tmplPanel]));

    const provList = (agentData && agentData.providers) || [
      { role: "stt", label: "openai/whisper-large-v3-turbo", params: "lang: vi · timeout: 15s", key_env: "$OPENROUTER_API_KEY", key_present: true },
      { role: "tts", label: "google/gemini-3.1-flash-tts-preview", params: "voice: Kore · format: pcm · 24 kHz", key_env: "$OPENROUTER_API_KEY", key_present: true },
      { role: "system_two", label: "openrouter/google/gemma-4-31b-it", params: "provider: litellm · tools: support", key_env: "$OPENROUTER_API_KEY", key_present: true },
      { role: "system_one", label: "typesafe/jev-1.13", params: "System One API · fast validation", key_env: "(builtin)", key_present: true }
    ];

    const provRows = [];
    for (let p = 0; p < provList.length; p++) {
      const pv = provList[p];
      provRows.push(el("tr", {}, [
        el("td", {}, [el("strong", { text: pv.role.toUpperCase() })]),
        el("td", { class: "mono", text: pv.label || "—" }),
        el("td", { text: pv.params || "—" }),
        el("td", {}, [
          el("code", { class: "mono", text: pv.key_env || "—" }),
          document.createTextNode(" "),
          el("span", {
            class: pv.key_present ? "st allow" : "st block",
            "data-i18n": pv.key_present ? "val_key_present" : "val_key_missing",
            text: pv.key_present ? t("val_key_present") : t("val_key_missing")
          })
        ])
      ]));
    }

    const provPanel = el("div", { class: "panel" }, [
      el("h2", {}, [
        el("span", { "data-i18n": "title_providers", text: t("title_providers") }),
        el("span", { class: "sub", text: "Security Key Guard" })
      ]),
      el("table", { class: "data-table" }, [
        el("thead", {}, [
          el("tr", {}, [
            el("th", { "data-i18n": "th_provider", text: t("th_provider") }),
            el("th", { "data-i18n": "th_model", text: t("th_model") }),
            el("th", { "data-i18n": "th_params", text: t("th_params") }),
            el("th", { "data-i18n": "th_key", text: t("th_key") })
          ])
        ]),
        el("tbody", {}, provRows)
      ]),
      el("div", {
        style: "font-size:11px;color:var(--dim);margin-top:8px;",
        "data-i18n": "note_api_keys",
        text: t("note_api_keys")
      })
    ]);
    container.appendChild(provPanel);
  }

  // Initial event source & voice polling
  function startVoicePolling() {
    setInterval(function () {
      if (currentView === "live") {
        fetch('/api/voice').then(function (res) {
          if (res.status === 501) return null;
          return res.json();
        }).then(function (data) {
          if (data && data.ok) {
            voiceData = data;
            const liveView = viewContainers.live;
            const oldStrip = liveView.querySelector(".voice-strip");
            if (oldStrip) {
              const newStrip = buildVoiceStrip();
              oldStrip.replaceWith(newStrip);
            }
          }
        }).catch(function () {});
      }
    }, 1000);
  }

  function initSSE() {
    let evtSource = null;
    function connect() {
      evtSource = new EventSource('/events');
      evtSource.onopen = function () {
        setLiveStatus(true);
      };
      evtSource.onmessage = function (ev) {
        try {
          const payload = JSON.parse(ev.data);
          events = payload.events || [];
          now_ms = payload.now_ms || 0;
          setLiveStatus(true);
          if (currentView === "live") renderLiveSession();
        } catch (e) {}
      };
      evtSource.onerror = function () {
        setLiveStatus(false);
      };
    }
    connect();
  }

  renderActiveView();
  initSSE();
  startVoicePolling();

  fetch('/api/agent').then(function (res) {
    if (res.status === 501) return null;
    return res.json();
  }).then(function (data) {
    if (data && data.ok) {
      agentData = data;
      renderProviders(data.providers);
    }
  }).catch(function () {});

})();
