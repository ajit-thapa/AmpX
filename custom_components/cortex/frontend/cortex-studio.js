/* Cortex Energy Studio. Vanilla custom element: live power flow, rate ribbon,
   24h chart, plan, history & analytics and house status. No build step, no libraries. */
const C = {
  solar: "#F5B800", grid: "#6F7BE8", batt: "#2DB67C", ev: "#3E9BEA", home: "#FF5401",
  peak: "#E5484D", shoulder: "#2DB67C", off_peak: "#F5A524",
};
const ICONS = {
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  grid: '<path d="M12 2 7 22M12 2l5 20M8.5 8h7M6.5 14h11M9 8l6 6M15 8l-6 6"/>',
  battery: '<rect x="2.5" y="7" width="16" height="10" rx="2.5"/><path d="M21.5 11v2M6.5 10v4M10.5 10v4"/>',
  car: '<path d="M4 16v-3l2-5h12l2 5v3M4 16h16M4 16v3h3v-3M20 16v3h-3v-3"/><circle cx="8" cy="13" r="1"/><circle cx="16" cy="13" r="1"/>',
  home: '<path d="m3 11 9-8 9 8M5 10v10h14V10M10 20v-6h4v6"/>',
  chart: '<path d="M4 20V11M10 20V4M16 20v-9M22 20H2"/>',
  plan: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/>',
  spark: '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
  bell: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7M10 20a2 2 0 0 0 4 0"/>',
  moon: '<path d="M20 14A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 10z"/>',
  arrow: '<path d="M7 17 17 7M8 7h9v9"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  send: '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v5M8 22h8"/>',
  star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
};
const icon = (n, cls = "ic") => `<svg viewBox="0 0 24 24" class="${cls}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n]}</svg>`;
const bigNum = (v, d = 1, unit = "") => {
  if (v === null || v === undefined || Number.isNaN(v)) return `<span class="n">–</span>`;
  const [i, f] = Math.abs(v).toFixed(d).split(".");
  return `<span class="n">${v < 0 ? "−" : ""}${i}${f ? `<span class="dec">.${f}</span>` : ""}</span>${unit ? `<span class="u">${unit}</span>` : ""}`;
};
const fmtH = h => (h === null || h === undefined || !Number.isFinite(h) ? "–" : h >= 1 ? Math.floor(h) + "h " + String(Math.round((h % 1) * 60)).padStart(2, "0") + "m" : Math.max(Math.round(h * 60), 1) + "m");
const NS = "http://www.w3.org/2000/svg";
const N = "sensor.neovolt_neovoltlocal_";
const E = {
  bt: [["Voltage", N + "battery_voltage", "mdi"], ["Current", N + "battery_current"], ["Power", N + "battery_power"], ["Health (SOH)", N + "combined_battery_soh"],
       ["Max cell temp", N + "battery_max_cell_temperature"], ["Min cell temp", N + "battery_min_cell_temperature"], ["Max cell V", N + "battery_max_cell_voltage"], ["Min cell V", N + "battery_min_cell_voltage"]],
  health: [["Inverter", N + "inverter_fault"], ["Battery", N + "battery_fault"], ["Protection", N + "battery_protection"], ["Grid freq", N + "grid_frequency"], ["Meter", "sensor.home_energy_purchased_today"]],
  life: [["Lifetime charged", N + "battery_charge_energy"], ["Lifetime discharged", N + "battery_discharge_energy"]],
  flows: [["Solar", N + "combined_pv_power", "#f2c744"], ["House", N + "combined_house_load", "#e8833a"], ["Battery", N + "combined_battery_power", "#7f5af0"], ["Grid", N + "grid_total_active_power", "#e45649"]],
  day: [["Solar", "sensor.neovolt_online_pv_generated_today", "#f2c744"], ["Import", "sensor.neovolt_online_grid_import_today", "#e45649"], ["Export", "sensor.neovolt_online_feed_in_today", "#50a14f"]],
  cyc: [["Charged", "sensor.neovolt_online_battery_charged_today", "#26a69a"], ["Discharged", "sensor.neovolt_online_battery_discharged_today", "#7e57c2"]],
  cost: [["Solar sold (period)", "sensor.agl_solar_sold_this_period"], ["Supply charge", "sensor.agl_supply_charge"], ["Recent cost total", "sensor.globird_energy_balance"],
         ["GloBird invoice", "sensor.globird_energy_latest_invoice"], ["Export total (period)", "sensor.agl_solar_feed_in_credit"], ["Consumption (period)", "sensor.agl_consumption_this_period"]],
  autos: ["automation.agl_plan_shoulder_grid_top_up_battery", "automation.agl_plan_evening_export_17_00_21_00_28c_fit", "automation.agl_plan_ev_charge_in_shoulder_window", "automation.agl_plan_ev_plug_in_gate_10_00_14_00_only", "automation.agl_plan_peak_guard_ev_and_battery"],
  nums: [["Battery capacity (kWh)", "input_number.system_battery_capacity"], ["BYD capacity (kWh)", "input_number.system_ev_battery_capacity"], ["PV capacity (kW)", "input_number.system_solar_inverter_size"],
         ["Wall connector (kW)", "input_number.system_ev_charger_power"], ["Round-trip efficiency", "input_number.system_battery_round_trip_efficiency"], ["Low-solar line (kWh)", "input_number.agl_low_solar_threshold"],
         ["BYD target SOC (%)", "input_number.byd_target_soc"], ["Shoulder (c)", "input_number.agl_plan_shoulder"], ["Off-peak (c)", "input_number.agl_plan_off_peak"],
         ["Peak high season (c)", "input_number.agl_plan_high_season_peak"], ["Peak low season (c)", "input_number.agl_plan_low_season_peak"], ["FiT evening (c)", "input_number.agl_plan_fit_evening"],
         ["FiT morning (c)", "input_number.agl_plan_fit_morning"], ["FiT off-peak (c)", "input_number.agl_plan_fit_off_peak"], ["Supply (c/day)", "input_number.agl_plan_supply_charge"]],
};
const EV = {
  img: "/api/image/serve/3215d9a31830fbbdda209ef2fddeae4b/original",
  soc: "sensor.byd_sealion_7_battery_level", power: "sensor.byd_sealion_7_battery_power",
  plug: "binary_sensor.byd_sealion_7_plug", charging: "binary_sensor.byd_sealion_7_charging",
  online: "binary_sensor.byd_sealion_7_online", remain: "sensor.byd_sealion_7_charge_remaining_time",
  locked: "binary_sensor.byd_sealion_7_locked", loc: "device_tracker.byd_sealion_7_location",
  full: "switch.byd_sealion_7_charge_to_full", sched: "switch.byd_sealion_7_schedule_enabled",
  daily: "switch.byd_sealion_7_repeat_daily", start: "time.byd_sealion_7_start_time", end: "time.byd_sealion_7_end_time",
  go: "button.byd_sealion_7_start_charging", poll: "button.byd_sealion_7_force_poll",
  cap: "input_number.system_ev_battery_capacity", kw: "input_number.system_ev_charger_power",
  wcStatus: "sensor.tesla_wall_connector_status", wcPower: "sensor.tesla_wall_connector_total_power",
  wcSession: "sensor.tesla_wall_connector_session_energy", wcV: "sensor.tesla_wall_connector_grid_voltage",
  wcA: ["sensor.tesla_wall_connector_phase_a_current", "sensor.tesla_wall_connector_phase_b_current", "sensor.tesla_wall_connector_phase_c_current"],
  wcT: [["Handle", "sensor.tesla_wall_connector_handle_temperature"], ["MCU", "sensor.tesla_wall_connector_mcu_temperature"], ["PCB", "sensor.tesla_wall_connector_pcb_temperature"]],
};
// Daily energy sensors reset at midnight and keep only sum/state statistics, so day
// totals are rebuilt from hourly "state" deltas (also gives tariff-accurate costs).
const AN = { pv: "sensor.neovolt_online_pv_generated_today", imp: "sensor.neovolt_online_grid_import_today", exp: "sensor.neovolt_online_feed_in_today",
  chg: "sensor.neovolt_online_battery_charged_today", dis: "sensor.neovolt_online_battery_discharged_today", load: "sensor.neovolt_online_consumed_today",
  evKwh: "sensor.tesla_wall_connector_energy" };
