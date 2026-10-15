/*
 * NeuroEdge session view — shared by `neuroedge trace view` (static) and
 * `neuroedge run --ui` (live). Plain DOM, no dependencies, no network.
 * Every string from a trace is set with textContent, never as HTML.
 *
 *   NE.stateAt(events, t)  -> what the pins, sensors, input lines, motion channels and screen were at t (ms)
 *   NE.mount(root, opts)   -> render; opts = {meta, board, agent, events, live, onCommand, onConfirm}
 *   (agent: labels, actions, commands, gate criteria — sim/ui.py describe_agent; absent in a trace view)
 */
(function (global) {
  "use strict";

  function stateAt(events, t) {
    const pins = {}, sensors = {}, inputs = {}, motion = {}, gates = [], asks = {}, askedBy = {};
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
      } else if ((e.type === "digital_in" || e.type === "digital_in_set") && typeof d.value === "boolean") {
        inputs[d.pin] = d.value;  // RFC-0007 §3a: the level of a digital.in line, high = true
      } else if (e.type === "motion_command") {
        motion[d.channel] = d.kind === "motor"
          ? "speed " + d.speed + " · ramp " + d.ramp_ms + " ms"
          : "target " + d.target;  // RFC-0011: a command holds its channel for one lease
      } else if (e.type === "motion_safe") {
        motion[d.channel] = d.state + " (" + d.cause + ")";
      } else if (e.type === "display_frame") {
        frame = d;
      } else if (e.type === "tts_stream_start") {
        speech = { text: d.text, offset_ms: e.offset_ms };
      } else if (e.type === "text_input") {
        heard = d.text;
        speech = null;  // a new turn: what the device said to the last one is not its answer
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
        const last = gates.length ? gates[gates.length - 1].call : null;  // the BLOCK that opened it
        askedBy[d.id] = last && last.name === d.action ? last : { name: d.action };
      } else if (e.type === "tool_confirmed") {
        // the gate runs again on the person's yes: that verdict answers the call that asked
        call = Object.assign({}, askedBy[d.id] || {}, { confirmed_by: d.source });
        delete asks[d.id];
      } else if (e.type === "tool_confirm_declined"
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
    return { pins: pins, sensors: sensors, inputs: inputs, motion: motion, frame: frame, gates: gates, speech: speech, heard: heard,
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
  // `name` is the pin's name, with the agent's label for it when it has one: the drawing follows
  // the words ("Máy sưởi", "porch_light"), in Vietnamese or English, a generic dot otherwise.
  function icon(name, on) {
    const c = on ? "var(--allow)" : "var(--dim)";
    if (/khoá|khóa|cửa|lock|door/.test(name)) {
      const shackle = on ? "M22 30 V20 a10 10 0 0 1 20 0" : "M22 30 V20 a10 10 0 0 1 20 0 V30";
      return svg('<path d="' + shackle + '" fill="none" stroke="' + c + '" stroke-width="5"/>' +
        '<rect x="14" y="30" width="36" height="26" rx="4" fill="' + c + '"/>' +
        '<circle cx="32" cy="43" r="4" fill="var(--panel)"/>');
    }
    if (/đèn|light|lamp|led/.test(name)) {
      return svg('<circle cx="32" cy="26" r="16" fill="' + (on ? "#f2cc60" : "none") + '" stroke="' + c + '" stroke-width="4"/>' +
        '<rect x="24" y="44" width="16" height="10" rx="2" fill="' + c + '"/>');
    }
    if (/sưởi|nhiệt|heat/.test(name)) {
      return svg('<path d="M32 8 C40 20 46 26 46 38 a14 14 0 0 1 -28 0 C18 30 24 26 26 18 C30 26 32 26 32 8 Z" fill="'
        + (on ? "#f0883e" : "none") + '" stroke="' + c + '" stroke-width="4" stroke-linejoin="round"/>');
    }
    if (/bơm|sục|quạt|khí|pump|fan|aera|vent/.test(name)) {
      return svg('<circle cx="32" cy="32" r="5" fill="' + c + '"/>' +
        '<path d="M32 27 C30 14 40 10 44 18 C46 23 38 27 32 27 Z M37 34 C49 38 48 49 39 50 C34 50 33 41 37 34 Z M27 34 C19 44 9 39 12 31 C14 26 23 28 27 34 Z" fill="'
        + (on ? "var(--allow)" : "none") + '" stroke="' + c + '" stroke-width="3"/>');
    }
    if (/relay|gate|rơ-le|công tắc|switch/.test(name)) {
      return svg('<circle cx="14" cy="40" r="5" fill="' + c + '"/><circle cx="50" cy="40" r="5" fill="' + c + '"/>' +
        '<line x1="14" y1="40" x2="' + (on ? 50 : 44) + '" y2="' + (on ? 40 : 18) + '" stroke="' + c + '" stroke-width="5" stroke-linecap="round"/>');
    }
    return svg('<circle cx="32" cy="32" r="18" fill="' + (on ? "var(--allow)" : "none") + '" stroke="' + c + '" stroke-width="4"/>');
  }

  function short(data) {
    const text = JSON.stringify(data);
    return text.length > 160 ? text.slice(0, 157) + "…" : text;
  }

  // --- words for people ---------------------------------------------------------------
  // The agent may name its pins, sensors and facts (`[ui.labels]` of agent.toml); otherwise the
  // page uses the gate's own `instructions` for a criterion, and the raw name last.
  const VERDICT = { ALLOW: "Cho phép", BLOCK: "Chặn", REJECTED: "Từ chối (sai lệnh)" };
  const SOURCE = { local_grammar: "Bạn gõ trên trang", mcp: "Brain / client MCP", system_one: "Trợ lý (System 1)",
    system_two: "Trợ lý (System 2)", test: "Bài test", ui: "Người trên trang" };
  const ON_BLOCK = { deny: "Không làm gì. Không ai xác nhận thay được.", ask: "Hỏi người ở nhà trước khi làm.",
    escalate: "Chuyển cho người phụ trách.", degrade: "Làm phương án an toàn hơn thay thế." };
  function yesNo(v) { return v === true ? "có" : v === false ? "không" : v === null || v === undefined ? "không rõ" : String(v); }

  // --- the view ---------------------------------------------------------------------
  function mount(root, opts) {
    const view = { opts: opts, events: opts.events || [], t: 0, follow: !!opts.live, received: Date.now(), now: 0 };
    const agent = opts.agent || {};
    const labels = agent.labels || {};
    const gates = agent.gates || {};
    const actions = {};
    for (const a of agent.actions || []) actions[a.name] = a;
    const sayFor = {};
    for (const c of agent.commands || []) if (!(c.tool in sayFor)) sayFor[c.tool] = c.say;
    function label(name) { return labels[name] || name; }
    function criterionText(gate, name) {
      if (labels[name]) return labels[name];
      const g = gates[gate];
      return (g && g.criteria[name] && g.criteria[name].instructions) || name;
    }
    function actionText(name) {
      const a = actions[name];
      return (sayFor[name] ? "“" + sayFor[name] + "”" : name) + (a && a.pins.length ? " · " + a.pins.map(label).join(", ") : "");
    }
    function send(text) { if (opts.onCommand) opts.onCommand(text); }
    // The agent's word for a pin decides its drawing; the pin's own name only when that says nothing.
    function pinIcon(pin, on) {
      const plain = icon(pin, on);
      if (!labels[pin]) return plain;
      const named = icon(labels[pin].toLowerCase(), on);
      return named.innerHTML === icon("", on).innerHTML ? plain : named;
    }
    function unit(u) { return u === "C" ? "°C" : u === "F" ? "°F" : u; }
    const OP = { gte: "≥", lte: "≤", equals: "=" };
    function ruleText(rule) { return rule.replace(/\b(gte|lte|equals) /g, function (_, op) { return OP[op] + " "; }); }
    const order = {};
    (agent.commands || []).forEach(function (c, i) { if (!(c.tool in order)) order[c.tool] = i; });
    // The page redraws four times a second; a panel is rebuilt only when what it shows changed,
    // so a value being typed, or a button under the pointer, is not thrown away.
    const drawn = {};
    function changed(panel, key) { key = JSON.stringify(key); if (drawn[panel] === key) return false; drawn[panel] = key; return true; }

    root.textContent = "";
    const meta = opts.meta || {};
    const help = el("details", { class: "help" }, [
      el("summary", { text: "Trang này là gì?" }),
      el("p", { text: "Một phiên chạy thử, không có phần cứng thật: thiết bị và cảm biến là giả lập. "
        + "Mọi lệnh, gõ ở đây hay từ brain qua MCP, đều đi qua gate trước khi chạm vào thiết bị." }),
      el("ol", {}, [
        el("li", { text: "Đổi cảm biến hoặc dữ kiện ở cột trái để tạo tình huống (ví dụ nước ấm)." }),
        el("li", { text: "Bấm một lệnh, hoặc để brain gọi qua MCP." }),
        el("li", { text: "Xem “Quyết định của gate”: ai yêu cầu, gate xét những điều kiện nào (✓ đạt, ✗ không đạt), và kết quả." }),
        el("li", { text: "Nếu gate cần người ở nhà, khung vàng hiện lên: chỉ người trên trang này trả lời được." }),
      ]),
    ]);
    const header = el("header", {}, [
      el("h1", { text: (meta.agent_version || "NeuroEdge session") }),
      el("span", { class: "chip", text: opts.live ? "Đang chạy · mô phỏng" : "Xem lại phiên đã ghi" }),
      el("span", { class: "meta", text: [meta.target, meta.board_id, meta.session_id].filter(Boolean).join(" · ") }),
      help,
    ]);
    const devices = el("div", { class: "devices" });
    const sensors = el("div");
    const facts = el("div");
    const screen = el("div", { class: "screen empty", text: "—" });
    const chat = el("div", { class: "chat" });
    const verdicts = el("div");
    const rows = el("tbody");
    const slider = el("input", { type: "range", min: "0", step: "1", value: "0" });
    const clock = el("output", { text: "0 ms" });
    const wantsScreen = (agent.requires || []).indexOf("display.write") >= 0
      || view.events.some(function (e) { return e.type === "display_frame"; });
    const screenPanel = el("section", { class: "panel" }, [el("h2", { text: "Màn hình" }), screen]);
    screenPanel.hidden = !wantsScreen;
    const left = el("div", { class: "stack" }, [
      el("section", { class: "panel" }, [el("h2", { text: "1 · Thiết bị" }),
        el("p", { class: "hint", text: opts.live ? "Trạng thái thật của từng chân. Nút bên dưới gửi lệnh, lệnh vẫn đi qua gate."
          : "Trạng thái của từng chân tại thời điểm đang xem." }), devices]),
      el("section", { class: "panel" }, [el("h2", { text: "2 · Cảm biến và dữ kiện" }),
        el("p", { class: "hint", text: opts.live ? "Đổi giá trị để tạo tình huống. Gate đọc dữ kiện, không đọc lời của brain."
          : "Giá trị cảm biến đã ghi trong phiên." }), sensors, facts]),
      screenPanel,
    ]);
    const right = el("div", { class: "stack" });
    // RFC-0006 — the device's question to a person, with the time left to answer.
    const askText = el("div", { class: "ask-text" });
    const askWhy = el("div", { class: "ask-why" });
    const askLeft = el("div", { class: "ask-left" });
    const askButtons = el("div", { class: "ask-buttons" });
    const ask = el("section", { class: "panel ask", role: "alertdialog", "aria-live": "assertive" },
      [el("h2", { text: "Thiết bị hỏi xác nhận" }), askText, askWhy, askLeft, askButtons]);
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
      const input = el("input", { placeholder: "Gõ lệnh cho agent — hoặc :sensor <tên> <giá trị>, :input <chân> <true|false>, :set <dữ kiện> <giá trị>", autocomplete: "off" });
      const form = el("form", { class: "say" }, [input, el("button", { type: "submit", text: "Gửi" })]);
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        if (input.value.trim()) send(input.value.trim());
        input.value = "";
      });
      const quick = el("div", { class: "quick" });
      for (const c of agent.commands || []) {
        const b = el("button", { type: "button", text: c.say, title: "tool " + c.tool });
        b.addEventListener("click", function () { send(c.say); });
        quick.appendChild(b);
      }
      right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "3 · Ra lệnh" }), form,
        (agent.commands || []).length ? el("p", { class: "hint below", text: "Lệnh agent hiểu (bấm để gửi):" }) : null, quick]));
    }
    if (!opts.live) {
      right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "Thời điểm" }), el("div", { class: "scrub" }, [slider, clock])]));
    }
    right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "Hội thoại · bạn ra lệnh, Trợ lý nói" }), chat]));
    right.appendChild(el("section", { class: "panel" }, [el("h2", { text: "4 · Quyết định của gate (mới nhất ở trên)" }), verdicts]));
    const count = el("span");
    right.appendChild(el("details", { class: "panel tech" }, [el("summary", {}, [document.createTextNode("Chi tiết kỹ thuật: dòng sự kiện "), count]),
      el("table", { class: "events" }, [rows])]));
    root.appendChild(header);
    root.appendChild(el("main", {}, [left, right]));

    function pinsDeclared() {
      const names = new Set();
      for (const a of agent.actions || []) for (const p of a.pins) names.add(p);
      if (!names.size) for (const p of (opts.board && opts.board.pins) || []) names.add(p);
      for (const e of view.events) if (e.type === "actuator_command") names.add(e.data.pin);
      return Array.from(names);
    }
    // The pins each decision moved: the commands after its result, up to the next call.
    function movedAfter(index) {
      const out = [];
      for (let i = index + 1; i < view.events.length; i++) {
        const e = view.events[i];
        if (e.type === "tool_call" || e.type === "gate_evaluation_begin" || e.type === "text_input") break;
        if (e.type === "actuator_command") out.push(label(e.data.pin) + " " + (e.data.operation === "on" ? "BẬT" : e.data.operation === "off" ? "TẮT"
          : e.data.operation === "pulse" ? "BẬT " + Math.round((e.data.duration_ms || 0) / 1000) + " s rồi tự tắt" : e.data.operation));
      }
      return out;
    }
    function conversation(t) {
      const lines = [];
      for (const e of view.events) {
        if (e.offset_ms > t) break;
        const d = e.data || {};
        if (e.type === "text_input") lines.push({ who: "Bạn", text: d.text });
        else if (e.type === "tool_call" && d.source === "mcp") lines.push({ who: "Brain (MCP)", text: "gọi " + actionText(d.name) });
        else if (e.type === "tts_stream_start" && !/^sha256:/.test(d.text || "")) lines.push({ who: "Thiết bị", text: d.text });
        else if (e.type === "gate_evaluation_result") lines.push({ who: "Gate", text: d.verdict === "ALLOW" ? "✓ cho phép" : "✗ chặn"
          + (d.failed_criterion ? (d.reason === "criterion_unavailable" ? " — không đọc được: " : " — chưa đạt: ")
            + label(d.failed_criterion) : ""), cls: d.verdict });
        else if (e.type === "sensor_set") lines.push({ who: "Bạn", text: "đặt " + label(d.sensor) + " = " + d.value, cls: "note" });
        else if (e.type === "tool_confirmed") lines.push({ who: "Người ở nhà", text: "Đồng ý" });
        else if (e.type === "tool_confirm_declined") lines.push({ who: "Người ở nhà", text: "Huỷ" });
        else if (e.type === "tool_confirm_expired") lines.push({ who: "Thiết bị", text: "Hết giờ, không ai trả lời: không làm." });
      }
      return lines.slice(-10);
    }

    function render() {
      const end = horizon(view.events);
      slider.max = String(end);
      if (view.follow) view.t = opts.live ? view.now + (Date.now() - view.received) : end;
      const t = view.t;
      slider.value = String(Math.min(t, end));
      clock.textContent = Math.round(t) + " ms";
      const s = stateAt(view.events, t);

      const pinKey = pinsDeclared().map(function (pin) { const p = s.pins[pin]; return [pin, !!(p && p.on), p && p.operation, p && p.aborted]; });
      const devicesFresh = changed("devices", pinKey);
      if (devicesFresh) devices.textContent = "";
      for (const pin of devicesFresh ? pinsDeclared() : []) {
        const p = s.pins[pin];
        const on = !!(p && p.on);
        const state = !p ? "TẮT" : on ? (p.operation === "pulse" ? "BẬT (xung)" : "BẬT") : (p.aborted ? "DỪNG GẤP" : "TẮT");
        const buttons = el("div", { class: "dev-actions" });
        if (opts.onCommand) {
          const mine = (agent.actions || []).filter(function (a) { return a.pins.indexOf(pin) >= 0 && sayFor[a.name]; })
            .sort(function (x, y) { return order[x.name] - order[y.name]; });
          for (const a of mine) {
            const b = el("button", { type: "button", text: sayFor[a.name], title: a.doc + " (gate " + a.gate + ")" });
            b.addEventListener("click", function () { send(sayFor[a.name]); });
            buttons.appendChild(b);
          }
        }
        devices.appendChild(el("div", { class: "device" + (on ? " on" : "") }, [
          pinIcon(pin, on),
          el("div", { class: "dev-name", text: label(pin) }),
          labels[pin] ? el("div", { class: "dev-pin", text: pin }) : null,
          el("div", { class: "state", text: state }),
          buttons,
        ]));
      }

      const sensorsFresh = changed("sensors", [s.sensors, s.inputs, s.motion]);
      if (sensorsFresh) sensors.textContent = "";
      // An agent loaded: the sensors it reads. A recording alone: what the board has.
      const sensorNames = new Set(Object.keys(s.sensors).concat(agent.sensors || [],
        Object.values(agent.sensor_facts || {}).map(function (r) { return r.sensor; })));
      if (!agent.sensors) for (const n of (opts.board && opts.board.sensors) || []) sensorNames.add(n);
      for (const name of sensorsFresh ? sensorNames : []) {
        const r = s.sensors[name];
        const shown = r ? String(r.value) + (r.unit && typeof r.value === "number" ? " " + unit(r.unit) : "") : "—";
        const row = el("div", { class: "sensor" }, [
          el("span", { class: "s-name", text: label(name) }),
          el("span", { class: "s-value" + (r && typeof r.value !== "number" ? " bad" : ""), text: shown }),
        ]);
        sensors.appendChild(row);
        for (const fact in agent.sensor_facts || {}) {
          const rule = agent.sensor_facts[fact];
          if (rule.sensor !== name) continue;
          sensors.appendChild(el("div", { class: "derived", text: "→ dữ kiện “" + label(fact) + "” = có khi " + label(name) + " " + ruleText(rule.rule) + ". Gate đọc dữ kiện này." }));
        }
        if (opts.onCommand) {
          const field = el("input", { type: "text", inputmode: "decimal", placeholder: "giá trị mới", "aria-label": "giá trị mới cho " + name });
          const set = el("button", { type: "button", text: "Đặt" });
          const lost = el("button", { type: "button", class: "ghost", text: "Mất tín hiệu", title: "Giả lập cảm biến hỏng: gửi một giá trị không đọc được" });
          set.addEventListener("click", function () { if (field.value.trim()) send(":sensor " + name + " " + field.value.trim()); field.value = ""; });
          field.addEventListener("keydown", function (ev) { if (ev.key === "Enter") set.click(); });
          lost.addEventListener("click", function () { send(":sensor " + name + " lỗi"); });
          sensors.appendChild(el("div", { class: "edit" }, [field, set, lost]));
        }
      }
      for (const name of sensorsFresh ? new Set(Object.keys(s.inputs).concat((opts.board && opts.board.inputs) || [])) : []) {
        if (!(name in s.inputs) && agent.actions) continue;
        sensors.appendChild(el("div", { class: "sensor" }, [el("span", { text: label(name) }),
          el("span", { text: name in s.inputs ? (s.inputs[name] ? "HIGH" : "LOW") : "—" })]));
      }
      for (const name of sensorsFresh ? new Set(Object.keys(s.motion).concat((opts.board && opts.board.motion) || [])) : []) {
        if (!(name in s.motion) && agent.actions) continue;
        sensors.appendChild(el("div", { class: "sensor" }, [el("span", { text: label(name) }),
          el("span", { text: name in s.motion ? s.motion[name] : "—" })]));
      }

      const factsFresh = changed("facts", agent.facts || {});
      if (factsFresh) facts.textContent = "";
      for (const name in factsFresh ? agent.facts || {} : {}) {
        const value = el("span", { class: "s-value", text: yesNo(agent.facts[name]) });
        const row = el("div", { class: "sensor" }, [el("span", { class: "s-name", text: label(name) }), value]);
        facts.appendChild(row);
        if (name === "owner_confirmed") {
          facts.appendChild(el("div", { class: "derived", text: "Chỉ đạt khi người ở nhà bấm Đồng ý, cho đúng một lần." }));
        }
      }

      if (s.frame) {
        screen.className = "screen";
        screen.textContent = s.frame.text !== undefined ? s.frame.text
          : s.frame.format + " " + s.frame.width + "×" + s.frame.height + "\n" + String(s.frame.sha256).slice(0, 23) + "…";
      } else { screen.className = "screen empty"; screen.textContent = "—"; }

      if (s.pending) {
        askId = s.pending.id;
        ask.hidden = false;
        askText.textContent = s.pending.message;
        askWhy.textContent = "Lệnh đang chờ: " + actionText(s.pending.action);
        askLeft.textContent = "Còn " + Math.max(0, Math.ceil((s.pending.expires_ms - t) / 1000))
          + " s · chỉ người trên thiết bị trả lời được — trợ lý và client MCP không xác nhận thay";
        askButtons.hidden = !opts.onConfirm;
      } else { askId = null; ask.hidden = true; }

      const said = conversation(t);
      if (changed("chat", said)) {
      chat.textContent = "";
      if (!said.length) chat.appendChild(el("div", { class: "hint", text: "Chưa có gì. Gõ hoặc bấm một lệnh." }));
      for (const line of said) {
        chat.appendChild(el("div", { class: "line" + (line.cls ? " " + line.cls : "") }, [el("b", { text: line.who + ": " }), document.createTextNode(line.text)]));
      }
      }

      const all = stateAt(view.events, Infinity).gates;
      const verdictsFresh = changed("verdicts", [all.length, all.map(function (g) { return g.offset_ms > t; })]);
      if (verdictsFresh) verdicts.textContent = "";
      if (!verdictsFresh) { /* unchanged */ } else {
      if (!all.length) verdicts.appendChild(el("div", { class: "hint", text: "Chưa có lần thẩm định gate nào." }));
      for (const g of all.slice().reverse()) {
        const r = g.result;
        const gateName = g.gate || r.blocked_by || "";
        const confirmed = r.confirmed || [];
        const asking = r.verdict === "BLOCK" && r.action === "ask"
          && (gates[gateName] ? (gates[gateName].on_block.confirms || []).indexOf(r.failed_criterion) >= 0 : true);
        const word = r.verdict === "BLOCK" && asking ? "Chặn · chờ người ở nhà" : (VERDICT[r.verdict] || r.verdict);
        const checks = el("ul", { class: "checks" });
        for (const name in r.evaluations || {}) {
          if (name === "call_source" || name === "call_channel") continue;
          const failed = name === r.failed_criterion;
          const waived = confirmed.indexOf(name) >= 0;
          checks.appendChild(el("li", { class: failed ? "fail" : waived ? "waived" : "pass" }, [
            el("span", { class: "mark", text: failed ? "✗" : waived ? "✓*" : "✓" }),
            document.createTextNode(" " + criterionText(gateName, name) + ": " + yesNo(r.evaluations[name])
              + (waived ? " — người ở nhà đã xác nhận" : "")),
          ]));
        }
        const moved = r.verdict === "ALLOW" ? movedAfter(g.index) : [];
        const outcome = r.verdict === "ALLOW"
          ? "Đã làm" + (moved.length ? ": " + moved.join(", ") : ".")
          : r.verdict === "REJECTED" ? "Lệnh không hợp lệ, không tới gate: " + (r.reason || "")
          : (r.reason === "criterion_unavailable" ? "Thiếu dữ kiện (cảm biến không đọc được) nên chặn. " : "")
            + (asking ? "Đang hỏi người ở nhà (khung vàng ở trên). “" + (r.message || "") + "”"
              : r.action === "ask" ? "Không hỏi ai: “" + criterionText(gateName, r.failed_criterion) + "” không phải điều người ở nhà xác nhận thay được, nên chặn hẳn."
              : (ON_BLOCK[r.action] || "") + (r.message ? " “" + r.message + "”" : ""));
        const card = el("div", { class: "verdict " + r.verdict + (asking ? " ASK" : "") + (g.offset_ms > t ? " future" : "") }, [
          el("div", { class: "v-head" }, [el("span", { class: "badge", text: word }),
            el("span", { class: "v-what", text: g.call ? actionText(g.call.name) : gateName })]),
          el("div", { class: "v-who", text: "Ai yêu cầu: " + (g.call && g.call.source ? (SOURCE[g.call.source] || g.call.source) : "—")
            + (g.call && g.call.confirmed_by ? " · người ở nhà đã đồng ý" : "") + " · gate " + gateName }),
          checks.childNodes.length ? el("div", { class: "v-label", text: "Gate xét:" }) : null,
          checks.childNodes.length ? checks : null,
          el("div", { class: "v-out", text: outcome }),
        ]);
        card.addEventListener("click", function () { view.follow = false; view.t = g.offset_ms; render(); });
        verdicts.appendChild(card);
      }
      }

      count.textContent = "(" + view.events.length + ")";
      let current = -1;
      view.events.forEach(function (e, i) { if (e.offset_ms <= t) current = i; });
      const rowsFresh = changed("rows", [view.events.length, current]);
      if (rowsFresh) rows.textContent = "";
      if (rowsFresh) view.events.forEach(function (e, i) {
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
