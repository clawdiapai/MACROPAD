"""
MacroPad Screen Backlight & LED Calibrator Studio
Nested debug view for precision color, brightness, and power management.
Served at `/debug/backlight` on the Unified Hub.
"""

BACKLIGHT_HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MacroPad Backlight & Screen LED Studio</title>
<style>
  :root {
    --bg-primary: #0a0e14;
    --bg-secondary: #131924;
    --bg-card: #182234;
    --accent-cyan: #00f3ff;
    --accent-green: #00ff66;
    --accent-amber: #ffb800;
    --accent-magenta: #ff007f;
    --accent-blue: #3a86ff;
    --accent-red: #ff3344;
    --text-main: #e6edf3;
    --text-dim: #7d8590;
    --border-color: #21262d;
    --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-primary);
    color: var(--text-main);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }

  header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-shrink: 0;
  }
  .title-group {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand-icon {
    font-size: 24px;
    filter: drop-shadow(0 0 10px var(--accent-amber));
  }
  h1 {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .nav-links {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .btn {
    background: #1c2638;
    color: var(--text-main);
    border: 1px solid var(--border-color);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }
  .btn:hover { background: #26354d; border-color: var(--text-dim); }
  .btn-cyan { color: var(--accent-cyan); border-color: rgba(0,243,255,0.4); }
  .btn-cyan:hover { background: rgba(0,243,255,0.15); border-color: var(--accent-cyan); }
  .btn-amber { color: var(--accent-amber); border-color: rgba(255,184,0,0.4); }
  .btn-amber:hover { background: rgba(255,184,0,0.15); border-color: var(--accent-amber); }
  .btn-green { color: var(--accent-green); border-color: rgba(0,255,102,0.4); }
  .btn-green:hover { background: rgba(0,255,102,0.15); border-color: var(--accent-green); }

  .status-badge {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .badge-online { background: rgba(0,255,102,0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }
  .badge-active { background: rgba(255,184,0,0.2); color: var(--accent-amber); border: 1px solid var(--accent-amber); }

  main {
    max-width: 1200px;
    margin: 20px auto;
    padding: 0 20px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    width: 100%;
  }
  @media (max-width: 900px) {
    main { grid-template-columns: 1fr; }
  }

  .card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .card-title {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 10px;
  }

  /* PREVIEW SIMULATOR */
  .preview-stage {
    background: #070a0f;
    border: 2px solid #26354d;
    border-radius: 12px;
    padding: 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }
  .macropad-frame {
    width: 220px;
    height: 220px;
    background: #121822;
    border: 4px solid #2b394e;
    border-radius: 16px;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.6);
  }
  .screen-bezel {
    width: 170px;
    height: 170px;
    background: #e6e6e2;
    border: 2px solid #334155;
    border-radius: 6px;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.25s ease, background-color 0.25s ease;
  }
  .eink-content {
    padding: 10px;
    color: #111;
    font-family: var(--font-mono);
    font-size: 10px;
    display: flex;
    flex-direction: column;
    height: 100%;
    justify-content: space-between;
  }
  .edge-led {
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #444;
    transition: all 0.2s ease;
  }
  .led-top { top: -6px; left: 50%; transform: translateX(-50%); }
  .led-bot { bottom: -6px; left: 50%; transform: translateX(-50%); }

  .telemetry-pills {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 15px;
    width: 100%;
  }
  .pill-box {
    background: #0d131d;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 10px;
    text-align: center;
  }
  .pill-lbl { font-size: 9px; color: var(--text-dim); text-transform: uppercase; font-weight: 700; margin-bottom: 3px; }
  .pill-val { font-family: var(--font-mono); font-size: 13px; font-weight: 700; }

  /* SLIDER CONTROLS */
  .control-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .control-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-weight: 600;
  }
  .slider-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  input[type="range"] {
    flex: 1;
    accent-color: var(--accent-amber);
    height: 6px;
    border-radius: 3px;
    background: #0d131d;
    cursor: pointer;
  }
  input[type="range"].range-red { accent-color: #ff3344; }
  input[type="range"].range-green { accent-color: #00ff66; }
  input[type="range"].range-blue { accent-color: #3a86ff; }
  input[type="range"].range-bright { accent-color: var(--accent-amber); }

  .num-input {
    width: 60px;
    background: #0d131d;
    border: 1px solid var(--border-color);
    color: #fff;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    padding: 4px 6px;
    border-radius: 4px;
    text-align: center;
  }

  /* PRESET BUTTONS */
  .presets-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }
  @media (max-width: 600px) {
    .presets-grid { grid-template-columns: repeat(2, 1fr); }
  }
  .preset-card {
    background: #0d131d;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 10px 8px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }
  .preset-card:hover {
    border-color: var(--accent-cyan);
    transform: translateY(-2px);
  }
  .preset-dot {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0 0 8px currentColor;
  }
  .preset-name {
    font-size: 11px;
    font-weight: 600;
    text-align: center;
  }
  .preset-sub {
    font-size: 9px;
    color: var(--text-dim);
    font-family: var(--font-mono);
  }

  /* POWER MODE CARD */
  .mode-toggle-box {
    background: #0d131d;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
  }
  .mode-desc {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .mode-title { font-size: 12px; font-weight: 700; color: #fff; }
  .mode-detail { font-size: 11px; color: var(--text-dim); line-height: 1.4; }
</style>
</head>
<body>

<header>
  <div class="title-group">
    <span class="brand-icon">💡</span>
    <div>
      <h1>Screen Backlight &amp; LED Studio</h1>
      <span style="font-size:11px; color:var(--text-dim);">ESP32-C3 Pixels 16 &amp; 17 Dynamic Drive Calibrator</span>
    </div>
  </div>

  <div class="nav-links">
    <span id="badge-pwr" class="status-badge badge-active">LED: ON</span>
    <span id="badge-vbat" class="status-badge badge-online">BAT: 3.72V</span>
    <a href="/debug" class="btn btn-amber">← Debug Console</a>
    <a href="/" class="btn btn-cyan">← Studio UI</a>
    <a href="http://192.168.1.58" target="_blank" class="btn" style="color:var(--accent-cyan);">ESP32 Direct ↗</a>
  </div>
</header>

<main>
  <!-- LEFT COLUMN: LIVE PREVIEW & TELEMETRY -->
  <div class="card">
    <div class="card-title">
      <span>🖥️ Live Backlight Glow Simulation</span>
      <button id="btn-master-pwr" class="btn btn-amber" onclick="toggleScreenLed()">Toggle Backlight</button>
    </div>

    <div class="preview-stage">
      <div class="macropad-frame">
        <div class="edge-led led-top" id="sim-led-16"></div>
        <div class="screen-bezel" id="sim-screen">
          <div class="eink-content">
            <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:9px;">
              <span>BANK 1</span>
              <span>EPD 1.54"</span>
            </div>
            <div style="text-align:center; margin:auto;">
              <div style="font-size:12px; font-weight:bold;">MACROPAD</div>
              <div style="font-size:9px; color:#555;">Dual WS2812B Glow</div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:8px; color:#666;">
              <span id="sim-mode-lbl">Modem-Sleep</span>
              <span id="sim-hex-lbl">#B45000</span>
            </div>
          </div>
        </div>
        <div class="edge-led led-bot" id="sim-led-17"></div>
      </div>
    </div>

    <div class="telemetry-pills">
      <div class="pill-box">
        <div class="pill-lbl">Active Hex</div>
        <div class="pill-val" id="val-hex" style="color:var(--accent-amber);">#B45000</div>
      </div>
      <div class="pill-box">
        <div class="pill-lbl">Est. LED Current</div>
        <div class="pill-val" id="val-draw" style="color:var(--accent-cyan);">~15 mA</div>
      </div>
      <div class="pill-box">
        <div class="pill-lbl">Headroom / Dropout</div>
        <div class="pill-val" id="val-headroom" style="color:var(--accent-green);">Stable (+0.9V)</div>
      </div>
    </div>

    <!-- WI-FI POWER MODE / FLICKER MITIGATION -->
    <div class="mode-toggle-box" style="margin-top:4px;">
      <div class="mode-desc">
        <div class="mode-title">⚡ Wi-Fi Modem-Sleep Beacon Mitigation</div>
        <div class="mode-detail" id="wifi-mode-desc">
          <b>Modem-Sleep (Current: ~50mA):</b> 100ms beacon pulses can modulate battery rail by ~50mV. Zero-blue / pure red avoids dropout flicker.
        </div>
      </div>
      <button id="btn-wifi-sleep" class="btn btn-cyan" style="flex-shrink:0; font-size:11px;" onclick="toggleWifiSleep()">
        Mode: Sleep Active
      </button>
    </div>
  </div>

  <!-- RIGHT COLUMN: PRECISION CONTROLS & PRESETS -->
  <div class="card">
    <div class="card-title">
      <span>🎛️ Color &amp; Brightness Tuner</span>
      <div style="display:flex; align-items:center; gap:8px;">
        <input type="color" id="native-picker" value="#b45000" onchange="onNativeColorChange(this.value)" style="border:none; width:28px; height:24px; border-radius:4px; cursor:pointer; background:none;">
        <span style="font-size:10px; color:var(--text-dim); font-family:var(--font-mono);">HEX</span>
      </div>
    </div>

    <!-- RED SLIDER -->
    <div class="control-group">
      <div class="control-header">
        <span style="color:#ff5566;">🔴 Red Channel (Vf = 1.9V, Zero Dropout)</span>
        <span id="txt-r" style="font-family:var(--font-mono); color:#ff5566;">180</span>
      </div>
      <div class="slider-row">
        <input type="range" class="range-red" id="rng-r" min="0" max="255" value="180" oninput="onRgbSliderChange()">
        <input type="number" class="num-input" id="num-r" min="0" max="255" value="180" oninput="onRgbNumChange('r')">
      </div>
    </div>

    <!-- GREEN SLIDER -->
    <div class="control-group">
      <div class="control-header">
        <span style="color:#00ff66;">🟢 Green Channel (Vf = 2.8V, Sensitive on Battery)</span>
        <span id="txt-g" style="font-family:var(--font-mono); color:#00ff66;">80</span>
      </div>
      <div class="slider-row">
        <input type="range" class="range-green" id="rng-g" min="0" max="255" value="80" oninput="onRgbSliderChange()">
        <input type="number" class="num-input" id="num-g" min="0" max="255" value="80" oninput="onRgbNumChange('g')">
      </div>
    </div>

    <!-- BLUE SLIDER -->
    <div class="control-group">
      <div class="control-header">
        <span style="color:#3a86ff;">🔵 Blue Channel (Vf = 3.2V, Drops out below 3.55V)</span>
        <span id="txt-b" style="font-family:var(--font-mono); color:#3a86ff;">0</span>
      </div>
      <div class="slider-row">
        <input type="range" class="range-blue" id="rng-b" min="0" max="255" value="0" oninput="onRgbSliderChange()">
        <input type="number" class="num-input" id="num-b" min="0" max="255" value="0" oninput="onRgbNumChange('b')">
      </div>
    </div>

    <!-- MASTER BRIGHTNESS -->
    <div class="control-group" style="padding-top:4px; border-top:1px solid rgba(255,255,255,0.06);">
      <div class="control-header">
        <span style="color:var(--accent-amber);">🔆 Master Intensity Multiplier</span>
        <span id="txt-bright" style="font-family:var(--font-mono); color:var(--accent-amber);">100%</span>
      </div>
      <div class="slider-row">
        <input type="range" class="range-bright" id="rng-bright" min="5" max="100" value="100" oninput="onBrightnessChange(this.value)">
        <input type="number" class="num-input" id="num-bright" min="5" max="100" value="100" oninput="onBrightnessChange(this.value)">
      </div>
    </div>

    <!-- ONE-TOUCH TEST PRESETS -->
    <div style="font-size:11px; font-weight:700; color:var(--text-dim); text-transform:uppercase; margin-top:8px;">
      One-Click Engineered Presets
    </div>
    <div class="presets-grid">
      <div class="preset-card" onclick="applyPreset(160, 25, 0, 'Candle Amber')">
        <div class="preset-dot" style="background:#a01900; color:#a01900;"></div>
        <div class="preset-name">Candle Amber</div>
        <div class="preset-sub">Warm ~11mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(180, 80, 0, 'Warm Gold')">
        <div class="preset-dot" style="background:#b45000; color:#b45000;"></div>
        <div class="preset-name">Warm Gold</div>
        <div class="preset-sub">Default ~15mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(180, 0, 0, 'Zero-Sag Ruby')">
        <div class="preset-dot" style="background:#b40000; color:#b40000;"></div>
        <div class="preset-name">Ruby (1.9V)</div>
        <div class="preset-sub">Zero Sag ~10mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(70, 15, 0, 'Stealth Glow')">
        <div class="preset-dot" style="background:#460f00; color:#460f00;"></div>
        <div class="preset-name">Stealth Glow</div>
        <div class="preset-sub">Ultra-low ~5mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(0, 140, 140, 'Ice Cyan')">
        <div class="preset-dot" style="background:#008c8c; color:#008c8c;"></div>
        <div class="preset-name">Ice Cyan</div>
        <div class="preset-sub">Vivid ~16mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(0, 160, 20, 'Emerald')">
        <div class="preset-dot" style="background:#00a014; color:#00a014;"></div>
        <div class="preset-name">Emerald</div>
        <div class="preset-sub">Pure ~10mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(140, 0, 150, 'Amethyst')">
        <div class="preset-dot" style="background:#8c0096; color:#8c0096;"></div>
        <div class="preset-name">Amethyst</div>
        <div class="preset-sub">Rich ~17mA</div>
      </div>
      <div class="preset-card" onclick="applyPreset(160, 140, 100, 'Daylight')">
        <div class="preset-dot" style="background:#a08c64; color:#a08c64;"></div>
        <div class="preset-name">Daylight</div>
        <div class="preset-sub">Crisp ~24mA</div>
      </div>
    </div>

    <!-- SUBTLE READING-FRIENDLY BACKLIGHT MOTION -->
    <div style="font-size:11px; font-weight:700; color:var(--text-dim); text-transform:uppercase; margin-top:8px;">
      Subtle Backlight Motion (Hides Wi-Fi Beacon Power Sag)
    </div>
    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px;">
      <div class="preset-card" id="btn-anim-0" onclick="applyAnim(0)">
        <span style="font-size:16px;">⏹️</span>
        <div class="preset-name">Fixed (Static)</div>
        <div class="preset-sub">Steady output</div>
      </div>
      <div class="preset-card" id="btn-anim-1" style="border-color:var(--accent-amber);" onclick="applyAnim(1)">
        <span style="font-size:16px;">🕯️</span>
        <div class="preset-name" style="color:var(--accent-amber);">Candle Ember</div>
        <div class="preset-sub">Subtle shimmer</div>
      </div>
      <div class="preset-card" id="btn-anim-2" onclick="applyAnim(2)">
        <span style="font-size:16px;">🌊</span>
        <div class="preset-name">Zen Breathe</div>
        <div class="preset-sub">Slow 4s pulse</div>
      </div>
      <div class="preset-card" id="btn-anim-3" onclick="applyAnim(3)">
        <span style="font-size:16px;">☯️</span>
        <div class="preset-name">Twin Aurora</div>
        <div class="preset-sub">Cross-fade</div>
      </div>
    </div>

    <!-- ANIMATION SPEED SLIDER / DIAL -->
    <div class="control-group" style="padding-top:8px; border-top:1px solid rgba(255,255,255,0.06); margin-top:8px;">
      <div class="control-header">
        <span style="color:var(--accent-cyan);">⚡ Animation Speed Dial</span>
        <span id="txt-speed" style="font-family:var(--font-mono); color:var(--accent-cyan);">1.0x</span>
      </div>
      <div class="slider-row">
        <input type="range" class="range-speed" id="rng-speed" min="20" max="300" value="100" style="accent-color:var(--accent-cyan); flex:1;" oninput="onSpeedChange(this.value)">
        <input type="number" class="num-input" id="num-speed" min="20" max="300" value="100" oninput="onSpeedChange(this.value)">
      </div>
    </div>
  </div>
</main>

<script>
  let ledActive = true;
  let wifiSleepActive = true;
  let curR = 180, curG = 80, curB = 0;
  let baseR = 180, baseG = 80, baseB = 0;
  let curBrightness = 100;
  let curAnim = 1;
  let curSpeed = 100;
  let sendTimeout = null;

  const MACROPAD_DIRECT_URL = "http://192.168.1.58";

  function toHex(n) {
    const s = Math.max(0, Math.min(255, Math.round(n))).toString(16);
    return s.length === 1 ? '0' + s : s;
  }

  function updateVisuals() {
    const hex = `#${toHex(curR)}${toHex(curG)}${toHex(curB)}`;
    document.getElementById('native-picker').value = hex;
    document.getElementById('val-hex').innerText = hex.toUpperCase();
    document.getElementById('sim-hex-lbl').innerText = hex.toUpperCase();

    // Sliders & texts
    document.getElementById('rng-r').value = curR;
    document.getElementById('num-r').value = curR;
    document.getElementById('txt-r').innerText = curR;

    document.getElementById('rng-g').value = curG;
    document.getElementById('num-g').value = curG;
    document.getElementById('txt-g').innerText = curG;

    document.getElementById('rng-b').value = curB;
    document.getElementById('num-b').value = curB;
    document.getElementById('txt-b').innerText = curB;

    // Simulation Glow
    const screen = document.getElementById('sim-screen');
    const led16 = document.getElementById('sim-led-16');
    const led17 = document.getElementById('sim-led-17');

    if (ledActive) {
      const glowColor = `rgba(${curR}, ${curG}, ${curB}, 0.55)`;
      const innerTint = `rgba(${curR}, ${curG}, ${curB}, 0.12)`;
      screen.style.boxShadow = `0 0 35px ${glowColor}, inset 0 0 25px ${innerTint}`;
      screen.style.backgroundColor = innerTint;
      led16.style.background = hex;
      led16.style.boxShadow = `0 0 12px ${hex}`;
      led17.style.background = hex;
      led17.style.boxShadow = `0 0 12px ${hex}`;
    } else {
      screen.style.boxShadow = 'none';
      screen.style.backgroundColor = '#e6e6e2';
      led16.style.background = '#333';
      led16.style.boxShadow = 'none';
      led17.style.background = '#333';
      led17.style.boxShadow = 'none';
    }

    // Current & Headroom estimation
    const ma = Math.round(((curR / 255 * 10) + (curG / 255 * 10) + (curB / 255 * 10)) * 2);
    document.getElementById('val-draw').innerText = ledActive ? `~${ma} mA` : '0 mA';

    const hrEl = document.getElementById('val-headroom');
    if (!ledActive) {
      hrEl.innerText = 'Off';
      hrEl.style.color = 'var(--text-dim)';
    } else if (curB > 20) {
      hrEl.innerText = 'Blue Dropout (Vf 3.2V)';
      hrEl.style.color = 'var(--accent-red)';
    } else if (curG > 100) {
      hrEl.innerText = 'High Green (Vf 2.8V)';
      hrEl.style.color = 'var(--accent-amber)';
    } else {
      hrEl.innerText = 'Solid (Vf < 2.2V)';
      hrEl.style.color = 'var(--accent-green)';
    }
  }

  function sendBacklightToDevice() {
    clearTimeout(sendTimeout);
    sendTimeout = setTimeout(async () => {
      const pwr = ledActive ? 'on' : 'off';
      // First try Pi Hub proxy, fallback to direct MacroPad IP
      try {
        await fetch(`/api/macropad/screen_led?state=${pwr}&r=${curR}&g=${curG}&b=${curB}&anim=${curAnim}&spd=${curSpeed}`, { method: 'POST' });
      } catch (e) {
        try {
          await fetch(`${MACROPAD_DIRECT_URL}/api/screen_led?state=${pwr}&r=${curR}&g=${curG}&b=${curB}&anim=${curAnim}&spd=${curSpeed}`);
        } catch (err) {}
      }
    }, 40);
  }

  function onSpeedChange(val) {
    curSpeed = Math.max(20, Math.min(300, parseInt(val) || 100));
    document.getElementById('rng-speed').value = curSpeed;
    document.getElementById('num-speed').value = curSpeed;
    document.getElementById('txt-speed').innerText = `${(curSpeed / 100.0).toFixed(1)}x`;
    sendBacklightToDevice();
  }

  function applyAnim(m) {
    curAnim = m;
    for (let i = 0; i <= 3; i++) {
      const el = document.getElementById(`btn-anim-${i}`);
      if (el) {
        el.style.borderColor = (i === m) ? 'var(--accent-amber)' : 'var(--border-color)';
      }
    }
    sendBacklightToDevice();
  }

  function onRgbSliderChange() {
    curR = parseInt(document.getElementById('rng-r').value);
    curG = parseInt(document.getElementById('rng-g').value);
    curB = parseInt(document.getElementById('rng-b').value);
    baseR = curR; baseG = curG; baseB = curB;
    curBrightness = 100;
    document.getElementById('rng-bright').value = 100;
    document.getElementById('num-bright').value = 100;
    document.getElementById('txt-bright').innerText = '100%';
    updateVisuals();
    sendBacklightToDevice();
  }

  function onRgbNumChange(ch) {
    if (ch === 'r') curR = Math.max(0, Math.min(255, parseInt(document.getElementById('num-r').value) || 0));
    if (ch === 'g') curG = Math.max(0, Math.min(255, parseInt(document.getElementById('num-g').value) || 0));
    if (ch === 'b') curB = Math.max(0, Math.min(255, parseInt(document.getElementById('num-b').value) || 0));
    baseR = curR; baseG = curG; baseB = curB;
    updateVisuals();
    sendBacklightToDevice();
  }

  function onBrightnessChange(val) {
    curBrightness = Math.max(5, Math.min(100, parseInt(val) || 100));
    document.getElementById('rng-bright').value = curBrightness;
    document.getElementById('num-bright').value = curBrightness;
    document.getElementById('txt-bright').innerText = `${curBrightness}%`;

    const factor = curBrightness / 100.0;
    curR = Math.round(baseR * factor);
    curG = Math.round(baseG * factor);
    curB = Math.round(baseB * factor);
    updateVisuals();
    sendBacklightToDevice();
  }

  function onNativeColorChange(hex) {
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    curR = r; curG = g; curB = b;
    baseR = r; baseG = g; baseB = b;
    curBrightness = 100;
    document.getElementById('rng-bright').value = 100;
    document.getElementById('num-bright').value = 100;
    document.getElementById('txt-bright').innerText = '100%';
    updateVisuals();
    sendBacklightToDevice();
  }

  function applyPreset(r, g, b, name) {
    curR = r; curG = g; curB = b;
    baseR = r; baseG = g; baseB = b;
    curBrightness = 100;
    ledActive = true;
    document.getElementById('rng-bright').value = 100;
    document.getElementById('num-bright').value = 100;
    document.getElementById('txt-bright').innerText = '100%';
    updateVisuals();
    sendBacklightToDevice();
  }

  async function toggleScreenLed() {
    ledActive = !ledActive;
    const btn = document.getElementById('btn-master-pwr');
    const badge = document.getElementById('badge-pwr');
    if (ledActive) {
      btn.innerText = 'Turn Off';
      badge.innerText = 'LED: ON';
      badge.className = 'status-badge badge-active';
    } else {
      btn.innerText = 'Turn On';
      badge.innerText = 'LED: OFF';
      badge.className = 'status-badge';
    }
    updateVisuals();
    sendBacklightToDevice();
  }

  async function toggleWifiSleep() {
    wifiSleepActive = !wifiSleepActive;
    const btn = document.getElementById('btn-wifi-sleep');
    const desc = document.getElementById('wifi-mode-desc');
    const simMode = document.getElementById('sim-mode-lbl');

    if (wifiSleepActive) {
      btn.innerText = 'Mode: Sleep Active';
      btn.className = 'btn btn-cyan';
      desc.innerHTML = '<b>Modem-Sleep (Current: ~50mA):</b> 100ms beacon pulses can modulate battery rail by ~50mV. Zero-blue / pure red avoids dropout flicker.';
      simMode.innerText = 'Modem-Sleep';
    } else {
      btn.innerText = 'Mode: Full Power (No Sleep)';
      btn.className = 'btn btn-amber';
      desc.innerHTML = '<b>Full Power (Current: ~103mA):</b> Constant non-oscillating power rail. Completely eliminates 10Hz beacon flicker regardless of LED color.';
      simMode.innerText = 'Full-Power';
    }

    try {
      await fetch(`/api/macropad/wifi_sleep?enabled=${wifiSleepActive ? 'true' : 'false'}`, { method: 'POST' });
    } catch (e) {
      try {
        await fetch(`${MACROPAD_DIRECT_URL}/api/wifi_sleep?enabled=${wifiSleepActive ? '1' : '0'}`);
      } catch (err) {}
    }
  }

  // Poll device status
  async function pollDevice() {
    try {
      const resp = await fetch(`${MACROPAD_DIRECT_URL}/api/status`);
      if (resp.ok) {
        const d = await resp.json();
        document.getElementById('badge-vbat').innerText = `BAT: ${d.vbat.toFixed(2)}V (${d.batt_pct}%)`;
      }
    } catch (e) {}
  }

  window.addEventListener('DOMContentLoaded', () => {
    updateVisuals();
    pollDevice();
    setInterval(pollDevice, 5000);
  });
</script>

</body>
</html>
"""