const AN_POWER = { pv: N + "combined_pv_power", load: N + "combined_house_load", grid: N + "grid_total_active_power", soc: N + "combined_battery_soc" };
let _tzf = null, _tzName = null;
function tzParts(ms, tz) {
  if (!_tzf || _tzName !== tz) { _tzName = tz; _tzf = new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23", weekday: "short" }); }
  const o = {}; _tzf.formatToParts(new Date(ms)).forEach(x => { o[x.type] = x.value; });
  return { key: `${o.year}-${o.month}-${o.day}`, hour: Number(o.hour) % 24, month: Number(o.month), biz: o.weekday !== "Sat" && o.weekday !== "Sun" };
}
function tariffAt(h, r) {
  let per = "off_peak", imp = r.off;
  if (h.hour >= 10 && h.hour < 14) { per = "shoulder"; imp = r.shoulder; }
  else if (h.hour >= 16 && h.hour < 20 && h.biz) { per = "peak"; imp = [11, 12, 1, 2, 3].includes(h.month) ? r.hi : r.lo; }
  const fit = h.hour >= 17 && h.hour < 21 ? r.fitE : h.hour >= 7 && h.hour < 8 ? r.fitM : r.fitO;
  return { per, imp, fit };
}
const dayLabel = (key, long) => long ? key.slice(8) + "/" + key.slice(5, 7) : new Date(key + "T12:00").toLocaleDateString([], { weekday: "short" });
const TABS = [["now", "Now", "bolt"], ["ev", "EV", "car"], ["battery", "Battery", "battery"], ["plan", "Plan", "plan"], ["analytics", "Analytics", "chart"], ["house", "Home", "home"], ["assistant", "Assistant", "spark"], ["settings", "Settings", "gear"]];
const BG_PATHS = ["/local/simple_dreams_light.jpg", "/local/images/simple_dreams_light.jpg", "/local/backgrounds/simple_dreams_light.jpg", "/local/cortex/simple_dreams_light.jpg"];
const CAT_ICON = { fact: "📌", preference: "⭐", person: "👤", place: "📍", routine: "🔁", note: "📝" };

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fx = (v, n = 1) => (v === null || v === undefined || Number.isNaN(v) ? "–" : Number(v).toFixed(n));

class CortexStudio extends HTMLElement {
  constructor() {
    super();
    try { this._tab = localStorage.getItem("cortex-studio-tab") || "now"; } catch (e) { this._tab = "now"; }
    if (this._tab === "history") this._tab = "analytics";
    if (!TABS.some(t => t[0] === this._tab)) this._tab = "now";
    this._series = null;
    this._seriesAt = 0;
  }
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._build();
      this._load();
      this._timer = setInterval(() => this._load(), 30000);
    } else if (this._data && this._tab === "now" && Date.now() - (this._lastPaint || 0) > 1500) {
      this._lastPaint = Date.now();
      this._paintLive();
    } else if (this._data && this._tab === "battery" && Date.now() - (this._lastPaint || 0) > 1500) {
      this._lastPaint = Date.now();
      this._battWidgets();
    } else if (this._data && this._tab === "ev" && Date.now() - (this._lastPaint || 0) > 1500) {
      this._lastPaint = Date.now();
      this._paintEv();
    }
  }
  set narrow(v) { this._narrow = v; }
  disconnectedCallback() { clearInterval(this._timer); }

  // ---- data -----------------------------------------------------------
  async _load() {
    try {
      this._data = await this._hass.callWS({ type: "cortex/overview" });
    } catch (e) {
      this._root.querySelector("#view").textContent = "Cortex is not loaded: " + (e.message || e.code);
      return;
    }
    const a = this._root.activeElement;
    if (a && (a.tagName === "INPUT" || a.tagName === "SELECT")) return;
    const mt = this._root.querySelector("#mtext");
    if (this._tab === "assistant" && mt && mt.value) return;
    const ci = this._root.querySelector("#chatin");
    if (this._tab === "assistant" && (this._chatBusy || (ci && ci.value))) return;
    this._render();
    if (this._tab === "now" && Date.now() - this._seriesAt > 300000) this._loadSeries();
    if (this._tab === "now") this._energy().then(() => this._tab === "now" && this._paintSplit()).catch(() => {});
    if (this._tab === "ev" && Date.now() - (this._evAt || 0) > 300000) this._loadEv();
    if (this._tab === "plan" && Date.now() - (this._earnAt || 0) > 120000) this._loadEarn();
    if ((this._tab === "battery" || this._tab === "analytics") && Date.now() - ((this._moreAt || {})[this._tab] || 0) > 300000) this._loadMore(this._tab);
  }

  _kw(id, invert = false) {
    const st = id && this._hass.states[id];
    if (!st) return null;
    const v = parseFloat(st.state);
    if (Number.isNaN(v)) return null;
    const unit = (st.attributes.unit_of_measurement || "kW").toLowerCase();
    const kw = unit === "w" ? v / 1000 : unit === "mw" ? v * 1000 : v;
    return invert ? -kw : kw;
  }
  _num(id) {
    const st = id && this._hass.states[id];
    const v = st ? parseFloat(st.state) : NaN;
    return Number.isNaN(v) ? null : v;
  }

  /** Live flows in kW. Conventions: grid + = import, battery + = charging. */
  _flows() {
    const s = this._data.studio || {};
    const pv = Math.max(this._kw(s.pv) ?? 0, 0);
    const grid = this._kw(s.grid, s.grid_invert) ?? 0;
    const batt = this._kw(s.battery, s.battery_invert) ?? 0;
    const ev = Math.max(this._kw(s.ev) ?? 0, 0);
    const load = Math.max(pv + grid - batt, 0);
    return { pv, grid, batt, ev, load, home: Math.max(load - ev, 0) };
  }

  async _loadSeries() {
    const s = this._data.studio || {};
    const ids = [s.pv, s.grid, s.battery, s.ev, s.soc].filter(Boolean);
    if (!ids.length) return;
    const end = new Date(), start = new Date(end.getTime() - 24 * 3600 * 1000);
    try {
      const res = await this._hass.callWS({
        type: "history/history_during_period", start_time: start.toISOString(), end_time: end.toISOString(),
        entity_ids: ids, minimal_response: true, no_attributes: false, significant_changes_only: false,
      });
      const N = 288, step = (end - start) / N;
      const resample = (id, invert, scale) => {
        const rows = res[id] || [];
        const unit = ((rows[0] && rows[0].a && rows[0].a.unit_of_measurement) || "kW").toLowerCase();
        const k = scale === false ? 1 : unit === "w" ? 0.001 : 1;
        const out = new Array(N).fill(null);
        let j = 0, last = null;
        for (let i = 0; i < N; i++) {
          const t = start.getTime() + i * step;
          while (j < rows.length && (rows[j].lu ?? rows[j].lc) * 1000 <= t) {
            const v = parseFloat(rows[j].s); last = Number.isNaN(v) ? last : v * k; j++;
          }
          out[i] = last === null ? null : (invert ? -last : last);
        }
        return out;
      };
      const pv = resample(s.pv, false), grid = resample(s.grid, s.grid_invert),
        batt = resample(s.battery, s.battery_invert), ev = resample(s.ev, false),
        soc = resample(s.soc, false, false);
      const load = pv.map((p, i) => (p === null ? null : Math.max(p + (grid[i] ?? 0) - (batt[i] ?? 0), 0)));
      this._series = { start, end, pv, grid, batt, ev, soc, load };
      this._seriesAt = Date.now();
      if (this._tab === "now") this._paintChart();
    } catch (e) { /* history is optional */ }
  }

  // ---- frame ----------------------------------------------------------
  _build() {
    this._root = this.attachShadow({ mode: "open" });
    this._root.innerHTML = `<style>${CSS}</style>
      <div class="bg" aria-hidden="true"></div>
      <header class="top">
        <div class="brand"><img class="logo" src="/cortex_static/icon.svg" alt="" width="40" height="40"><div><h1>Cortex</h1><div class="sub" id="greet"></div></div></div>
        <nav id="tabs" aria-label="Sections"></nav>
        <div class="tools"><span id="clock" class="clock"></span>
          <button class="ib" id="chatbtn" aria-label="Ask Cortex" title="Ask Cortex">${icon("chat")}</button>
          <button class="ib" id="bell" aria-label="Alerts" title="Alerts">${icon("bell")}<i class="badge" id="badge" hidden></i></button>
          <button class="ib" id="theme" aria-label="Switch theme"></button></div>
      </header>
      <main id="view" aria-live="polite"><div class="grid"><div class="card wide skel"></div><div class="card w8 skel tall"></div><div class="card w4 skel tall"></div></div></main>`;
    // Optional photo from HA local storage (/config/www). First path that loads wins.
    const bg = this._root.querySelector(".bg");
    const tryBg = i => { if (i >= BG_PATHS.length) return; const im = new Image();
      im.onload = () => { bg.style.backgroundImage = `url(${BG_PATHS[i]})`; bg.classList.add("on"); }; im.onerror = () => tryBg(i + 1); im.src = BG_PATHS[i]; };
    tryBg(0);
    const nav = this._root.querySelector("#tabs");
    nav.innerHTML = TABS.map(([k, l, ic]) => `<button data-tab="${k}" aria-label="${l}">${icon(ic)}<span>${l}</span></button>`).join("");
    nav.querySelectorAll("button").forEach(b => b.onclick = () => this._go(b.dataset.tab));
    this._root.querySelector("#bell").onclick = () => this._go("house");
    this._root.querySelector("#chatbtn").onclick = () => { this._go("assistant"); const i = this._root.querySelector("#chatin"); if (i) i.focus(); };
    this._root.querySelector("#theme").onclick = () => {
      const next = { auto: "light", light: "dark", dark: "auto" }[this._themePref()];
      try { localStorage.setItem("cortex-studio-theme", next); } catch (e) { /* ignore */ }
      this._applyTheme(); this._paintChart();
    };
    this._applyTheme();
    this._w = 0;
    if (window.ResizeObserver) { this._ro = new ResizeObserver(() => { const w = this.clientWidth; if (Math.abs(w - this._w) > 24) { this._w = w; if (this._tab === "now") { this._paintChart(); this._paintLive(); } } }); this._ro.observe(this); }
  }
  _themePref() { try { return localStorage.getItem("cortex-studio-theme") || "auto"; } catch (e) { return "auto"; } }
  _applyTheme() {
    const pref = this._themePref(), hd = this._hass && this._hass.themes ? this._hass.themes.darkMode : undefined;
    const dark = pref === "dark" || (pref === "auto" && (hd !== undefined ? !!hd : !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches)));
    this.setAttribute("data-theme", dark ? "dark" : "light");
    const b = this._root && this._root.querySelector("#theme");
    if (b) { b.innerHTML = icon(dark ? "sun" : "moon") + (pref === "auto" ? '<i class="auto">A</i>' : ""); b.title = "Theme: " + pref; b.setAttribute("aria-label", "Theme: " + pref + ". Click to change"); }
  }
  _go(tab) {
    this._tab = tab;
    try { localStorage.setItem("cortex-studio-tab", tab); } catch (e) { /* ignore */ }
    this._render();
    if (tab === "now" && !this._series) this._loadSeries();
    if (tab === "now") this._energy().then(() => this._tab === "now" && this._paintSplit()).catch(() => {});
    if (tab === "ev" && Date.now() - (this._evAt || 0) > 300000) this._loadEv();
    if (tab === "plan" && Date.now() - (this._earnAt || 0) > 120000) this._loadEarn();
    if ((tab === "battery" || tab === "analytics") && Date.now() - ((this._moreAt || {})[tab] || 0) > 300000) this._loadMore(tab);
  }

  _render() {
    const d = this._data; if (!d) return;
    this._pc = {};
    const r = this._root;
    r.querySelectorAll("#tabs button").forEach(b => { b.classList.toggle("on", b.dataset.tab === this._tab); if (b.dataset.tab === this._tab) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    const now = new Date(), h = now.getHours();
    r.querySelector("#clock").textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    r.querySelector("#greet").innerHTML = `${h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"}<span class="gdate"> · ${now.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}</span>`;
    const alerts = (d.health || []).length + ((d.security || { ok: true }).ok ? 0 : ((d.security.issues || []).length || 1)), bd = r.querySelector("#badge");
    bd.hidden = !alerts; bd.textContent = alerts > 9 ? "9+" : String(alerts || "");
    const view = r.querySelector("#view");
    view.innerHTML = ({ now: () => this._viewNow(), ev: () => this._viewEv(), battery: () => this._viewBattery(), analytics: () => this._viewAnalytics(), plan: () => this._viewPlan(), house: () => this._viewHouse(), assistant: () => this._viewAssistant(), settings: () => this._viewSettings() })[this._tab]();
    view.querySelectorAll("[data-go]").forEach(b => b.onclick = () => this._go(b.dataset.go));
    ({ now: () => { this._paintLive(); this._paintChart(); }, ev: () => { this._wireEv(); this._paintEv(); }, battery: () => { this._battWidgets(); this._paintMore("battery"); this._wireCtl(); }, analytics: () => this._paintMore("analytics"), plan: () => { this._wirePlan(); this._wireExtras(); this._paintEarn(); }, house: () => this._wireHouse(), assistant: () => { this._wireChat(); this._wireAssistant(); }, settings: () => this._wireSettings() })[this._tab]();
  }
  /** Write HTML only when it changed, so animations and focus survive the 1.5 s live refresh. */
  _paintTo(sel, html) {
    const el = this._root.querySelector(sel); if (!el) return;
    this._pc = this._pc || {};
    if (this._pc[sel] === html) return;
    this._pc[sel] = html; el.innerHTML = html;
  }
  _socNow() { const s = this._data.studio || {}; return this._num(s.soc) ?? this._num(N + "combined_battery_soc") ?? this._num(N + "battery_soc"); }

  // ---- NOW ------------------------------------------------------------
  /** Today's money, indicative: current rates applied to today's kWh. */
  _money() {
    const s = this._data.studio || {}, e = this._data.energy, n = id => (id ? this._num(id) : null);
    const gen = n(s.day_pv) ?? n(AN.pv) ?? 0, exp = n(s.day_export) ?? n(AN.exp) ?? 0, imp = n(s.day_import) ?? n(AN.imp) ?? 0, used = n(s.day_load) ?? n(AN.load);
    const p = (e.import_rate ?? 0) / 100, f = (e.feed_in_rate ?? 0) / 100, self = Math.max(gen - exp, 0);
    return { gen, exp, imp, used, self, p, f, avoided: self * p, earned: exp * f, spent: imp * p, net: self * p + exp * f - imp * p,
      ss: used && used > 0.5 ? Math.max(0, Math.min(100, (1 - imp / used) * 100)) : null };
  }
  _insight() {
    const d = this._data, sec = d.security || { ok: true, issues: [] }, last = ((d.autopilot || {}).decisions || [])[0];
    if ((d.health || []).length) return { tone: "warn", ic: "bell", title: d.health.length > 1 ? `${d.health.length} things need attention` : "Needs attention", text: d.health[0] + (d.health.length > 1 ? ` and ${d.health.length - 1} more` : ""), go: "house" };
    if (!sec.ok) return { tone: "warn", ic: "bell", title: "Security", text: (sec.issues || [])[0] || "Check doors and locks", go: "house" };
    const tip = (d.advice || []).find(t => t.level !== "info");
    if (tip) return { tone: tip.level === "warn" ? "warn" : "act", ic: tip.level === "warn" ? "bell" : "bolt", title: tip.text, text: tip.why || "Cortex suggests", go: "now" };
    if (last) return { tone: "ok", ic: "spark", title: `Autopilot: ${last.window === "topup" ? "top-up" : "evening export"} ${last.do ? "go" : "hold"}`, text: last.reason || "", go: "plan" };
    return { tone: "ok", ic: "check", title: "All systems normal", text: "Nothing needs your attention right now.", go: null };
  }
  _kpisHtml() {
    const m = this._money(), e = this._data.energy, $ = v => (v < 0 ? "−$" : "$") + Math.abs(v).toFixed(2);
    const k = (ic, col, label, val, sub) => `<div class="kpi"><span class="kic" style="--k:${col}">${icon(ic)}</span><div class="kbody"><div class="klab">${label}</div><div class="kval">${val}</div><div class="ksub">${sub}</div></div></div>`;
    const fc = e.pv_today;
    return k("sun", C.solar, "Solar today", bigNum(m.gen, 1, "kWh"), fc === null || fc === undefined ? "no forecast" : `forecast ${fx(fc, 0)} kWh`)
      + k("home", C.home, "Home used", bigNum(m.used, 1, "kWh"), m.ss === null ? "–" : `${fx(m.ss, 0)}% self-sufficient`)
      + k("grid", C.grid, "From grid", bigNum(m.imp, 1, "kWh"), `${fx(m.exp, 1)} kWh sent back`)
      + k("bolt", m.net >= 0 ? C.shoulder : C.peak, "Net today", `<span class="n">${m.net < 0 ? "−" : ""}$${Math.abs(m.net).toFixed(2).replace(/\.(\d+)$/, '<span class="dec">.$1</span>')}</span>`, `${$(m.avoided)} saved · ${$(m.earned)} earned`);
  }
  _viewNow() {
    const d = this._data, e = d.energy, ins = this._insight(), ap = d.autopilot || { mode: "off" };
    const mode = { auto: ["Autopilot", C.shoulder], shadow: ["Advising", C.off_peak], off: ["Manual", "#8a8279"] }[ap.mode] || ["Manual", "#8a8279"];
    const hours = d.schedule.map(r => {
      const p = r.import <= 12 ? "shoulder" : r.import >= 40 ? "peak" : "off_peak";
      return `<i class="${r.hour === d.hour ? "cur" : ""}" style="background:${C[p]}" title="${r.hour}:00 · ${r.import}c import · ${r.feed_in}c feed-in"></i>`;
    }).join("");
    const go = (t, label) => `<button class="go" data-go="${t}" aria-label="${label}">${icon("arrow")}</button>`;
    return `<section class="grid now">
      <div class="card wide insight ${ins.tone}"><span class="iic">${icon(ins.ic)}</span>
        <div class="itx"><b>${esc(ins.title)}</b><span>${esc(ins.text)}</span></div>
        <button class="pill btn" style="--pc:${mode[1]}" data-go="battery" aria-label="Open battery control">${mode[0]}</button>
        ${ins.go ? `<button class="go" data-go="${ins.go}" aria-label="Details">${icon("arrow")}</button>` : ""}</div>
      <div class="card wide kpis" id="kpis"></div>
      <div class="card w8 hero"><div class="chead"><h2>Energy flow</h2><span class="chip live"><i></i>Live</span></div><div id="flow"></div></div>
      <div class="card w4 side">
        <div class="chead"><h2>Battery</h2>${go("battery", "Open battery")}</div><div id="arc"></div>
        <div class="sep"></div>
        <div class="chead"><h2>Tariff now</h2>${go("plan", "Open plan")}</div>
        <div class="ratenow"><span class="pill" style="--pc:${C[e.period]}">${esc(e.period.replace("_", " "))}</span><div class="kval">${bigNum(e.import_rate, 2, "c/kWh")}</div></div>
        <div class="ribbon" title="Import rate by hour">${hours}</div>
        <div class="ticks"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
        <div class="nextline" id="nextline"></div><div class="prog"><i id="np"></i></div></div>
      <div class="card wide"><div class="chead"><h2>Last 24 hours</h2><span class="legend"><b style="color:${C.solar}">●</b> Solar <b style="color:${C.home}">●</b> Home <b style="color:${C.grid}">●</b> Grid <b style="color:${C.batt}">●</b> Battery %</span></div>
        <div id="chart" class="chart"><div class="muted">Loading history…</div></div></div>
      <div class="card w8"><div class="chead"><h2>Where energy went today</h2>${go("analytics", "Open analytics")}</div><div id="mix"></div></div>
      <div class="card w4"><div class="chead"><h2>Solar</h2>${go("analytics", "Open analytics")}</div><div id="sol"></div></div>
      <div class="card w8"><div class="chead"><h2>Cortex suggests</h2>${go("assistant", "Ask Cortex")}</div>${this._adviceHtml()}</div>
      <div class="card w4"><div class="chead"><h2>Solar shortfall</h2>${go("plan", "Open plan")}</div><div id="short"></div></div>
      <div class="card wide"><div class="chead"><h2>Energy storage</h2>${go("battery", "Open battery")}</div>
        <div class="estore"><div class="esub"><div data-bhost="house"></div></div><div class="esub"><div data-bhost="ev"></div></div></div>
        <div class="muted" style="margin-top:10px">${esc(e.storage_summary || "")}</div></div>
    </section>`;
  }

  _paintLive() {
    const f = this._flows();
    this._paintTo("#kpis", this._kpisHtml());
    this._paintTo("#flow", flowSvg(f, { soc: this._socNow(), compact: this.clientWidth < 640 }));
    this._paintArc(f);
    this._battWidgets();
    this._paintVisuals();
  }
  _paintArc(f) {
    const soc = this._socNow(), cap = this._num("input_number.system_battery_capacity") ?? 50, floor = this._num("number.neovolt_online_minimum_soc");
    const chg = f.batt > 0.05, dis = f.batt < -0.05;
    let eta = "";
    if (soc !== null) {
      if (chg && soc < 99.5) eta = `Full in ${fmtH((100 - soc) / 100 * cap / f.batt)}`;
      else if (dis) eta = `${fmtH(Math.max(soc - (floor ?? 0), 0) / 100 * cap / -f.batt)} to reserve`;
    }
    const kwh = soc === null ? "" : `${fx(soc * cap / 100, 1)} of ${fx(cap, 0)} kWh`;
    this._paintTo("#arc", arcGauge(soc, { state: chg ? `Charging ${fx(f.batt)} kW` : dis ? `Discharging ${fx(-f.batt)} kW` : "Standby", sub: [eta, kwh].filter(Boolean).join(" · "), color: levelColor(soc),
      marks: [{ pct: floor, color: C.peak, label: "Reserve" }] }));
  }

  _paintVisuals() {
    const r = this._root, e = this._data.energy, d = this._data, m = this._money();
    this._paintTo("#sol", solarBars(m.gen, e.pv_today, e.pv_tomorrow, e.low_solar, e.solar_day));
    if (this._en) this._paintSplit(); else this._paintTo("#mix", mixBar(m.self, m.exp, m.imp));
    this._paintTo("#short", shortGauge(e.pv_shortfall));
    // time to the next rate change
    const now = Date.now(), next = new Date(e.next_change).getTime(), sch = d.schedule || [];
    let h = d.hour, cur = (sch.find(x => x.hour === h) || {}).import, back = 0;
    while (back < 24 && (sch.find(x => x.hour === (h + 23) % 24) || {}).import === cur) { h = (h + 23) % 24; back++; }
    const st = new Date(); st.setHours(h, 0, 0, 0); if (st.getTime() > now) st.setDate(st.getDate() - 1);
    const frac = Math.max(0, Math.min((now - st.getTime()) / Math.max(next - st.getTime(), 1), 1)), mins = Math.max(Math.round((next - now) / 60000), 0);
    const nl = r.querySelector("#nextline"), np = r.querySelector("#np"), col = C[e.next_period] || C.ev;
    if (nl) nl.innerHTML = `Next: <b style="color:${col}">${esc(e.next_period.replace("_", " "))}</b> at ${new Date(next).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · in ${fmtH(mins / 60)}`;
    if (np) { np.style.width = frac * 100 + "%"; np.style.background = col; }
  }

  _paintChart() {
    const el = this._root.querySelector("#chart"), s = this._series;
    if (!el || !s) return;
    const W = Math.max(Math.round(el.clientWidth) || 900, 320), H = W < 560 ? 220 : 260, L = 40, R = 40, T = 12, B = 26, N = 288;
    const x = i => L + (i / (N - 1)) * (W - L - R);
    const vals = [...s.pv, ...s.load, ...s.grid].filter(v => v !== null);
    const hiP = Math.max(1, ...vals) * 1.1, loP = Math.min(0, ...vals) * 1.1;
    const clampY = y => Math.max(T, Math.min(H - B, y));
    const yP = v => clampY(T + (1 - (v - loP) / (hiP - loP || 1)) * (H - T - B));
    const ySoc = v => clampY(T + (1 - v / 100) * (H - T - B));
    const line = (arr, y, color, w = 2, dash = "") => {
      let dstr = "", pen = false;
      arr.forEach((v, i) => { if (v === null) { pen = false; return; } dstr += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); pen = true; });
      return `<path d="${dstr}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round" ${dash ? `stroke-dasharray="${dash}"` : ""}/>`;
    };
    let ad = "";
    s.pv.forEach((v, i) => { ad += (i ? "L" : "M") + x(i).toFixed(1) + " " + yP(Math.max(v ?? 0, 0)).toFixed(1); });
    const area = `<path d="${ad}L${x(N - 1)} ${yP(0)}L${x(0)} ${yP(0)}Z" fill="url(#pvg)"/>`;
    let grid = "";
    for (let k = 0; k <= 4; k++) {
      const v = loP + ((hiP - loP) * k) / 4, y = yP(v);
      grid += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" class="gl"/><text x="${L - 8}" y="${y + 3}" text-anchor="end" class="ax">${v.toFixed(v >= 10 ? 0 : 1)}</text>`;
    }
    for (let k = 0; k <= 100; k += 50) grid += `<text x="${W - R + 8}" y="${ySoc(k) + 3}" class="ax">${k}%</text>`;
    let hrs = "";
    for (let h = 0; h <= 24; h += W < 560 ? 6 : 3) {
      const t = new Date(s.start.getTime() + (h / 24) * (s.end - s.start)), i = (h / 24) * (N - 1);
      hrs += `<text x="${x(i)}" y="${H - 6}" text-anchor="middle" class="ax">${t.toLocaleTimeString([], { hour: "numeric" })}</text>`;
    }
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="24 hour energy chart"><defs><linearGradient id="pvg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${C.solar}" stop-opacity=".45"/><stop offset="1" stop-color="${C.solar}" stop-opacity=".02"/></linearGradient></defs>
      ${grid}${hrs}<line x1="${L}" x2="${W - R}" y1="${yP(0)}" y2="${yP(0)}" class="zl"/>
      ${area}${line(s.pv, yP, C.solar, 2)}${line(s.load, yP, C.home, 2.4)}${line(s.grid, yP, C.grid, 1.6, "4 4")}${line(s.soc, ySoc, C.batt, 2.4)}
      <line class="cur" x1="0" x2="0" y1="${T}" y2="${H - B}" style="display:none"/></svg><div class="tip" hidden></div>`;
    const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), cur = el.querySelector(".cur");
    const show = ev => {
      const rc = svg.getBoundingClientRect(), px = (ev.clientX - rc.left) * (W / rc.width);
      const i = Math.round(Math.max(0, Math.min(1, (px - L) / (W - L - R))) * (N - 1)), cx = x(i);
      cur.setAttribute("x1", cx); cur.setAttribute("x2", cx); cur.style.display = "";
      const t = new Date(s.start.getTime() + (i / (N - 1)) * (s.end - s.start)), v = (a, u, d = 1) => (a[i] === null || a[i] === undefined ? "–" : a[i].toFixed(d) + u);
      tip.innerHTML = `<b>${t.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</b><span><i style="background:${C.solar}"></i>Solar ${v(s.pv, " kW")}</span><span><i style="background:${C.home}"></i>Home ${v(s.load, " kW")}</span><span><i style="background:${C.grid}"></i>Grid ${v(s.grid, " kW")}</span><span><i style="background:${C.batt}"></i>Battery ${v(s.soc, "%", 0)}</span>`;
      tip.hidden = false; const tw = tip.offsetWidth; tip.style.left = Math.max(0, Math.min(cx / W * rc.width + 12, rc.width - tw)) + "px";
    };
    svg.onpointermove = show; svg.onpointerdown = show;
    svg.onpointerleave = () => { tip.hidden = true; cur.style.display = "none"; };
  }

  // ---- EV -------------------------------------------------------------
  async _loadEv() {
    this._evAt = Date.now();
    const end = new Date(), start = new Date(end.getTime() - 24 * 3600 * 1000);
    try {
      const res = await this._hass.callWS({
        type: "history/history_during_period", start_time: start.toISOString(), end_time: end.toISOString(),
        entity_ids: [EV.soc, EV.power], minimal_response: true, no_attributes: true, significant_changes_only: false,
      });
      const N = 144, step = (end - start) / N;
      const rs = id => {
        const rows = res[id] || [], out = new Array(N).fill(null); let j = 0, last = null;
        for (let i = 0; i < N; i++) {
          const t = start.getTime() + i * step;
          while (j < rows.length && (rows[j].lu ?? rows[j].lc) * 1000 <= t) { const v = parseFloat(rows[j].s); if (!Number.isNaN(v)) last = v; j++; }
          out[i] = last;
        }
        return out;
      };
      this._evSeries = { start, end, soc: rs(EV.soc), power: rs(EV.power) };
      if (this._tab === "ev") this._paintEv();
    } catch (e) { /* optional */ }
  }

  _evPlan() {
    const d = this._data, e = d.energy, sch = d.schedule || [];
    const soc = this._num(EV.soc) ?? 0, cap = this._num(EV.cap) ?? 82.5, kw = this._num(EV.kw) ?? 7.4;
    const target = this._evTarget ?? 80;
    const need = Math.max(target - soc, 0) * cap / 100;
    const f = this._flows(), surplus = Math.max(f.pv - f.home - Math.max(f.batt, 0), 0);
    const cheapest = sch.length ? Math.min(...sch.map(r => r.import)) : e.import_rate;
    const cheapHours = sch.filter(r => r.import === cheapest).map(r => r.hour);
    const now = e.import_rate;
    return { soc, cap, kw, target, need, hours: need / kw, now, cheapest, cheapHours,
      costNow: need * now / 100, costCheap: need * cheapest / 100, surplus, cover: Math.min(surplus / kw, 1) };
  }

  _viewEv() {
    const wcA = EV.wcA.map((id, i) => `<div class="phase"><span>${"ABC"[i]}</span><div><i data-a="${i}"></i></div><b data-av="${i}">–</b></div>`).join("");
    const temps = EV.wcT.map(([n], i) => `<div class="phase"><span>${n}</span><div><i data-t="${i}"></i></div><b data-tv="${i}">–</b></div>`).join("");
    return `<section class="grid">
      <div class="card evhero wide"><div class="stage">
          <div class="carbox"><div class="carpic"><img src="${EV.img}" alt="BYD Sealion 7" onerror="this.style.display='none'">${carOverlay()}</div>
            <div class="carglow" id="ev-glow"></div>
            <div class="cartop"><span class="carname">BYD Sealion 7</span><span id="ev-state" class="pill"></span></div>
            <div class="carbar"><div class="barbg"><i id="ev-fill"></i><u id="ev-mark"></u></div>
              <div class="barlbl"><b id="ev-big"></b><span id="ev-sub" class="muted"></span></div></div></div>
          <div class="evside"><div class="stats" id="ev-stats"></div></div></div></div>
      <div class="card w6"><h2>Charge planner <span class="muted">drag to set target</span></h2>
        <div class="big" id="ev-target-big"></div>
        <input type="range" id="ev-target" min="20" max="100" step="1" value="${this._evTarget ?? 80}" class="slider">
        <div class="seg" style="margin:8px 0">${[60, 80, 90, 100].map(v => `<button data-tgt="${v}">${v}%</button>`).join("")}</div>
        <div id="ev-plan"></div></div>
      ${this._evCtlCard()}
      <div class="card wide"><h2>Last 24 hours <span class="legend"><b style="color:${C.ev}">■</b> charge level <b style="color:${C.solar}">━</b> power</span></h2>
        <div class="chart"><svg id="ev-chart" viewBox="0 0 900 220" preserveAspectRatio="none"></svg></div></div>
      <div class="card wide"><h2>Tesla Wall Connector <span id="wc-state" class="pill"></span></h2>
        <div class="stats" id="wc-stats"></div>
        <div class="muted" style="margin-top:10px">Phase current (A)</div>${wcA}
        <div class="muted" style="margin-top:10px">Temperature (°C)</div>${temps}</div>
    </section>`;
  }

  _evCtlCard() {
    return `<div class="card w6"><h2>EV charging controls</h2>
        <div class="row"><span>Start charging now</span><button id="ev-go">Start</button></div>
        <div class="row"><span>Refresh car data</span><button id="ev-poll">Poll</button></div>
        <label class="row"><span>Charge to full</span><input type="checkbox" class="sw" data-sw="full"></label>
        <label class="row"><span>Schedule</span><input type="checkbox" class="sw" data-sw="sched"></label>
        <label class="row"><span>Repeat daily</span><input type="checkbox" class="sw" data-sw="daily"></label>
        <div class="row"><span>Window</span><span><input type="time" id="ev-start"> – <input type="time" id="ev-end"></span></div>
        <div class="seg" style="margin-top:8px"><button id="ev-cheap" title="Set the schedule to the cheapest hours">Cheapest hours</button><button id="ev-sun" title="Set the schedule to 10:00–14:00 shoulder">Shoulder 10–14</button></div>
        <div class="muted" id="ev-ctlmsg" style="margin-top:6px"></div></div>`;
  }
  _wireEv() {
    const q = s => this._root.querySelector(s);
    const call = async (dom, svc, data) => {
      try { await this._hass.callService(dom, svc, data); q("#ev-ctlmsg").textContent = ""; }
      catch (e) { q("#ev-ctlmsg").textContent = "Failed: " + (e.message || e); }
    };
    const slider = q("#ev-target");
    slider.oninput = () => { this._evTarget = Number(slider.value); this._paintEv(); };
    this._root.querySelectorAll("[data-tgt]").forEach(b => b.onclick = () => { this._evTarget = Number(b.dataset.tgt); slider.value = this._evTarget; this._paintEv(); });
    this._wireEvCtl(call);
  }
  _wireEvCtl(call) {
    const q = s => this._root.querySelector(s);
    if (!call) call = (dom, svc, data) => this._hass.callService(dom, svc, data).then(() => { const m = q("#ev-ctlmsg"); if (m) m.textContent = ""; }, e => { const m = q("#ev-ctlmsg"); if (m) m.textContent = "Failed: " + (e.message || e); });
    q("#ev-go").onclick = () => call("button", "press", { entity_id: EV.go });
    q("#ev-poll").onclick = () => call("button", "press", { entity_id: EV.poll });
    this._root.querySelectorAll("[data-sw]").forEach(c => c.onchange = () =>
      call("switch", c.checked ? "turn_on" : "turn_off", { entity_id: EV[c.dataset.sw] }));
    const setT = (id, v) => v && call("time", "set_value", { entity_id: id, time: v.length === 5 ? v + ":00" : v });
    q("#ev-start").onchange = e => setT(EV.start, e.target.value);
    q("#ev-end").onchange = e => setT(EV.end, e.target.value);
    const preset = async (a, b) => {
      await call("time", "set_value", { entity_id: EV.start, time: a });
      await call("time", "set_value", { entity_id: EV.end, time: b });
      await call("switch", "turn_on", { entity_id: EV.sched });
    };
    q("#ev-sun").onclick = () => preset("10:00:00", "14:00:00");
    q("#ev-cheap").onclick = () => {
      const h = this._evPlan().cheapHours;
      if (!h.length) return;
      const pad = n => String(n % 24).padStart(2, "0") + ":00:00";
      preset(pad(Math.min(...h)), pad(Math.max(...h) + 1));
    };
  }

  _paintEv() {
    const q = s => this._root.querySelector(s); if (!q("#ev-state")) return;
    const st = id => this._hass.states[id];
    const on = id => st(id) && st(id).state === "on";
    const home = st(EV.loc) && st(EV.loc).state === "home";
    const pl = this._evPlan();
    const charging = on(EV.charging), plugged = on(EV.plug);
    const kwNow = (this._num(EV.power) ?? 0) / (((st(EV.power) || {}).attributes || {}).unit_of_measurement === "W" ? 1000 : 1);
    const pill = q("#ev-state");
    pill.textContent = charging ? "Charging" : plugged ? "Plugged in" : home ? "Home" : "Away";
    pill.style.setProperty("--pc", charging ? C.shoulder : plugged ? C.off_peak : "#8a8279");
    this._battWidgets();
    const fill = q("#ev-fill"); if (fill) {
      fill.style.width = Math.max(0, Math.min(pl.soc, 100)) + "%"; fill.style.backgroundColor = charging ? C.shoulder : C.ev;
      q("#ev-mark").style.left = pl.target + "%";
      q("#ev-big").textContent = Math.round(pl.soc) + "%";
      q("#ev-sub").textContent = `${fx(pl.soc * pl.cap / 100, 1)} of ${fx(pl.cap, 0)} kWh · target ${pl.target}%` + (charging ? ` · ⚡ charging ${fx(kwNow)} kW` : plugged ? " · plugged in" : "");
      q("#ev-glow").className = "carglow" + (plugged || charging ? " on" : "") + (charging ? " chg" : "");
      fill.classList.toggle("chg", charging); const cb = q(".carbox"); cb.classList.toggle("chg", charging); cb.classList.toggle("plug", plugged || charging); carOverlaySet(cb, pl.soc, plugged, charging);
    }
    q("#ev-stats").innerHTML = [
      ["Power", charging ? fx(kwNow) + " kW" : "–", C.ev], ["Time left", (st(EV.remain) || {}).state && st(EV.remain).state !== "unknown" ? st(EV.remain).state : "–", C.shoulder],
      ["Solar surplus", fx(pl.surplus) + " kW", C.solar], ["Locked", on(EV.locked) ? "no" : "yes", on(EV.locked) ? C.peak : C.shoulder],
    ].map(([l, v, col]) => `<div class="stat" style="border-color:${col}"><span class="muted">${l}</span><b>${v}</b></div>`).join("");
    // planner
    q("#ev-target-big").innerHTML = `${pl.target}% <small>needs ${fx(pl.need, 1)} kWh · ${fx(pl.hours, 1)} h at ${fx(pl.kw)} kW</small>`;
    const solarPct = Math.round(pl.cover * 100);
    q("#ev-plan").innerHTML = `
      <div class="row"><span>Cost at today's ${fx(pl.now, 1)}c</span><b>$${fx(pl.costNow, 2)}</b></div>
      <div class="row"><span>Cost at cheapest ${fx(pl.cheapest, 1)}c${pl.cheapHours.length ? ` (${pl.cheapHours[0]}:00–${pl.cheapHours[pl.cheapHours.length - 1] + 1}:00)` : ""}</span><b class="ok">$${fx(pl.costCheap, 2)}</b></div>
      <div class="row"><span>You save by waiting</span><b>$${fx(pl.costNow - pl.costCheap, 2)}</b></div>
      <div class="row"><span>Solar covers right now</span><b>${solarPct}%</b></div>
      <div class="hbar" style="grid-template-columns:1fr"><div><i style="width:${solarPct}%;background:${C.solar}"></i></div></div>`;
    this._paintEvCtl();
    // wall connector
    const wc = st(EV.wcStatus), veh = on("binary_sensor.tesla_wall_connector_vehicle_connected");
    const wp = q("#wc-state"); wp.textContent = wc ? wc.state.replace(/_/g, " ") : "–"; wp.style.setProperty("--pc", veh ? C.shoulder : "#8a8279");
    const wcKw = (this._kw(EV.wcPower) ?? 0);
    q("#wc-stats").innerHTML = [["Power", fx(wcKw) + " kW"], ["Session", fx(this._num(EV.wcSession), 1) + " kWh"], ["Grid", fx(this._num(EV.wcV), 0) + " V"], ["Vehicle", veh ? "connected" : "no"]]
      .map(([l, v]) => `<div class="stat" style="border-color:${C.ev}"><span class="muted">${l}</span><b>${v}</b></div>`).join("");
    EV.wcA.forEach((id, i) => { const a = this._num(id) ?? 0; q(`[data-a="${i}"]`).style.width = Math.min(a / 32 * 100, 100) + "%"; q(`[data-a="${i}"]`).style.background = C.ev; q(`[data-av="${i}"]`).textContent = fx(a, 0); });
    EV.wcT.forEach(([, id], i) => { const t = this._num(id) ?? 0; q(`[data-t="${i}"]`).style.width = Math.min(t / 90 * 100, 100) + "%"; q(`[data-t="${i}"]`).style.background = t > 70 ? C.peak : t > 55 ? C.off_peak : C.shoulder; q(`[data-tv="${i}"]`).textContent = fx(t, 0); });
    this._paintEvChart();
  }

  _paintEvCtl() {
    const q = s => this._root.querySelector(s), st = id => this._hass.states[id], on = id => st(id) && st(id).state === "on";
    if (!q("#ev-start")) return;
    // controls (skip while the user is editing)
    this._root.querySelectorAll("[data-sw]").forEach(c => { c.checked = on(EV[c.dataset.sw]); });
    const hm = id => ((st(id) || {}).state || "").slice(0, 5);
    const s1 = q("#ev-start"), s2 = q("#ev-end");
    if (this._root.activeElement !== s1) s1.value = hm(EV.start);
    if (this._root.activeElement !== s2) s2.value = hm(EV.end);
  }

  _paintEvChart() {
    const svg = this._root.querySelector("#ev-chart"), s = this._evSeries; if (!svg || !s) return;
    const W = 900, H = 220, L = 34, R = 34, T = 10, B = 24, N = s.soc.length;
    const x = i => L + (i / (N - 1)) * (W - L - R);
    const maxP = Math.max(...s.power.filter(v => v !== null), 1) * 1.1;
    const ys = v => T + (1 - v / 100) * (H - T - B), yp = v => T + (1 - v / maxP) * (H - T - B);
    const line = (arr, fn) => arr.map((v, i) => v === null ? "" : (i && arr[i - 1] !== null ? "L" : "M") + x(i).toFixed(1) + " " + fn(v).toFixed(1)).join("");
    const soc = line(s.soc, ys);
    let grid = "";
    for (let k = 0; k <= 4; k++) { const v = k * 25; grid += `<line x1="${L}" x2="${W - R}" y1="${ys(v)}" y2="${ys(v)}" stroke="currentColor" opacity=".1"/><text x="${L - 4}" y="${ys(v) + 3}" text-anchor="end" class="ax">${v}%</text>`; }
    let hrs = "";
    for (let k = 0; k <= 24; k += 4) { const t = new Date(s.start.getTime() + k / 24 * (s.end - s.start)); hrs += `<text x="${x(Math.min(k / 24 * (N - 1), N - 1))}" y="${H - 6}" text-anchor="middle" class="ax">${t.getHours()}:00</text>`; }
    svg.innerHTML = `${grid}${hrs}<path d="${soc} L${x(N - 1)} ${ys(0)} L${x(0)} ${ys(0)} Z" fill="${C.ev}" opacity=".15"/>
      <path d="${soc}" fill="none" stroke="${C.ev}" stroke-width="2.5"/><path d="${line(s.power, yp)}" fill="none" stroke="${C.solar}" stroke-width="2"/>
      <text x="${W - R + 4}" y="${yp(maxP) + 10}" class="ax">${maxP.toFixed(0)}</text>`;
  }

  _battWidgets() {
    const r = this._root, f = this._flows(), s = this._data.studio || {};
    r.querySelectorAll("[data-bhost]").forEach(h => { if (!h.querySelector(".batt")) h.innerHTML = battHTML(h.dataset.bhost, h.dataset.bhost === "house" ? "Home ESS" : "BYD Sealion 7"); });
    const house = r.querySelector('[data-b="house"]'), ev = r.querySelector('[data-b="ev"]');
    if (house) {
      const soc = this._num(s.soc) ?? this._num(N + "combined_battery_soc") ?? this._num(N + "battery_soc"), cap = this._num("input_number.system_battery_capacity") ?? 50;
      const floor = this._num("number.neovolt_online_minimum_soc");
      battSet(house, { pct: soc, charging: f.batt > 0.05, discharging: f.batt < -0.05,
        sub: `${fx(soc === null ? null : soc * cap / 100, 1)} of ${fx(cap, 0)} kWh · ` + (f.batt > 0.05 ? "▼ charging " + fx(f.batt) + " kW" : f.batt < -0.05 ? "▲ discharging " + fx(-f.batt) + " kW" : "idle"),
        marks: [{ pct: floor, color: C.peak, label: "Reserve" }] });
    }
    if (ev) {
      const soc = this._num(EV.soc) ?? this._num(s.ev_soc), cap = this._num(EV.cap) ?? 82.5;
      const chg = this._hass.states[EV.charging] && this._hass.states[EV.charging].state === "on";
      const kw = f.ev;
      battSet(ev, { pct: soc, charging: chg || kw > 0.05, plugged: !!this._data.energy.ev_plugged || (this._hass.states[EV.plug] || {}).state === "on",
        sub: `${fx(soc === null ? null : soc * cap / 100, 1)} of ${fx(cap, 0)} kWh · ` + (chg || kw > 0.05 ? "⚡ charging " + fx(kw) + " kW" : (this._data.energy.ev_plugged ? "plugged in" : "unplugged")),
        marks: [{ pct: this._tab === "ev" && this._evTarget !== undefined ? this._evTarget : this._num("input_number.byd_target_soc"), color: C.home, label: "Target" }] });
    }
  }

  // ---- generic data loaders -------------------------------------------
  async _hist(ids, hours, n = 144, scale = {}) {
    const end = new Date(), start = new Date(end.getTime() - hours * 3600000);
    const res = await this._hass.callWS({ type: "history/history_during_period", start_time: start.toISOString(), end_time: end.toISOString(),
      entity_ids: ids, minimal_response: true, no_attributes: true, significant_changes_only: false }).catch(() => ({}));
    const step = (end - start) / n, out = { start, end };
    ids.forEach(id => {
      const rows = res[id] || [], a = new Array(n).fill(null); let j = 0, last = null;
      for (let i = 0; i < n; i++) {
        const t = start.getTime() + i * step;
        while (j < rows.length && (rows[j].lu ?? rows[j].lc) * 1000 <= t) { const v = parseFloat(rows[j].s); if (!Number.isNaN(v)) last = v * (scale[id] ?? 1); j++; }
        a[i] = last;
      }
      out[id] = a;
    });
    return out;
  }
  _rates() {
    const n = (id, d) => this._num(id) ?? d;
    return { shoulder: n("input_number.agl_plan_shoulder", 11.11), off: n("input_number.agl_plan_off_peak", 32.12), hi: n("input_number.agl_plan_high_season_peak", 41.91),
      lo: n("input_number.agl_plan_low_season_peak", 42.416), fitE: n("input_number.agl_plan_fit_evening", 28), fitM: n("input_number.agl_plan_fit_morning", 3),
      fitO: n("input_number.agl_plan_fit_off_peak", 3), supply: n("input_number.agl_plan_supply_charge", 166.617) };
  }
  /** Loads 30 days of hourly energy deltas + daily power/SOC stats + EV energy (cached 5 min). */
  async _energy() {
    if (this._en && Date.now() - this._en.at < 300000) return this._en;
    if (this._enP) return this._enP;
    this._enP = (async () => {
      const tz = (this._hass.config && this._hass.config.time_zone) || undefined, s = (this._data && this._data.studio) || {};
      const ids = { pv: s.day_pv || AN.pv, imp: s.day_import || AN.imp, exp: s.day_export || AN.exp, chg: AN.chg, dis: AN.dis, load: s.day_load || AN.load };
      const start = new Date(Date.now() - 32 * 86400000).toISOString();
      const ws = extra => this._hass.callWS({ type: "recorder/statistics_during_period", start_time: start, ...extra }).catch(() => ({}));
      const [hr, dayP, evD] = await Promise.all([
        ws({ statistic_ids: [...new Set(Object.values(ids))], period: "hour", types: ["state"] }),
        ws({ statistic_ids: Object.values(AN_POWER), period: "day", types: ["mean", "min", "max"] }),
        ws({ statistic_ids: [AN.evKwh], period: "day", types: ["change"] })]);
      const hours = new Map();
      Object.keys(ids).forEach(k => {
        const rows = (hr[ids[k]] || []).slice().sort((a, b) => new Date(a.start) - new Date(b.start)), last = {};
        rows.forEach(r => {
          const t = +new Date(r.start), v = r.state;
          if (v === null || v === undefined) return;
          const p = tzParts(t, tz), prev = last[p.key];
          let d = prev === undefined ? v : v - prev;
          if (d < 0) d = v;           // counter reset
          if (d > 40) d = 0;          // implausible hour: glitch
          last[p.key] = v;
          let h = hours.get(t);
          if (!h) { h = { t, ...p, pv: 0, imp: 0, exp: 0, chg: 0, dis: 0, load: 0 }; hours.set(t, h); }
          h[k] = d;
        });
      });
      const byDay = (res, id, f) => { const m = {}; (res[id] || []).forEach(r => { m[tzParts(+new Date(r.start), tz).key] = f(r); }); return m; };
      const power = {};
      Object.entries(AN_POWER).forEach(([k, id]) => { power[k] = byDay(dayP, id, r => r); });
      this._en = { at: Date.now(), tz, ids, hours: [...hours.values()].sort((a, b) => a.t - b.t), power, ev: byDay(evD, AN.evKwh, r => r.change) };
      this._enP = null;
      return this._en;
    })();
    try { return await this._enP; } finally { this._enP = null; }
  }
  /** Daily + hourly rows with costs. Today is topped up from the live counters. */
  _enCompute() {
    const en = this._en; if (!en) return null;
    const r = this._rates(), hrs = en.hours.map(h => ({ ...h })), now = Date.now(), cur = Math.floor(now / 3600000) * 3600000, pc = tzParts(now, en.tz);
    ["pv", "imp", "exp", "chg", "dis", "load"].forEach(k => {
      const live = this._num(en.ids[k]); if (live === null) return;
      const have = hrs.filter(h => h.key === pc.key).reduce((a, h) => a + h[k], 0);
      if (live > have + 0.005) {
        let h = hrs.find(x => x.t === cur);
        if (!h) { h = { t: cur, ...pc, pv: 0, imp: 0, exp: 0, chg: 0, dis: 0, load: 0 }; hrs.push(h); }
        h[k] += live - have;
      }
    });
    const days = new Map();
    hrs.forEach(h => {
      const t = tariffAt(h, r); h.per = t.per; h.rate = t.imp; h.fit = t.fit;
      h.used = h.load > 0 ? h.load : Math.max(h.pv + h.imp + h.dis - h.exp - h.chg, 0);
      h.cImp = h.imp * h.rate / 100; h.cExp = h.exp * h.fit / 100; h.cBase = h.used * h.rate / 100;
      let d = days.get(h.key);
      if (!d) { d = { key: h.key, pv: 0, imp: 0, exp: 0, chg: 0, dis: 0, used: 0, cImp: 0, cExp: 0, cBase: 0, per: { shoulder: { kwh: 0, cost: 0 }, peak: { kwh: 0, cost: 0 }, off_peak: { kwh: 0, cost: 0 } }, expEve: 0, cExpEve: 0 }; days.set(h.key, d); }
      ["pv", "imp", "exp", "chg", "dis", "used", "cImp", "cExp", "cBase"].forEach(k => { d[k] += h[k]; });
      d.per[h.per].kwh += h.imp; d.per[h.per].cost += h.cImp;
      if (h.hour >= 17 && h.hour < 21) { d.expEve += h.exp; d.cExpEve += h.cExp; }
    });
    const list = [...days.values()].sort((a, b) => a.key.localeCompare(b.key)).slice(-30);
    list.forEach(d => {
      d.supply = r.supply / 100; d.net = d.cImp - d.cExp + d.supply; d.saved = d.cBase - (d.cImp - d.cExp);
      d.ss = d.used > 0.5 ? Math.max(0, Math.min(100, (1 - d.imp / d.used) * 100)) : null;
      d.sc = d.pv > 0.5 ? Math.max(0, Math.min(100, (1 - d.exp / d.pv) * 100)) : null;
      d.ev = en.ev[d.key] ?? null;
      const g = k => (en.power[k] || {})[d.key] || null;
      d.pvMax = g("pv") ? g("pv").max : null; d.loadMax = g("load") ? g("load").max : null; d.gridMax = g("grid") ? g("grid").max : null; d.gridMin = g("grid") ? g("grid").min : null;
      d.soc = g("soc") ? { min: g("soc").min, mean: g("soc").mean, max: g("soc").max } : null;
    });
    return { days: list, hrs, rates: r };
  }
  _st(id) { return this._hass.states[id]; }
  _tile(label, id, color) {
    const st = this._st(id), v = st ? st.state : "–", u = st && st.attributes.unit_of_measurement ? " " + st.attributes.unit_of_measurement : "";
    const num = parseFloat(v), show = Number.isNaN(num) ? v : (Math.abs(num) >= 100 ? num.toFixed(0) : num.toFixed(Math.abs(num) < 10 ? 2 : 1)).replace(/\.?0+$/, "");
    return `<div class="stat" style="border-color:${color || C.ev}"><span class="muted">${esc(label)}</span><b>${esc(show)}<small>${esc(u)}</small></b></div>`;
  }
  async _loadMore(tab) {
    if (tab === "battery") {
      const f = E.flows.map(x => x[1]);
      const [fl, soc, tmp] = await Promise.all([this._hist(f, 24, 144), this._hist([N + "combined_battery_soc"], 48, 144), this._hist([N + "battery_max_cell_temperature", N + "battery_min_cell_temperature"], 24, 144)]);
      this._bt = { fl, soc, tmp };
    } else if (tab === "analytics") {
      const pvId = "sensor.sungrow_pv", fc = "sensor.pv_forecast_power_now", sun = "sensor.sun_solar_elevation";
      const [, sol, rate] = await Promise.all([this._energy().catch(() => null), this._hist([pvId, fc, sun], 36, 216, { [fc]: 0.001 }),
        this._hist(["sensor.agl_plan_import_rate", "sensor.agl_plan_feed_in_rate"], 48, 96)]);
      this._an = { sol, rate };
    }
    this._moreAt = { ...(this._moreAt || {}), [tab]: Date.now() };
    if (this._tab === tab) this._paintMore(tab);
  }

  // ---- BATTERY ---------------------------------------------------------
  _viewBattery() {
    const soc = this._num(N + "combined_battery_soc") ?? this._num(N + "battery_soc");
    const cap = this._num("input_number.system_battery_capacity") ?? 50;
    return `<section class="grid">
      ${this._ctlCards()}
      <div class="card w4"><h2>Home ESS</h2><div data-bhost="house"></div>
        <div class="stats" style="margin-top:12px">${E.life.map(([l, id]) => this._tile(l, id, C.batt)).join("")}</div></div>
      <div class="card w4"><h2>Monitor</h2><div class="stats">${E.bt.map(([l, id]) => this._tile(l, id, C.batt)).join("")}</div></div>
      <div class="card w4"><h2>System health</h2><div class="stats">${E.health.map(([l, id]) => {
        const st = this._st(id), ok = st && /^(ok|normal|none|0)$/i.test(st.state);
        return this._tile(l, id, st && (ok || !isNaN(parseFloat(st.state))) ? C.shoulder : C.peak); }).join("")}</div></div>
      <div class="card wide"><h2>Power flows today (W)</h2><div id="bt-flows"></div></div>
      <div class="card w6"><h2>Charge level, 48 h (%)</h2><div id="bt-soc"></div></div>
      <div class="card w6"><h2>Cell temperatures, 24 h (°C)</h2><div id="bt-tmp"></div></div>
    </section>`;
  }

  // ---- BATTERY CONTROL: automatic or manual ----------------------------
  _ctlMode() {
    const c = this._data.control || {};
    return c.autopilot_mode === "auto" ? "auto" : c.autopilot_mode === "shadow" ? "advise" : (c.auto_topup || c.auto_export ? "timers" : "manual");
  }
  /** Neovolt / inverter output settings, found by name so no entity ids are hard-coded. */
  _neoControls() {
    const dom = e => e.split(".")[0], re = /feed.?in|cutoff|dispatch|export limit|active power|discharg|charg\w*\s+(start|end)|minimum soc|grid power offset|pv switch/i, own = /^(neovolt|local\b|inverter|sg10rs)/i;
    return Object.entries(this._hass.states).filter(([id, st]) => st && ["switch", "number", "select", "time"].includes(dom(id))
      && own.test((st.attributes || {}).friendly_name || "") && re.test(st.attributes.friendly_name || "") && st.state !== "unavailable")
      .map(([id, st]) => ({ ...st, entity_id: id, attributes: st.attributes }))
      .sort((a, b) => (a.attributes.friendly_name || "").localeCompare(b.attributes.friendly_name || ""));
  }
  _ctlCards() {
    const d = this._data, c = d.control; if (!c) return "";
    const mode = this._ctlMode(), manual = mode === "manual";
    const MODES = [["manual", "✋", "Manual", "You decide. Cortex never starts or stops the battery."],
      ["timers", "⏱", "Timers", "Fixed windows: grid top-up in the shoulder, export in the evening."],
      ["advise", "💡", "Advise", "Autopilot plans each window and tells you. It takes no action."],
      ["auto", "🤖", "Autopilot", "Your local AI plans inside hard limits, then acts by itself."]];
    const dm = c.mode_entity && this._hass.states[c.mode_entity], dispatch = dm ? dm.state : "–";
    const dcol = /discharge/i.test(dispatch) ? C.off_peak : /charge/i.test(dispatch) ? C.grid : C.shoulder;
    const ap = d.autopilot || { decisions: [] }, last = (ap.decisions || [])[0];
    const slider = (k, label, min, max, step, unit) => `<div class="lim"><div class="limh"><span>${label}</span><b><output data-out="${k}">${c[k]}</output> ${unit}</b></div>
      <input type="range" class="slider" data-opt="${k}" value="${c[k]}" min="${min}" max="${max}" step="${step}"></div>`;
    const tiles = MODES.map(([k, ic, t, sub]) => `<button class="mt ${k === mode ? "on" : ""} ${k === "manual" ? "man" : "aut"}" data-cm="${k}"><span class="mti">${ic}</span><b>${t}</b><span class="muted">${sub}</span></button>`).join("");
    const manualPane = `<h3>Manual dispatch</h3>
      <div class="mbtns"><button class="mb exp" id="m-exp"><span>⬆</span>Discharge to grid<small>${c.export_kw} kW down to ${c.export_floor}%</small></button>
        <button class="mb top" id="m-top"><span>⬇</span>Charge from grid<small>${c.topup_kw} kW up to 100%</small></button>
        <button class="mb stp" id="m-stop"><span>■</span>Stop<small>back to normal</small></button></div>`;
    const autoPane = `<h3>Latest Autopilot decision</h3>${last ? `<div class="dd"><b>${last.window === "topup" ? "Top-up" : "Export"} ${last.do ? "✅ go" : "⏸ hold"}</b><span>${esc(last.reason || "")}</span><span class="muted">${esc(last.result || "")}</span></div>` : '<div class="muted">No decision yet.</div>'}
      <div class="seg" style="margin-top:8px"><button id="ap-topup">Plan top-up</button><button id="ap-export">Plan export</button></div>
      ${mode === "advise" || mode === "auto" ? `<label class="row" style="margin-top:6px"><span>Ask the local AI first</span>${this._toggle(`data-optb="use_ai"`, c.use_ai)}</label>` : ""}`;
    return `<div class="card wide ctl"><h2>Battery control <span class="pill" style="--pc:${dcol}">dispatch: ${esc(dispatch)}</span></h2>
      <div class="mtiles">${tiles}</div>
      <div class="ctl2">
        <div><h3>Limits <span class="muted">used by timers, Autopilot and manual dispatch</span></h3>
          ${slider("export_kw", "Export power", 0.5, 10, 0.5, "kW")}${slider("export_floor", "Export floor, battery stops at", 10, 90, 1, "%")}${slider("topup_kw", "Top-up power", 0.5, 10, 0.5, "kW")}
          <div class="evfirst"><label class="row"><span><b>EV first</b><span class="muted">While the EV charges, the battery feeds the car first. It exports until the daily supply charge is covered, then only ${Math.round((c.ev_trickle_kw ?? 0.2) * 1000)} W to cover the inverter.</span></span>${this._toggle(`data-optev="1"`, c.ev_priority)}</label>
            <div class="row"><span class="muted">Supply charge today</span><b>$${fx(d.energy.export_earned, 2)} earned · ${d.energy.supply_left > 0 ? "$" + fx(d.energy.supply_left, 2) + " to go" : "covered ✓"}</b></div>
            ${d.energy.ev_guard ? `<div class="evnote">${icon("car")}<span>${esc(d.energy.ev_guard)}</span></div>` : ""}</div></div>
        <div>${manual ? manualPane : autoPane}</div></div>
      <div class="toast" id="ctl-msg"></div></div>
      ${this._neoCard(manual, mode)}`;
  }
  _toggle(attrs, on, dis = false) { return `<label class="tg"><input type="checkbox" ${attrs} ${on ? "checked" : ""}${dis ? " disabled" : ""}><i></i></label>`; }
  _neoCard(manual, mode) {
    const group = n => /dispatch/i.test(n) ? "Dispatch" : /feed.?in/i.test(n) ? "Grid feed-in" : /cutoff|minimum soc|charg\w*\s+(start|end)/i.test(n) ? "Battery limits" : "Inverter";
    const order = ["Grid feed-in", "Dispatch", "Battery limits", "Inverter"], groups = {};
    const short = n => { const t = n.replace(/^(neovolt online|neovolt|local|inverter|sg10rs \(local\)|sg10rs)\s+/i, ""); return t.charAt(0).toUpperCase() + t.slice(1); };
    for (const st of this._neoControls()) {
      const id = st.entity_id, a = st.attributes, dm = id.split(".")[0], fn = a.friendly_name || id;
      const w = dm === "switch" ? this._toggle(`data-ctl="${id}"`, st.state === "on")
        : dm === "number" ? `<div class="nstep"><button data-step="-1" data-for="${id}">−</button><input type="number" data-ctl="${id}" value="${esc(st.state)}" step="${a.step || "any"}" min="${a.min ?? ""}" max="${a.max ?? ""}"><button data-step="1" data-for="${id}">+</button>${a.unit_of_measurement ? `<span class="muted">${esc(a.unit_of_measurement)}</span>` : ""}</div>`
        : dm === "select" ? `<select data-ctl="${id}">${(a.options || []).map(o => `<option${o === st.state ? " selected" : ""}>${esc(o)}</option>`).join("")}</select>`
        : `<input type="time" data-ctl="${id}" value="${esc(String(st.state).slice(0, 5))}">`;
      (groups[group(fn)] = groups[group(fn)] || []).push(`<div class="srow"><span>${esc(short(fn))}</span>${w}</div>`);
    }
    const blocks = order.filter(g => groups[g]).map(g => `<div class="grp"><h3>${g}</h3>${groups[g].join("")}</div>`).join("");
    const label = { timers: "Timers", advise: "Advise", auto: "Autopilot" }[mode];
    return `<div class="card wide"><h2>Neovolt output settings</h2>
      ${manual ? "" : `<div class="lockbar"><span>🔒 Locked while Cortex runs <b>${label}</b>, so it and your edits don't fight.</span><button id="to-manual">Switch to Manual</button></div>`}
      ${blocks ? `<div class="grps ${manual ? "" : "locked"}">${blocks}</div>` : '<div class="muted">No Neovolt output controls found.</div>'}
      <div class="muted" style="margin-top:8px">These write straight to the Neovolt and inverter entities.</div></div>`;
  }
  _wireCtl() {
    const r = this._root, q = s => r.querySelector(s), msg = (t, bad) => { const m = q("#ctl-msg"); if (m) { m.textContent = t; m.className = "toast" + (t ? " show" : "") + (bad ? " bad" : ""); } };
    const presets = { manual: { autopilot_mode: "off", auto_topup: false, auto_export: false }, timers: { autopilot_mode: "off", auto_topup: true, auto_export: true },
      advise: { autopilot_mode: "shadow", auto_topup: false, auto_export: false }, auto: { autopilot_mode: "auto" } };
    const save = async options => { msg("Saving…"); try { await this._hass.callWS({ type: "cortex/set_options", options }); msg("Saved. Cortex is reloading…"); setTimeout(() => this._load(), 3500); } catch (e) { msg("Failed: " + (e.message || e.code), true); } };
    r.querySelectorAll("[data-cm]").forEach(b => b.onclick = () => { if (b.dataset.cm !== this._ctlMode()) save(presets[b.dataset.cm]); });
    const tm = q("#to-manual"); if (tm) tm.onclick = () => save(presets.manual);
    const key = { export_kw: "export_kw", topup_kw: "topup_kw", export_floor: "export_floor_soc" };
    r.querySelectorAll("[data-opt]").forEach(i => {
      const out = q(`[data-out="${i.dataset.opt}"]`);
      i.oninput = () => { if (out) out.textContent = i.value; };
      i.onchange = () => { const v = parseFloat(i.value); if (!Number.isNaN(v)) save({ [key[i.dataset.opt]]: v }); };
    });
    r.querySelectorAll("[data-optb]").forEach(i => i.onchange = () => save({ autopilot_use_ai: i.checked }));
    r.querySelectorAll("[data-optev]").forEach(i => i.onchange = () => save({ ev_priority: i.checked }));
    const act = async (action, extra) => { msg("Sending…"); try { const x = await this._hass.callWS({ type: "cortex/action", action, ...extra }); msg(typeof x.result === "string" ? x.result : "Done"); } catch (e) { msg("Failed: " + (e.message || e.code), true); } setTimeout(() => this._load(), 1500); };
    const val = k => parseFloat((q(`[data-opt="${k}"]`) || {}).value);
    const click = (id, fn) => { const el = q(id); if (el) el.onclick = fn; };
    click("#m-exp", () => act("manual_export", { kw: val("export_kw"), soc: val("export_floor") }));
    click("#m-top", () => act("manual_topup", { kw: val("topup_kw"), soc: 100 }));
    click("#m-stop", () => act("manual_stop"));
    click("#ap-topup", () => act("autopilot_topup")); click("#ap-export", () => act("autopilot_export"));
    const call = (dm, sv, data) => this._hass.callService(dm, sv, data).then(() => msg("Sent to " + data.entity_id), e => msg("Failed: " + (e.message || e), true));
    r.querySelectorAll("[data-ctl]").forEach(el => el.onchange = () => {
      const id = el.dataset.ctl, dm = id.split(".")[0];
      if (dm === "switch") call("switch", el.checked ? "turn_on" : "turn_off", { entity_id: id });
      else if (dm === "number") { const v = parseFloat(el.value); if (!Number.isNaN(v)) call("number", "set_value", { entity_id: id, value: v }); }
      else if (dm === "select") call("select", "select_option", { entity_id: id, option: el.value });
      else call("time", "set_value", { entity_id: id, time: el.value.length === 5 ? el.value + ":00" : el.value });
    });
    r.querySelectorAll("[data-step]").forEach(b => b.onclick = () => {
      const i = q(`input[data-ctl="${b.dataset.for}"]`); if (!i) return;
      const st = parseFloat(i.step) || 1, v = (parseFloat(i.value) || 0) + st * Number(b.dataset.step);
      i.value = String(Math.round(Math.min(i.max === "" ? Infinity : +i.max, Math.max(i.min === "" ? -Infinity : +i.min, v)) * 1000) / 1000);
      i.dispatchEvent(new Event("change"));
    });
  }

  // ---- ADVICE, SOLAR SPLIT --------------------------------------------
  _adviceHtml() {
    const tips = this._data.advice || [];
    if (!tips.length) return '<div class="muted">No tips right now.</div>';
    const ic = { warn: "bell", act: "bolt", info: "spark" };
    return `<div class="tips">${tips.map(t => `<div class="tip-row ${t.level}"><span class="tic">${icon(ic[t.level] || "spark")}</span><div><b>${esc(t.text)}</b>${t.why ? `<span>${esc(t.why)}</span>` : ""}</div></div>`).join("")}</div>
      <div class="muted" style="margin-top:10px">Instant checks, no AI needed. <button class="ghost" data-go="assistant">Ask Cortex ↗</button></div>`;
  }
  /** Today's energy split by path, rebuilt hour by hour from the meter counters. */
  _splitToday() {
    const c = this._enCompute(); if (!c || !c.hrs.length) return null;
    const key = tzParts(Date.now(), this._en.tz).key, o = { s2h: 0, s2b: 0, s2g: 0, b2h: 0, b2g: 0, g2h: 0, g2b: 0 };
    c.hrs.filter(h => h.key === key).forEach(h => {
      const used = h.used, s2h = Math.min(h.pv, used), r = h.pv - s2h, s2b = Math.min(r, h.chg), s2g = Math.min(r - s2b, h.exp);
      const b2h = Math.min(h.dis, used - s2h), b2g = Math.max(Math.min(h.dis - b2h, h.exp - s2g), 0);
      o.s2h += s2h; o.s2b += s2b; o.s2g += s2g; o.b2h += b2h; o.b2g += b2g;
      o.g2h += Math.max(used - s2h - b2h, 0); o.g2b += Math.max(h.chg - s2b, 0);
    });
    return o;
  }
  _paintSplit() {
    const sp = this._splitToday();
    this._paintTo("#mix", sp ? sankeySvg(sp) : '<div class="muted">Loading today\'s split…</div>');
  }

  // ---- PLAN COMPARISON -------------------------------------------------
  _planCompare(c, keys, n) {
    const hrs = c.hrs.filter(h => keys.has(h.key)), r = c.rates;
    const cur = { id: "current", name: "Current plan (AGL)", current: true, supply: r.supply, cost: h => [tariffAt(h, r).imp, tariffAt(h, r).fit] };
    const mine = (this._data.plans || []).map(p => ({ ...p, cost: h => [planRate(p.import, p.import_default, h), planRate(p.fit, p.fit_default, h)] }));
    const rows = [cur, ...mine].map(p => {
      let imp = 0, exp = 0;
      hrs.forEach(h => { const [a, b] = p.cost(h); imp += h.imp * a / 100; exp += h.exp * b / 100; });
      const supply = (p.supply || 0) / 100 * n, total = imp - exp + supply;
      return { ...p, imp, exp, supply, total, month: total / n * 30 };
    }).sort((a, b) => a.total - b.total);
    const base = rows.find(x => x.current), mx = Math.max(...rows.map(x => Math.abs(x.month)), 1);
    const $ = v => (v < 0 ? "−$" : "$") + Math.abs(v).toFixed(2);
    return `<div class="card wide"><div class="chead"><h2>Plan comparison <span class="muted">your real usage, last ${n} day${n === 1 ? "" : "s"}</span></h2><button class="ghost" data-go="settings">Edit plans ↗</button></div>
      ${rows.map((x, i) => `<div class="pc ${x.current ? "cur" : ""}"><div class="pcn"><b>${esc(x.name)}</b>${i === 0 ? '<span class="pill" style="--pc:' + C.shoulder + '">cheapest</span>' : ""}${x.current ? '<span class="pill" style="--pc:' + C.grid + '">now</span>' : ""}
          <span class="muted">${$(x.imp)} bought · ${$(x.exp)} earned · ${$(x.supply)} supply</span></div>
        <div class="pcb"><i style="width:${Math.max(Math.abs(x.month) / mx * 100, 2)}%;background:${x.current ? C.grid : i === 0 ? C.shoulder : C.off_peak}"></i></div>
        <div class="pcv"><b>${$(x.month)}</b><span class="muted">/month</span>${x.current ? "" : `<span class="${x.total < base.total ? "ok" : "bad"}">${x.total < base.total ? "saves " : "costs "}${$(Math.abs(base.month - x.month))}</span>`}</div></div>`).join("")}
      <div class="muted" style="margin-top:8px">${mine.length ? "Replays each hour you actually bought and sold. A different plan could also change how you would run the battery, so treat this as a guide." : "Add the rates from another retailer's offer in Settings to see what it would have cost you."}</div></div>`;
  }

  // ---- SETTINGS -------------------------------------------------------
  _viewSettings() {
    const d = this._data, st = d.settings || {};
    return `<section class="grid">
      <div class="card wide sethead"><div><h2>Settings</h2><div class="muted">Control your devices and how Cortex runs them. Changes apply straight away.</div></div>
        <nav class="seg jump">${[["set-battery", "Battery"], ["set-ev", "EV"], ["set-devices", "Devices"], ["set-auto", "Automations"], ["set-plans", "Plans"], ["set-ai", "AI"]].map(([id, l]) => `<button data-jump="${id}">${l}</button>`).join("")}</nav></div>
      <div id="set-battery" style="display:contents">${this._ctlCards()}</div>
      <div id="set-ev" style="display:contents">${this._evCtlCard()}
        <div class="card w6"><h2>EV status</h2><div data-bhost="ev"></div></div></div>
      <div class="card wide" id="set-devices"><div class="chead"><h2>Devices</h2><span class="muted">Energy hardware Cortex reads and controls</span></div><div id="devs"><div class="muted">Loading devices…</div></div></div>
      <div id="set-auto" style="display:contents">${this._sysCards()}</div>
      <div class="card wide" id="set-plans"><div class="chead"><h2>Plans to compare</h2><button id="pl-add" class="ghost">+ Add plan</button></div><div id="plans"></div>
        <div class="row"><span class="muted">Rates in cents per kWh, supply in cents per day. Bands are hours from–to; anything outside a band uses the default.</span><button id="pl-save">Save plans</button></div><div class="toast" id="pl-msg"></div></div>
      <div class="card wide" id="set-ai"><h2>AI and chat</h2>
        <div class="row"><span>Answer style</span><span class="seg" id="set-style">${[["brief", "Brief"], ["normal", "Normal"], ["detailed", "Detailed"]].map(([k, l]) => `<button data-style="${k}" class="${(st.style || "brief") === k ? "on" : ""}">${l}</button>`).join("")}</span></div>
        <div class="row col"><span>Household instructions <span class="muted">Cortex follows these in every chat, e.g. "Call me Ajit. Use 24-hour time. Never start the dishwasher after 22:00."</span></span>
          <textarea id="set-notes" maxlength="600" rows="3" placeholder="Anything the assistant should always know or do">${esc(st.notes || "")}</textarea>
          <div class="rowend"><span class="muted" id="notes-n">${(st.notes || "").length}/600</span><button id="set-notes-save">Save instructions</button></div></div>
        <div class="row"><span>Speakers for announcements</span><b class="${st.speakers ? "ok" : "bad"}">${st.speakers ? "set up" : "none chosen"}</b></div>
        <div class="row"><span>Camera vision (AI Task)</span><b class="${st.ai_task ? "ok" : "bad"}">${st.ai_task ? "set up" : "not set up"}</b></div>
        <div class="row"><span>Conversation agent for chat and Autopilot</span><select id="set-agent"><option value="">Home Assistant default</option></select></div>
        <div class="row"><span>AI calls allowed per hour</span><div class="nstep"><input type="number" id="set-aph" min="0" max="120" step="1" value="${st.ai_per_hour ?? 12}"></div></div>
        <div class="row"><span>More options (speakers, quiet hours, sensors)</span><a class="lnk" href="/config/integrations/integration/cortex" target="_top">Open integration ↗</a></div>
        <div class="toast" id="set-msg"></div></div>
    </section>`;
  }
  _wireSettings() {
    const r = this._root, q = s => r.querySelector(s), d = this._data;
    r.querySelectorAll("[data-jump]").forEach(b => b.onclick = () => { const el = q("#" + b.dataset.jump); const t = el && (el.firstElementChild || el); if (t) t.scrollIntoView({ behavior: "smooth", block: "start" }); });
    this._wireCtl(); this._wireEvCtl(); this._paintEvCtl(); this._wireExtras(); this._battWidgets();
    this._loadDevices();
    // plans
    this._plansDraft = this._plansDraft || JSON.parse(JSON.stringify(d.plans || []));
    this._paintPlans();
    q("#pl-add").onclick = () => { this._plansDraft.push({ id: "p" + Date.now().toString(36), name: "New plan", supply: 110, import_default: 30, import: [{ from: 10, to: 14, rate: 15, days: "all" }], fit_default: 5, fit: [] }); this._paintPlans(); };
    q("#pl-save").onclick = async () => {
      const m = q("#pl-msg"), show = (t, bad) => { m.textContent = t; m.className = "toast show" + (bad ? " bad" : ""); };
      try { const x = await this._hass.callWS({ type: "cortex/plans_save", plans: this._plansDraft }); this._data.plans = x.plans; show("Saved. Compare them on the Analytics tab."); }
      catch (e) { show("Failed: " + (e.message || e.code), true); }
    };
    // AI settings
    const msg = (t, bad) => { const m = q("#set-msg"); m.textContent = t; m.className = "toast show" + (bad ? " bad" : ""); };
    const save = async opts => { try { await this._hass.callWS({ type: "cortex/set_options", options: opts }); msg("Saved. Cortex is reloading…"); setTimeout(() => this._load(), 3500); } catch (e) { msg("Failed: " + (e.message || e.code), true); } };
    this._agents().then(list => {
      const sel = q("#set-agent"); if (!sel) return;
      sel.innerHTML = '<option value="">Home Assistant default</option>' + list.map(a => `<option value="${esc(a.id)}"${a.id === (d.settings || {}).agent ? " selected" : ""}>${esc(a.name)}</option>`).join("");
      sel.onchange = () => save({ conversation_agent: sel.value });
    });
    r.querySelectorAll("[data-style]").forEach(b => b.onclick = () => save({ assistant_style: b.dataset.style }));
    const nt = q("#set-notes"); nt.oninput = () => { q("#notes-n").textContent = nt.value.length + "/600"; };
    q("#set-notes-save").onclick = () => save({ assistant_notes: nt.value.trim() });
    q("#set-aph").onchange = e => { const v = parseInt(e.target.value, 10); if (!Number.isNaN(v)) save({ ai_per_hour: v }); };
  }
  _paintPlans() {
    const el = this._root.querySelector("#plans"); if (!el) return;
    const P = this._plansDraft;
    const band = (pi, kind, b, bi) => `<div class="band"><input type="number" min="0" max="23" value="${b.from}" data-b="${pi}:${kind}:${bi}:from" aria-label="From hour"><span>–</span><input type="number" min="1" max="24" value="${b.to}" data-b="${pi}:${kind}:${bi}:to" aria-label="To hour">
      <input type="number" step="0.01" value="${b.rate}" data-b="${pi}:${kind}:${bi}:rate" aria-label="Rate"><span class="muted">c</span>
      <select data-b="${pi}:${kind}:${bi}:days">${["all", "weekday", "weekend"].map(x => `<option${x === (b.days || "all") ? " selected" : ""}>${x}</option>`).join("")}</select>
      <button class="ghost" data-bdel="${pi}:${kind}:${bi}" aria-label="Remove band">✕</button></div>`;
    el.innerHTML = P.length ? P.map((p, i) => `<div class="plan"><div class="planh"><input value="${esc(p.name)}" data-p="${i}:name" aria-label="Plan name" class="pname"><button class="ghost" data-pdel="${i}">Delete</button></div>
      <div class="pgrid"><label>Supply <input type="number" step="0.01" value="${p.supply}" data-p="${i}:supply"> c/day</label>
        <label>Import default <input type="number" step="0.01" value="${p.import_default}" data-p="${i}:import_default"> c</label>
        <label>Feed-in default <input type="number" step="0.01" value="${p.fit_default}" data-p="${i}:fit_default"> c</label></div>
      <div class="bands"><h3>Import bands <button class="ghost" data-badd="${i}:import">+ band</button></h3>${(p.import || []).map((b, j) => band(i, "import", b, j)).join("") || '<div class="muted">Flat rate.</div>'}</div>
      <div class="bands"><h3>Feed-in bands <button class="ghost" data-badd="${i}:fit">+ band</button></h3>${(p.fit || []).map((b, j) => band(i, "fit", b, j)).join("") || '<div class="muted">Flat rate.</div>'}</div></div>`).join("")
      : '<div class="muted">No plans yet. Add one with the rates from a retailer\'s offer (GloBird, Amber, another AGL plan…).</div>';
    const num = v => (v === "" ? 0 : Number(v));
    el.querySelectorAll("[data-p]").forEach(i => i.onchange = () => { const [pi, k] = i.dataset.p.split(":"); P[pi][k] = k === "name" ? i.value : num(i.value); });
    el.querySelectorAll("[data-b]").forEach(i => i.onchange = () => { const [pi, kind, bi, k] = i.dataset.b.split(":"); P[pi][kind][bi][k] = k === "days" ? i.value : num(i.value); });
    el.querySelectorAll("[data-pdel]").forEach(b => b.onclick = () => { P.splice(Number(b.dataset.pdel), 1); this._paintPlans(); });
    el.querySelectorAll("[data-badd]").forEach(b => b.onclick = () => { const [pi, kind] = b.dataset.badd.split(":"); (P[pi][kind] = P[pi][kind] || []).push({ from: 16, to: 20, rate: 40, days: "weekday" }); this._paintPlans(); });
    el.querySelectorAll("[data-bdel]").forEach(b => b.onclick = () => { const [pi, kind, bi] = b.dataset.bdel.split(":"); P[pi][kind].splice(Number(bi), 1); this._paintPlans(); });
  }
  async _loadDevices() {
    if (!this._devs || Date.now() - this._devs.at > 120000) {
      try {
        const [devs, ents] = await Promise.all([this._hass.callWS({ type: "config/device_registry/list" }), this._hass.callWS({ type: "config/entity_registry/list" })]);
        this._devs = { at: Date.now(), devs, ents };
      } catch (e) { const el = this._root.querySelector("#devs"); if (el) el.innerHTML = '<div class="muted">Device list needs an admin user.</div>'; return; }
    }
    this._paintDevices();
  }
  _paintDevices() {
    const el = this._root.querySelector("#devs"); if (!el || !this._devs) return;
    const { devs, ents } = this._devs, s = this._data.studio || {}, ignore = new Set((this._data.settings || {}).health_ignore || []);
    const known = new Set([s.pv, s.grid, s.battery, s.ev, s.soc, s.ev_soc, s.day_pv, s.day_load, s.day_export, s.day_import, ...Object.values(EV).flat().filter(x => typeof x === "string"),
      ...E.bt.map(x => x[1]), ...E.health.map(x => x[1]), (this._data.control || {}).mode_entity].filter(Boolean));
    const byDev = {}; ents.forEach(e => { if (e.device_id && !e.disabled_by) (byDev[e.device_id] = byDev[e.device_id] || []).push(e.entity_id); });
    const energy = /neovolt|sungrow|tesla|byd|alpha|byte.?watt|solcast|forecast\.solar|wall connector/i;
    const list = devs.filter(dv => (byDev[dv.id] || []).some(id => known.has(id)) || energy.test(`${dv.manufacturer || ""} ${dv.model || ""} ${dv.name || ""}`))
      .map(dv => {
        const ids = byDev[dv.id] || [], sts = ids.map(id => this._hass.states[id]).filter(Boolean);
        const down = sts.filter(x => x.state === "unavailable").length, last = Math.max(0, ...sts.map(x => +new Date(x.last_updated)));
        return { dv, ids, down, total: sts.length, last, watched: ids.length && !ids.every(id => ignore.has(id)) };
      }).sort((a, b) => (b.down > 0) - (a.down > 0) || (a.dv.name_by_user || a.dv.name || "").localeCompare(b.dv.name_by_user || b.dv.name || ""));
    const ago = t => { if (!t) return "–"; const m = Math.round((Date.now() - t) / 60000); return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.round(m / 60) + " h ago" : Math.round(m / 1440) + " d ago"; };
    el.innerHTML = list.length ? `<div class="devs">${list.map(x => `<div class="dev">
        <span class="dst ${x.total === 0 ? "" : x.down === x.total ? "off" : x.down ? "part" : "on"}" title="${x.down ? x.down + " of " + x.total + " unavailable" : "online"}"></span>
        <div class="dn"><b>${esc(x.dv.name_by_user || x.dv.name || "Device")}</b><span class="muted">${esc([x.dv.manufacturer, x.dv.model].filter(Boolean).join(" · "))}</span></div>
        <div class="dm"><span>${x.total} entities${x.down ? ` · <b class="bad">${x.down} offline</b>` : ""}</span><span class="muted">updated ${ago(x.last)}</span></div>
        <label class="dw" title="Report this device in house health">Health ${this._toggle(`data-watch="${x.dv.id}"`, x.watched)}</label>
        <a class="lnk" href="/config/devices/device/${x.dv.id}" target="_top" aria-label="Open in Home Assistant">${icon("arrow")}</a></div>`).join("")}</div>
      <div class="toast" id="dev-msg"></div>` : '<div class="muted">No energy devices found.</div>';
    el.querySelectorAll("[data-watch]").forEach(t => t.onchange = async () => {
      const ids = byDev[t.dataset.watch] || [], set = new Set(ignore);
      ids.forEach(id => (t.checked ? set.delete(id) : set.add(id)));
      const m = el.querySelector("#dev-msg");
      try { await this._hass.callWS({ type: "cortex/set_options", options: { health_ignore: [...set] } }); m.textContent = t.checked ? "House health watches it again." : "House health will ignore it."; m.className = "toast show"; setTimeout(() => this._load(), 3500); }
      catch (e) { m.textContent = "Failed: " + (e.message || e.code); m.className = "toast show bad"; }
    });
  }

  // ---- CHAT -----------------------------------------------------------
  async _agents() {
    if (this._agentList) return this._agentList;
    try { const r = await this._hass.callWS({ type: "conversation/agent/list", language: this._hass.language }); this._agentList = (r.agents || []).map(a => ({ id: a.id, name: a.name })); }
    catch (e) { this._agentList = []; }
    return this._agentList;
  }
  _chatState() {
    if (!this._chat) { try { this._chat = JSON.parse(sessionStorage.getItem("cortex-chat") || "null"); } catch (e) { /* ignore */ } }
    if (!this._chat) this._chat = { msgs: [], cid: null };
    return this._chat;
  }
  _chatPrefs() {
    let p = {}; try { p = JSON.parse(localStorage.getItem("cortex-chat-prefs") || "{}"); } catch (e) { /* ignore */ }
    return { speak: "off", cat: "energy", mine: [], ...p };
  }
  _setChatPrefs(ch) { const p = { ...this._chatPrefs(), ...ch }; try { localStorage.setItem("cortex-chat-prefs", JSON.stringify(p)); } catch (e) { /* ignore */ } return p; }
  _chatCard() {
    const pr = this._chatPrefs(), mic = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    const cats = [["energy", "Energy"], ["ev", "EV"], ["house", "House"], ["routines", "Routines"], ["remind", "Reminders"], ["mine", "My prompts"]];
    return `<div class="card wide chat"><div class="chead"><h2>${icon("spark")} Ask Cortex</h2>
        <div class="chtools"><select id="chat-agent" aria-label="Agent"></select>
          <select id="chat-speak" aria-label="Speak replies"><option value="off">Silent</option><option value="device">Speak here</option><option value="house">Speak on speakers</option></select>
          <button class="ghost" id="chat-export" title="Download this chat">Export</button><button class="ghost" id="chat-new">New chat</button></div></div>
      <div class="msgs" id="msgs" aria-live="polite"></div>
      <div class="pcats seg">${cats.map(([k, l]) => `<button data-pcat="${k}" class="${pr.cat === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <div class="qp" id="qp"></div>
      <form class="chatf" id="chatf">${mic ? `<button type="button" class="mic" id="chatmic" aria-label="Speak your message">${icon("mic")}</button>` : ""}
        <input id="chatin" autocomplete="off" placeholder="Ask anything, or tell Cortex what to do…" aria-label="Message">
        <button type="button" class="star" id="chatstar" aria-label="Save as one of my prompts" title="Save as my prompt">${icon("star")}</button>
        <button type="submit" aria-label="Send" id="chatsend">${icon("send")}</button></form></div>`;
  }
  _promptsFor(cat) {
    const P = {
      energy: ["What should I do with energy right now?", "Why did the battery top up today?", "How much did solar save me today?", "Start exporting the battery", "Stop the battery dispatch", "Switch the battery to Autopilot", "Is tomorrow a low solar day?"],
      ev: ["When should I charge the EV?", "How full is the EV and how long to 80%?", "Is the EV charging right now?", "What will a full charge cost in the shoulder window?"],
      house: ["Is the house locked up?", "Who came to the door today?", "What happened around the house today?", "Look at the front door camera", "Any house health problems?", "Be quiet for an hour"],
      routines: ["Make a goodnight routine that turns off all lights at 23:00", "What routines do I have?", "Run the goodnight routine", "Tell me when the garage door opens"],
      remind: ["Remind me at 9pm to put the bins out", "Remind me in 30 minutes to check the oven", "What reminders do I have?", "Give me today's briefing", "Give me the weekly summary"],
    };
    return cat === "mine" ? this._chatPrefs().mine : P[cat] || [];
  }
  _paintPrompts() {
    const el = this._root.querySelector("#qp"); if (!el) return;
    const cat = this._chatPrefs().cat, list = this._promptsFor(cat);
    el.innerHTML = list.length ? list.map((p, i) => `<span class="chipw"><button class="chip" data-qp="${esc(p)}">${esc(p)}</button>${cat === "mine" ? `<button class="ghost x" data-qdel="${i}" aria-label="Remove prompt">✕</button>` : ""}</span>`).join("")
      : '<span class="muted">Type a message and press ☆ to keep it here.</span>';
    el.querySelectorAll("[data-qp]").forEach(b => b.onclick = () => this._chatSend(b.dataset.qp));
    el.querySelectorAll("[data-qdel]").forEach(b => b.onclick = () => { const m = this._chatPrefs().mine; m.splice(Number(b.dataset.qdel), 1); this._setChatPrefs({ mine: m }); this._paintPrompts(); });
  }
  _paintChat() {
    const el = this._root.querySelector("#msgs"); if (!el) return;
    const c = this._chatState(), fmt = t => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\n/g, "<br>");
    const lastAi = c.msgs.map(m => m.who).lastIndexOf("ai");
    el.innerHTML = c.msgs.length ? c.msgs.map((m, i) => `<div class="mwrap ${m.who}"><div class="msg ${m.who}${m.err ? " err" : ""}">${fmt(m.text)}</div>
        ${m.who === "ai" ? `<div class="macts"><button class="ghost" data-mcopy="${i}">Copy</button><button class="ghost" data-mspeak="${i}">Speak</button>${i === lastAi ? '<button class="ghost" data-mretry="1">Retry</button>' : ""}${m.t ? `<span class="muted">${m.t}</span>` : ""}</div>` : ""}</div>`).join("")
        + (this._chatBusy ? '<div class="msg ai typing"><i></i><i></i><i></i></div>' : "")
      : `<div class="empty">${icon("spark")}<b>Ask about your energy, house or reminders.</b>
          <span>Cortex can control the battery, give tips, look at cameras, announce on speakers, set reminders and watches, and create or run routines. With Assist turned on for your agent it can also control any exposed device.</span></div>`;
    const say = t => this._speak(t);
    el.querySelectorAll("[data-mcopy]").forEach(b => b.onclick = () => { try { navigator.clipboard.writeText(c.msgs[b.dataset.mcopy].text); b.textContent = "Copied"; } catch (e) { /* ignore */ } });
    el.querySelectorAll("[data-mspeak]").forEach(b => b.onclick = () => say(c.msgs[b.dataset.mspeak].text, true));
    el.querySelectorAll("[data-mretry]").forEach(b => b.onclick = () => { const last = [...c.msgs].reverse().find(m => m.who === "me"); if (last) { c.msgs.splice(c.msgs.lastIndexOf(last)); this._chatSend(last.text); } });
    el.scrollTop = el.scrollHeight;
  }
  _speak(text, force) {
    const mode = this._chatPrefs().speak, plain = String(text).replace(/\*\*|`/g, "");
    if (mode === "house") { this._hass.callService("cortex", "say", { message: plain }).catch(() => {}); return; }
    if ((mode === "device" || force) && window.speechSynthesis) { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(plain); u.lang = this._hass.language || "en"; speechSynthesis.speak(u); }
  }
  _keepChat() { const c = this._chatState(); try { sessionStorage.setItem("cortex-chat", JSON.stringify({ msgs: c.msgs.slice(-40), cid: c.cid })); } catch (e) { /* ignore */ } }
  async _chatSend(text) {
    const q = s => this._root.querySelector(s), c = this._chatState();
    text = (text || "").trim(); if (!text || this._chatBusy) return;
    const t = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    c.msgs.push({ who: "me", text, t: t() }); this._chatBusy = true; this._paintChat(); this._keepChat();
    const sel = q("#chat-agent"), agent = sel ? sel.value : "";
    try {
      const res = await this._hass.callWS({ type: "conversation/process", text, conversation_id: c.cid || undefined, agent_id: agent || undefined, language: this._hass.language });
      c.cid = res.conversation_id || c.cid;
      const reply = (((res.response || {}).speech || {}).plain || {}).speech || "Done.";
      c.msgs.push({ who: "ai", text: reply, err: (res.response || {}).response_type === "error", t: t() });
      this._speak(reply);
    } catch (e) { c.msgs.push({ who: "ai", text: "Couldn't reach the agent: " + (e.message || e.code), err: true, t: t() }); }
    this._chatBusy = false; this._paintChat(); this._keepChat();
    if (/export|top.?up|charg|stop|battery|autopilot|routine|quiet|watch/i.test(text)) setTimeout(() => this._load(), 2500);
  }
  _wireChat() {
    const r = this._root, q = s => r.querySelector(s), c = this._chatState(), pr = this._chatPrefs();
    this._agents().then(list => {
      const sel = q("#chat-agent"); if (!sel) return;
      let pick = null; try { pick = localStorage.getItem("cortex-chat-agent"); } catch (e) { /* ignore */ }
      const def = pick ?? ((this._data.settings || {}).agent || "");
      sel.innerHTML = '<option value="">Default agent</option>' + list.map(a => `<option value="${esc(a.id)}"${a.id === def ? " selected" : ""}>${esc(a.name)}</option>`).join("");
      sel.onchange = () => { try { localStorage.setItem("cortex-chat-agent", sel.value); } catch (e) { /* ignore */ } c.cid = null; };
    });
    const sp = q("#chat-speak"); sp.value = pr.speak; sp.onchange = () => this._setChatPrefs({ speak: sp.value });
    r.querySelectorAll("[data-pcat]").forEach(b => b.onclick = () => { this._setChatPrefs({ cat: b.dataset.pcat }); r.querySelectorAll("[data-pcat]").forEach(x => x.classList.toggle("on", x === b)); this._paintPrompts(); });
    q("#chatf").onsubmit = e => { e.preventDefault(); const i = q("#chatin"); const t = i.value; i.value = ""; this._chatSend(t); };
    q("#chatstar").onclick = () => { const v = q("#chatin").value.trim(); if (!v) return; const m = this._chatPrefs().mine.filter(x => x !== v); m.unshift(v); this._setChatPrefs({ mine: m.slice(0, 20), cat: "mine" }); r.querySelectorAll("[data-pcat]").forEach(x => x.classList.toggle("on", x.dataset.pcat === "mine")); this._paintPrompts(); };
    q("#chat-new").onclick = () => { c.msgs = []; c.cid = null; this._keepChat(); this._paintChat(); };
    q("#chat-export").onclick = () => {
      const txt = c.msgs.map(m => `[${m.t || ""}] ${m.who === "me" ? "You" : "Cortex"}: ${m.text}`).join("\n\n") || "(empty chat)";
      const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([txt], { type: "text/plain" })); a.download = `cortex-chat-${new Date().toISOString().slice(0, 10)}.txt`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    };
    const micB = q("#chatmic");
    if (micB) micB.onclick = () => {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (this._rec) { this._rec.stop(); return; }
      const rec = new SR(); rec.lang = this._hass.language || "en-AU"; rec.interimResults = true; this._rec = rec; micB.classList.add("on");
      rec.onresult = e => { const t = [...e.results].map(x => x[0].transcript).join(""); q("#chatin").value = t; if (e.results[e.results.length - 1].isFinal) { rec.stop(); q("#chatin").value = ""; this._chatSend(t); } };
      rec.onend = rec.onerror = () => { this._rec = null; micB.classList.remove("on"); };
      rec.start();
    };
    this._paintPrompts(); this._paintChat();
  }

  // ---- ANALYTICS -------------------------------------------------------
  _viewAnalytics() {
    const todays = [["Solar generated", AN.pv, C.solar], ["Exported", AN.exp, C.shoulder], ["Imported", AN.imp, C.peak], ["Used", AN.load, C.home],
      ["Battery charged", AN.chg, C.batt], ["Battery discharged", AN.dis, "#7e57c2"], ["Battery level", "sensor.neovolt_online_soc", C.batt]];
    return `<section class="grid">
      <div class="card wide"><h2>Today</h2><div class="stats">${todays.map(([l, id, c]) => this._tile(l, id, c)).join("")}</div>
        <div class="row" style="margin-top:8px"><span>${esc((this._st("sensor.daily_summary") || {}).state || "")}</span><span class="muted">Best appliance time: <b>${esc((this._st("sensor.best_time_to_run_appliances") || {}).state || "–")}</b></span></div></div>
      <div id="an-body" style="display:contents"><div class="card wide muted">Loading analytics…</div></div>
    </section>`;
  }
  _anBody() {
    const c = this._enCompute();
    if (!c || !c.days.length) return `<div class="card wide"><h2>History</h2><div class="muted">No statistics yet. Energy history appears once Home Assistant has compiled a few hours of data.</div></div>`;
    const R = this._anRange || 14, days = c.days.slice(-R), keys = new Set(days.map(d => d.key)), long = days.length > 10, lbl = days.map(d => dayLabel(d.key, long));
    const sum = k => days.reduce((a, d) => a + (d[k] || 0), 0), n = days.length;
    const pv = sum("pv"), used = sum("used"), imp = sum("imp"), exp = sum("exp"), chg = sum("chg"), dis = sum("dis"), cImp = sum("cImp"), cExp = sum("cExp"), saved = sum("saved");
    const ss = used > 0 ? Math.max(0, Math.min(100, (1 - imp / used) * 100)) : null, sc = pv > 0 ? Math.max(0, Math.min(100, (1 - exp / pv) * 100)) : null;
    const supply = days.reduce((a, d) => a + d.supply, 0), net = cImp - cExp + supply, ev = sum("ev");
    const cap = this._num("input_number.system_battery_capacity") ?? 50, f = (v, d = 0) => fx(v, d), $ = v => (v < 0 ? "-$" : "$") + fx(Math.abs(v), 2);
    const T = (l, v, col, sub) => `<div class="stat" style="border-color:${col}"><span class="muted">${l}</span><b>${v}</b>${sub ? `<span class="muted">${sub}</span>` : ""}</div>`;
    const best = (k, max = true) => days.filter(d => d[k] !== null && d[k] !== undefined).reduce((a, d) => (!a || (max ? d[k] > a[k] : d[k] < a[k]) ? d : a), null);
    const bd = (d, k, u) => d ? `${dayLabel(d.key, true)} · ${fx(d[k], 1)}${u}` : "–";
    const seg = `<span class="seg">${[7, 14, 30].map(x => `<button data-anr="${x}" class="${x === R ? "on" : ""}">${x}d</button>`).join("")}</span>`;
    const chart = (series, o) => lineChart(series, { labels: lbl, ...o });
    // hourly profile
    const prof = h => { const a = new Array(24).fill(0); c.hrs.filter(x => keys.has(x.key)).forEach(x => { a[x.hour] += x[h]; }); return a.map(v => v / n); };
    const per = ["shoulder", "peak", "off_peak"].map(p => ({ id: p, name: { shoulder: "Shoulder 10–14", peak: "Peak 16–20", off_peak: "Off-peak" }[p], color: { shoulder: C.shoulder, peak: C.peak, off_peak: C.off_peak }[p],
      kwh: days.reduce((a, d) => a + d.per[p].kwh, 0), cost: days.reduce((a, d) => a + d.per[p].cost, 0) }));
    const pk = Math.max(...per.map(p => p.kwh), 0.1), expEve = sum("expEve"), cExpEve = sum("cExpEve");
    const rowBar = (name, color, kwh, cost, mx) => `<div class="row"><span style="min-width:120px">${name}</span><span style="flex:1;margin:0 10px;background:rgba(127,127,127,.15);border-radius:6px;height:10px;align-self:center"><i style="display:block;height:10px;border-radius:6px;width:${Math.min(kwh / mx * 100, 100)}%;background:${color}"></i></span><b>${f(kwh, 1)} kWh · ${$(cost)}</b></div>`;
    const evDays = days.map(d => d.ev || 0);
    return `<div class="card wide"><h2>Last ${n} day${n === 1 ? "" : "s"} ${seg}</h2><div class="stats">
        ${T("Solar", f(pv) + " kWh", C.solar, f(pv / n, 1) + " kWh/day")}${T("Used", f(used) + " kWh", C.home, f(used / n, 1) + " kWh/day")}
        ${T("Imported", f(imp) + " kWh", C.grid, $(cImp) + " at tariff")}${T("Exported", f(exp) + " kWh", C.shoulder, $(cExp) + " earned")}
        ${T("Self-sufficiency", ss === null ? "–" : f(ss) + "%", C.batt, "share of use not from grid")}${T("Self-consumption", sc === null ? "–" : f(sc) + "%", "#12b5cb", "share of solar used on-site")}
        ${T("Net bill", $(net), net <= 0 ? C.shoulder : C.peak, "import − export + supply " + $(supply))}${T("Saved vs no solar", $(saved), C.shoulder, "excl. supply charge")}
        ${T("Battery cycles", f(dis / cap, 1), "#7e57c2", f(dis, 0) + " kWh out · " + f(chg, 0) + " in")}${T("Battery out/in", chg > 1 ? f(dis / chg * 100) + "%" : "–", C.batt, "energy returned")}
        ${T("EV charged", ev > 0 ? f(ev, 1) + " kWh" : "–", C.ev, ev > 0 ? f(ev / Math.max(used, 1) * 100) + "% of use" : "")}
        ${T("Avg cost / day", $(net / n), C.off_peak, "incl. supply")}</div>
      <div class="row" style="margin-top:8px"><span class="muted">Best solar: <b>${bd(best("pv"), "pv", " kWh")}</b></span><span class="muted">Most imported: <b>${bd(best("imp"), "imp", " kWh")}</b></span><span class="muted">Most saved: <b>${best("saved") ? dayLabel(best("saved").key, true) + " · " + $(best("saved").saved) : "–"}</b></span></div>
      <div class="muted">Costs use your Plan rates by hour (public holidays treated as normal days). Today updates live.</div></div>
      ${this._planCompare(c, keys, n)}
      <div class="card wide"><h2>Daily energy (kWh)</h2>${barChart(lbl, [{ name: "Solar", color: C.solar, data: days.map(d => d.pv) }, { name: "Used", color: C.home, data: days.map(d => d.used) },
        { name: "Imported", color: C.grid, data: days.map(d => d.imp) }, { name: "Exported", color: C.shoulder, data: days.map(d => d.exp) }], { w: 1100, h: 230 })}</div>
      <div class="card w6"><h2>Daily money ($)</h2>${barChart(lbl, [{ name: "Import cost", color: C.peak, data: days.map(d => d.cImp) }, { name: "Export earned", color: C.shoulder, data: days.map(d => d.cExp) },
        { name: "Saved vs no solar", color: C.solar, data: days.map(d => Math.max(d.saved, 0)) }], { unit: "$", dec: 2 })}</div>
      <div class="card w6"><h2>Self-sufficiency & self-consumption (%)</h2>${chart([{ name: "Self-sufficiency", color: "#0f9d58", data: days.map(d => d.ss) }, { name: "Self-consumption", color: "#12b5cb", data: days.map(d => d.sc) }], { min: 0, max: 100 })}</div>
      <div class="card w6"><h2>Import by rate period</h2>${per.map(p => rowBar(p.name, p.color, p.kwh, p.cost, pk)).join("")}
        <div class="muted" style="margin-top:6px">Aim: shift peak use to battery; top up in the 10–14 shoulder.</div></div>
      <div class="card w6"><h2>Export earnings</h2>${rowBar("Evening FiT 17–21", C.shoulder, expEve, cExpEve, Math.max(exp, 0.1))}${rowBar("Other hours", C.off_peak, exp - expEve, cExp - cExpEve, Math.max(exp, 0.1))}
        <div class="row"><span>Average per exported kWh</span><b>${exp > 0 ? fx(cExp / exp * 100, 1) + "c" : "–"}</b></div></div>
      <div class="card wide"><h2>Typical day: average kWh per hour</h2>${lineChart([{ name: "Solar", color: C.solar, data: prof("pv"), area: true }, { name: "Used", color: C.home, data: prof("used") },
        { name: "Imported", color: C.grid, data: prof("imp") }, { name: "Exported", color: C.shoulder, data: prof("exp") }], { labels: Array.from({ length: 24 }, (_, h) => h + ":00"), min: 0, w: 1100, h: 220 })}</div>
      <div class="card w6"><h2>Battery cycling (kWh/day)</h2>${barChart(lbl, [{ name: "Charged", color: C.batt, data: days.map(d => d.chg) }, { name: "Discharged", color: "#7e57c2", data: days.map(d => d.dis) }])}</div>
      <div class="card w6"><h2>Battery level range (%)</h2>${chart([{ name: "Max", color: C.shoulder, data: days.map(d => d.soc && d.soc.max) }, { name: "Average", color: C.batt, data: days.map(d => d.soc && d.soc.mean) },
        { name: "Min", color: C.off_peak, data: days.map(d => d.soc && d.soc.min) }], { min: 0, max: 100 })}</div>
      <div class="card w6"><h2>Peak power each day (kW)</h2>${chart([{ name: "House load", color: C.home, data: days.map(d => d.loadMax === null ? null : d.loadMax / 1000) }, { name: "Solar", color: C.solar, data: days.map(d => d.pvMax === null ? null : d.pvMax / 1000) },
        { name: "Grid", color: C.grid, data: days.map(d => d.gridMax === null ? null : Math.abs(((this._data.studio || {}).grid_invert ? -d.gridMin : d.gridMax)) / 1000) }], { min: 0 })}</div>
      <div class="card w6"><h2>EV charging (kWh/day)</h2>${barChart(lbl, [{ name: "Tesla wall connector", color: C.ev, data: evDays }])}</div>
      <div class="card wide"><h2>Solar production vs forecast, last 36 h (kW)</h2><div id="an-sol"></div></div>
      <div class="card w6"><h2>AGL rates 48h (c/kWh)</h2><div id="an-rate"></div></div>
      <div class="card w6"><h2>Cost tracking</h2><div class="stats">${E.cost.map(([l, id]) => this._tile(l, id, C.off_peak)).join("")}</div></div>`;
  }

  _paintMore(tab) {
    const q = id => this._root.querySelector(id), put = (id, h) => { const el = q(id); if (el) el.innerHTML = h; };
    if (tab === "battery" && this._bt) {
      const { fl, soc, tmp } = this._bt;
      put("#bt-flows", lineChart(E.flows.map(([n, id, c], i) => ({ name: n, color: c, data: fl[id], area: i === 0 })), { start: fl.start, end: fl.end, h: 240, w: 1100 }));
      put("#bt-soc", lineChart([{ name: "SOC", color: C.batt, data: soc[N + "combined_battery_soc"], area: true }], { min: 0, max: 100, start: soc.start, end: soc.end }));
      put("#bt-tmp", lineChart([{ name: "Max cell", color: "#e8833a", data: tmp[N + "battery_max_cell_temperature"] }, { name: "Min cell", color: "#4a90d9", data: tmp[N + "battery_min_cell_temperature"] }], { start: tmp.start, end: tmp.end }));
    }
    if (tab === "analytics") {
      const body = q("#an-body");
      if (body && this._en) {
        body.innerHTML = this._anBody();
        body.querySelectorAll("[data-anr]").forEach(b => b.onclick = () => { this._anRange = Number(b.dataset.anr); this._paintMore("analytics"); });
      }
      if (this._an) {
        const { sol, rate } = this._an, ids = ["sensor.sungrow_pv", "sensor.pv_forecast_power_now"];
        put("#an-sol", lineChart([{ name: "Actual PV", color: "#FFB300", data: sol[ids[0]], area: true }, { name: "Forecast", color: "#00B0FF", data: sol[ids[1]] }], { start: sol.start, end: sol.end, min: 0, h: 220, w: 1100 }));
        put("#an-rate", lineChart([{ name: "Import", color: "#e45649", data: rate["sensor.agl_plan_import_rate"] }, { name: "Feed-in", color: "#50a14f", data: rate["sensor.agl_plan_feed_in_rate"] }], { step: true, min: 0, start: rate.start, end: rate.end }));
      }
    }
  }

  // ---- PLAN extras: money, rate windows, automations, settings ---------
  _planExtras() {
    const m = this._money(), exp = m.exp, imp = m.imp, p = m.p, f = m.f, self = m.self, net = m.net;
    const h = new Date().getHours(), bd = this._data.energy.business_day, high = this._data.energy.high_season;
    const v = id => fx(this._num(id), 2), now = (a, b) => (h >= a && h < b ? '<b class="ok">◀ now</b>' : "");
    const pk = high ? "input_number.agl_plan_high_season_peak" : "input_number.agl_plan_low_season_peak";
    return `<div class="card"><h2>Money today</h2>
        <div class="row"><span>Solar used on-site (${fx(self, 1)} kWh)</span><b>$${fx(self * p, 2)} avoided</b></div>
        <div class="row"><span>Exported (${fx(exp, 1)} kWh)</span><b>$${fx(exp * f, 2)} earned</b></div>
        <div class="row"><span>Imported (${fx(imp, 1)} kWh)</span><b>$${fx(imp * p, 2)} spent</b></div>
        <div class="row"><span><b>Net benefit</b></span><b class="${net >= 0 ? "ok" : "bad"}">$${fx(net, 2)}</b></div>
        <div class="muted">Indicative: uses the current rate for all kWh.</div></div>
      <div class="card"><h2>Rate windows</h2>
        <div class="row"><span>10–14 Shoulder</span><span><b>${v("input_number.agl_plan_shoulder")}c</b> ${now(10, 14)}</span></div>
        <div class="row"><span>14–16 Off peak</span><span><b>${v("input_number.agl_plan_off_peak")}c</b> ${now(14, 16)}</span></div>
        <div class="row"><span>16–20 ${bd ? "Peak" : "Off peak (no peak today)"}</span><span><b>${bd ? v(pk) : v("input_number.agl_plan_off_peak")}c</b> ${now(16, 20)}</span></div>
        <div class="row"><span>20–10 Off peak</span><span><b>${v("input_number.agl_plan_off_peak")}c</b> ${h >= 20 || h < 10 ? '<b class="ok">◀ now</b>' : ""}</span></div>
        <div class="row"><span>FiT 07–08 / 17–21</span><span><b>${v("input_number.agl_plan_fit_morning")}c / ${v("input_number.agl_plan_fit_evening")}c</b></span></div>
        <div class="muted">Supply ${v("input_number.agl_plan_supply_charge")} c/day · ${high ? "high" : "low"} season.</div></div>
`;
  }
  _sysCards() {
    return `<div class="card w6"><h2>Automations</h2>${E.autos.map(id => { const st = this._st(id); return st ? `<label class="row"><span>${esc(st.attributes.friendly_name || id)}</span><input type="checkbox" class="sw" data-auto="${id}" ${st.state === "on" ? "checked" : ""}></label>` : ""; }).join("") || '<div class="muted">None found.</div>'}</div>
      <div class="card w6"><h2>System settings <span class="muted">edit a value, press Enter</span></h2>${E.nums.map(([l, id]) => { const st = this._st(id); return st ? `<div class="row"><span>${esc(l)}</span><input type="number" class="num" data-num="${id}" value="${esc(st.state)}" step="${st.attributes.step || "any"}" min="${st.attributes.min ?? ""}" max="${st.attributes.max ?? ""}"></div>` : ""; }).join("")}</div>`;
  }
  _wireExtras() {
    const call = (d, sv, data) => this._hass.callService(d, sv, data).catch(() => {});
    this._root.querySelectorAll("[data-auto]").forEach(c => c.onchange = () => call("automation", c.checked ? "turn_on" : "turn_off", { entity_id: c.dataset.auto }));
    this._root.querySelectorAll("[data-num]").forEach(i => i.onchange = () => { const v = parseFloat(i.value); if (!Number.isNaN(v)) call("input_number", "set_value", { entity_id: i.dataset.num, value: v }); });
  }

  // ---- HOUSEKEEPING extras --------------------------------------------
  _houseExtras() {
    const ups = Object.entries(this._hass.states).filter(([k, s]) => k.startsWith("update.") && s.state === "on").map(([k, s]) => s.attributes.friendly_name || k);
    const w = this._st("weather.forecast_ingleburn");
    return `<div class="card w6"><h2>Housekeeping</h2>
        <div class="row"><span>Updates pending</span><b>${ups.length ? esc(ups.join(", ")) : "None"}</b></div>
        <div class="row"><span>Internet speed</span><b>${esc((this._st("sensor.fast_com_download") || {}).state || "–")} Mbps</b></div>
        <div class="row"><span>Solar exported at battery full</span><b>${esc((this._st("input_number.solar_exported_at_battery_full") || {}).state || "–")}</b></div>
        ${w ? `<div class="row"><span>Weather</span><b>${esc(w.state.replace(/-/g, " "))} ${w.attributes.temperature ?? ""}°</b></div>` : ""}</div>`;
  }

  // ---- evening export plan: earnings vs daily supply charge -------------
  async _loadEarn() {
    const id = (this._data.studio || {}).day_export; if (!id) return;
    this._earnAt = Date.now();
    const start = new Date(); start.setHours(0, 0, 0, 0);
    const res = await this._hass.callWS({ type: "history/history_during_period", start_time: start.toISOString(), end_time: new Date().toISOString(),
      entity_ids: [id], minimal_response: true, no_attributes: true, significant_changes_only: false }).catch(() => ({}));
    const sch = this._data.schedule || [], rate = h => (sch.find(r => r.hour === h) || { feed_in: 0 }).feed_in;
    const buckets = {}; let prev = null, kwh = 0, earned = 0;
    (res[id] || []).forEach(r => {
      const v = parseFloat(r.s); if (Number.isNaN(v)) return;
      const t = new Date((r.lu ?? r.lc) * 1000);
      if (prev !== null && v > prev && v - prev < 5) { const d = v - prev, c = rate(t.getHours()); buckets[c] = (buckets[c] || 0) + d; kwh += d; earned += d * c / 100; }
      prev = v;
    });
    this._earn = { buckets, kwh, earned };
    if (this._tab === "plan") this._paintEarn();
  }
  _paintEarn() {
    const el = this._root.querySelector("#earn"), d = this._data; if (!el || !d) return;
    const e = d.energy, m = this._earn || { buckets: {}, kwh: 0, earned: 0 };
    const daily = e.daily_charge ?? 0, sch = d.schedule || [], top = Math.max(...sch.map(r => r.feed_in), 0) || e.feed_in_rate || 1;
    const left = Math.max(daily - m.earned, 0), covered = left <= 0.004, pct = daily ? Math.min(m.earned / daily, 1) * 100 : 0;
    const needKwh = left / (top / 100), expKw = Math.max(-this._flows().grid, 0), nowRate = e.feed_in_rate ?? 0;
    const rows = Object.keys(m.buckets).map(Number).sort((a, b) => b - a).map(c =>
      `<div class="row"><span class="muted">${fx(c, 0)}c × ${fx(m.buckets[c], 1)} kWh</span><b>$${fx(m.buckets[c] * c / 100, 2)}</b></div>`).join("");
    const usable = e.battery_usable ?? 0, can = usable >= needKwh;
    el.innerHTML = `
      <div class="hero-top"><div class="big">$${fx(m.earned, 2)}<small>of $${fx(daily, 2)} supply charge</small></div>
        <span class="pill" style="--pc:${covered ? C.shoulder : C.off_peak};align-self:center">${covered ? "covered ✓" : "$" + fx(left, 2) + " to go"}</span></div>
      <div class="hbar" style="grid-template-columns:1fr;margin:10px 0"><div style="height:14px"><i style="width:${pct}%;background:${covered ? C.shoulder : C.off_peak}"></i></div></div>
      <div class="row"><span>${covered ? "Surplus earned" : "Left to cover"}</span><b>${covered ? "$" + fx(m.earned - daily, 2) : "$" + fx(left, 2) + " ≈ " + fx(needKwh, 2) + " kWh at " + fx(top, 0) + "c"}</b></div>
      <div class="row"><span>Feed-in now</span><b>${fx(nowRate, 0)}c</b></div>
      <div class="row"><span>Exporting now</span><b>${expKw > 0.05 ? fx(expKw) + " kW → $" + fx(expKw * nowRate / 100, 2) + "/h" : "not exporting"}</b></div>
      <div class="row"><span>Exported today</span><b>${fx(m.kwh, 1)} kWh</b></div>${rows}
      ${covered ? "" : `<div class="row"><span>Battery usable</span><b class="${can ? "ok" : "bad"}">${fx(usable, 1)} kWh ${can ? "· enough" : "· short by " + fx(needKwh - usable, 1)}</b></div>`}
      <div class="muted">Earnings = each kWh exported × the feed-in rate at that hour.</div>`;
  }

  // ---- PLAN -----------------------------------------------------------
  _viewPlan() {
    const d = this._data, e = d.energy, sch = d.schedule;
    const W = 900, H = 260, L = 34, T = 14, B = 26, n = sch.length, bw = (W - L - 10) / n;
    const maxR = Math.max(...sch.map(r => Math.max(r.import, r.feed_in)), 1) * 1.1;
    const y = v => T + (1 - v / maxR) * (H - T - B);
    let bars = "", pts = "", labels = "";
    sch.forEach((r, i) => {
      const p = r.import <= 12 ? "shoulder" : r.import >= 40 ? "peak" : "off_peak";
      const bx = L + i * bw;
      bars += `<rect x="${bx + 1}" y="${y(r.import)}" width="${bw - 2}" height="${H - B - y(r.import)}" rx="2" fill="${C[p]}" opacity="${r.hour === d.hour ? 1 : .78}"${r.hour === d.hour ? ' stroke="currentColor" stroke-width="2"' : ""}><title>${r.hour}:00 import ${r.import}c, feed-in ${r.feed_in}c</title></rect>`;
      pts += (i ? "L" : "M") + (bx + bw / 2).toFixed(1) + " " + y(r.feed_in).toFixed(1);
      if (r.hour % 3 === 0) labels += `<text x="${bx + bw / 2}" y="${H - 8}" text-anchor="middle" class="ax">${r.hour}</text>`;
    });
    let grid = "";
    for (let k = 0; k <= 4; k++) { const v = (maxR * k) / 4; grid += `<line x1="${L}" x2="${W - 10}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" opacity=".1"/><text x="${L - 4}" y="${y(v) + 3}" text-anchor="end" class="ax">${v.toFixed(0)}c</text>`; }
    const solarDay = e.solar_day === "low" ? C.peak : C.shoulder;
    const ap = d.autopilot || { mode: "off", decisions: [] };
    const pvT = e.pv_today, pvM = e.pv_tomorrow, mx = Math.max(pvT || 0, pvM || 0, e.low_solar || 30, 1);
    const bar = (v, label) => `<div class="hbar"><span>${label}</span><div><i style="width:${v === null ? 0 : Math.min(v / mx, 1) * 100}%;background:${C.solar}"></i></div><b>${v === null ? "–" : fx(v, 0) + " kWh"}</b></div>`;
    return `<section class="grid">
      <div class="card wide"><h2>Today's rates <span class="legend"><b style="color:${C.shoulder}">■</b> shoulder <b style="color:${C.off_peak}">■</b> off-peak <b style="color:${C.peak}">■</b> peak <b style="color:#2e7d32">━</b> feed-in</span></h2>
        <div class="chart"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}${bars}
        <path d="${pts}" fill="none" stroke="#2e7d32" stroke-width="2.5"/>${labels}</svg></div></div>
      <div class="card w6"><h2>Solar forecast</h2>${bar(pvT, "Today")}${bar(pvM, "Tomorrow")}
        <div class="row"><span>Low-solar line</span><b>${fx(e.low_solar, 0)} kWh</b></div>
        <div class="row"><span>Today is a</span><b style="color:${solarDay}">${esc(e.solar_day)} day</b></div>
        <div class="row"><span>Shortfall vs need</span><b>${e.pv_shortfall === null ? "–" : fx(e.pv_shortfall, 1) + " kWh"}</b></div></div>
      <div class="card w6"><h2>Evening export plan</h2><div id="earn"><div class="muted">Loading…</div></div></div>
      <div class="card wide"><h2>Autopilot <span class="pill" style="--pc:${ap.mode === "auto" ? C.shoulder : ap.mode === "shadow" ? C.off_peak : "#8a8279"}">${esc(ap.mode)}</span>
        <span class="seg"><button id="ap-topup">Plan top-up</button><button id="ap-export">Plan export</button></span></h2>
        ${(ap.decisions || []).length ? ap.decisions.map(x => `<div class="row"><span><b>${x.window === "topup" ? "Top-up" : "Export"}</b> ${x.do ? "✅" : "⏸"} ${esc(x.reason)}
          ${x.do ? `<span class="muted">· ${x.kw} kW ${x.window === "topup" ? "to " + x.target_soc : "to floor " + x.floor_soc}%</span>` : ""}
          ${x.outcome ? `<br><span class="muted">${esc(x.outcome)}</span>` : ""}</span>
          <span class="muted">${esc(x.source)} · ${esc(x.result)} · ${(x.time || "").slice(5, 16).replace("T", " ")}</span></div>`).join("")
          : `<div class="muted">No decisions yet. Autopilot plans at the start of the shoulder window and the evening feed-in window.</div>`}</div>
      <div class="card"><h2>Next change</h2>
        <div class="big">${esc(e.next_period.replace("_", " "))}</div>
        <div class="muted">at ${new Date(e.next_change).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}</div>
        <div class="row"><span>Business day</span><b>${e.business_day ? "yes" : "no (no peak)"}</b></div>
        <div class="row"><span>High season</span><b>${e.high_season ? "yes" : "no"}</b></div></div>
      ${this._planExtras()}
    </section>`;
  }

  _wirePlan() {
    const act = async action => { try { await this._hass.callWS({ type: "cortex/action", action }); } catch (e) { /* shown next load */ } this._load(); };
    const t = this._root.querySelector("#ap-topup"), x = this._root.querySelector("#ap-export");
    if (t) t.onclick = () => act("autopilot_topup");
    if (x) x.onclick = () => act("autopilot_export");
  }

  // ---- HOME -----------------------------------------------------------
  _list(arr, fn, empty) { return arr.length ? arr.map(fn).join("") : `<div class="muted">${empty}</div>`; }
  _viewHouse() {
    const d = this._data, sec = d.security || { ok: true, issues: [] }, v = d.visitors || { log: [], parcels: 0, today: 0, spots: {}, cameras: [] };
    const wk = d.week || {}, hm = t => t.slice(5, 16).replace("T", " ");
    const cams = (v.cameras || []).map(c => `<div class="row"><span class="muted">${esc(c)}</span><span><input data-spot="${esc(c)}" value="${esc((v.spots || {})[c] || "")}" placeholder="e.g. front porch" size="14"> <button class="ghost" data-savespot="${esc(c)}">Save</button></span></div>`).join("");
    return `<section class="grid">
      <div class="card"><h2>Security</h2>${sec.ok ? `<div class="big ok">All shut and locked</div>` : sec.issues.map(i => `<div class="row bad">${esc(i)}</div>`).join("")}
        <div class="row"><span class="muted">Read-only sweep</span><button id="seccheck">Check now</button></div><div class="muted" id="hmsg"></div></div>
      <div class="card"><h2>Visitors today: ${v.today} · parcels waiting: ${v.parcels}</h2>
        ${this._list(v.log.slice(0, 6), x => `<div class="row"><span>${esc(x.kind)}: ${esc(x.text)}</span><span class="muted">${hm(x.time)}</span></div>`, "No visitors yet.")}
        ${v.parcels ? `<div class="row"><span></span><button id="collected">Parcels collected</button></div>` : ""}
        ${cams ? `<h2 style="margin-top:12px">Camera spots</h2>${cams}` : ""}</div>
      <div class="card"><h2>House health</h2>${this._list(d.health, h => `<div class="row">${esc(h)}</div>`, `<span class="ok">All clear</span>`)}
        <div class="row"><span class="muted">Speech ${d.hushed ? "hushed" : "active"}</span><button id="hush">${d.hushed ? "Unhush" : "Hush 1h"}</button></div></div>
      ${this._houseExtras()}
      <div class="card w6"><h2>This week</h2>${this._list(Object.keys(wk).sort(), k => `<div class="row"><span class="muted">${esc(k.replace(/_/g, " "))}</span><b>${Number(wk[k]).toFixed(Number.isInteger(wk[k]) ? 0 : 1)}</b></div>`, "Nothing recorded yet.")}</div>
      <div class="card wide"><h2>Timeline</h2>${this._list((d.timeline || []).slice(0, 14), x => `<div class="row"><span>${esc(x.text)}</span><span class="muted">${esc(x.kind)} · ${hm(x.time)}</span></div>`, "No events yet.")}</div>
    </section>`;
  }
  async _act(msg, note) {
    try { const r = await this._hass.callWS({ type: "cortex/action", ...msg }); if (note) this._note = note(r.result); }
    catch (e) { this._note = "Failed: " + (e.message || e.code); }
    await this._load();
  }
  async _ws(msg) { try { await this._hass.callWS(msg); } catch (e) { this._note = "Failed: " + (e.message || e.code); } await this._load(); }
  _flash() { const m = this._root.querySelector("#hmsg"); if (m && this._note) { m.textContent = this._note; } this._note = null; }
  _wireHouse() {
    const r = this._root, click = (id, fn) => { const el = r.querySelector(id); if (el) el.onclick = fn; };
    click("#seccheck", () => this._act({ action: "security_check" }, x => x.text));
    click("#collected", () => this._act({ action: "parcels_collected" }));
    click("#hush", () => this._ws({ type: "cortex/hush", minutes: this._data.hushed ? 0 : 60 }));
    r.querySelectorAll("[data-savespot]").forEach(b => b.onclick = () => {
      const i = r.querySelector(`[data-spot="${b.dataset.savespot}"]`);
      this._act({ action: "set_spot", camera: b.dataset.savespot, spot: i.value.trim() }, () => "Saved");
    });
    this._flash();
  }

  // ---- ASSISTANT (memory, reminders, routines, tools) -------------------
  _viewAssistant() {
    const d = this._data, hm = t => t.slice(5, 16).replace("T", " ");
    const mem = this._list(d.memories.slice().reverse(), m => `<div class="mem"><span>${CAT_ICON[m.category] || "📌"}</span><span class="t">${esc(m.text)}</span><button class="ghost" data-del="${m.id}">✕</button></div>`, "Nothing remembered yet.");
    const rem = this._list(d.reminders, r => `<div class="row"><span>${esc(r.message)}</span><span class="muted">${new Date(r.at).toLocaleString([], { hour: "2-digit", minute: "2-digit", weekday: "short" })} <button class="ghost" data-cancel="reminder:${r.id}">✕</button></span></div>`, "No reminders.");
    const wat = this._list(d.watches, w => `<div class="row"><span>${esc(w.entity_id)}${w.to_state ? " → " + esc(w.to_state) : ""}</span><button class="ghost" data-cancel="watch:${w.id}">✕</button></div>`, "No watches.");
    const sug = this._list(d.suggestions || [], x => `<div class="mem"><span>💡</span><span class="t">${esc(x.text)}</span><button data-acc="${x.id}">Automate</button><button class="ghost" data-dis="${x.id}">✕</button></div>`, "No suggestions yet. Cortex learns from the entities you list under Configure.");
    const rout = this._list(d.routines || [], r => `<div class="row"><span>${esc(r.name)} <span class="muted">${r.schedule ? "at " + esc(r.schedule.at) + " " + esc(r.schedule.days) : r.on_state ? "when " + esc(r.on_state.entity_id) + " is " + esc(r.on_state.to) : "on demand"}</span></span>
      <span><button data-run="${esc(r.name)}">Run</button> <button class="ghost" data-delr="${esc(r.name)}">✕</button></span></div>`, "No routines. Ask the assistant to make one, or accept a suggestion.");
    const speech = this._list((d.speech || []).slice(0, 8), s => `<div class="row"><span>${esc(s.text)}</span><span class="muted">${s.time.slice(11, 16)} ${s.spoken ? "🔊" : "🔇 " + esc(s.reason || "")}</span></div>`, "Nothing said yet.");
    return `<section class="grid">
      ${this._chatCard()}
      <div class="card wide"><h2>Memory (${d.memories.length})</h2>
        <div class="row"><input id="mtext" placeholder="Something worth remembering" style="flex:1"><select id="mcat">${d.categories.map(c => `<option>${esc(c)}</option>`).join("")}</select><button id="madd">Add</button></div>${mem}</div>
      <div class="card w6"><h2>Reminders</h2>${rem}<h2 style="margin-top:12px">Watches</h2>${wat}</div>
      <div class="card w6"><h2>Routines</h2>${rout}</div>
      <div class="card wide"><h2>Suggestions</h2>${sug}</div>
      <div class="card w6"><h2>Tools</h2>
        <div class="row"><span>Backup now (${(d.backups || []).length} saved)</span><button id="backup">Back up</button></div>
        <div class="row"><span>Weekly report</span><button id="weekly">Say it now</button></div>
        <div class="row"><span>Speech ${d.hushed ? "hushed" : "active"}</span><button id="hush">${d.hushed ? "Unhush" : "Hush 1h"}</button></div>
        <div class="muted" id="hmsg"></div></div>
      <div class="card w6"><h2>Recent speech</h2>${speech}</div>
    </section>`;
  }
  _wireAssistant() {
    const r = this._root, click = (id, fn) => { const el = r.querySelector(id); if (el) el.onclick = fn; };
    r.querySelectorAll("[data-del]").forEach(b => b.onclick = () => this._ws({ type: "cortex/memory_delete", target: b.dataset.del }));
    r.querySelectorAll("[data-cancel]").forEach(b => b.onclick = () => { const [kind, id] = b.dataset.cancel.split(":"); this._ws({ type: "cortex/cancel", kind, target: id }); });
    r.querySelectorAll("[data-acc]").forEach(b => b.onclick = () => this._act({ action: "accept_suggestion", target: b.dataset.acc }, () => "Routine created"));
    r.querySelectorAll("[data-dis]").forEach(b => b.onclick = () => this._act({ action: "dismiss_suggestion", target: b.dataset.dis }));
    r.querySelectorAll("[data-run]").forEach(b => b.onclick = () => this._act({ action: "run_routine", target: b.dataset.run }, () => "Ran " + b.dataset.run));
    r.querySelectorAll("[data-delr]").forEach(b => b.onclick = () => this._act({ action: "delete_routine", target: b.dataset.delr }));
    click("#backup", () => this._act({ action: "backup" }, x => "Saved " + String(x).split("/").pop()));
    click("#weekly", () => this._act({ action: "weekly_report" }, () => "Weekly report sent"));
    click("#hush", () => this._ws({ type: "cortex/hush", minutes: this._data.hushed ? 0 : 60 }));
    const add = () => { const t = r.querySelector("#mtext").value.trim(); if (t) this._ws({ type: "cortex/memory_add", text: t, category: r.querySelector("#mcat").value }); };
    click("#madd", add);
    const mt = r.querySelector("#mtext"); if (mt) mt.onkeydown = e => { if (e.key === "Enter") add(); };
    this._flash();
  }
}

/** Rate for an hour from a plan's bands (first match wins), else the default. */
function planRate(bands, def, h) {
  for (const b of bands || []) {
    const dayOk = !b.days || b.days === "all" || (b.days === "weekday") === !!h.biz;
    const inH = b.from <= b.to ? h.hour >= b.from && h.hour < b.to : h.hour >= b.from || h.hour < b.to;
    if (dayOk && inH) return b.rate;
  }
  return def;
}
/** Sankey of today's energy: sources on the left, destinations on the right. */
function sankeySvg(o) {
  const L = [["solar", "Solar", C.solar, o.s2h + o.s2b + o.s2g], ["batt", "Battery", C.batt, o.b2h + o.b2g], ["grid", "Grid", C.grid, o.g2h + o.g2b]];
  const R = [["home", "Home", C.home, o.s2h + o.b2h + o.g2h], ["batt", "Battery", C.batt, o.s2b + o.g2b], ["grid", "Grid", C.grid, o.s2g + o.b2g]];
  const links = [["solar", "home", o.s2h], ["solar", "batt", o.s2b], ["solar", "grid", o.s2g], ["batt", "home", o.b2h], ["batt", "grid", o.b2g], ["grid", "home", o.g2h], ["grid", "batt", o.g2b]];
  const sum = a => a.reduce((t, x) => t + x[3], 0), tot = Math.max(sum(L), sum(R));
  if (tot < 0.05) return '<div class="muted">No energy recorded yet today.</div>';
  const W = 560, H = 250, gap = 16, x0 = 150, x1 = W - 150, k = (H - 20 - gap * 2) / tot;
  const place = arr => { let y = 10; const out = {}; arr.forEach(([id, , , v]) => { const h = v > 0.01 ? Math.max(v * k, 3) : 0; out[id] = { y, h, off: 0, v }; if (h) y += h + gap; }); return out; };
  const lp = place(L), rp = place(R);
  const ribbons = links.filter(l => l[2] > 0.01).map(([a, b, v]) => {
    const w = Math.max(v * k, 1.5), s = lp[a], t = rp[b], sy = s.y + s.off, ty = t.y + t.off, xm = (x0 + x1) / 2;
    s.off += w; t.off += w;
    const col = L.find(x => x[0] === a)[2];
    return `<path d="M${x0} ${sy.toFixed(1)}C${xm} ${sy.toFixed(1)} ${xm} ${ty.toFixed(1)} ${x1} ${ty.toFixed(1)}L${x1} ${(ty + w).toFixed(1)}C${xm} ${(ty + w).toFixed(1)} ${xm} ${(sy + w).toFixed(1)} ${x0} ${(sy + w).toFixed(1)}Z" fill="${col}" class="rib"><title>${a} → ${b}: ${fx(v, 1)} kWh</title></path>`;
  }).join("");
  const nodes = (arr, pos, left) => arr.filter(([id]) => pos[id].h).map(([id, name, col]) => {
    const p = pos[id], x = left ? x0 - 10 : x1, tx = left ? x0 - 18 : x1 + 18, a = left ? "end" : "start", cy = p.y + p.h / 2;
    return `<rect x="${x}" y="${p.y}" width="10" height="${p.h}" rx="4" fill="${col}"/><text x="${tx}" y="${cy - 1}" text-anchor="${a}" class="sk1">${name}</text><text x="${tx}" y="${cy + 14}" text-anchor="${a}" class="sk2">${fx(p.v, 1)} kWh</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="sankey" role="img" aria-label="Today's energy flows">${ribbons}${nodes(L, lp, true)}${nodes(R, rp, false)}</svg>
    <div class="skfoot"><span><b>${fx(o.s2h + o.s2b + o.s2g, 1)}</b> kWh solar · <b>${Math.round((o.s2h + o.s2b) / Math.max(o.s2h + o.s2b + o.s2g, 0.01) * 100)}%</b> kept at home</span><span><b>${fx(o.g2h + o.g2b, 1)}</b> kWh bought · <b>${fx(o.s2g + o.b2g, 1)}</b> kWh sold</span></div>`;
}

// ---- generic charts ------------------------------------------------------
function lineChart(series, o = {}) {
  const W = o.w || 520, H = o.h || 200, L = 40, R = 12, T = 10, B = 22;
  const all = series.flatMap(s => s.data.filter(v => v != null && !Number.isNaN(v)));
  if (!all.length) return `<div class="muted" style="padding:20px">No data yet.</div>`;
  const lo = o.min ?? Math.min(0, ...all), hi = o.max ?? (Math.max(...all, 1) * 1.08), n = series[0].data.length;
  const x = i => L + (i / Math.max(n - 1, 1)) * (W - L - R), y = v => T + (1 - (v - lo) / (hi - lo || 1)) * (H - T - B);
  let g = "";
  for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" opacity=".1"/><text x="${L - 4}" y="${y(v) + 3}" text-anchor="end" class="ax">${Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1)}</text>`; }
  let lab = "";
  if (o.labels) { const st = Math.max(1, Math.ceil(n / 8)); o.labels.forEach((t, i) => { if (i % st === 0) lab += `<text x="${x(i)}" y="${H - 6}" text-anchor="middle" class="ax">${esc(t)}</text>`; }); }
  else if (o.start) for (let k = 0; k <= 6; k++) { const t = new Date(o.start.getTime() + (o.end - o.start) * k / 6); lab += `<text x="${x(k / 6 * (n - 1))}" y="${H - 6}" text-anchor="middle" class="ax">${o.days ? t.toLocaleDateString([], { weekday: "short" }) : t.getHours() + ":00"}</text>`; }
  const path = (d, step) => d.map((v, i) => v == null || Number.isNaN(v) ? "" : (i && d[i - 1] != null && !Number.isNaN(d[i - 1]) ? (step ? `H${x(i).toFixed(1)}V` : "L") : "M") + (step && i && d[i - 1] != null ? y(v).toFixed(1) : x(i).toFixed(1) + " " + y(v).toFixed(1))).join("");
  const body = series.map(s => {
    const d = path(s.data, o.step);
    const area = s.area ? `<path d="${d} L${x(n - 1)} ${y(Math.max(lo, 0))} L${x(0)} ${y(Math.max(lo, 0))} Z" fill="${s.color}" opacity=".16"/>` : "";
    return area + `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round"/>`;
  }).join("");
  return `<div class="chart" style="height:${H}px"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${g}${lab}${body}</svg></div>${legend(series)}`;
}
function legend(series) { return `<div class="lg">${series.map(s => `<span><b style="color:${s.color}">■</b> ${esc(s.name)}</span>`).join("")}</div>`; }
function barChart(days, series, o = {}) {
  const W = o.w || 520, H = o.h || 200, L = 40, R = 12, T = 10, B = 22, n = days.length;
  if (!n) return `<div class="muted" style="padding:20px">No data yet.</div>`;
  const hi = Math.max(...series.flatMap(s => s.data.map(v => v || 0)), 1) * 1.1, gw = (W - L - R) / n, bw = gw / (series.length + 1), every = o.every || Math.ceil(n / 14), dec = o.dec ?? 1, unit = o.unit || "";
  const y = v => T + (1 - v / hi) * (H - T - B);
  let g = "";
  for (let k = 0; k <= 4; k++) { const v = hi * k / 4; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" opacity=".1"/><text x="${L - 4}" y="${y(v) + 3}" text-anchor="end" class="ax">${v.toFixed(hi >= 10 ? 0 : 1)}</text>`; }
  const bars = days.map((d, i) => series.map((s, j) => { const v = s.data[i] || 0; return `<rect x="${L + i * gw + bw / 2 + j * bw}" y="${y(v)}" width="${bw - 1}" height="${H - B - y(v)}" rx="2" fill="${s.color}"><title>${d}: ${s.name} ${unit}${v.toFixed(dec)}</title></rect>`; }).join("")
    + (i % every === 0 ? `<text x="${L + i * gw + gw / 2}" y="${H - 6}" text-anchor="middle" class="ax">${d}</text>` : "")).join("");
  return `<div class="chart" style="height:${H}px"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${g}${bars}</svg></div>${legend(series)}`;
}

// ---- battery visuals: Neovolt ESS tower and SUV, optional PNG overrides --------
const levelColor = p => (p === null ? "#757575" : p < 20 ? C.peak : p < 40 ? C.off_peak : C.shoulder);
// Drop transparent PNGs here to replace the drawings: /config/www/cortex/<name>.png
const BIMG = { house: "/local/cortex/neovolt-ess.png", ev: EV.img }; // EV: the stored BYD photo (HA image entity)
const CAR_BODY = "M26 132C20 126 18 106 21 94C24 86 38 80 62 72C100 52 142 26 192 18C222 14 262 14 294 22C324 30 348 58 364 72C382 78 410 86 420 98C426 106 426 120 422 132L416 140L34 140Z";
const CAR_GLASS = "M348 70C332 44 312 33 288 27L196 26C160 30 120 52 88 70Z";
function carSvg(k) {
  const wheel = x => `<circle cx="${x}" cy="116" r="40" style="fill:var(--card-background-color,#222)"/><circle cx="${x}" cy="116" r="34" fill="#17181a"/><circle cx="${x}" cy="116" r="34" fill="none" stroke="#444" stroke-width="2"/>
      <g class="spin" style="transform-origin:${x}px 116px">${Array.from({ length: 10 }, (_, i) => { const a = i * 36 * Math.PI / 180; return `<line x1="${x + 7 * Math.cos(a)}" y1="${116 + 7 * Math.sin(a)}" x2="${x + 26 * Math.cos(a)}" y2="${116 + 26 * Math.sin(a)}" stroke="#bdbdbd" stroke-width="${i % 2 ? 2 : 4}" stroke-linecap="round"/>`; }).join("")}</g>
      <circle cx="${x}" cy="116" r="27" fill="none" stroke="#e0e0e0" stroke-width="3"/><circle cx="${x}" cy="116" r="6" fill="#9e9e9e"/>`;
  return `<svg viewBox="0 0 440 170" class="battsvg car">
    <defs><clipPath id="cb-${k}"><path d="${CAR_BODY}"/></clipPath><clipPath id="cf-${k}"><rect class="fclip" x="18" y="8" width="0" height="140"/></clipPath>
      <linearGradient id="cg-${k}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/></linearGradient>
      <linearGradient id="cs-${k}"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".6"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
      <linearGradient id="gl-${k}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#cfe8ff" stop-opacity=".55"/><stop offset="1" stop-color="#1b2a38" stop-opacity=".85"/></linearGradient></defs>
    <ellipse class="cglow" cx="222" cy="156" rx="190" ry="11"/>
    <line class="cflow" x1="0" x2="215" y1="160" y2="160" stroke-width="3" stroke-dasharray="6 10" stroke-linecap="round"/>
    <g clip-path="url(#cb-${k})"><path d="${CAR_BODY}" fill="currentColor" opacity=".13"/>
      <rect class="bfill" x="18" y="8" width="0" height="140"/><rect class="bfill" style="fill:url(#cg-${k})" x="18" y="8" width="0" height="140"/>
      <g clip-path="url(#cf-${k})"><rect class="bsheen" x="-90" y="8" width="90" height="140" fill="url(#cs-${k})"/></g></g>
    <path d="${CAR_GLASS}" fill="url(#gl-${k})"/><line x1="214" x2="214" y1="26" y2="70" stroke="currentColor" stroke-opacity=".5" stroke-width="3"/>
    <path d="M26 132C20 126 18 106 21 94C24 86 38 80 62 72C100 52 142 26 192 18C222 14 262 14 294 22C324 30 348 58 364 72C382 78 410 86 420 98C426 106 426 120 422 132L416 140L34 140Z" fill="none" stroke="currentColor" stroke-width="3" opacity=".65" stroke-linejoin="round"/>
    <path d="M214 70C212 90 212 112 214 128M302 70C300 90 300 112 302 128" fill="none" stroke="currentColor" stroke-opacity=".4" stroke-width="2"/>
    <path d="M196 84h14M284 84h14" stroke="currentColor" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>
    <path d="M356 70l16 2c3 1 3 5-1 6l-14 1z" fill="currentColor" opacity=".55"/>
    <path d="M60 134L360 134" stroke="currentColor" stroke-opacity=".35" stroke-width="3"/>
    <path class="clamp" d="M396 92C406 94 414 98 420 104L418 108C410 104 402 101 392 100Z" fill="#fff59d"/>
    <path class="ctail" d="M21 94C22 90 26 88 30 86L40 84L40 90L26 98Z" fill="#ef5350"/>
    <circle cx="62" cy="100" r="5" style="fill:var(--card-background-color,#222)" stroke="currentColor" stroke-opacity=".8"/><path class="cbolt" d="M63 94l-5 8h4l-2 7 6-9h-4z" fill="#fff59d"/>
    <g class="wheels">${wheel(105)}${wheel(372)}</g><g class="bmarks"></g></svg>`;
}
function towerSvg(k) {
  const mods = Array.from({ length: 5 }, (_, i) => `<rect x="36" y="${17 + i * 41}" width="108" height="3" style="fill:var(--card-background-color,#222)"/>`).join("");
  const wave = "M-40 0" + Array.from({ length: 12 }, () => " q10 -6 20 0 t20 0").join("");
  return `<svg viewBox="0 0 190 240" class="battsvg tower">
    <defs><clipPath id="tb-${k}"><rect x="36" y="14" width="108" height="206" rx="10"/></clipPath>
      <linearGradient id="tg-${k}" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".22"/><stop offset=".35" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient></defs>
    <rect x="30" y="224" width="120" height="8" rx="3" fill="currentColor" opacity=".35"/>
    <g clip-path="url(#tb-${k})"><rect x="36" y="14" width="108" height="206" fill="currentColor" opacity=".08"/>
      <g class="twrap"><g class="twaveg"><path class="bfill twv" d="${wave} V260 H-40Z"/></g></g>
      <rect class="bfill tfl" x="36" y="220" width="108" height="0"/>${mods}
      <rect x="36" y="14" width="108" height="206" fill="url(#tg-${k})"/></g>
    <rect x="30" y="8" width="120" height="216" rx="14" fill="none" stroke="currentColor" stroke-width="3" opacity=".6"/>
    <rect x="48" y="22" width="40" height="7" rx="3" fill="currentColor" opacity=".28"/><circle class="tled" cx="126" cy="26" r="4"/>
    <g class="tflow tdn">${[0, 1, 2].map(i => `<path class="tch" style="animation-delay:${-i * 0.55}s" d="M164 191 l8 9 l8 -9" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`).join("")}</g>
    <g class="tflow tup">${[0, 1, 2].map(i => `<path class="tch" style="animation-delay:${-i * 0.55}s" d="M164 200 l8 -9 l8 9" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`).join("")}</g>
    <g class="bmarks"></g></svg>`;
}
function towerLevel(el, p, col) {
  const h = 206 * p / 100, y = 220 - h;
  el.querySelectorAll(".twv,.tfl").forEach(r => { r.style.fill = col; });
  const tf = el.querySelector(".tfl"); tf.style.y = y + "px"; tf.style.height = h + "px";
  el.querySelector(".twrap").style.transform = `translateY(${y + 2}px)`;
}
// Battery % chip and plug badge laid over the BYD photo
function carOverlay() {
  return `<div class="csoc"><span class="cbat"><i></i></span><b>–</b></div>
    <div class="cplug" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2v5M15 2v5M6 7h12v3a6 6 0 0 1-12 0zM12 16v6"/></svg><span></span></div>`;
}
function carOverlaySet(root, pct, plugged, charging) {
  const p = pct === null || pct === undefined ? null : Math.max(0, Math.min(pct, 100)), col = levelColor(p);
  root.querySelectorAll(".csoc").forEach(e => { e.style.setProperty("--p", p ?? 0); e.style.setProperty("--lc", col); e.querySelector("b").textContent = p === null ? "–" : Math.round(p) + "%"; });
  root.querySelectorAll(".cplug").forEach(e => {
    const on = !!(plugged || charging); e.hidden = !on; e.classList.toggle("chg", !!charging);
    e.querySelector("span").textContent = charging ? "Charging" : "Plugged in";
  });
}
function battHTML(key, label) {
  return `<div class="batt ${key === "ev" ? "carw" : "towerw"}" data-b="${key}">
    <div class="bstage">${key === "ev" ? carSvg(key) : towerSvg(key)}
      <div class="bimg" hidden><img alt=""><div class="bfl"></div><div class="bimk"></div>${key === "ev" ? carOverlay() : ""}</div></div>
    ${key === "ev" ? `<div class="bbar" hidden><i></i><span class="bmk"></span></div>` : ""}
    <div class="battmeta"><span class="bbig"></span><b>${esc(label)}</b><span class="muted bsub"></span></div></div>`;
}
function cutout(im) {
  try {
    const W = Math.min(im.naturalWidth, 720), H = Math.round(im.naturalHeight * W / im.naturalWidth);
    const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
    const cx = cv.getContext("2d", { willReadFrequently: true }); cx.drawImage(im, 0, 0, W, H);
    const img = cx.getImageData(0, 0, W, H), d = img.data;
    if (d[3] < 200 || d[(W - 1) * 4 + 3] < 200) return null; // already transparent
    const px = (x, y) => (y * W + x) * 4, corners = [[0, 0], [W - 1, 0], [0, H - 1], [W - 1, H - 1]].map(([x, y]) => [d[px(x, y)], d[px(x, y) + 1], d[px(x, y) + 2]]);
    const ref = [0, 1, 2].map(c => corners.reduce((a, k) => a + k[c], 0) / 4), tol = 46, seen = new Uint8Array(W * H), q = [];
    const near = i => { const j = i * 4; return Math.hypot(d[j] - ref[0], d[j + 1] - ref[1], d[j + 2] - ref[2]) < tol; };
    const push = i => { if (!seen[i] && near(i)) { seen[i] = 1; q.push(i); } };
    for (let x = 0; x < W; x++) { push(x); push((H - 1) * W + x); }
    for (let y = 0; y < H; y++) { push(y * W); push(y * W + W - 1); }
    while (q.length) { const i = q.pop(), x = i % W, y = (i / W) | 0; if (x > 0) push(i - 1); if (x < W - 1) push(i + 1); if (y > 0) push(i - W); if (y < H - 1) push(i + W); }
    let n = 0; for (let i = 0; i < seen.length; i++) if (seen[i]) { d[i * 4 + 3] = 0; n++; }
    const frac = n / seen.length; if (frac < 0.15 || frac > 0.92) return null;
    cx.putImageData(img, 0, 0); return cv.toDataURL("image/png");
  } catch (e) { return null; }
}
function battImg(root) {
  if (root._img !== undefined) return;
  root._img = "pending";
  const key = root.dataset.b, im = new Image();
  im.onload = () => {
    root._img = "ok";
    const wrap = root.querySelector(".bimg"), pic = wrap.querySelector("img");
    const plain = key === "ev", src = plain ? BIMG.ev : (cutout(im) || BIMG[key]);
    pic.src = src; wrap.style.setProperty("--m", `url("${src}")`);
    wrap.hidden = false; root.querySelector(".battsvg").style.display = "none"; root.classList.add("photo");
    if (plain) { root._img = "plain"; wrap.classList.add("plain"); root.querySelector(".bbar").hidden = false; }
    if (root._last) battSet(root, root._last);
  };
  im.onerror = () => { root._img = "no"; };
  im.src = BIMG[key];
}
function battSet(root, o) {
  if (!root) return;
  root._last = o; battImg(root);
  const pct = o.pct === null || o.pct === undefined ? null : Math.max(0, Math.min(o.pct, 100)), p = pct ?? 0, col = levelColor(pct), ev = root.dataset.b === "ev";
  root.classList.toggle("plug", !!(o.plugged || o.charging)); root.classList.toggle("chg", !!o.charging); root.classList.toggle("dis", !!o.discharging); root.style.setProperty("--bc", col);
  root.querySelector(".bbig").textContent = pct === null ? "–" : Math.round(pct) + "%";
  root.querySelector(".bsub").textContent = o.sub || "";
  const marks = (o.marks || []).filter(m => m.pct !== null && m.pct !== undefined);
  if (root._img === "plain") {
    const bar = root.querySelector(".bbar");
    bar.querySelector("i").style.width = p + "%"; carOverlaySet(root, pct, o.plugged, o.charging);
    bar.querySelector(".bmk").innerHTML = marks.map(m => `<u title="${esc(m.label)} ${Math.round(m.pct)}%" style="left:${m.pct}%;background:${m.color}"></u>`).join("");
    return;
  }
  if (root._img === "ok") {
    const wrap = root.querySelector(".bimg");
    wrap.style.setProperty(ev ? "--r" : "--t", (100 - p) + "%");
    root.querySelector(".bimk").innerHTML = marks.map(m => `<i title="${esc(m.label)} ${Math.round(m.pct)}%" style="background:${m.color};${ev ? `left:${m.pct}%;top:0;bottom:0;width:3px` : `bottom:${m.pct}%;left:0;right:0;height:3px`}"></i>`).join("");
    return;
  }
  root.querySelectorAll(".bfill").forEach((r, i) => { if (!i || r.classList.contains("twv") || r.classList.contains("tfl")) r.style.fill = col; });
  if (ev) {
    const w = 406 * p / 100;
    root.querySelectorAll(".bfill").forEach(r => { r.style.width = w + "px"; }); root.querySelector(".fclip").style.width = w + "px";
    root.querySelector(".bmarks").innerHTML = marks.map(m => { const x = 18 + 406 * m.pct / 100; return `<g><title>${esc(m.label)} ${Math.round(m.pct)}%</title><line x1="${x}" x2="${x}" y1="8" y2="148" stroke="${m.color}" stroke-width="3" stroke-dasharray="5 3"/><circle cx="${x}" cy="8" r="4" fill="${m.color}"/></g>`; }).join("");
  } else {
    towerLevel(root, p, col); const y = 220 - 206 * p / 100;
    root.querySelector(".bmarks").innerHTML = marks.map(m => { const my = 220 - 206 * m.pct / 100; return `<g><title>${esc(m.label)} ${Math.round(m.pct)}%</title><line x1="26" x2="154" y1="${my}" y2="${my}" stroke="${m.color}" stroke-width="3" stroke-dasharray="5 3"/><circle cx="26" cy="${my}" r="4" fill="${m.color}"/></g>`; }).join("");
  }
}

// ---- SVG pieces ---------------------------------------------------------
function gauge(pct, label, color, sub) {
  const r = 46, c = 2 * Math.PI * r, p = pct === null ? 0 : Math.max(0, Math.min(pct, 100)) / 100;
  return `<div class="gauge"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="${r}" fill="none" stroke="currentColor" opacity=".12" stroke-width="10"/>
    <circle cx="60" cy="60" r="${r}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="round"
      stroke-dasharray="${c * p} ${c}" transform="rotate(-90 60 60)"/>
    <text x="60" y="64" text-anchor="middle" class="gv">${pct === null ? "–" : Math.round(pct) + "%"}</text></svg>
    <b>${label}</b><span class="muted">${esc(sub)}</span></div>`;
}

/** Live power flow: five tiles joined by animated links (dots travel in the direction of the energy). */
function flowSvg(f, o = {}) {
  const cp = !!o.compact, W = cp ? 400 : 560, side = cp ? 58 : 84;
  const P = { solar: [W / 2, 52], grid: [side, 164], home: [W / 2, 164], batt: [W - side, 164], ev: [W / 2, 276] };
  const sz = big => [big ? (cp ? 124 : 136) : (cp ? 96 : 112), big ? 96 : 76];
  const node = (k, label, kw, color, ic, big) => {
    const [cx, cy] = P[k], [w, h] = sz(big), on = Math.abs(kw) >= 0.05;
    return `<g class="node ${on ? "act" : ""}" style="--nc:${color}"><rect x="${cx - w / 2}" y="${cy - h / 2}" width="${w}" height="${h}" rx="24" class="nbg"/>
      <g transform="translate(${cx - 12} ${cy - h / 2 + 9})" class="nic" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[ic]}</g>
      <text x="${cx}" y="${cy + (big ? 14 : 11)}" text-anchor="middle" class="nval${big ? " big" : ""}">${fx(Math.abs(kw))}<tspan class="nu"> kW</tspan></text>
      <text x="${cx}" y="${cy + h / 2 - 9}" text-anchor="middle" class="nlab">${esc(label)}</text></g>`;
  };
  const link = (a, b, kw, color) => {
    const [[x1, y1], [x2, y2]] = [a, b], base = `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="lk"/>`;
    if (Math.abs(kw) < 0.05) return base;
    const rev = kw < 0, w = Math.round(Math.min(3 + Math.abs(kw) * 0.7, 8) * 2) / 2, dur = Math.round(Math.max(0.6, 2.4 - Math.abs(kw) * 0.16) * 10) / 10;
    const [sx, sy, ex, ey] = rev ? [x2, y2, x1, y1] : [x1, y1, x2, y2];
    return base + `<line x1="${sx}" y1="${sy}" x2="${ex}" y2="${ey}" stroke="${color}" stroke-width="${w}" stroke-linecap="round" stroke-dasharray="0.1 14" class="flow" style="animation-duration:${dur}s"/>`;
  };
  const [sw] = sz(false), [hw] = sz(true), hx = P.home[0];
  const soc = o.soc === null || o.soc === undefined ? "" : ` · ${Math.round(o.soc)}%`;
  return `<svg viewBox="0 0 ${W} 330" class="flowsvg" role="img" aria-label="Live power flow">
    ${link([hx, 90], [hx, 116], f.pv, C.solar)}${link([side + sw / 2, 164], [hx - hw / 2, 164], f.grid, C.grid)}${link([hx + hw / 2, 164], [W - side - sw / 2, 164], f.batt, C.batt)}${link([hx, 212], [hx, 238], f.ev, C.ev)}
    ${node("solar", "Solar", f.pv, C.solar, "sun")}${node("grid", f.grid > 0.05 ? "Importing" : f.grid < -0.05 ? "Exporting" : "Grid", f.grid, C.grid, "grid")}
    ${node("batt", (f.batt > 0.05 ? "Charging" : f.batt < -0.05 ? "Discharging" : "Battery") + soc, f.batt, C.batt, "battery")}
    ${node("ev", "EV", f.ev, C.ev, "car")}${node("home", "Home", f.home, C.home, "home", true)}</svg>`;
}

/** Half-circle battery gauge with reserve marker. */
function arcGauge(pct, o) {
  const R = 100, cx = 130, cy = 120, len = Math.PI * R, p = pct === null || pct === undefined ? 0 : Math.max(0, Math.min(pct, 100)) / 100;
  const d = `M${cx - R} ${cy} A${R} ${R} 0 0 1 ${cx + R} ${cy}`;
  const ticks = (o.marks || []).filter(m => m.pct !== null && m.pct !== undefined).map(m => {
    const a = Math.PI * (1 - m.pct / 100), c = Math.cos(a), s = Math.sin(a);
    return `<line x1="${(cx + (R - 17) * c).toFixed(1)}" y1="${(cy - (R - 17) * s).toFixed(1)}" x2="${(cx + (R + 17) * c).toFixed(1)}" y2="${(cy - (R + 17) * s).toFixed(1)}" stroke="${m.color}" stroke-width="3" stroke-linecap="round"><title>${esc(m.label)} ${Math.round(m.pct)}%</title></line>`;
  }).join("");
  return `<svg viewBox="0 0 260 150" class="arc" role="img" aria-label="Battery ${pct === null ? "unknown" : Math.round(pct) + " percent"}">
    <path d="${d}" fill="none" class="atrack" stroke-width="22" stroke-linecap="round"/>
    <path d="${d}" fill="none" stroke="${o.color}" stroke-width="22" stroke-linecap="round" stroke-dasharray="${(len * p).toFixed(1)} ${len.toFixed(1)}"/>
    ${ticks}
    <text x="130" y="62" text-anchor="middle" class="astate">${esc(o.state)}</text>
    <text x="130" y="112" text-anchor="middle" class="abig">${pct === null || pct === undefined ? "–" : Math.round(pct)}<tspan class="apc">%</tspan></text></svg>
    <div class="asub">${esc(o.sub || "")}</div>`;
}

/** Three vertical pill bars: generated so far, today's forecast, tomorrow's forecast, with the low-solar line. */
function solarBars(gen, fc, tom, low, day) {
  const mx = Math.max(gen || 0, fc || 0, tom || 0, low || 0, 1) * 1.12, h = v => (v === null || v === undefined ? 0 : Math.min(v / mx, 1) * 100);
  const col = [C.solar, "var(--o)", "color-mix(in srgb,var(--o) 45%,var(--surface3))"], vals = [gen, fc, tom], lab = ["So far", "Forecast", "Tomorrow"];
  const dc = day === "low" ? C.peak : C.shoulder;
  return `<div class="vbs"><div class="vtr">${vals.map((v, i) => `<div class="vbt"><i style="height:${h(v)}%;background:${col[i]}"></i></div>`).join("")}
      ${low ? `<u class="vline" style="bottom:${h(low)}%"><span>low-solar ${fx(low, 0)}</span></u>` : ""}</div>
    <div class="vlab">${vals.map((v, i) => `<div><b>${v === null || v === undefined ? "–" : fx(v, 0)}<small> kWh</small></b><span>${lab[i]}</span></div>`).join("")}</div>
    <div class="vsub"><span class="dot" style="background:${dc}"></span>${esc(day || "–")} solar day</div></div>`;
}

/** One rounded bar split into solar used on site, sent to the grid and drawn from the grid. */
function mixBar(self, exp, imp) {
  const tot = self + exp + imp;
  if (tot < 0.05) return `<div class="muted">No energy recorded yet today.</div>`;
  const seg = [["Solar used at home", self, C.solar], ["Sent to grid", exp, C.shoulder], ["Bought from grid", imp, C.grid]];
  return `<div class="mixbar">${seg.map(([n, v, c]) => `<i style="flex:${Math.max(v, 0.001)};background:${c}" title="${n} ${fx(v, 1)} kWh"></i>`).join("")}</div>
    <div class="mixleg">${seg.map(([n, v, c]) => `<div><span class="dot" style="background:${c}"></span><span class="mn">${n}</span><b>${fx(v, 1)}<small> kWh</small></b><span class="muted">${Math.round(v / tot * 100)}%</span></div>`).join("")}</div>`;
}

/** Gauge of today's solar surplus (left, green) or shortfall (right, amber to red). */
function shortGauge(v) {
  const lo = -20, hi = 30, pt = (deg, rr = 80) => { const a = (180 - deg) * Math.PI / 180; return [(100 + rr * Math.cos(a)).toFixed(1), (100 - rr * Math.sin(a)).toFixed(1)]; };
  const arc = (a, b) => { const [x1, y1] = pt(a), [x2, y2] = pt(b); return `M${x1} ${y1} A80 80 0 0 1 ${x2} ${y2}`; };
  const deg = x => 180 * (x - lo) / (hi - lo), rot = -90 + (v === null || v === undefined ? 0 : 180 * (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo));
  const msg = v === null || v === undefined ? "–" : v <= 0 ? `<b style="color:${C.shoulder}">${fx(-v, 1)} kWh surplus</b><span>no top-up needed</span>` : `<b style="color:${v > 10 ? C.peak : C.off_peak}">${fx(v, 1)} kWh short</b><span>grid top-up likely</span>`;
  return `<svg viewBox="0 0 200 118" class="fuel" role="img" aria-label="Solar shortfall gauge">
    <path d="${arc(0, deg(0))}" fill="none" stroke="${C.shoulder}" stroke-width="14" stroke-linecap="round"/><path d="${arc(deg(0) + 3, deg(10))}" fill="none" stroke="${C.off_peak}" stroke-width="14"/><path d="${arc(deg(10) + 3, 180)}" fill="none" stroke="${C.peak}" stroke-width="14" stroke-linecap="round"/>
    <g style="transform-origin:100px 100px;transform:rotate(${rot}deg);transition:transform 1s cubic-bezier(.3,1.4,.5,1)"><line x1="100" y1="100" x2="100" y2="36" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></g>
    <circle cx="100" cy="100" r="8" fill="currentColor"/></svg><div class="vsub shortmsg">${msg}</div>`;
}

const CSS = `
*,*:before,*:after{box-sizing:border-box}
:host{
  --o:#FF5401;--o-deep:#D14400;--y:#FDC111;
  --bg:#ECE8E1;--surface:#FBFAF8;--surface2:#F3F0EB;--surface3:#E4DFD7;
  --text:#1E1B18;--muted:#6A635B;--line:rgba(30,27,24,.10);--nav:rgba(30,27,24,.06);
  --good:#15803D;--warn:#B45309;--bad:#C62828;
  --shadow:0 1px 2px rgba(70,45,20,.06),0 10px 28px rgba(70,45,20,.07);
  --r-md:16px;--r-lg:24px;--r-pill:999px;
  --primary-text-color:var(--text);--secondary-text-color:var(--muted);--card-background-color:var(--surface);--primary-background-color:var(--bg);
  --divider-color:var(--line);--primary-color:var(--o-deep);--text-primary-color:#fff;
  display:block;position:relative;isolation:isolate;min-height:100%;padding:20px 24px 56px;color:var(--text);background:var(--bg);
  --ff:"Inter","SF Pro Text",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font:15px/1.45 var(--ff);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased;
  color-scheme:light}
:host([data-theme=dark]){
  --bg:#14110E;--surface:#1D1915;--surface2:#27221D;--surface3:#352F28;
  --text:#F4EFE9;--muted:#A9A198;--line:rgba(244,239,233,.11);--nav:rgba(255,255,255,.07);
  --o:#FF6A22;--o-deep:#FF6A22;--good:#4ADE80;--warn:#FBBF24;--bad:#FF7A7A;
  --shadow:0 1px 2px #0007,0 12px 30px #0006;--text-primary-color:#1A0E05;color-scheme:dark}
.bg{position:absolute;inset:0;z-index:-1;pointer-events:none;background:center 0/cover no-repeat;opacity:0;transition:opacity .8s;-webkit-mask-image:linear-gradient(#000,transparent 60%);mask-image:linear-gradient(#000,transparent 60%)}
.bg.on{opacity:.22}:host([data-theme=dark]) .bg.on{opacity:.12}

/* ---- header ---- */
.top{display:flex;align-items:center;gap:18px;max-width:1360px;margin:0 auto 22px}
.brand{display:flex;align-items:center;gap:12px;min-width:0}.brand h1{font-size:20px;line-height:1.1;margin:0;font-weight:700;letter-spacing:-.01em}
.logo{border-radius:12px;box-shadow:var(--shadow);flex:none}.sub{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
nav#tabs{display:flex;gap:2px;padding:5px;background:var(--nav);border-radius:var(--r-pill);margin:0 auto}
nav#tabs button{display:flex;align-items:center;gap:8px;background:transparent;color:var(--muted);padding:9px 16px;min-height:42px;font-weight:600}
nav#tabs button:hover{color:var(--text);background:color-mix(in srgb,var(--surface) 60%,transparent);filter:none}
nav#tabs button.on{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}nav#tabs button.on .ic{color:var(--o)}
.ic{width:20px;height:20px;flex:none}
.tools{display:flex;align-items:center;gap:8px;margin-left:auto}.clock{font-size:14px;color:var(--muted);margin-right:4px}
.ib{position:relative;width:42px;height:42px;padding:0;border-radius:50%;background:var(--surface);color:var(--text);border:1px solid var(--line);display:grid;place-items:center;box-shadow:var(--shadow)}
.ib .auto{position:absolute;right:-2px;bottom:-2px;font:700 9px/14px var(--ff);width:14px;height:14px;border-radius:50%;background:var(--o);color:var(--text-primary-color);text-align:center;font-style:normal}
.badge{position:absolute;top:-3px;right:-3px;min-width:18px;height:18px;border-radius:9px;background:var(--bad);color:#fff;font:700 11px/18px var(--ff);text-align:center;padding:0 4px;font-style:normal}.badge[hidden]{display:none}
@media (max-width:1440px){nav#tabs button span{display:none}nav#tabs button.on span{display:inline}.clock{display:none}}
@media (max-width:760px){
  .gdate{display:none}.chead{flex-wrap:wrap}.chead h2{white-space:nowrap}.legend{font-size:12px;gap:8px}
  :host{padding:14px 14px 104px}.top{margin-bottom:16px}.brand h1{font-size:18px}
  nav#tabs{position:fixed;left:50%;bottom:max(12px,env(safe-area-inset-bottom));transform:translateX(-50%);z-index:20;width:calc(100% - 24px);max-width:460px;justify-content:space-between;padding:6px;
    background:color-mix(in srgb,var(--surface) 90%,transparent);-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px);border:1px solid var(--line);box-shadow:0 10px 36px #0004}
  nav#tabs button{flex-direction:column;gap:3px;padding:7px 2px;min-height:54px;flex:1;min-width:0;font-size:10.5px;border-radius:20px}
  nav#tabs button span,nav#tabs button.on span{display:inline}nav#tabs button .ic{width:22px;height:22px}}

/* ---- layout ---- */
.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px;max-width:1360px;margin:0 auto;grid-auto-flow:dense}
.card{grid-column:span 4;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:20px;box-shadow:var(--shadow);min-width:0;position:relative}
.wide{grid-column:1/-1}.w4{grid-column:span 4}.w6{grid-column:span 6}.w8{grid-column:span 8}
@media (max-width:1100px){.card,.w4,.w6{grid-column:span 6}.w8,.side{grid-column:1/-1}}
@media (max-width:720px){.card,.w4,.w6,.w8,.side{grid-column:1/-1}.card{padding:16px;border-radius:20px}}
h2{font-size:15px;margin:0 0 12px;font-weight:650;letter-spacing:-.005em;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
h2 .muted,h3 .muted{font-weight:400;font-size:12.5px}
h3{font-size:13px;margin:6px 0 8px;font-weight:650;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.chead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}.chead h2{margin:0}
.muted{color:var(--muted);font-size:13px}
.legend,.lg{font-weight:500;font-size:12.5px;color:var(--muted);display:flex;gap:12px;flex-wrap:wrap}.lg{margin-top:6px}.legend b{font-size:10px}
.sep{height:1px;background:var(--line);margin:16px 0}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:middle}
.skel{min-height:96px;background:linear-gradient(100deg,var(--surface) 30%,var(--surface2) 50%,var(--surface) 70%);background-size:200% 100%;animation:shim 1.4s linear infinite}.skel.tall{min-height:320px}
@keyframes shim{to{background-position:-200% 0}}

/* ---- type ---- */
.big{font-size:32px;font-weight:700;line-height:1.15;letter-spacing:-.02em}.big small{font-size:14px;font-weight:500;color:var(--muted);margin-left:6px;letter-spacing:0}
.n{font-size:30px;font-weight:700;letter-spacing:-.025em;line-height:1.1}.dec{color:var(--muted);font-weight:500}.u{font-size:13px;color:var(--muted);margin-left:5px;font-weight:500}
.ok{color:var(--good)}.bad{color:var(--bad)}.right{text-align:right}
.hero-top{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}

/* ---- controls ---- */
button{font:600 14px/1 var(--ff);cursor:pointer;border:0;border-radius:var(--r-pill);padding:11px 18px;min-height:40px;background:var(--primary-color);color:var(--text-primary-color);transition:transform .12s,filter .15s,background .15s,box-shadow .15s}
button:hover{filter:brightness(1.07)}button:active{transform:scale(.97)}button:disabled{opacity:.5;cursor:default}
button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid color-mix(in srgb,var(--o) 55%,transparent);outline-offset:2px}
button.ghost{background:transparent;color:var(--muted);padding:6px 10px;min-height:32px;font-weight:500}button.ghost:hover{background:var(--surface2);color:var(--text);filter:none}
button.go{width:36px;height:36px;min-height:0;padding:0;display:grid;place-items:center;background:var(--surface2);color:var(--text);flex:none}button.go:hover{background:var(--surface3);filter:none}button.go .ic{width:18px;height:18px}
.seg{display:inline-flex;gap:2px;padding:3px;background:var(--surface2);border-radius:var(--r-pill)}
.seg button{background:transparent;color:var(--muted);padding:7px 14px;min-height:34px;font-weight:600}.seg button:hover{color:var(--text);filter:none}
.seg button.on{background:var(--primary-color);color:var(--text-primary-color)}
input,select{font:500 14px var(--ff);color:var(--text);background:var(--surface2);border:1px solid var(--line);border-radius:12px;padding:9px 12px;min-height:40px}
input[type=range]{padding:0;border:0;background:transparent;min-height:28px;accent-color:var(--o-deep)}
input[type=time]{padding:7px 10px}
.num{width:96px;text-align:right}
input.sw{appearance:none;-webkit-appearance:none;width:46px;height:28px;min-height:0;border-radius:99px;background:var(--surface3);position:relative;cursor:pointer;border:0;padding:0;transition:background .2s;flex:none}
input.sw:after{content:"";position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:#fff;box-shadow:0 1px 3px #0005;transition:transform .2s}
input.sw:checked{background:var(--o)}input.sw:checked:after{transform:translateX(18px)}
.tg{position:relative;display:inline-block;width:46px;height:28px;flex:none}.tg input{opacity:0;width:0;height:0;position:absolute;min-height:0}
.tg i{position:absolute;inset:0;border-radius:99px;background:var(--surface3);transition:background .2s;cursor:pointer}
.tg i:after{content:"";position:absolute;left:3px;top:3px;width:22px;height:22px;border-radius:50%;background:#fff;transition:transform .2s;box-shadow:0 1px 3px #0005}
.tg input:checked+i{background:var(--o)}.tg input:checked+i:after{transform:translateX(18px)}.tg input:focus-visible+i{outline:3px solid color-mix(in srgb,var(--o) 55%,transparent);outline-offset:2px}
.pill{--pc:#8a8279;display:inline-flex;align-items:center;padding:4px 12px;border-radius:var(--r-pill);font-size:12.5px;font-weight:650;text-transform:capitalize;white-space:nowrap;
  background:color-mix(in srgb,var(--pc) 18%,transparent);color:color-mix(in srgb,var(--pc) 55%,var(--text));border:1px solid color-mix(in srgb,var(--pc) 30%,transparent)}
button.pill{min-height:0;font:650 12.5px/1 var(--ff);padding:5px 12px}
.chip{display:inline-flex;align-items:center;gap:7px;padding:4px 12px;border-radius:var(--r-pill);font-size:12.5px;font-weight:600;background:var(--surface2);color:var(--muted)}
.chip.live i{width:8px;height:8px;border-radius:50%;background:var(--good);animation:blink 1.6s ease-in-out infinite}

/* ---- rows, stats ---- */
.row{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center;flex-wrap:wrap}.row:last-child{border-bottom:0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.stat{display:flex;flex-direction:column;gap:2px;background:var(--surface2);border:0 solid;border-radius:var(--r-md);padding:12px 14px;position:relative}
.stat:before{content:"";position:absolute;top:14px;right:14px;width:0;height:0;border:4px solid;border-color:inherit;border-radius:50%}
.stat b{font-size:20px;font-weight:700;letter-spacing:-.01em}.stat b small{font-size:12px;font-weight:500;color:var(--muted);margin-left:3px}.stat .muted{font-size:12.5px}
.hbar{display:grid;grid-template-columns:74px 1fr 70px;gap:8px;align-items:center;margin:8px 0}
.hbar div{height:12px;background:var(--surface3);border-radius:6px;overflow:hidden}.hbar i{display:block;height:100%;border-radius:6px}
.mem{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center}.mem .t{flex:1}
.phase{display:grid;grid-template-columns:44px 1fr 36px;gap:8px;align-items:center;margin:6px 0;font-size:13px}
.phase div{height:10px;background:var(--surface3);border-radius:5px;overflow:hidden}.phase i{display:block;height:100%;border-radius:5px;transition:width .6s}.phase b{text-align:right}

/* ---- NOW ---- */
.insight{display:flex;align-items:center;gap:14px;padding:14px 18px;border-radius:var(--r-lg)}
.iic{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;flex:none;background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.insight.warn .iic{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}.insight.warn{border-color:color-mix(in srgb,var(--warn) 35%,var(--line))}
.itx{display:flex;flex-direction:column;min-width:0;flex:1}.itx b{font-size:15px}.itx span{font-size:13.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;padding:6px 8px}
.kpi{display:flex;gap:14px;align-items:center;padding:14px 16px;border-left:1px solid var(--line);min-width:0}.kpi:first-child{border-left:0}
.kic{width:44px;height:44px;border-radius:15px;display:grid;place-items:center;flex:none;background:color-mix(in srgb,var(--k) 18%,transparent);color:color-mix(in srgb,var(--k) 72%,var(--text))}
.klab{font-size:13px;color:var(--muted);font-weight:500}.kval{line-height:1.15}.ksub{font-size:12.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kbody{min-width:0}
@media (max-width:1000px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi:nth-child(3){border-left:0}.kpi:nth-child(n+3){border-top:1px solid var(--line)}}
@media (max-width:480px){.kpi{padding:12px 8px;gap:10px}.kic{width:38px;height:38px}.n{font-size:24px}.ksub{white-space:normal}.insight{flex-wrap:wrap}.itx{flex-basis:calc(100% - 60px)}}
.hero{display:flex;flex-direction:column}#flow{flex:1;display:flex;align-items:center}.flowsvg{width:100%;max-height:400px;display:block;margin:0 auto}
.lk{stroke:var(--surface3);stroke-width:3;stroke-linecap:round}
.flow{animation:dash linear infinite}@keyframes dash{to{stroke-dashoffset:-14.1}}
.nbg{fill:var(--surface2);stroke:var(--line);stroke-width:1.5;transition:fill .4s,stroke .4s}
.node.act .nbg{stroke:var(--nc);stroke-width:2;fill:color-mix(in srgb,var(--nc) 11%,var(--surface))}
.nic{color:color-mix(in srgb,var(--nc) 80%,var(--text));opacity:.55}.node.act .nic{opacity:1}
.nval{font:700 17px var(--ff);fill:var(--text)}.nval.big{font-size:23px}.nu{font:500 11px var(--ff);fill:var(--muted)}.nlab{font:500 11px var(--ff);fill:var(--muted)}
.arc{width:100%;max-width:300px;display:block;margin:0 auto}.atrack{stroke:var(--surface3)}.astate{font:600 12.5px var(--ff);fill:var(--muted)}
.abig{font:700 44px var(--ff);fill:var(--text);letter-spacing:-.03em}.apc{font-size:20px;font-weight:500;fill:var(--muted)}
.asub{text-align:center;color:var(--muted);font-size:13px;margin-top:-4px}
.ratenow{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
.ribbon{display:flex;gap:3px;height:28px}.ribbon i{flex:1;border-radius:7px;opacity:.72}.ribbon i.cur{opacity:1;outline:2px solid var(--text);outline-offset:2px}
.ticks{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:5px}
.nextline{font-size:13px;color:var(--muted);margin-top:10px}.nextline b{text-transform:capitalize}
.prog{height:6px;background:var(--surface3);border-radius:3px;margin-top:8px;overflow:hidden}.prog i{display:block;height:100%;border-radius:3px;transition:width 1s}
.chart{width:100%;position:relative;height:240px}.chart svg{display:block;width:100%;height:100%;color:var(--text);touch-action:pan-y}#chart{height:auto}#chart svg{height:auto}
.ax{font-size:10.5px;fill:var(--muted)}.gl{stroke:var(--line);stroke-dasharray:3 5}.zl{stroke:var(--surface3)}.cur{stroke:var(--text);stroke-opacity:.35;stroke-width:1.5}
.tip{position:absolute;top:6px;display:flex;flex-direction:column;gap:3px;padding:10px 12px;border-radius:14px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow);font-size:12.5px;pointer-events:none;z-index:2;white-space:nowrap}
.tip[hidden]{display:none}.tip b{font-size:13px}.tip i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}
.vtr{position:relative;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;height:170px;align-items:stretch}
.vbt{position:relative;background:var(--surface2);border-radius:18px;overflow:hidden}.vbt i{position:absolute;left:0;right:0;bottom:0;border-radius:18px;animation:grow .9s cubic-bezier(.2,.8,.2,1)}@keyframes grow{from{height:0}}
.vline{position:absolute;left:-4px;right:-4px;border-top:2px dashed var(--bad);text-decoration:none;pointer-events:none;opacity:.8}.vline span{position:absolute;right:0;top:-18px;font-size:11px;color:var(--bad);font-weight:600;background:var(--surface);padding:0 4px;border-radius:4px}
.vlab{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:center;margin-top:10px}.vlab b{display:block;font-size:17px}.vlab small{font-size:11px;color:var(--muted);font-weight:500}.vlab span{font-size:12px;color:var(--muted)}
.vsub{margin-top:12px;font-size:13px;color:var(--muted)}
.mixbar{display:flex;gap:4px;height:64px}.mixbar i{border-radius:16px;min-width:8px;transition:flex .8s}
.mixleg{display:flex;flex-direction:column;margin-top:12px}.mixleg>div{display:grid;grid-template-columns:auto 1fr auto 42px;align-items:center;gap:0;padding:8px 0;border-bottom:1px solid var(--line);font-size:13.5px}.mixleg>div:last-child{border-bottom:0}
.mixleg b{font-size:14px}.mixleg b small{font-size:11px;color:var(--muted);font-weight:500}.mixleg .muted{text-align:right}
.fuel{width:100%;max-width:260px;display:block;margin:4px auto 0;color:var(--text)}
.shortmsg{display:flex;flex-direction:column;align-items:center;text-align:center;margin-top:6px;text-transform:none}.shortmsg b{font-size:18px}
.estore{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.esub{background:var(--surface2);border-radius:20px;padding:16px}
@media (max-width:760px){.estore{grid-template-columns:1fr}}

/* ---- battery control ---- */
.ctl2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px 32px;margin-top:18px}
.mtiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.mt{display:flex;flex-direction:column;gap:5px;align-items:flex-start;text-align:left;padding:14px 16px;border-radius:20px;background:var(--surface2);color:var(--text);border:2px solid transparent;font-weight:500;min-height:0}
.mt .mti{font-size:22px;line-height:1}.mt b{font-size:15px}.mt .muted{font-size:12.5px;line-height:1.4}
.mt:hover{background:var(--surface3);filter:none}
.mt.on{border-color:var(--o);background:color-mix(in srgb,var(--o) 10%,var(--surface))}
.lim{margin:8px 0 14px}.limh{display:flex;justify-content:space-between;font-size:14px;margin-bottom:2px}
.mbtns{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.mb{display:flex;flex-direction:column;align-items:flex-start;gap:3px;padding:14px 16px;border-radius:20px;font-size:15px;font-weight:700;color:#fff;text-align:left;min-height:0}
.mb span{font-size:20px;line-height:1}.mb small{font-weight:500;opacity:.9;font-size:12px}
.mb.exp{background:#C2410C}.mb.top{background:#1D4ED8}.mb.stp{background:transparent;color:var(--text);border:2px solid var(--bad)}.mb.stp span{color:var(--bad)}
.dd{display:flex;flex-direction:column;gap:2px;padding:12px 14px;border-radius:16px;background:var(--surface2)}
.toast{max-height:0;overflow:hidden;opacity:0;margin-top:0;padding:0 14px;border-radius:12px;font-size:13.5px;transition:all .25s;background:color-mix(in srgb,var(--good) 16%,transparent)}
.toast.show{max-height:70px;opacity:1;margin-top:14px;padding:10px 14px}.toast.bad{background:color-mix(in srgb,var(--bad) 18%,transparent)}
.lockbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;margin-bottom:14px;border-radius:16px;background:var(--surface2);font-size:13.5px}
.grps{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}.grps.locked{opacity:.5;pointer-events:none;filter:grayscale(.5)}
.grp{padding:12px 16px;border-radius:20px;background:var(--surface2)}
.srow{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--line);min-height:44px}.srow:last-child{border-bottom:0}.srow>span:first-child{font-size:14px}
.nstep{display:inline-flex;align-items:center;gap:6px}.nstep button{width:32px;height:32px;min-height:0;padding:0;border-radius:50%;font-size:17px;line-height:1;background:var(--surface3);color:var(--text)}
.nstep input{width:68px;text-align:center;padding:6px}.nstep .muted{margin-left:2px}

/* ---- EV / battery visuals (kept) ---- */
.evring{width:100%;max-width:220px;display:block;margin:0 auto 10px;color:var(--text)}
.slider{width:100%;height:28px}
.evhero{padding:0;overflow:hidden}
.stage{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(240px,1fr)}
.carbox{position:relative;min-height:360px;padding:54px 0 84px;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(120% 90% at 50% 38%,color-mix(in srgb,var(--o) 16%,transparent),transparent 70%)}
.carglow{position:absolute;left:12%;right:12%;bottom:62px;height:26px;border-radius:50%;background:radial-gradient(closest-side,#4ade8088,transparent);opacity:0;transition:opacity .6s}
.carglow.on{opacity:1;animation:glow 2s ease-in-out infinite}@keyframes glow{50%{opacity:.55}}
.carglow.on:not(.chg){background:radial-gradient(closest-side,#ffa72688,transparent)}
.cartop{position:absolute;top:16px;left:20px;right:20px;display:flex;justify-content:space-between;align-items:center;z-index:2}
.carname{font-size:18px;font-weight:700}
.carbar{position:absolute;left:20px;right:20px;bottom:16px;z-index:2}
.barbg{position:relative;height:14px;border-radius:7px;background:var(--surface3);overflow:visible}
.barbg i{position:absolute;left:0;top:0;bottom:0;border-radius:7px;transition:width .8s,background .4s}
.barbg i.chg{background-image:repeating-linear-gradient(115deg,#ffffff45 0 9px,transparent 9px 18px);background-size:36px 100%;animation:stripes .8s linear infinite}@keyframes stripes{to{background-position:36px 0}}
.barbg u{position:absolute;top:-4px;bottom:-4px;width:3px;margin-left:-1px;border-radius:2px;background:var(--o);text-decoration:none}
.barlbl{display:flex;justify-content:space-between;align-items:baseline;margin-top:8px}.barlbl b{font-size:24px}
.evside{padding:20px;display:flex;flex-direction:column;justify-content:center;gap:10px;background:var(--surface2)}
@media (max-width:760px){.stage{grid-template-columns:1fr}.carbox{min-height:260px}}
.battstack{display:flex;flex-direction:column;gap:22px}
.batt{display:flex;flex-direction:column;gap:6px;color:var(--text);--bc:#2DB67C}
.towerw{flex-direction:row;align-items:center;gap:18px}.towerw .bstage{flex:0 0 42%;max-width:190px}.towerw .battmeta{align-items:flex-start;text-align:left}
.battsvg{width:100%;display:block;margin:0 auto;overflow:visible}.car{max-width:380px}
.bfill{transition:width 1s ease,y 1s ease,height 1s ease,fill .6s}.fclip{transition:width 1s ease}
.chg .battsvg,.chg .bimg{filter:drop-shadow(0 0 8px var(--bc))}
.bsheen{opacity:0}.chg .bsheen{opacity:1;animation:sheen 2s linear infinite}@keyframes sheen{from{transform:translateX(0)}to{transform:translateX(480px)}}
.cglow{fill:var(--bc);opacity:0;filter:blur(8px)}.chg .cglow{opacity:.5;animation:glow 2s ease-in-out infinite}
.cflow{stroke:var(--bc);opacity:0}.chg .cflow{opacity:.8;animation:dashmove .8s linear infinite}@keyframes dashmove{to{stroke-dashoffset:-16}}
.cbolt{opacity:0}.chg .cbolt{animation:pulse 1.1s ease-in-out infinite}@keyframes pulse{50%{opacity:1}0%,100%{opacity:.15}}
.ctail{opacity:.55}.chg .ctail{opacity:1}.clamp{opacity:.25}.chg .clamp{opacity:.9}
.spin{animation:none}
.twaveg{animation:wavex 2.4s linear infinite}@keyframes wavex{to{transform:translateX(40px)}}
.twrap{transition:transform 1s ease}
.tled{fill:#4ade80;animation:blink 2s ease-in-out infinite}@keyframes blink{50%{opacity:.3}}
.tflow{opacity:0}.tch{stroke:var(--bc);opacity:0}.chg .tdn,.dis .tup{opacity:1}
.chg .tdn .tch{animation:down 1.6s linear infinite}.dis .tup .tch{animation:up 1.6s linear infinite}
@keyframes up{0%{transform:translateY(20px);opacity:0}30%{opacity:1}100%{transform:translateY(-150px);opacity:0}}
@keyframes down{0%{transform:translateY(-150px);opacity:0}30%{opacity:1}100%{transform:translateY(20px);opacity:0}}
.bstage{position:relative}
.bimg{position:relative;width:100%;max-width:380px;margin:0 auto}.bimg img{width:100%;display:block;filter:grayscale(1) brightness(.6);opacity:.4}
.bfl{position:absolute;inset:0;-webkit-mask-image:var(--m);mask-image:var(--m);-webkit-mask-size:100% 100%;mask-size:100% 100%;-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;
  background:linear-gradient(105deg,var(--bc) 0 40%,color-mix(in srgb,var(--bc) 55%,#fff) 50%,var(--bc) 60% 100%);background-size:250% 100%;transition:clip-path 1s ease}
.carw .bfl{clip-path:inset(0 var(--r,100%) 0 0)}.towerw .bfl{clip-path:inset(var(--t,100%) 0 0 0)}
.chg .bfl{animation:photo 2.2s linear infinite}@keyframes photo{from{background-position:150% 0}to{background-position:-50% 0}}
.carpic{position:relative;display:inline-block;max-width:88%;z-index:1}.carpic img{max-width:100%!important}
.csoc,.cplug{position:absolute;display:flex;white-space:nowrap;align-items:center;gap:7px;background:rgba(14,18,26,.84);color:#fff;border-radius:999px;padding:5px 12px;font-weight:700;border:1px solid rgba(255,255,255,.2);z-index:3;box-shadow:0 4px 14px #0006}
.csoc{left:8px;bottom:8px;font-size:17px}.cplug{right:8px;top:8px;font-size:13px;border-color:#ffa726}.cplug[hidden]{display:none}.cplug svg{width:17px;height:17px;color:#ffa726}
.cplug.chg{border-color:#4ade80}.cplug.chg svg{color:#4ade80;animation:blink 1.2s ease-in-out infinite}
.cbat{position:relative;width:28px;height:14px;border:2px solid #fff;border-radius:4px;display:inline-block}.cbat:after{content:"";position:absolute;right:-5px;top:2px;width:3px;height:6px;background:#fff;border-radius:0 2px 2px 0}
.cbat i{position:absolute;left:1px;top:1px;bottom:1px;width:calc((100% - 2px) * var(--p,0) / 100);background:var(--lc,#4ade80);border-radius:1px;transition:width 1s}
.carbox img{max-width:88%;max-height:230px;object-fit:contain;filter:drop-shadow(0 18px 18px #0006);position:relative;z-index:1}
.carbox.plug img{filter:drop-shadow(0 8px 22px #ffa726cc) drop-shadow(0 0 6px #ffa72688)}
.carbox.chg img{animation:carpulse2 2.2s ease-in-out infinite}@keyframes carpulse2{0%,100%{filter:drop-shadow(0 8px 18px #4ade8099) drop-shadow(0 0 4px #4ade8066)}50%{filter:drop-shadow(0 10px 32px #4ade80ee) drop-shadow(0 0 14px #4ade80cc)}}
.bimg.plain img{filter:drop-shadow(0 14px 14px #0006);opacity:1}.bimg.plain .bfl,.bimg.plain .bimk{display:none}
.plug .bimg.plain img{filter:drop-shadow(0 8px 20px #ffa726cc)}
.chg .bimg.plain img{animation:carpulse 2.2s ease-in-out infinite}@keyframes carpulse{0%,100%{filter:drop-shadow(0 8px 16px #4ade8099)}50%{filter:drop-shadow(0 10px 30px #4ade80ee) drop-shadow(0 0 12px #4ade80cc)}}
.bbar{position:relative;width:100%;height:12px;border-radius:6px;background:var(--surface3);margin:12px auto 4px;max-width:380px;overflow:hidden}
.bbar i{position:absolute;left:0;top:0;bottom:0;width:0;background:var(--bc);border-radius:6px;transition:width 1s}
.chg .bbar i{background-image:repeating-linear-gradient(115deg,#ffffff45 0 9px,transparent 9px 18px);background-size:36px 100%;animation:stripes .8s linear infinite}
.bbar u{position:absolute;top:0;bottom:0;width:3px}
.bimk{position:absolute;inset:0;pointer-events:none}.bimk i{position:absolute;opacity:.9}
.battmeta{display:flex;flex-direction:column;align-items:center;text-align:center;font-size:13px;gap:2px}
.battmeta b{font-size:15px}.bbig{font-size:36px;font-weight:700;line-height:1.1;color:var(--bc);letter-spacing:-.02em}

.evfirst{margin-top:6px;padding:4px 14px;border-radius:16px;background:var(--surface2)}.evfirst .row>span:first-child{display:flex;flex-direction:column;gap:2px;max-width:80%}
.evnote{display:flex;gap:10px;align-items:center;padding:8px 0 10px;font-size:13px}.evnote .ic{color:var(--o)}
/* ---- v0.16: assistant options ---- */
.pcats{flex-wrap:wrap;align-self:flex-start}.pcats button{padding:6px 12px;min-height:32px;font-size:13px}
.chipw{display:inline-flex;align-items:center;flex:none}.chipw .x{min-height:28px;padding:2px 6px;margin-left:-4px}
.mwrap{display:flex;flex-direction:column;gap:3px}.mwrap.me{align-items:flex-end}.mwrap.ai{align-items:flex-start}
.macts{display:flex;gap:2px;align-items:center;opacity:.75}.macts button{min-height:26px;padding:3px 8px;font-size:12px}.macts .muted{font-size:11.5px;margin-left:6px}
.msg code{font-family:ui-monospace,monospace;font-size:13px;background:color-mix(in srgb,var(--text) 10%,transparent);padding:1px 5px;border-radius:6px}
.chatf .mic,.chatf .star{background:var(--surface2);color:var(--text)}.chatf .mic.on{background:var(--bad);color:#fff;animation:blink 1.2s infinite}
textarea{font:500 14px/1.45 var(--ff);color:var(--text);background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:10px 12px;width:100%;resize:vertical}
.row.col{flex-direction:column;align-items:stretch}.rowend{display:flex;justify-content:space-between;align-items:center}
.chatf input{min-width:0}
@media (max-width:720px){.chtools{flex-wrap:wrap;justify-content:flex-end}.chead:has(.chtools){flex-wrap:wrap}.chatf{gap:6px}.chatf button{width:44px;height:44px}.chatf input{min-height:44px;padding:10px 14px}}

/* ---- v0.15: advice, sankey, plans, settings, chat ---- */
.tips{display:flex;flex-direction:column;gap:10px}
.tip-row{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:16px;background:var(--surface2)}
.tip-row b{display:block;font-weight:600;font-size:14px;line-height:1.4}.tip-row span{font-size:12.5px;color:var(--muted)}
.tic{width:34px;height:34px;border-radius:12px;display:grid;place-items:center;flex:none;background:color-mix(in srgb,var(--muted) 16%,transparent);color:var(--muted)}.tic .ic{width:18px;height:18px}
.tip-row.act .tic{background:color-mix(in srgb,var(--o) 16%,transparent);color:var(--o)}.tip-row.warn .tic{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.tip-row.warn{box-shadow:inset 3px 0 0 var(--warn)}.tip-row.act{box-shadow:inset 3px 0 0 var(--o)}
.sankey{width:100%;display:block}.rib{opacity:.55;transition:opacity .2s}.rib:hover{opacity:.85}
.sk1{font:600 13px var(--ff);fill:var(--text)}.sk2{font:500 12px var(--ff);fill:var(--muted)}
.skfoot{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin-top:8px}.skfoot b{color:var(--text)}
.pc{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr) auto;gap:16px;align-items:center;padding:12px 0;border-bottom:1px solid var(--line)}.pc:last-of-type{border-bottom:0}
.pc.cur .pcn b{color:var(--text)}.pcn{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;min-width:0}.pcn .muted{flex-basis:100%;font-size:12.5px}
.pcb{height:12px;background:var(--surface2);border-radius:6px;overflow:hidden}.pcb i{display:block;height:100%;border-radius:6px}
.pcv{display:flex;flex-direction:column;align-items:flex-end;min-width:110px}.pcv b{font-size:18px}.pcv .ok,.pcv .bad{font-size:12.5px;font-weight:600}
@media (max-width:720px){.pc{grid-template-columns:1fr auto}.pcb{grid-column:1/-1;grid-row:2}}
.sethead{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}.sethead h2{margin-bottom:4px}
.jump{flex-wrap:wrap}
.devs{display:flex;flex-direction:column}
.dev{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto auto;gap:14px;align-items:center;padding:12px 4px;border-bottom:1px solid var(--line)}.dev:last-child{border-bottom:0}
.dst{width:10px;height:10px;border-radius:50%;background:var(--muted)}.dst.on{background:var(--good)}.dst.part{background:var(--warn)}.dst.off{background:var(--bad)}
.dn,.dm{display:flex;flex-direction:column;min-width:0}.dn b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dm{align-items:flex-end;font-size:13px}
.dw{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted)}
a.lnk{color:var(--o-deep);font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:4px}a.lnk .ic{width:18px;height:18px}
:host([data-theme=dark]) a.lnk{color:var(--o)}
@media (max-width:720px){.dev{grid-template-columns:auto minmax(0,1fr) auto;row-gap:6px}.dm{grid-column:2;align-items:flex-start}.dw{grid-column:2/4}}
.plan{padding:14px 16px;border-radius:20px;background:var(--surface2);margin-bottom:12px}
.planh{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px}.pname{font-weight:700;font-size:15px;flex:1;max-width:340px;background:var(--surface)}
.pgrid{display:flex;flex-wrap:wrap;gap:10px 22px;margin-bottom:6px}.pgrid label{display:flex;align-items:center;gap:8px;font-size:13.5px}
.plan input[type=number]{width:84px;background:var(--surface);min-height:36px;padding:6px 10px}.plan select{background:var(--surface);min-height:36px;padding:6px 10px}
.bands h3{margin:12px 0 6px}.band{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:6px 0}.band input[type=number]{width:64px}
.chat{display:flex;flex-direction:column;gap:12px}.chat h2 .ic{color:var(--o)}
.chtools{display:flex;gap:8px;align-items:center}.chtools select{min-height:36px;padding:6px 10px;max-width:220px}
.msgs{display:flex;flex-direction:column;gap:10px;max-height:420px;min-height:160px;overflow:auto;padding:4px 2px;scroll-behavior:smooth}
.msg{max-width:78%;padding:11px 15px;border-radius:20px;font-size:14.5px;line-height:1.45;white-space:normal;word-wrap:break-word}
.msg.me{align-self:flex-end;background:var(--o-deep);color:var(--text-primary-color);border-bottom-right-radius:6px}
.msg.ai{align-self:flex-start;background:var(--surface2);border-bottom-left-radius:6px}.msg.err{box-shadow:inset 3px 0 0 var(--bad)}
.typing{display:flex;gap:5px;padding:14px 16px}.typing i{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:blink 1.2s infinite}.typing i:nth-child(2){animation-delay:.2s}.typing i:nth-child(3){animation-delay:.4s}
.empty{display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px;margin:auto;max-width:460px;padding:20px;color:var(--muted);font-size:13.5px}.empty .ic{width:30px;height:30px;color:var(--o)}.empty b{color:var(--text);font-size:15px}
.qp{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}.qp .chip{border:1px solid var(--line);cursor:pointer;white-space:nowrap;min-height:34px;font:500 13px var(--ff);color:var(--text);background:var(--surface2);padding:7px 14px}.qp .chip:hover{background:var(--surface3);filter:none}
.chatf{display:flex;gap:8px}.chatf input{flex:1;min-height:48px;border-radius:24px;padding:12px 18px;font-size:15px}
.chatf button{width:48px;height:48px;padding:0;display:grid;place-items:center;flex:none}
@media (max-width:720px){.msg{max-width:90%}.chtools select{max-width:150px}}

@media (prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.001s!important;animation-iteration-count:1!important;transition-duration:.001s!important}}
`;
if (!customElements.get("cortex-studio")) customElements.define("cortex-studio", CortexStudio); // a second load of this module must not throw
