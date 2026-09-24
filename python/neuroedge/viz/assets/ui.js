/*
 * NeuroEdge session view — shared by `neuroedge trace view` (static) and
 * `neuroedge run --ui` (live). Plain DOM, no dependencies, no network.
 * Every string from a trace is set with textContent, never as HTML.
 *
 *   NE.stateAt(events, t)  -> what the pins, sensors and screen were at t (ms)
 *   NE.mount(root, opts)   -> render; opts = {meta, board, events, live, onCommand}
 */
(function (global) {
  "use strict";

  function stateAt(events, t) {
    const pins = {}, sensors = {}, gates = [], asks = {};
    let frame = null, begin = null, speech = null, heard = null, call = null;
    for (const [i, e] of events.entries()) {
      if (e.offset_ms > t) break;
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
      } else if (e.type === "tts_stream_start") {
        speech = { text: d.text, offset_ms: e.offset_ms };
      } else if (e.type === "text_input") {
        heard = d.text;
      } else if (e.type === "tool_call") {
        call = d; // the gate evaluation that follows answers this call: say who asked
      } else if (e.type === "tool_call_rejected") {
        // the schema refused it, so no gate ran: still a decision the page should show
        gates.push({ index: i, offset_ms: e.offset_ms, gate: d.name, call: call,
          result: { verdict: "REJECTED", reason: (d.problems || []).join("; ") } });
        call = null;
      } else if (e.type === "action_requested") {
        if (call && call.name !== d.action) call = null; // c.do() reached some other way
      } else if (e.type === "tool_confirm_requested") {
        asks[d.id] = d;  // RFC-0006: the device asked a person
      } else if (e.type === "tool_confirmed" || e.type === "tool_confirm_declined"
                 || e.type === "tool_confirm_expired") {
        delete asks[d.id];
      } else if (e.type === "gate_evaluation_begin") {
        begin = d.gate;
      } else if (e.type === "gate_evaluation_result") {
        gates.push({ index: i, offset_ms: e.offset_ms, gate: begin || d.blocked_by, call: call, result: d });
        begin = null;
        call = null;
      }
    }
    for (const name in pins) pins[name].on = t < pins[name].until;
    // The newest question still open at t, and not past its expiry.
    let pending = null;
    for (const id in asks) if (asks[id].expires_ms > t) pending = asks[id];
    return { pins: pins, sensors: sensors, frame: frame, gates: gates, speech: speech, heard: heard,
             pending: pending };
  }

  function horizon(events) {
    let end = 0;
    for (const e of events) {
      end = Math.max(end, e.offset_ms);
      if (e.type === "actuator_command" && e.data.operation === "pulse") {
        end = Math.max(end, e.offset_ms + (e.data.duration_ms || 0));
      }
    }
    return end;
  }

  // --- tiny DOM helpers -------------------------------------------------------------
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const key in attrs || {}) {
      if (key === "text") node.textContent = attrs[key];
      else if (key === "class") node.className = attrs[key];
      else node.setAttribute(key, attrs[key]);
    }
    for (const child of children || []) if (child) node.appendChild(child);
    return node;
  }
  const SVG = "http://www.w3.org/2000/svg";
  function svg(markup) {
    // markup is built only from the constants below, never from trace data
    const node = document.createElementNS(SVG, "svg");
    node.setAttribute("viewBox", "0 0 64 64");
    node.innerHTML = markup;
    return node;
  }
  function icon(pin, on) {
    const c = on ? "var(--allow)" : "var(--dim)";
    if (/lock/.test(pin)) {
      const shackle = on ? "M22 30 V20 a10 10 0 0 1 20 0" : "M22 30 V20 a10 10 0 0 1 20 0 V30";
      return svg('<path d="' + shackle + '" fill="none" stroke="' + c + '" stroke-width="5"/>' +
        '<rect x="14" y="30" width="36" height="26" rx="4" fill="' + c + '"/>' +
        '<circle cx="32" cy="43" r="4" fill="var(--panel)"/>');
    }
    if (/light|lamp|led/.test(pin)) {
      return svg('<circle cx="32" cy="26" r="16" fill="' + (on ? "#f2cc60" : "none") + '" stroke="' + c + '" stroke-width="4"/>' +
        '<rect x="24" y="44" width="16" height="10" rx="2" fill="' + c + '"/>');
    }
    if (/relay|gate/.test(pin)) {
      return svg('<circle cx="14" cy="40" r="5" fill="' + c + '"/><circle cx="50" cy="40" r="5" fill="' + c + '"/>' +
        '<line x1="14" y1="40" x2="' + (on ? 50 : 44) + '" y2="' + (on ? 40 : 18) + '" stroke="' + c + '" stroke-width="5" stroke-linecap="round"/>');
    }
    return svg('<circle cx="32" cy="32" r="18" fill="' + (on ? "var(--allow)" : "none") + '" stroke="' + c + '" stroke-width="4"/>');
  }

  function short(data) {
    const text = JSON.stringify(data);
    return text.length > 160 ? text.slice(0, 157) + "…" : text;
  }

  // --- the view ---------------------------------------------------------------------
  function mount(root, opts) {
    const view = { opts: opts, events: opts.events || [], t: 0, follow: !!opts.live, received: Date.now(), now: 0 };
    root.textContent = "";
    const meta = opts.meta || {};
    const header = el("header", {}, [
      el("h1", { text: (meta.agent_version || "NeuroEdge session") }),
      el("span", { class: "meta", text: [meta.session_id, meta.target, meta.board_id, meta.timestamp_utc].filter(Boolean).join(" · ") }),
    ]);
    const devices = el("div", { class: "devices" });
    const sensors = el("div");
    const screen = el("div", { class: "screen empty", text: "—" });
    const heard = el("div", { class: "why", text: "" });
    const said = el("div", { class: "speech", text: "—" });
    const verdicts = el("div");
    const rows = el("tbody");
    const slider = el("input", { type: "range", min: "0", step: "1", value: "0" });
    const clock = el("output", { text: "0 ms" });
    const left = el("div", { class: "stack" }, [
      el("section", { class: "panel" }, [el("h2", { text: "Thiết bị" }), devices]),
      el("section", { class: "panel" }, [el("h2", { text: "Cảm biến" }), sensors]),
      el("section", { class: "panel" }, [el("h2", { text: "Trợ lý nói" }), heard, said]),
      el("section", { class: "panel" }, [el("h2", { text: "Màn hình" }), screen]),
    ]);
    const right = el("div", { class: "stack" });
    // RFC-0006 — the device's question to a person, with the time left to answer.
    const askText = el("div", { class: "ask-text" });
    const askLeft = el("div", { class: "ask-left" });
    const askButtons = el("div", { class: "ask-buttons" });
    const ask = el("section", { class: "panel ask", role: "alertdialog", "aria-live": "assertive" },
      [el("h2", { text: "Thiết bị hỏi xác nhận" }), askText, askLeft, askButtons]);
    ask.hidden = true;
    let askId = null;
    if (opts.onConfirm) {
      const yes = el("button", { type: "button", class: "yes", text: "Đồng ý" });
      const no = el("button", { type: "button", class: "no", text: "Huỷ" });
      yes.addEventListener("click", function () { if (askId) opts.onConfirm(askId, true); });
      no.addEventListener("click", function () { if (askId) opts.onConfirm(askId, false); });
      askButtons.appendChild(yes);
      askButtons.appendChild(no);
    }
    right.appendChild(ask);
    if (opts.onCommand) {
      const input = el("input", { placeholder: "Gõ lệnh cho agent — hoặc :sensor <tên> <giá trị>, :set <dữ kiện> <giá trị>", autocomplete: "off" });
      const form = el("form", { class: "say" }, [input, el("button", { type: "submit", text: "Gửi" })]);
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        if (input.value.trim()) opts.onCommand(input.value.trim());
        input.value = "";
      });
      right.appendChild(el("section", { class: "panel" }, [form]));
    }
    if (!opts.live) {
      right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "Thời điểm" }), el("div", { class: "scrub" }, [slider, clock])]));
    }
    right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "Phán quyết gate" }), verdicts]));
    right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "Dòng sự kiện" }),
      el("table", { class: "events" }, [rows])]));
    root.appendChild(header);
    root.appendChild(el("main", {}, [left, right]));

    function pinsDeclared() {
      const names = new Set((opts.board && opts.board.pins) || []);
      for (const e of view.events) if (e.type === "actuator_command") names.add(e.data.pin);
      return Array.from(names);
    }

    function render() {
      const end = horizon(view.events);
      slider.max = String(end);
      if (view.follow) view.t = opts.live ? view.now + (Date.now() - view.received) : end;
      const t = view.t;
      slider.value = String(Math.min(t, end));
      clock.textContent = Math.round(t) + " ms";
      const s = stateAt(view.events, t);

      devices.textContent = "";
      for (const pin of pinsDeclared()) {
        const p = s.pins[pin];
        const on = !!(p && p.on);
        const label = !p ? "LOW" : on ? (p.operation === "pulse" ? "PULSE" : "HIGH") : (p.aborted ? "ABORTED" : "LOW");
        devices.appendChild(el("div", { class: "device" + (on ? " on" : "") }, [
          icon(pin, on), el("div", { text: pin }), el("div", { class: "state", text: label }),
        ]));
      }
      sensors.textContent = "";
      const sensorNames = new Set(Object.keys(s.sensors).concat((opts.board && opts.board.sensors) || []));
      for (const name of sensorNames) {
        const r = s.sensors[name];
        sensors.appendChild(el("div", { class: "sensor" }, [
          el("span", { text: name }),
          el("span", { text: r ? String(r.value) + (r.unit ? " " + r.unit : "") : "—" }),
        ]));
      }
      if (s.frame) {
        screen.className = "screen";
        screen.textContent = s.frame.text !== undefined ? s.frame.text
          : s.frame.format + " " + s.frame.width + "×" + s.frame.height + "\n" + String(s.frame.sha256).slice(0, 23) + "…";
      } else { screen.className = "screen empty"; screen.textContent = "—"; }
      heard.textContent = s.heard ? "Bạn: " + s.heard : "";
      if (s.pending) {
        askId = s.pending.id;
        ask.hidden = false;
        askText.textContent = s.pending.message + " (" + s.pending.action + ")";
        askLeft.textContent = "Còn " + Math.max(0, Math.ceil((s.pending.expires_ms - t) / 1000))
          + " s · chỉ người trên thiết bị trả lời được — trợ lý và client MCP không xác nhận thay";
        askButtons.hidden = !opts.onConfirm;
      } else { askId = null; ask.hidden = true; }
      said.textContent = s.speech ? s.speech.text : "—";

      verdicts.textContent = "";
      const all = stateAt(view.events, Infinity).gates;
      if (!all.length) verdicts.appendChild(el("div", { class: "why", text: "Chưa có lần thẩm định gate nào." }));
      for (const g of all) {
        const r = g.result;
        const why = [r.reason, r.failed_criterion && "tiêu chí " + r.failed_criterion].filter(Boolean).join(" · ")
          + (r.action ? " → " + r.action + (r.escalated_to ? " " + r.escalated_to : "") : "");
        const card = el("div", { class: "verdict " + r.verdict + (g.offset_ms > t ? " future" : "") }, [
          el("span", { class: "badge", text: r.verdict }), document.createTextNode(" "),
          el("span", { text: g.gate || "" }),
          g.call ? el("div", { class: "why via", text: "tool_call " + g.call.name + " · " + g.call.source }) : null,
          why ? el("div", { class: "why", text: why }) : null,
          r.evaluations ? el("div", { class: "why", text: short(r.evaluations) }) : null,
        ]);
        card.addEventListener("click", function () { view.follow = false; view.t = g.offset_ms; render(); });
        verdicts.appendChild(card);
      }

      rows.textContent = "";
      let current = -1;
      view.events.forEach(function (e, i) { if (e.offset_ms <= t) current = i; });
      view.events.forEach(function (e, i) {
        const tr = el("tr", { class: i > current ? "future" : i === current ? "current" : "" }, [
          el("td", { text: e.offset_ms + " ms" }),
          el("td", {}, [el("code", { text: e.type })]),
          el("td", { class: "data", text: short(e.data) }),
        ]);
        tr.addEventListener("click", function () { view.follow = false; view.t = e.offset_ms; render(); });
        rows.appendChild(tr);
      });
    }

    slider.addEventListener("input", function () { view.follow = false; view.t = Number(slider.value); render(); });
    // Open on the last event, where the latest decision is in effect (a pulse may
    // still be running); the slider goes on to the end of the longest pulse.
    view.t = opts.live || !view.events.length ? 0 : view.events[view.events.length - 1].offset_ms;
    render();
    if (opts.live) setInterval(render, 250);

    return {
      update: function (events, nowMs) {
        view.events = events;
        view.now = nowMs;
        view.received = Date.now();
        view.follow = true;
        render();
      },
    };
  }

  global.NE = { stateAt: stateAt, horizon: horizon, mount: mount };
  if (typeof module !== "undefined") module.exports = global.NE;
})(typeof window !== "undefined" ? window : globalThis);
