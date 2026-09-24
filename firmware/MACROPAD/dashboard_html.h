#ifndef DASHBOARD_HTML_H
#define DASHBOARD_HTML_H

#include <pgmspace.h>

const char INDEX_HTML[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MacroPad On-Device Debugger</title>
<style>
  :root {
    --bg-main: #0a0e14;
    --bg-sec: #131924;
    --bg-card: #182234;
    --bg-term: #070a0f;
    --cyan: #00f3ff;
    --green: #00ff66;
    --amber: #ffb800;
    --red: #ff3344;
    --mag: #ff007f;
    --text: #e6edf3;
    --dim: #7d8590;
    --border: #21262d;
    --mono: 'SFMono-Regular', Consolas, Menlo, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-main);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  header {
    background: var(--bg-sec);
    border-bottom: 1px solid var(--border);
    padding: 8px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
  }
  .header-left { display: flex; align-items: center; gap: 10px; }
  .brand { font-size: 14px; font-weight: 700; text-transform: uppercase; color: #fff; display: flex; align-items: center; gap: 6px; }
  .badge { font-family: var(--mono); font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; text-transform: uppercase; }
  .badge-online { background: rgba(0,255,102,0.15); color: var(--green); border: 1px solid var(--green); }
  .badge-awake { background: rgba(0,243,255,0.15); color: var(--cyan); border: 1px solid var(--cyan); }
  .badge-sleep { background: rgba(255,184,0,0.15); color: var(--amber); border: 1px solid var(--amber); }

  .telemetry { display: flex; align-items: center; gap: 14px; }
  .metric { display: flex; flex-direction: column; }
  .m-lbl { font-size: 9px; color: var(--dim); text-transform: uppercase; font-weight: 600; }
  .m-val { font-family: var(--mono); font-size: 12px; font-weight: 600; color: #fff; }
  .val-cyan { color: var(--cyan); }
  .val-green { color: var(--green); }
  .val-amber { color: var(--amber); }

  .btn {
    background: #1f293d;
    border: 1px solid #334155;
    color: #fff;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    cursor: pointer;
    transition: 0.15s;
  }
  .btn:hover { background: #2a3952; }
  .btn-awake.active { background: rgba(0,243,255,0.25); border-color: var(--cyan); color: var(--cyan); box-shadow: 0 0 8px rgba(0,243,255,0.4); }

  main { flex: 1; display: grid; grid-template-columns: 1fr 340px; overflow: hidden; }

  /* TERMINAL */
  .term-col { display: flex; flex-direction: column; background: var(--bg-term); border-right: 1px solid var(--border); overflow: hidden; }
  .term-top { background: #0d1219; padding: 6px 12px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-shrink: 0; }
  .term-search { background: #161b22; border: 1px solid var(--border); border-radius: 4px; color: #fff; padding: 3px 8px; font-size: 11px; font-family: var(--mono); width: 140px; }
  .term-logs { flex: 1; overflow-y: auto; padding: 10px 12px; font-family: var(--mono); font-size: 11px; line-height: 1.5; }
  .log-line { display: flex; gap: 8px; padding: 2px 0; border-bottom: 1px solid rgba(255,255,255,0.02); }
  .log-line:hover { background: rgba(255,255,255,0.03); }
  .l-time { color: #555; flex-shrink: 0; }
  .l-lvl { font-weight: 700; padding: 1px 4px; border-radius: 2px; font-size: 9px; flex-shrink: 0; }
  .lvl-INFO { background: rgba(58,134,255,0.15); color: #3a86ff; }
  .lvl-INP  { background: rgba(0,255,102,0.15); color: var(--green); }
  .lvl-SYS  { background: rgba(0,243,255,0.15); color: var(--cyan); }
  .lvl-DISP { background: rgba(255,0,127,0.15); color: var(--mag); }
  .lvl-WARN { background: rgba(255,184,0,0.15); color: var(--amber); }
  .lvl-ERR  { background: rgba(255,51,68,0.25); color: var(--red); font-weight: 800; }
  .l-tag { color: #888; flex-shrink: 0; width: 55px; }
  .l-msg { color: var(--text); flex: 1; word-break: break-all; }

  /* SIDEBAR */
  .side-col { background: var(--bg-sec); display: flex; flex-direction: column; overflow-y: auto; padding: 12px; gap: 12px; }
  .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; }
  .card-h { font-size: 10px; font-weight: 700; color: var(--dim); text-transform: uppercase; display: flex; justify-content: space-between; }

  /* 4x4 MATRIX */
  .matrix { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }
  .mkey {
    background: #111822; border: 1px solid #232b36; border-radius: 4px; height: 38px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-family: var(--mono); user-select: none;
  }
  .mkey .k-num { font-size: 8px; color: #555; }
  .mkey .k-lbl { font-size: 9px; font-weight: 600; color: #999; }
  .mkey.active-slot { border-color: var(--green); background: rgba(0,255,102,0.15); }
  .mkey.active-slot .k-lbl { color: var(--green); }
  .mkey.key-5 { border-color: var(--amber); }
  .mkey.key-5.active { background: rgba(0,243,255,0.3); border-color: var(--cyan); box-shadow: 0 0 8px var(--cyan); }
  .mkey.flash { background: var(--cyan) !important; color: #000 !important; }

  /* ENCODERS */
  .enc-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .enc-box { background: #111822; border: 1px solid #232b36; border-radius: 4px; padding: 6px; display: flex; flex-direction: column; align-items: center; gap: 3px; font-size: 9px; }
  .knob { width: 26px; height: 26px; border-radius: 50%; border: 2px dashed #444; display: flex; align-items: center; justify-content: center; font-weight: 700; transition: 0.15s; }
  .enc-box.cw .knob { border-color: var(--green); transform: rotate(40deg); }
  .enc-box.ccw .knob { border-color: var(--cyan); transform: rotate(-40deg); }
  .enc-box.click .knob { background: var(--mag); color: #fff; }

  /* EINK PREVIEW */
  .eink { background: #e8eaed; color: #111; border-radius: 4px; padding: 8px; font-family: var(--mono); display: flex; flex-direction: column; gap: 4px; border: 2px solid #333; }
  .eink-top { display: flex; justify-content: space-between; font-size: 8px; font-weight: 700; border-bottom: 1px solid #999; padding-bottom: 2px; }
  .eink-g { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; }
  .eink-c { background: #fff; border: 1px solid #bbb; font-size: 9px; font-weight: 700; text-align: center; padding: 3px 1px; }
  .eink-pop { background: #111; color: #fff; font-size: 9px; font-weight: 700; text-align: center; padding: 4px; border-radius: 2px; }

  .ctrl-row { display: flex; gap: 4px; }
  .ctrl-inp { flex: 1; background: #111822; border: 1px solid var(--border); border-radius: 4px; color: #fff; padding: 4px 6px; font-size: 11px; }
</style>
</head>
<body>

<header>
  <div class="header-left">
    <span style="font-size:18px;">⚡</span>
    <span class="brand">MacroPad ESP32-C3 <span id="badge-st" class="badge badge-online">ONLINE</span></span>
    <button id="btn-stay-awake" class="btn btn-awake" onclick="toggleStayAwake()">Stay Awake: OFF</button>
  </div>

  <div class="telemetry">
    <div class="metric"><span class="m-lbl">Battery</span><span id="m-vbat" class="m-val val-green">-- V</span></div>
    <div class="metric"><span class="m-lbl">WiFi RSSI</span><span id="m-rssi" class="m-val val-cyan">-- dBm</span></div>
    <div class="metric"><span class="m-lbl">Free Heap</span><span id="m-heap" class="m-val">-- KB</span></div>
    <div class="metric"><span class="m-lbl">Layer</span><span id="m-layer" class="m-val val-amber">B1 L1</span></div>
    <div class="metric"><span class="m-lbl">Boot Reason</span><span id="m-reset" class="m-val" style="font-size:10px; color:#aaa;">Init</span></div>
  </div>
</header>

<main>
  <section class="term-col">
    <div class="term-top">
      <div style="font-size:10px; font-weight:700; color:var(--dim); text-transform:uppercase;">DEVICE LOGS (REAL-TIME RING BUFFER)</div>
      <input type="text" id="filter-input" class="term-search" placeholder="Search logs..." oninput="renderLogs()">
      <div style="display:flex; gap:4px;">
        <button id="btn-scroll" class="btn" style="padding:2px 6px; font-size:10px;" onclick="toggleScroll()">Auto-Scroll: ON</button>
        <button class="btn" style="padding:2px 6px; font-size:10px;" onclick="clearDisplay()">Clear</button>
      </div>
    </div>
    <div id="term-logs" class="term-logs"></div>
  </section>

  <section class="side-col">
    <div class="card">
      <div class="card-h"><span>4×4 Matrix</span><span id="mod-ind" style="color:#666;">MOD: OFF</span></div>
      <div class="matrix" id="matrix"></div>
    </div>

    <div class="card">
      <div class="card-h">Rotary Encoders</div>
      <div class="enc-row">
        <div class="enc-box" id="enc-2"><div class="knob">2</div><span>Enc 2 (Top-L)</span></div>
        <div class="enc-box" id="enc-1"><div class="knob">HW</div><span>HW (Top-R)</span></div>
        <div class="enc-box" id="enc-3"><div class="knob">1</div><span>Enc 1 (Bot-L)</span></div>
      </div>
    </div>

    <div class="card">
      <div class="card-h">1.54" E-Ink Preview</div>
      <div class="eink">
        <div class="eink-top"><span id="eink-title">BANK 1</span><span id="eink-bat">BAT: 3.8V</span></div>
        <div class="eink-g" id="eink-g"></div>
        <div class="eink-pop" id="eink-pop" style="display:none;"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-h">Send E-Ink Popup</div>
      <div class="ctrl-row">
        <input type="text" id="pop-inp" class="ctrl-inp" placeholder="Popup message..." value="DEBUG OK">
        <button class="btn" style="background:#00f3ff22; color:var(--cyan); border-color:var(--cyan);" onclick="sendPopup()">Send</button>
      </div>
      <div class="ctrl-row" style="margin-top:4px;">
        <button class="btn" style="flex:1;" onclick="setBank(1)">Bank 1</button>
        <button class="btn" style="flex:1;" onclick="setBank(2)">Bank 2</button>
        <button class="btn" style="flex:1;" onclick="setBank(3)">Bank 3</button>
        <button class="btn" style="flex:1;" onclick="setBank(4)">Bank 4</button>
      </div>
    </div>
    <div class="card">
      <div class="card-h">System Controls</div>
      <div class="ctrl-row">
        <button class="btn" style="flex:1; border-color:var(--amber); color:var(--amber);" onclick="testDeepSleep()">Test Deep Sleep</button>
        <button class="btn" style="flex:1; border-color:var(--red); color:var(--red);" onclick="rebootDevice()">Reboot</button>
      </div>
    </div>
  </section>
</main>

<script>
  let logs = [];
  let autoScroll = true;
  let stayAwake = false;

  const keyLabels = {
    1:"Slot 1", 2:"Slot 2", 3:"Slot 3", 4:"Slot 4",
    5:"MOD/LT", 6:"ACT 1", 7:"ACT 2", 8:"ACT 3",
    9:"FIXED 9", 10:"ACT 4", 11:"ACT 5", 12:"ACT 6",
    13:"MIC/AUD", 14:"ACT 7", 15:"ACT 8", 16:"ACT 9"
  };

  function initUI() {
    const mg = document.getElementById('matrix');
    mg.innerHTML = '';
    for (let i = 1; i <= 16; i++) {
      const k = document.createElement('div');
      k.id = `k-${i}`;
      k.className = `mkey ${i === 5 ? 'key-5' : ''}`;
      k.innerHTML = `<span class="k-num">${i}</span><span class="k-lbl">${keyLabels[i]}</span>`;
      mg.appendChild(k);
    }

    const eg = document.getElementById('eink-g');
    eg.innerHTML = '';
    for (let i = 1; i <= 9; i++) {
      const c = document.createElement('div');
      c.id = `ec-${i}`;
      c.className = 'eink-c';
      c.innerText = `ACT ${i}`;
      eg.appendChild(c);
    }
  }

  function formatTime(ms) {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    const milli = ms % 1000;
    return `${m.toString().padStart(2,'0')}:${sec.toString().padStart(2,'0')}.${milli.toString().padStart(3,'0')}`;
  }

  function pollData() {
    fetch('/api/status')
      .then(r => r.json())
      .then(s => {
        document.getElementById('m-vbat').innerText = `${s.vbat.toFixed(2)} V`;
        document.getElementById('m-rssi').innerText = `${s.rssi} dBm`;
        document.getElementById('m-heap').innerText = `${Math.round(s.heap / 1024)} KB`;
        document.getElementById('m-layer').innerText = `B${s.bank} L${s.layer}`;
        document.getElementById('m-reset').innerText = s.reset_reason || 'OK';

        // Stay Awake button status
        stayAwake = !!s.stay_awake;
        const ab = document.getElementById('btn-stay-awake');
        if (stayAwake) {
          ab.classList.add('active');
          ab.innerText = 'Stay Awake: ON';
        } else {
          ab.classList.remove('active');
          ab.innerText = 'Stay Awake: OFF';
        }

        // Active slot
        for (let i = 1; i <= 4; i++) {
          const el = document.getElementById(`k-${i}`);
          if (el) {
            if (i === s.slot) el.classList.add('active-slot');
            else el.classList.remove('active-slot');
          }
        }

        // Modifier
        const k5 = document.getElementById('k-5');
        const mi = document.getElementById('mod-ind');
        if (s.modifier) {
          k5.classList.add('active');
          mi.innerText = 'MOD: HELD';
          mi.style.color = 'var(--cyan)';
        } else {
          k5.classList.remove('active');
          mi.innerText = 'MOD: OFF';
          mi.style.color = '#666';
        }

        // E-Ink
        document.getElementById('eink-title').innerText = `BANK ${s.bank}: LAYER ${s.layer}`;
        document.getElementById('eink-bat').innerText = `BAT: ${s.vbat.toFixed(2)}V`;
        const pop = document.getElementById('eink-pop');
        if (s.screen_msg) {
          pop.innerText = s.screen_msg;
          pop.style.display = 'block';
        } else {
          pop.style.display = 'none';
        }
      })
      .catch(() => {});

    fetch('/api/logs')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          logs = data;
          renderLogs();
        }
      })
      .catch(() => {});
  }

  function renderLogs() {
    const c = document.getElementById('term-logs');
    const filter = document.getElementById('filter-input').value.toLowerCase();
    c.innerHTML = '';

    logs.forEach(l => {
      if (filter && !l.msg.toLowerCase().includes(filter) && !l.tag.toLowerCase().includes(filter)) return;
      const row = document.createElement('div');
      row.className = 'log-line';
      row.innerHTML = `
        <span class="l-time">${formatTime(l.t)}</span>
        <span class="l-lvl lvl-${l.lvl}">${l.lvl}</span>
        <span class="l-tag">[${l.tag}]</span>
        <span class="l-msg">${escapeHtml(l.msg)}</span>
      `;
      c.appendChild(row);
    });

    if (autoScroll) c.scrollTop = c.scrollHeight;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function toggleStayAwake() {
    fetch('/api/toggle_stay_awake', { method: 'POST' }).then(() => pollData());
  }

  function toggleScroll() {
    autoScroll = !autoScroll;
    const b = document.getElementById('btn-scroll');
    b.innerText = `Auto-Scroll: ${autoScroll ? 'ON' : 'OFF'}`;
  }

  function clearDisplay() {
    document.getElementById('term-logs').innerHTML = '';
  }

  function sendPopup() {
    const msg = document.getElementById('pop-inp').value;
    if (msg) fetch(`/api/send_popup?msg=${encodeURIComponent(msg)}`, { method: 'POST' });
  }

  function setBank(b) {
    fetch(`/api/set_layer?bank=${b}`, { method: 'POST' });
  }

  function testDeepSleep() {
    if (confirm("Trigger Low Battery Deep Sleep now?\n\n- Screen will show '! LOW BATT SLEEP !'\n- LEDs turn off & power drops to ~15uA\n- Wake up by pressing any Matrix Key")) {
      fetch('/api/test_deep_sleep', { method: 'POST' });
    }
  }

  function rebootDevice() {
    if (confirm("Reboot MacroPad?")) {
      fetch('/api/reboot', { method: 'POST' });
    }
  }

  initUI();
  pollData();
  setInterval(pollData, 1500);
</script>
</body>
</html>
)rawliteral";

#endif // DASHBOARD_HTML_H
