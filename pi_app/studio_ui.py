"""
MacroPad Studio — Consumer-Grade WYSIWYG Hardware Configurator & Full-Picture Visualizer.
Served at `/` on the Unified Hub, while the raw telemetry/MQTT/battery engineering console lives at `/debug`.
"""

STUDIO_HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MacroPad Studio — WYSIWYG Configurator</title>
<style>
  :root {
    --bg-dark: #090c12;
    --bg-panel: #111622;
    --bg-card: #171e2e;
    --bg-elevated: #1e273b;
    --border: #263147;
    --border-bright: #384866;
    --text-main: #f0f4f8;
    --text-muted: #8b98b1;
    --accent-cyan: #00e5ff;
    --accent-green: #00e676;
    --accent-amber: #ffab00;
    --accent-purple: #b388ff;
    --accent-pink: #ff4081;
    --accent-blue: #2979ff;
    --accent-red: #ff5252;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-mono: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: radial-gradient(circle at 30% 20%, #131a29 0%, #070a0f 100%);
    color: var(--text-main);
    font-family: var(--font-sans);
    font-size: 13px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }

  /* ================= TOP NAVIGATION BAR ================= */
  .topbar {
    background: rgba(17, 22, 34, 0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    padding: 10px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .brand-area {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand-logo {
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: linear-gradient(135deg, #00e5ff 0%, #2979ff 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 16px;
    color: #05080f;
    box-shadow: 0 0 16px rgba(0, 229, 255, 0.35);
  }
  .brand-title {
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.3px;
    color: #fff;
  }
  .brand-sub {
    font-size: 11px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .hw-profile-select {
    background: var(--bg-card);
    color: var(--accent-cyan);
    border: 1px solid var(--border-bright);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }

  .status-strip {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 11px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-main);
  }
  .pill-clickable {
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .pill-clickable:hover {
    border-color: var(--accent-cyan);
    transform: translateY(-1px);
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
  }
  .dot-online { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
  .dot-sleep { background: var(--accent-amber); box-shadow: 0 0 8px var(--accent-amber); }
  .dot-offline { background: var(--accent-red); }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 7px 13px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid var(--border-bright);
    background: var(--bg-elevated);
    color: var(--text-main);
    cursor: pointer;
    transition: all 0.15s ease;
    text-decoration: none;
  }
  .btn:hover {
    border-color: var(--accent-cyan);
    background: #25314a;
  }
  .btn-primary {
    background: linear-gradient(135deg, #00e5ff 0%, #00b0ff 100%);
    color: #050811;
    border-color: transparent;
    font-weight: 700;
  }
  .btn-primary:hover {
    filter: brightness(1.1);
    box-shadow: 0 0 14px rgba(0, 229, 255, 0.4);
  }
  .btn-green {
    background: rgba(0, 230, 118, 0.15);
    color: var(--accent-green);
    border-color: rgba(0, 230, 118, 0.45);
  }
  .btn-green:hover {
    background: rgba(0, 230, 118, 0.25);
  }
  .btn-amber {
    background: rgba(255, 171, 0, 0.15);
    color: var(--accent-amber);
    border-color: rgba(255, 171, 0, 0.45);
  }

  .mode-switcher-pill {
    display: flex;
    align-items: center;
    gap: 3px;
    padding: 3px 4px !important;
    background: #090e18 !important;
    border: 1px solid #1f2c42 !important;
    border-radius: 9px !important;
  }
  .mode-btn {
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 700;
    padding: 4px 9px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .mode-btn:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.05);
  }
  .mode-btn.active-mode-auto {
    background: rgba(0, 230, 118, 0.18);
    color: var(--accent-green);
    border: 1px solid rgba(0, 230, 118, 0.5);
    box-shadow: 0 0 10px rgba(0, 230, 118, 0.25);
  }
  .mode-btn.active-mode-manual {
    background: rgba(0, 229, 255, 0.16);
    color: var(--accent-cyan);
    border: 1px solid rgba(0, 229, 255, 0.5);
    box-shadow: 0 0 10px rgba(0, 229, 255, 0.25);
  }
  .mode-btn.active-mode-debug {
    background: rgba(255, 171, 0, 0.2);
    color: var(--accent-amber);
    border: 1px solid rgba(255, 171, 0, 0.55);
    box-shadow: 0 0 10px rgba(255, 171, 0, 0.3);
  }

  /* ================= LAYER RIBBON BAR ================= */
  .layer-ribbon {
    background: rgba(13, 17, 27, 0.85);
    border-bottom: 1px solid var(--border);
    padding: 8px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    overflow-x: auto;
  }
  .bank-group {
    display: flex;
    align-items: center;
    gap: 4px;
    background: #0c101a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px 5px;
    flex-shrink: 0;
  }
  .bank-label {
    font-size: 10px;
    font-weight: 800;
    color: var(--text-muted);
    padding: 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
  }
  .layer-tab {
    padding: 5px 9px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 5px;
    transition: all 0.12s ease;
    white-space: nowrap;
  }
  .layer-tab:hover {
    color: #fff;
    background: rgba(255,255,255,0.05);
  }
  .layer-tab.active-edit {
    background: rgba(0, 229, 255, 0.16);
    color: var(--accent-cyan);
    border-color: var(--accent-cyan);
    font-weight: 700;
  }
  .layer-tab.live-on-pad {
    box-shadow: inset 0 -2px 0 var(--accent-green);
  }
  .app-tag {
    font-size: 9px;
    padding: 1px 4px;
    border-radius: 3px;
    background: rgba(179, 136, 255, 0.2);
    color: var(--accent-purple);
    font-weight: 700;
  }

  /* ================= MAIN STUDIO WORKSPACE ================= */
  .workspace {
    display: grid;
    grid-template-columns: 1fr 430px;
    gap: 20px;
    padding: 20px;
    max-width: 1650px;
    width: 100%;
    margin: 0 auto;
    flex: 1;
    align-items: start;
  }
  @media (max-width: 1220px) {
    .workspace { grid-template-columns: 1fr; }
  }

  .stage-column {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* ================= WYSIWYG PHYSICAL DEVICE ENCLOSURE ================= */
  .device-stage-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    box-shadow: 0 16px 40px rgba(0,0,0,0.45);
  }
  .stage-header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
  }
  .stage-title {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* Photorealistic Anodized Aluminum Case */
  .macropad-chassis {
    position: relative;
    background: linear-gradient(145deg, #1d2128 0%, #12151a 55%, #0d0f13 100%);
    border: 2px solid #2e3440;
    border-radius: 22px;
    padding: 28px 28px 26px 28px;
    box-shadow:
      0 24px 60px rgba(0, 0, 0, 0.75),
      inset 0 2px 3px rgba(255, 255, 255, 0.08),
      inset 0 -4px 8px rgba(0, 0, 0, 0.7);
    display: grid;
    grid-template-columns: 112px 368px 168px;
    gap: 20px;
    align-items: center;
    user-select: none;
  }
  @media (max-width: 820px) {
    .macropad-chassis {
      transform: scale(0.82);
      transform-origin: top center;
    }
  }

  /* USB-C Braided Cable Top Connector */
  .usbc-plug {
    position: absolute;
    top: -18px;
    left: 61%;
    transform: translateX(-50%);
    width: 44px;
    height: 18px;
    background: linear-gradient(90deg, #252a34, #3b4252, #252a34);
    border: 1px solid #4c566a;
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 8px;
    color: #88c0d0;
    font-family: var(--font-mono);
    letter-spacing: 0.5px;
  }

  /* 4 Brass Corner Screws */
  .screw {
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #ffd56b 0%, #c89628 70%, #78550d 100%);
    border: 1.5px solid #4a3508;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.6);
  }
  .screw::after {
    content: '';
    position: absolute;
    top: 3px; left: 3px;
    width: 4px; height: 4px;
    border-radius: 50%;
    background: #2b1d03;
  }
  .screw.tl { top: 10px; left: 10px; }
  .screw.tr { top: 10px; right: 10px; }
  .screw.bl { bottom: 10px; left: 10px; }
  .screw.br { bottom: 10px; right: 10px; }

  /* Left Encoders Column (Green Top-Left + Black Bottom-Left) */
  .left-encoders-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    height: 340px;
    padding: 8px 0;
  }
  .encoder-unit {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    cursor: pointer;
    padding: 6px;
    border-radius: 12px;
    border: 1.5px solid transparent;
    transition: all 0.15s ease;
    width: 110px;
  }
  .encoder-unit:hover, .encoder-unit.selected-control {
    border-color: var(--accent-cyan);
    background: rgba(0, 229, 255, 0.07);
  }
  .knob-circle {
    width: 76px;
    height: 76px;
    border-radius: 50%;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 20px rgba(0,0,0,0.65), inset 0 2px 4px rgba(255,255,255,0.2);
  }
  /* Knurled Forest Green Knob (Top-Left Encoder 3) */
  .knob-green {
    background: radial-gradient(circle at 35% 30%, #467a5c 0%, #264a36 65%, #162e20 100%);
    border: 3px dashed #356348;
  }
  /* Stepped Matte Black Knob (Bottom-Left Encoder 2) */
  .knob-black {
    background: radial-gradient(circle at 35% 30%, #3a3f47 0%, #1d2025 65%, #0e1013 100%);
    border: 3px solid #2c313a;
  }
  .knob-black::before {
    content: '';
    width: 54px;
    height: 54px;
    border-radius: 50%;
    border: 1.5px solid rgba(255,255,255,0.12);
    position: absolute;
  }
  /* Flared Gunmetal Knob with Pointer Line (Right Encoder 1) */
  .knob-gunmetal {
    width: 74px;
    height: 74px;
    background: conic-gradient(from 210deg, #4b525e, #7b8390, #383d47, #676f7d, #4b525e);
    border: 3px solid #2e3440;
  }
  .knob-pointer {
    position: absolute;
    top: 7px;
    width: 3px;
    height: 14px;
    border-radius: 2px;
    background: #eceff4;
    box-shadow: 0 0 4px rgba(0,0,0,0.8);
  }
  .knob-cap-label {
    font-size: 10px;
    font-weight: 800;
    color: rgba(255,255,255,0.85);
    text-shadow: 0 1px 3px rgba(0,0,0,0.9);
    text-align: center;
    line-height: 1.1;
  }
  .enc-caption {
    text-align: center;
    font-size: 9.5px;
    line-height: 1.25;
    color: var(--text-muted);
  }
  .enc-caption strong {
    color: var(--text-main);
    display: block;
    font-size: 10px;
  }

  /* Center 4x4 Key Matrix */
  .matrix-4x4 {
    display: grid;
    grid-template-columns: repeat(4, 84px);
    grid-template-rows: repeat(4, 84px);
    gap: 10px;
    background: #0b0d12;
    padding: 10px;
    border-radius: 14px;
    border: 1px solid #232834;
    box-shadow: inset 0 4px 10px rgba(0,0,0,0.85);
  }

  .keycap {
    position: relative;
    border-radius: 10px;
    background: linear-gradient(180deg, #2b303c 0%, #20242d 75%, #171a21 100%);
    border: 1.5px solid #383f4e;
    box-shadow:
      0 5px 0 #0d0f14,
      0 7px 12px rgba(0,0,0,0.6),
      inset 0 1px 1px rgba(255,255,255,0.12);
    padding: 5px 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    transition: all 0.12s ease;
    overflow: hidden;
  }
  .keycap:hover {
    border-color: var(--accent-cyan);
    transform: translateY(-1px);
  }
  .keycap.selected-control {
    border-color: var(--accent-cyan);
    box-shadow:
      0 0 0 2px rgba(0, 229, 255, 0.35),
      0 5px 0 #0d0f14;
    background: linear-gradient(180deg, #323c4e 0%, #232b3a 80%, #19202c 100%);
  }
  .keycap.live-pressed {
    transform: translateY(3px);
    box-shadow: 0 2px 0 #0d0f14, 0 0 18px var(--accent-green);
    border-color: var(--accent-green);
  }

  /* Top Row A, B, C, D Keys */
  .keycap.key-top-slot {
    background: linear-gradient(180deg, #323846 0%, #242934 80%, #1a1e26 100%);
  }
  .keycap.key-top-slot.active-slot-led {
    border-bottom: 3px solid var(--accent-cyan);
  }
  .top-letter {
    font-size: 16px;
    font-weight: 800;
    color: #e5e9f0;
    line-height: 1;
  }
  .key-tap-line {
    font-size: 9px;
    font-weight: 700;
    color: var(--accent-cyan);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }
  .key-hold-badge {
    font-size: 8.5px;
    font-weight: 700;
    padding: 1.5px 5px;
    border-radius: 4px;
    background: rgba(255, 171, 0, 0.18);
    color: var(--accent-amber);
    border: 1px solid rgba(255, 171, 0, 0.35);
    white-space: nowrap;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .key-hold-badge.radial-badge {
    background: rgba(0, 229, 255, 0.16);
    color: var(--accent-cyan);
    border-color: rgba(0, 229, 255, 0.4);
  }

  /* Left Fixed Column Keys (5, 9, 13) */
  .keycap.key-fixed {
    background: linear-gradient(180deg, #272c37 0%, #1b1f27 80%, #14171d 100%);
  }
  .fixed-symbol {
    font-size: 17px;
    line-height: 1;
    margin-top: 2px;
  }

  /* 3x3 Dynamic Matrix Keycaps */
  .dyn-cell-num {
    position: absolute;
    top: 3px;
    left: 5px;
    font-size: 8px;
    font-family: var(--font-mono);
    color: rgba(255,255,255,0.3);
  }
  .power-corner-glyph {
    position: absolute;
    top: 3px;
    right: 5px;
    font-size: 9px;
    color: rgba(255,255,255,0.45);
  }
  .homing-bar {
    width: 18px;
    height: 2px;
    background: rgba(255,255,255,0.38);
    border-radius: 1px;
    position: absolute;
    bottom: 3px;
  }
  .keycap-icon-canvas {
    width: 24px;
    height: 24px;
    image-rendering: pixelated;
    margin-top: 4px;
  }
  .dyn-key-label {
    font-size: 10.5px;
    font-weight: 800;
    color: #fff;
    text-align: center;
    line-height: 1.1;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Right Column: Gunmetal Encoder + Square E-Ink Screen */
  .right-screen-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    height: 356px;
  }
  .eink-bezel {
    width: 162px;
    height: 162px;
    background: #0a0c10;
    border: 3px solid #2b303c;
    border-radius: 10px;
    padding: 6px;
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.9);
    display: flex;
    flex-direction: column;
    position: relative;
  }
  .eink-paper {
    background: #dfe5e1;
    color: #111513;
    width: 100%;
    height: 100%;
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: var(--font-mono);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.25);
  }
  .eink-topbar {
    height: 16px;
    background: #111513;
    color: #dfe5e1;
    font-size: 9px;
    font-weight: 800;
    padding: 0 5px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .eink-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(3, 1fr);
  }
  .eink-cell {
    border-right: 1px solid #111513;
    border-bottom: 1px solid #111513;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2px;
    text-align: center;
    overflow: hidden;
    cursor: pointer;
  }
  .eink-cell:nth-child(3n) { border-right: none; }
  .eink-cell:nth-child(n+7) { border-bottom: none; }
  .eink-cell:hover { background: rgba(0, 0, 0, 0.08); }
  .eink-cell-lbl {
    font-size: 7.5px;
    font-weight: 800;
    line-height: 1.1;
    color: #111513;
    word-break: break-word;
  }

  /* ================= FULL 16-LAYER VISUAL CHEAT-SHEET MATRIX ================= */
  .cheatsheet-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px;
  }
  .cheatsheet-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 12px;
    margin-top: 12px;
  }
  .mini-layer-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .mini-layer-card:hover {
    border-color: var(--accent-cyan);
    transform: translateY(-2px);
  }
  .mini-layer-card.active-edit {
    border-color: var(--accent-cyan);
    box-shadow: 0 0 0 1px var(--accent-cyan);
  }
  .mini-layer-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 11px;
    font-weight: 700;
  }
  .mini-3x3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
  }
  .mini-cell {
    background: #0d121c;
    border: 1px solid #222b3d;
    border-radius: 4px;
    padding: 4px 3px;
    text-align: center;
    font-size: 9px;
    font-weight: 700;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mini-cell.has-radial {
    border-bottom: 2px solid var(--accent-cyan);
  }

  /* ================= RIGHT INSPECTOR PANEL ================= */
  .inspector-panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    position: sticky;
    top: 68px;
    display: flex;
    flex-direction: column;
    max-height: calc(100vh - 88px);
    box-shadow: 0 16px 40px rgba(0,0,0,0.45);
  }
  .inspector-tabs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    background: #0c1018;
    border-bottom: 1px solid var(--border);
  }
  .insp-tab {
    padding: 12px 10px;
    text-align: center;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.15s ease;
  }
  .insp-tab.active {
    color: var(--accent-cyan);
    border-bottom-color: var(--accent-cyan);
    background: rgba(0, 229, 255, 0.06);
  }
  .inspector-body {
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .field-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .input-box, .select-box {
    width: 100%;
    padding: 8px 10px;
    border-radius: 7px;
    border: 1px solid var(--border-bright);
    background: #0c101a;
    color: #fff;
    font-size: 12px;
    font-family: var(--font-sans);
  }
  .input-box:focus, .select-box:focus {
    outline: none;
    border-color: var(--accent-cyan);
  }

  /* Visual Icon Picker Grid */
  .icon-picker-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    max-height: 156px;
    overflow-y: auto;
    padding: 6px;
    background: #0b0f18;
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .icon-tile {
    aspect-ratio: 1;
    border-radius: 6px;
    border: 1px solid #1f293d;
    background: #131926;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    cursor: pointer;
    padding: 3px;
    transition: all 0.12s ease;
  }
  .icon-tile:hover {
    border-color: var(--accent-cyan);
    background: #1c263b;
  }
  .icon-tile.selected {
    border-color: var(--accent-cyan);
    background: rgba(0, 229, 255, 0.18);
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
  }
  .icon-tile span {
    font-size: 7.5px;
    color: var(--text-muted);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Interactive Radial Pie Menu Preview & Editor */
  .radial-box {
    background: #0d121d;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .radial-wheel-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6px 0;
  }
  .slice-row {
    display: grid;
    grid-template-columns: 22px 95px 1fr 26px;
    gap: 5px;
    align-items: center;
    background: var(--bg-card);
    padding: 5px 6px;
    border-radius: 6px;
    border: 1px solid var(--border);
  }
  .slice-row.active-slice {
    border-color: var(--accent-cyan);
  }

  .app-rule-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 10px;
    display: flex;
    flex-direction: column;
    gap: 7px;
  }
</style>
</head>
<body>

<!-- ================= TOP NAVIGATION BAR ================= -->
<header class="topbar">
  <div class="brand-area">
    <div class="brand-logo">M</div>
    <div>
      <div class="brand-title">MacroPad Studio</div>
      <div class="brand-sub">
        <span>WYSIWYG Hardware Surface</span>
        <span>•</span>
        <select id="hw-model-select" class="hw-profile-select" title="Modular Hardware Profile (Future-ready)">
          <option value="macropad_pro_16">MacroPad Pro (16-Key • 3-Knob • E-Ink)</option>
          <option value="macropad_mini_4" disabled>MacroPad Mini (4-Key • 1-Knob) [Coming Soon]</option>
          <option value="macropad_one_1" disabled>MacroPad Nano (1-Key Macro) [Coming Soon]</option>
        </select>
      </div>
    </div>
  </div>

  <div class="status-strip">
    <div class="pill" title="MacroPad Connection & Battery">
      <span id="status-dot" class="dot dot-online"></span>
      <span id="status-text">ONLINE</span>
      <span style="color:var(--text-muted)">|</span>
      <span id="batt-text" style="color:var(--accent-green); font-family:var(--font-mono);">--V (--%)</span>
    </div>

    <div class="pill mode-switcher-pill" title="MacroPad Operating Mode: Auto Mode (Dynamic App Sensing) / Manual (16 Layers) / Debug (Diagnostics)">
      <button id="btn-mode-auto" class="mode-btn active-mode-auto" onclick="setDeviceMode('automode')" title="Dynamic layer switching based on focused Windows application">🤖 AUTOMODE</button>
      <button id="btn-mode-manual" class="mode-btn" onclick="setDeviceMode('manual')" title="Static manual layer switching (Bank 1..4, L1..L16)">🎛️ MANUAL</button>
      <button id="btn-mode-debug" class="mode-btn" onclick="setDeviceMode('debug')" title="Dedicated hardware diagnostics, modem sleep, deep sleep, and HUD testing">🛠️ DEBUG</button>
    </div>

    <div class="pill" title="Currently Focused Windows Application">
      <span>🎯 Focused:</span>
      <strong id="focused-app-text" style="color:var(--accent-cyan); font-family:var(--font-mono);">--</strong>
    </div>

    <button class="btn" onclick="openTdxLibraryModal()" style="background:rgba(0,229,255,0.14); color:var(--accent-cyan); border-color:rgba(0,229,255,0.45); font-weight:700;" title="Browse & Import 260+ Harvested 3Dconnexion Application Profiles, Icons & Radial Menus">
      📦 3Dconnexion Library (260)
    </button>
    <a href="/debug/backlight" class="btn" style="color:var(--accent-amber); border-color:rgba(255,184,0,0.4);" title="Open Dedicated Screen Backlight & LED Calibrator">
      💡 Backlight
    </a>
    <a href="/debug" class="btn" title="Open Engineering Telemetry, Battery Curves, MQTT & Raw Logs">
      🛠️ Debug & Telemetry
    </a>
  </div>
</header>

<!-- ================= ALL-16-LAYERS RIBBON BAR ================= -->
<nav class="layer-ribbon" id="layer-ribbon"></nav>

<!-- ================= MAIN WORKSPACE ================= -->
<main class="workspace">

  <!-- LEFT / CENTER STAGE: WYSIWYG HARDWARE + FULL 16-LAYER CHEAT-SHEET -->
  <div class="stage-column">

    <!-- 1. INTERACTIVE WYSIWYG HARDWARE SURFACE -->
    <section class="device-stage-card">
      <div class="stage-header">
        <div class="stage-title">
          <span id="active-layer-heading">Layer 13: Fusion 360</span>
          <span id="live-pad-indicator" class="pill" style="font-size:10px; padding:3px 8px; background:rgba(0,230,118,0.12); color:var(--accent-green); border-color:rgba(0,230,118,0.35);">
            ● Live on Pad
          </span>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <label style="font-size:11px; color:var(--text-muted); display:flex; align-items:center; gap:5px; cursor:pointer;">
            <input type="checkbox" id="chk-live-preview-sync" checked style="accent-color:var(--accent-cyan);">
            Sync selection to physical E-Ink screen
          </label>
          <button class="btn" onclick="openTdxLibraryModal()" style="border-color:rgba(0,229,255,0.4); color:var(--accent-cyan);" title="Import a 3Dconnexion App Profile into this Layer">📦 Import 3Dx App</button>
          <button class="btn btn-green" onclick="pushSelectedLayerToPad()">⚡ Push to Device</button>
          <button class="btn btn-primary" onclick="saveCurrentLayer()">💾 Save Layer</button>
        </div>
      </div>

      <!-- PHOTOREALISTIC CHASSIS MATCHING USER PHOTO -->
      <div class="macropad-chassis">
        <div class="usbc-plug">USB-C</div>
        <div class="screw tl"></div>
        <div class="screw tr"></div>
        <div class="screw bl"></div>
        <div class="screw br"></div>

        <!-- LEFT COLUMN: 2 ROTARY ENCODERS (TOP-LEFT GREEN, BOTTOM-LEFT BLACK) -->
        <div class="left-encoders-col">
          <!-- Top-Left Green Knurled Knob (Encoder 3) -->
          <div class="encoder-unit" id="ctrl-enc-3" onclick="selectControl('encoder', 3)">
            <div class="knob-circle knob-green">
              <div class="knob-cap-label" id="enc3-cap">ENC 3<br>TOP-L</div>
            </div>
            <div class="enc-caption" id="enc3-caption">
              <strong>Top-Left Knob</strong>
              <span>Turn: Zoom / Discord</span>
            </div>
          </div>

          <!-- Bottom-Left Black Stepped Knob (Encoder 2) -->
          <div class="encoder-unit" id="ctrl-enc-2" onclick="selectControl('encoder', 2)">
            <div class="knob-circle knob-black">
              <div class="knob-cap-label" id="enc2-cap">ENC 2<br>BTM-L</div>
            </div>
            <div class="enc-caption" id="enc2-caption">
              <strong>Bottom-Left Knob</strong>
              <span>Turn: User Vol / Undo</span>
            </div>
          </div>
        </div>

        <!-- CENTER 4x4 KEY MATRIX -->
        <div class="matrix-4x4" id="wysiwyg-matrix-4x4">
          <!-- Populated dynamically by renderHardwareCanvas() -->
        </div>

        <!-- RIGHT COLUMN: GUNMETAL ENCODER 1 + SQUARE E-INK DISPLAY -->
        <div class="right-screen-col">
          <!-- Top-Right Gunmetal Knob (Encoder 1) -->
          <div class="encoder-unit" id="ctrl-enc-1" onclick="selectControl('encoder', 1)">
            <div class="knob-circle knob-gunmetal">
              <div class="knob-pointer"></div>
              <div class="knob-cap-label" style="margin-top:12px;">MASTER</div>
            </div>
            <div class="enc-caption" id="enc1-caption">
              <strong>Right Master Knob</strong>
              <span>Turn: Master / Zoom</span>
            </div>
          </div>

          <!-- Bottom-Right Square E-Ink Display Replica -->
          <div class="eink-bezel" title="Live 200x200 E-Ink Screen Mirror (Click any cell to edit)">
            <div class="eink-paper">
              <div class="eink-topbar">
                <span id="eink-hdr-left">B1L1 [A]</span>
                <span id="eink-hdr-right">100%</span>
              </div>
              <div class="eink-grid" id="eink-screen-grid"></div>
            </div>
          </div>
        </div>
      </div>

      <div style="font-size:11px; color:var(--text-muted); text-align:center;">
        💡 <strong>Tip:</strong> Click any keycap or rotary knob above to customize its <strong>Tap Action</strong>, <strong>Icon</strong>, <strong>Hold Radial Pie Menu</strong>, or <strong>Mouse Modifier</strong>. Double-click top keys <strong>A / B / C / D</strong> to jump between layers in the current bank.
      </div>
    </section>

    <!-- 2. FULL PICTURE: ALL 16 LAYERS AT A GLANCE -->
    <section class="cheatsheet-card">
      <div class="stage-header">
        <div class="stage-title">
          <span>🗺️ Full Device Map — All 16 Layers at a Glance</span>
          <span style="font-size:11px; font-weight:400; color:var(--text-muted);">(Click any layer card to load & edit)</span>
        </div>
      </div>
      <div class="cheatsheet-grid" id="all-layers-cheatsheet"></div>
    </section>

  </div>

  <!-- RIGHT INSPECTOR PANEL -->
  <aside class="inspector-panel">
    <div class="inspector-tabs">
      <div class="insp-tab active" id="tab-btn-key" onclick="switchInspectorTab('key')">🎹 Key & Knob Editor</div>
      <div class="insp-tab" id="tab-btn-apps" onclick="switchInspectorTab('apps')">🤖 App Auto-Switch</div>
    </div>

    <!-- TAB 1: CONTEXT-AWARE KEY / KNOB / RADIAL INSPECTOR -->
    <div class="inspector-body" id="inspector-tab-key"></div>

    <!-- TAB 2: APP AUTO-SWITCH RULES STUDIO -->
    <div class="inspector-body" id="inspector-tab-apps" style="display:none;"></div>
  </aside>

</main>

<!-- ================= 3DCONNEXION APP LIBRARY MODAL (260+ APPS) ================= -->
<div id="tdx-library-modal" style="display:none; position:fixed; inset:0; z-index:9999; background:rgba(8,10,14,0.84); backdrop-filter:blur(6px); align-items:center; justify-content:center; padding:24px;">
  <div style="width:100%; max-width:1160px; height:86vh; background:var(--bg-panel); border:1px solid var(--border); border-radius:16px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 24px 64px rgba(0,0,0,0.75);">
    <!-- Header -->
    <div style="padding:14px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; background:var(--bg-card);">
      <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-size:22px;">📦</span>
        <div>
          <div style="font-size:15px; font-weight:800; color:#fff;">Multi-Driver Harvested Application Library</div>
          <div id="tdx-stats-subtitle" style="font-size:11px; color:var(--text-muted);">312 Apps • 398 Driver Presets across 3Dconnexion, Loupedeck, TourBox, Wacom & PowerUser</div>
        </div>
      </div>
      <div style="display:flex; gap:10px; align-items:center;">
        <input type="text" id="tdx-search-input" class="input-field" placeholder="🔍 Search app or .exe (Blender, Photoshop, Premiere, Bambu, Krita, KiCad...)" oninput="renderTdxAppList()" style="width:340px; padding:7px 12px;">
        <button class="btn" onclick="closeTdxLibraryModal()" style="padding:6px 12px;">✕ Close</button>
      </div>
    </div>

    <!-- Body: Left App List + Right App Inspector & Layer Importer -->
    <div style="flex:1; display:grid; grid-template-columns:360px 1fr; overflow:hidden;">
      <!-- Left Column: Source Filter Pills + App List -->
      <div style="border-right:1px solid var(--border); display:flex; flex-direction:column; background:rgba(0,0,0,0.18); overflow:hidden;">
        <div id="tdx-source-filters" style="padding:8px 10px; border-bottom:1px solid var(--border); display:flex; gap:4px; flex-wrap:wrap; background:rgba(0,0,0,0.12);">
          <button class="btn btn-src-filter active" onclick="setTdxSourceFilter('all')" data-src="all" style="padding:3px 7px; font-size:10px;">All</button>
          <button class="btn btn-src-filter" onclick="setTdxSourceFilter('3Dconnexion')" data-src="3Dconnexion" style="padding:3px 7px; font-size:10px;">🧊 3Dx</button>
          <button class="btn btn-src-filter" onclick="setTdxSourceFilter('Loupedeck')" data-src="Loupedeck" style="padding:3px 7px; font-size:10px;">🎛️ LD</button>
          <button class="btn btn-src-filter" onclick="setTdxSourceFilter('TourBox')" data-src="TourBox" style="padding:3px 7px; font-size:10px;">🎮 TB</button>
          <button class="btn btn-src-filter" onclick="setTdxSourceFilter('Wacom')" data-src="Wacom" style="padding:3px 7px; font-size:10px;">✒️ Wacom</button>
          <button class="btn btn-src-filter" onclick="setTdxSourceFilter('PowerUser')" data-src="PowerUser" style="padding:3px 7px; font-size:10px;">⚡ Power</button>
          <button class="btn btn-src-filter" onclick="setTdxSourceFilter('multi')" data-src="multi" style="padding:3px 7px; font-size:10px; color:var(--accent-amber);">🔀 Multi</button>
        </div>
        <div id="tdx-app-list" style="flex:1; overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:6px;"></div>
      </div>

      <!-- Right App Preview & Importer -->
      <div id="tdx-app-detail" style="overflow-y:auto; padding:18px; display:flex; flex-direction:column; gap:16px;"></div>
    </div>
  </div>
</div>

<script>
  // ================= STATE & ACTION CATALOG =================
  let layersStore = {};
  let iconsLibrary = {};
  let tdxCatalogApps = [];
  let tdxStats = {};
  let selectedTdxAppId = "blender";
  let selectedTdxSourceFilter = "all";
  let selectedDetailPresetSource = "";
  let appRulesConfig = {
    auto_app_mode: true,
    untracked_behavior: 'stay',
    fallback_layer: 1,
    top_modifiers: { "1": "SHIFT", "2": "CTRL", "3": "ALT", "4": "ORBIT_CLUTCH" },
    rules: []
  };
  let liveDeviceState = {
    layer: 1,
    bank: 1,
    slot: 1,
    vbat: 4.0,
    batt_pct: 80,
    state: 'online',
    auto_app_mode: true,
    in_call: false,
    focused_app_exe: '',
    focused_app_title: '',
    grid_labels: []
  };

  let selectedLayerId = "13";
  let selectedControl = { type: 'cell', index: 1 }; // 'cell' (1..9), 'top' (1..4), 'fixed' (5,9,13), 'encoder' (1..3)
  let selectedRadialSliceIdx = 0;

  // Friendly Guided Action Catalog so users never need to memorize syntax
  const ACTION_CATALOG = [
    {
      group: "🛠️ Fusion 360 — Sketch & 2D",
      items: [
        { label: "Line (L)", val: "fusion:line" },
        { label: "Create Sketch", val: "fusion:create_sketch" },
        { label: "Finish Sketch", val: "fusion:finish_sketch" },
        { label: "2-Point Rectangle (R)", val: "fusion:rect_2pt" },
        { label: "Center Rectangle", val: "fusion:rect_center" },
        { label: "3-Point Rectangle", val: "fusion:rect_3pt" },
        { label: "Center Circle (C)", val: "fusion:circle_center" },
        { label: "3-Point Arc", val: "fusion:arc_3pt" },
        { label: "Fit Point Spline", val: "fusion:spline_fit" },
        { label: "Circumscribed Polygon", val: "fusion:poly_circum" },
        { label: "Inscribed Polygon", val: "fusion:poly_inscr" },
        { label: "Center Slot", val: "fusion:slot_center" },
        { label: "Sketch Dimension (D)", val: "fusion:dimension" },
        { label: "Offset (O)", val: "fusion:offset" },
        { label: "Trim (T)", val: "fusion:trim" },
        { label: "Extend", val: "fusion:extend" },
        { label: "Project Geometry (P)", val: "fusion:project" },
        { label: "Construction Line (X)", val: "fusion:construction" },
        { label: "2D Sketch Mirror", val: "fusion:sketch_mirror" }
      ]
    },
    {
      group: "🧊 Fusion 360 — 3D Solid & Modify",
      items: [
        { label: "Extrude (E)", val: "fusion:extrude" },
        { label: "Revolve", val: "fusion:revolve" },
        { label: "Sweep", val: "fusion:sweep" },
        { label: "Loft", val: "fusion:loft" },
        { label: "Hole (H)", val: "fusion:hole" },
        { label: "Thread", val: "fusion:thread" },
        { label: "Fillet (F)", val: "fusion:fillet" },
        { label: "Chamfer", val: "fusion:chamfer" },
        { label: "Shell", val: "fusion:shell" },
        { label: "Press Pull (Q)", val: "fusion:press_pull" },
        { label: "Combine Bodies", val: "fusion:combine" },
        { label: "Split Body", val: "fusion:split_body" },
        { label: "Split Face", val: "fusion:split_face" },
        { label: "Mirror 3D", val: "fusion:mirror_3d" },
        { label: "Rectangular Pattern", val: "fusion:pattern_rect" },
        { label: "Circular Pattern", val: "fusion:pattern_circ" },
        { label: "Move / Copy (M)", val: "fusion:move" },
        { label: "Align", val: "fusion:align" },
        { label: "Scale", val: "fusion:scale" }
      ]
    },
    {
      group: "🔍 Fusion 360 — Inspect, Planes & View",
      items: [
        { label: "Measure (I)", val: "fusion:measure" },
        { label: "Section Analysis", val: "fusion:section" },
        { label: "Interference Check", val: "fusion:interference" },
        { label: "Offset Plane", val: "fusion:plane_offset" },
        { label: "Midplane", val: "fusion:plane_mid" },
        { label: "Parameters (fx)", val: "fusion:parameters" },
        { label: "View: Home Isometric", val: "fusion_view:iso" },
        { label: "View: Top", val: "fusion_view:top" },
        { label: "View: Front", val: "fusion_view:front" },
        { label: "View: Right", val: "fusion_view:right" },
        { label: "View: Fit to Screen (F6)", val: "fusion_view:fit" },
        { label: "Cancel / Escape (ESC)", val: "cad_key:ESC" }
      ]
    },
    {
      group: "🎙️ Discord & Audio Mixer",
      items: [
        { label: "Discord Mic Mute Toggle", val: "discord_mic_mute" },
        { label: "Discord Deafen Toggle", val: "discord_deafen" },
        { label: "Discord App Volume -10%", val: "discord_vol_down" },
        { label: "Discord App Volume +10%", val: "discord_vol_up" },
        { label: "Discord App Volume 100%", val: "discord_vol_reset" },
        { label: "Output -> Logitech G321 Headphones", val: "audio_headphones" },
        { label: "Output -> Edifier Speakers", val: "audio_speakers" },
        { label: "Sync Live Discord Voice Call", val: "discord_sync_call" },
        { label: "Toggle 5-User Demo Voice Call", val: "discord_demo_call" }
      ]
    },
    {
      group: "📐 AutoCAD Commands",
      items: [
        { label: "AutoCAD: LINE (L)", val: "cad_cmd:L" },
        { label: "AutoCAD: PLINE (PL)", val: "cad_cmd:PL" },
        { label: "AutoCAD: RECTANG (REC)", val: "cad_cmd:REC" },
        { label: "AutoCAD: CIRCLE (C)", val: "cad_cmd:C" },
        { label: "AutoCAD: ARC (A)", val: "cad_cmd:A" },
        { label: "AutoCAD: MOVE (M)", val: "cad_cmd:M" },
        { label: "AutoCAD: COPY (CO)", val: "cad_cmd:CO" },
        { label: "AutoCAD: ROTATE (RO)", val: "cad_cmd:RO" },
        { label: "AutoCAD: TRIM (TR)", val: "cad_cmd:TR" },
        { label: "AutoCAD: EXTEND (EX)", val: "cad_cmd:EX" },
        { label: "AutoCAD: OFFSET (O)", val: "cad_cmd:O" },
        { label: "AutoCAD: MIRROR (MI)", val: "cad_cmd:MI" },
        { label: "AutoCAD: FILLET (F)", val: "cad_cmd:F" },
        { label: "AutoCAD: CHAMFER (CHA)", val: "cad_cmd:CHA" },
        { label: "AutoCAD: DIM (DIM)", val: "cad_cmd:DIM" },
        { label: "AutoCAD: LAYER MGR (LA)", val: "cad_cmd:LA" },
        { label: "AutoCAD: ZOOM EXTENTS (Z E)", val: "cad_cmd:Z E" }
      ]
    },
    {
      group: "⌨️ Common Keyboard Shortcuts & System",
      items: [
        { label: "Undo (Ctrl+Z)", val: "hotkey:CTRL+Z" },
        { label: "Redo (Ctrl+Y)", val: "hotkey:CTRL+Y" },
        { label: "Save (Ctrl+S)", val: "hotkey:CTRL+S" },
        { label: "Copy (Ctrl+C)", val: "hotkey:CTRL+C" },
        { label: "Paste (Ctrl+V)", val: "hotkey:CTRL+V" },
        { label: "Escape (ESC)", val: "cad_key:ESC" },
        { label: "Enter", val: "hotkey:ENTER" },
        { label: "Space", val: "hotkey:SPACE" },
        { label: "Delete", val: "hotkey:DELETE" },
        { label: "Wake-on-LAN PC", val: "wakeonlan" },
        { label: "Room Light Toggle", val: "light_toggle" }
      ]
    }
  ];

  function escapeHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatActionFriendly(act) {
    if (!act) return 'None';
    for (const grp of ACTION_CATALOG) {
      for (const it of grp.items) {
        if (it.val === act) return it.label;
      }
    }
    return act;
  }

  // Renders 1-bit hex bitmap (24x24) onto a canvas
  function drawIconHexOnCanvas(canvas, hexStr, fgColor = '#00e5ff', bgColor = null) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = 24, h = 24;
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);
    if (bgColor) {
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, w, h);
    }
    if (!hexStr || hexStr.length < 144) return;
    ctx.fillStyle = fgColor;
    const bytesPerRow = 3;
    for (let r = 0; r < h; r++) {
      for (let b = 0; b < bytesPerRow; b++) {
        const byteIndex = (r * bytesPerRow + b) * 2;
        const byteVal = parseInt(hexStr.substr(byteIndex, 2), 16);
        for (let bit = 0; bit < 8; bit++) {
          if ((byteVal & (1 << (7 - bit))) !== 0) {
            ctx.fillRect(b * 8 + bit, r, 1, 1);
          }
        }
      }
    }
  }

  // ================= INITIALIZATION & WEBSOCKET =================
  async function initStudio() {
    await loadTdxCatalog();
    await loadAllConfig();
    connectWebSocket();
  }

  async function loadAllConfig() {
    try {
      const res = await fetch('/api/layers');
      const data = await res.json();
      layersStore = data.layers || {};
      iconsLibrary = data.icons || {};
      if (data.app_rules_config) {
        appRulesConfig = data.app_rules_config;
      }
      if (data.current_layer) {
        liveDeviceState.layer = data.current_layer;
        selectedLayerId = String(data.current_layer);
      }
      if (data.mode) {
        liveDeviceState.mode = data.mode;
      }
      if (typeof data.auto_app_mode !== 'undefined') {
        liveDeviceState.auto_app_mode = data.auto_app_mode;
      }
      renderAll();
      updateTopStatusBar();
    } catch (e) {
      console.error('Failed to load studio config:', e);
    }
  }

  function connectWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'state' && msg.data) {
          const prevLayer = liveDeviceState.layer;
          liveDeviceState = { ...liveDeviceState, ...msg.data };
          updateTopStatusBar();
          if (liveDeviceState.layer && prevLayer !== liveDeviceState.layer) {
            if (document.getElementById('chk-live-preview-sync')?.checked) {
              selectedLayerId = String(liveDeviceState.layer);
            }
            renderLayerRibbon();
            renderHardwareCanvas();
            renderCheatsheet();
          } else {
            renderEinkPreview();
          }
        }
      } catch (e) {}
    };
    ws.onclose = () => setTimeout(connectWebSocket, 2500);
  }

  function updateTopStatusBar() {
    const dot = document.getElementById('status-dot');
    const stTxt = document.getElementById('status-text');
    const battTxt = document.getElementById('batt-text');
    const autoBadge = document.getElementById('auto-app-badge');
    const focTxt = document.getElementById('focused-app-text');

    const st = (liveDeviceState.state || 'online').toLowerCase();
    dot.className = 'dot ' + (st === 'online' ? 'dot-online' : st.includes('sleep') ? 'dot-sleep' : 'dot-offline');
    stTxt.textContent = st.toUpperCase();

    const vbat = Number(liveDeviceState.vbat || 0).toFixed(2);
    const pct = liveDeviceState.batt_pct ?? '--';
    battTxt.textContent = `${vbat}V (${pct}%)`;

    const activeMode = (liveDeviceState.mode || (liveDeviceState.auto_app_mode ? 'automode' : 'manual')).toLowerCase();
    document.getElementById('btn-mode-auto')?.classList.toggle('active-mode-auto', activeMode === 'automode' || activeMode === 'auto');
    document.getElementById('btn-mode-manual')?.classList.toggle('active-mode-manual', activeMode === 'manual');
    document.getElementById('btn-mode-debug')?.classList.toggle('active-mode-debug', activeMode === 'debug');

    if (autoBadge) {
      autoBadge.textContent = activeMode.toUpperCase();
      autoBadge.style.color = (activeMode === 'automode' || activeMode === 'auto') ? 'var(--accent-green)' : (activeMode === 'debug') ? 'var(--accent-amber)' : 'var(--accent-cyan)';
    }

    const exe = liveDeviceState.focused_exe || liveDeviceState.focused_app_exe || 'None';
    const title = liveDeviceState.focused_title || liveDeviceState.focused_app_title || '';
    const matchRule = liveDeviceState.matched_rule || liveDeviceState.active_app_rule || '';
    const ruleStr = matchRule ? ` → ${matchRule}` : '';
    focTxt.textContent = `${exe}${ruleStr}`;
    focTxt.title = title ? `${exe} — "${title}"` : exe;

    const btnTrack = document.getElementById('btn-track-focused-app');
    if (btnTrack) {
      btnTrack.textContent = `+ Track Focused App (${exe})`;
    }
    const studioBanner = document.getElementById('studio-live-app-banner');
    if (studioBanner) {
      studioBanner.textContent = exe !== 'None' ? `${exe}${title ? ' • "' + title + '"' : ''}${ruleStr}` : 'Waiting for PC Bridge...';
    }
  }

  async function setDeviceMode(mode) {
    try {
      const res = await fetch('/api/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      const data = await res.json();
      liveDeviceState.mode = data.mode;
      liveDeviceState.auto_app_mode = data.auto_app_mode;
      updateTopStatusBar();
    } catch (e) {
      alert('Error setting mode: ' + e);
    }
  }

  function renderAll() {
    updateTopStatusBar();
    renderLayerRibbon();
    renderHardwareCanvas();
    renderInspector();
    renderAppRulesTab();
    renderCheatsheet();
  }

  // ================= 1. TOP 16-LAYER RIBBON =================
  function getAppBadgeForLayer(lid) {
    const rules = appRulesConfig.rules || [];
    const found = rules.find(r => r.enabled !== false && Number(r.target_layer || r.layer) === Number(lid));
    if (!found) return '';
    const shortName = (found.name || '').replace('Autodesk ', '').replace('Adobe ', '').split(' ')[0];
    return `<span class="app-tag">📱 ${escapeHtml(shortName)}</span>`;
  }

  function renderLayerRibbon() {
    const rib = document.getElementById('layer-ribbon');
    rib.innerHTML = '';
    const slotLetters = ['A', 'B', 'C', 'D'];

    for (let bank = 1; bank <= 4; bank++) {
      const grp = document.createElement('div');
      grp.className = 'bank-group';
      grp.innerHTML = `<span class="bank-label">Bank ${bank}</span>`;

      for (let slot = 1; slot <= 4; slot++) {
        const lid = String((bank - 1) * 4 + slot);
        const lObj = layersStore[lid] || { name: `Layer ${lid}` };
        const btn = document.createElement('button');
        const isEdit = String(selectedLayerId) === lid;
        const isLive = String(liveDeviceState.layer) === lid;
        btn.className = `layer-tab ${isEdit ? 'active-edit' : ''} ${isLive ? 'live-on-pad' : ''}`;
        btn.innerHTML = `
          <span style="opacity:0.65; font-family:var(--font-mono);">${slotLetters[slot-1]}·L${lid}</span>
          <span>${escapeHtml(lObj.name || 'Custom')}</span>
          ${getAppBadgeForLayer(lid)}
        `;
        btn.onclick = () => selectLayer(lid);
        grp.appendChild(btn);
      }
      rib.appendChild(grp);
    }
  }

  async function selectLayer(lid) {
    selectedLayerId = String(lid);
    renderLayerRibbon();
    renderHardwareCanvas();
    renderInspector();
    renderCheatsheet();
    if (document.getElementById('chk-live-preview-sync')?.checked) {
      await pushSelectedLayerToPad(true);
    }
  }

  async function pushSelectedLayerToPad(fast = false) {
    try {
      await fetch(`/api/layers/${selectedLayerId}/apply?fast=${fast ? 'true' : 'false'}`, { method: 'POST' });
      liveDeviceState.layer = Number(selectedLayerId);
      renderLayerRibbon();
    } catch (e) {}
  }

  // ================= 2. WYSIWYG HARDWARE SURFACE =================
  function renderHardwareCanvas() {
    const lid = Number(selectedLayerId);
    const lObj = layersStore[selectedLayerId] || { name: `Layer ${lid}`, cells: [] };
    const bank = Math.floor((lid - 1) / 4) + 1;
    const slot = ((lid - 1) % 4) + 1;
    const slotLetters = ['A', 'B', 'C', 'D'];

    document.getElementById('active-layer-heading').textContent =
      `Bank ${bank} • Key ${slotLetters[slot - 1]} (Layer ${lid}: ${lObj.name || 'Custom'})`;

    const liveInd = document.getElementById('live-pad-indicator');
    if (Number(liveDeviceState.layer) === lid) {
      liveInd.style.display = 'inline-flex';
    } else {
      liveInd.style.display = 'none';
    }

    // Update 3 Rotary Encoder captions based on Layer context
    updateEncoderCaptions(lid);

    // Highlight selected encoder if applicable
    for (let e = 1; e <= 3; e++) {
      const el = document.getElementById(`ctrl-enc-${e}`);
      if (el) {
        el.classList.toggle('selected-control', selectedControl.type === 'encoder' && selectedControl.index === e);
      }
    }

    // Build 4x4 Key Matrix
    const mat = document.getElementById('wysiwyg-matrix-4x4');
    mat.innerHTML = '';

    // Row 1: Top Keys A, B, C, D (Slots 1..4)
    const topMods = appRulesConfig.top_modifiers || { "1": "SHIFT", "2": "CTRL", "3": "ALT", "4": "ORBIT_CLUTCH" };
    for (let s = 1; s <= 4; s++) {
      const targetLid = (bank - 1) * 4 + s;
      const targetLayerObj = layersStore[String(targetLid)] || { name: `L${targetLid}` };
      const modName = (topMods[String(s)] || 'NONE').replace('_CLUTCH', '');
      const isSelected = (selectedControl.type === 'top' && selectedControl.index === s);
      const isActiveSlot = (slot === s);

      const keyEl = document.createElement('div');
      keyEl.className = `keycap key-top-slot ${isSelected ? 'selected-control' : ''} ${isActiveSlot ? 'active-slot-led' : ''}`;
      keyEl.title = `Click to configure Top Key ${slotLetters[s-1]} • Double-click to switch to Layer ${targetLid}`;
      keyEl.innerHTML = `
        <div class="top-letter">${slotLetters[s - 1]}</div>
        <div class="key-tap-line">Tap: L${targetLid}</div>
        <div class="key-hold-badge">Hold: ${escapeHtml(modName)}</div>
      `;
      keyEl.onclick = () => selectControl('top', s);
      keyEl.ondblclick = () => selectLayer(String(targetLid));
      mat.appendChild(keyEl);
    }

    // Rows 2..4: Col 1 is Fixed Keys (5=Sun, 9=Speaker, 13=Mute), Cols 2..4 are 3x3 Dynamic Cells (1..9)
    const fixedMeta = {
      5:  { glyph: '☀️', tap: 'Tap: Light', hold: 'Hold: Mod' },
      9:  { glyph: '🔊', tap: liveDeviceState.auto_app_mode ? 'Auto: ON [A]' : 'Auto: OFF', hold: 'Hold: HUD' },
      13: { glyph: '🔇', tap: 'Tap: Mic Mute', hold: 'Hold: Audio' }
    };
    const fixedIdsByRow = [5, 9, 13];

    for (let r = 0; r < 3; r++) {
      // Column 1: Fixed Key
      const fid = fixedIdsByRow[r];
      const fm = fixedMeta[fid];
      const fSelected = (selectedControl.type === 'fixed' && selectedControl.index === fid);
      const fEl = document.createElement('div');
      fEl.className = `keycap key-fixed ${fSelected ? 'selected-control' : ''}`;
      fEl.innerHTML = `
        <div class="fixed-symbol">${fm.glyph}</div>
        <div class="key-tap-line" style="color:#d8dee9;">${fm.tap}</div>
        <div class="key-hold-badge" style="background:rgba(255,255,255,0.06); color:var(--text-muted); border-color:transparent;">${fm.hold}</div>
      `;
      fEl.onclick = () => selectControl('fixed', fid);
      mat.appendChild(fEl);

      // Columns 2..4: Dynamic 3x3 Cells
      for (let c = 0; c < 3; c++) {
        const cellIdx = r * 3 + c + 1; // 1..9
        const cellData = (lObj.cells || [])[cellIdx - 1] || { index: cellIdx, label: `KEY ${cellIdx}`, icon: '', action: '' };
        const isCellSel = (selectedControl.type === 'cell' && selectedControl.index === cellIdx);
        const hasRadial = !!(cellData.hold_enabled && cellData.radial_slices && cellData.radial_slices.length > 0);

        const cEl = document.createElement('div');
        cEl.className = `keycap ${isCellSel ? 'selected-control' : ''}`;

        let holdBadgeHtml = '';
        if (lid === 2 && liveDeviceState.in_call) {
          holdBadgeHtml = `<div class="key-hold-badge">Hold: Mute</div>`;
        } else if (hasRadial) {
          holdBadgeHtml = `<div class="key-hold-badge radial-badge">🥧 ${cellData.radial_slices.length} Slices</div>`;
        } else {
          const shortAct = formatActionFriendly(cellData.action).split('(')[0].trim();
          holdBadgeHtml = `<div style="font-size:8px; color:var(--text-muted); max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(shortAct)}</div>`;
        }

        cEl.innerHTML = `
          <span class="dyn-cell-num">#${cellIdx}</span>
          ${cellIdx === 9 ? '<span class="power-corner-glyph">⏻</span>' : ''}
          <canvas id="keycap-canvas-${cellIdx}" class="keycap-icon-canvas"></canvas>
          <div class="dyn-key-label">${escapeHtml(cellData.label || `KEY ${cellIdx}`)}</div>
          ${holdBadgeHtml}
          ${cellIdx === 5 ? '<div class="homing-bar"></div>' : ''}
        `;
        cEl.onclick = () => selectControl('cell', cellIdx);
        mat.appendChild(cEl);

        // Draw 24x24 icon on keycap canvas
        const icObj = iconsLibrary[cellData.icon];
        const cv = cEl.querySelector('canvas');
        if (icObj && icObj.hex) {
          drawIconHexOnCanvas(cv, icObj.hex, isCellSel ? '#00e5ff' : '#eceff4');
        } else if (cv) {
          cv.style.display = 'none';
        }
      }
    }

    renderEinkPreview();
  }

  function updateEncoderCaptions(lid) {
    const e1 = document.getElementById('enc1-caption');
    const e2 = document.getElementById('enc2-caption');
    const e3 = document.getElementById('enc3-caption');
    if (lid === 2) {
      e1.innerHTML = `<strong>Right Knob (Master)</strong><span>Turn: Master • Tap: 80%</span>`;
      e2.innerHTML = `<strong>Btm-Left (User Vol)</strong><span>Turn: >User • Tap: 80%</span>`;
      e3.innerHTML = `<strong>Top-Left (Discord)</strong><span>Turn: Discord • Tap: 80%</span>`;
    } else if (lid >= 5) {
      e1.innerHTML = `<strong>Right Knob (Zoom)</strong><span>Turn: Zoom Wheel</span>`;
      e2.innerHTML = `<strong>Btm-Left (History)</strong><span>Turn: Undo/Redo • Tap: Space</span>`;
      e3.innerHTML = `<strong>Top-Left (Bank/Zoom)</strong><span>Turn: Zoom • Tap: Bank</span>`;
    } else {
      e1.innerHTML = `<strong>Right Knob (Master)</strong><span>Turn: Master • Tap: LEDs</span>`;
      e2.innerHTML = `<strong>Btm-Left Knob</strong><span>Hold 🔇: Discord Vol</span>`;
      e3.innerHTML = `<strong>Top-Left Knob</strong><span>Tap: Cycle Bank 1–4</span>`;
    }
  }

  function renderEinkPreview() {
    const lid = Number(selectedLayerId);
    const lObj = layersStore[selectedLayerId] || { name: `Layer ${lid}`, cells: [] };
    const bank = Math.floor((lid - 1) / 4) + 1;
    const slot = ((lid - 1) % 4) + 1;
    const autoTag = liveDeviceState.auto_app_mode ? ' [A]' : '';

    document.getElementById('eink-hdr-left').textContent = `B${bank}L${slot}${autoTag}`;
    document.getElementById('eink-hdr-right').textContent = `${liveDeviceState.batt_pct ?? 80}%`;

    const gridEl = document.getElementById('eink-screen-grid');
    gridEl.innerHTML = '';

    // If viewing Layer 2 and currently in a live Discord voice call, show the live call member labels!
    const showLiveDiscordCall = (lid === 2 && liveDeviceState.in_call && Array.isArray(liveDeviceState.grid_labels) && liveDeviceState.grid_labels.length > 0);

    for (let i = 0; i < 9; i++) {
      const cellEl = document.createElement('div');
      cellEl.className = 'eink-cell';
      cellEl.onclick = () => selectControl('cell', i + 1);

      if (showLiveDiscordCall) {
        const rawLbl = liveDeviceState.grid_labels[i] || '';
        const cleanLbl = rawLbl.replace(/^[*]/, '🔊');
        cellEl.innerHTML = `<div class="eink-cell-lbl" style="white-space:pre-line; font-size:8.5px;">${escapeHtml(cleanLbl)}</div>`;
      } else {
        const cData = (lObj.cells || [])[i] || { label: '' };
        const icObj = iconsLibrary[cData.icon];
        if (icObj && icObj.hex) {
          const cv = document.createElement('canvas');
          cv.style.cssText = 'width:20px; height:20px; image-rendering:pixelated; margin-bottom:2px;';
          drawIconHexOnCanvas(cv, icObj.hex, '#111513');
          cellEl.appendChild(cv);
        }
        const lblDiv = document.createElement('div');
        lblDiv.className = 'eink-cell-lbl';
        lblDiv.textContent = cData.label || '';
        cellEl.appendChild(lblDiv);
      }
      gridEl.appendChild(cellEl);
    }
  }

  function selectControl(type, index) {
    selectedControl = { type, index };
    selectedRadialSliceIdx = 0;
    switchInspectorTab('key');
    renderHardwareCanvas();
    renderInspector();
  }

  function switchInspectorTab(tab) {
    document.getElementById('tab-btn-key').classList.toggle('active', tab === 'key');
    document.getElementById('tab-btn-apps').classList.toggle('active', tab === 'apps');
    document.getElementById('inspector-tab-key').style.display = tab === 'key' ? 'flex' : 'none';
    document.getElementById('inspector-tab-apps').style.display = tab === 'apps' ? 'flex' : 'none';
    if (tab === 'apps') renderAppRulesTab();
  }

  // ================= 3. CONTEXT-AWARE RIGHT INSPECTOR =================
  function buildGuidedActionOptionsHtml(currentVal) {
    let html = `<option value="">-- Select a Guided Action or Type Custom Below --</option>`;
    for (const grp of ACTION_CATALOG) {
      html += `<optgroup label="${escapeHtml(grp.group)}">`;
      for (const it of grp.items) {
        const sel = (it.val === currentVal) ? 'selected' : '';
        html += `<option value="${escapeHtml(it.val)}" ${sel}>${escapeHtml(it.label)}</option>`;
      }
      html += `</optgroup>`;
    }
    return html;
  }

  function renderInspector() {
    const box = document.getElementById('inspector-tab-key');
    const lObj = layersStore[selectedLayerId] || { name: `Layer ${selectedLayerId}`, cells: [] };

    // A. Top-Row Keys A, B, C, D Inspector
    if (selectedControl.type === 'top') {
      const s = selectedControl.index;
      const letters = ['A', 'B', 'C', 'D'];
      const topMods = appRulesConfig.top_modifiers || { "1": "SHIFT", "2": "CTRL", "3": "ALT", "4": "ORBIT_CLUTCH" };
      const curMod = topMods[String(s)] || 'NONE';
      const bank = Math.floor((Number(selectedLayerId) - 1) / 4) + 1;
      const targetLid = (bank - 1) * 4 + s;

      box.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h3 style="font-size:15px;">Top-Row Key ${letters[s-1]} (Slot ${s})</h3>
          <span class="pill" style="font-size:10px;">Dual-Role Key</span>
        </div>
        <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:10px; font-size:12px; line-height:1.5;">
          <div>⚡ <strong>Quick Tap (&lt;190ms):</strong> Switches MacroPad to <strong>Bank ${bank} • Slot ${letters[s-1]} (Layer ${targetLid})</strong>.</div>
          <div style="margin-top:4px;">🖱️ <strong>Press &amp; Hold (≥190ms):</strong> Holds down a live keyboard/mouse modifier on your PC while you use your mouse!</div>
        </div>
        <div class="field-group">
          <label class="field-label">Hold (≥190ms) Mouse Combo Modifier</label>
          <select class="select-box" onchange="updateTopModifier(${s}, this.value)">
            <option value="SHIFT" ${curMod==='SHIFT'?'selected':''}>SHIFT (Hold Shift while clicking/dragging mouse)</option>
            <option value="CTRL" ${curMod==='CTRL'?'selected':''}>CTRL (Hold Ctrl for multi-select / zoom)</option>
            <option value="ALT" ${curMod==='ALT'?'selected':''}>ALT (Hold Alt modifier)</option>
            <option value="ORBIT_CLUTCH" ${curMod==='ORBIT_CLUTCH'?'selected':''}>ORBIT CLUTCH (Holds Shift + Middle Mouse Button — just move mouse to 3D Orbit!)</option>
            <option value="PAN_CLUTCH" ${curMod==='PAN_CLUTCH'?'selected':''}>PAN CLUTCH (Holds Middle Mouse Button — just move mouse to Pan!)</option>
            <option value="ZOOM_CLUTCH" ${curMod==='ZOOM_CLUTCH'?'selected':''}>ZOOM CLUTCH (Holds Ctrl + Shift + Middle Mouse Button)</option>
            <option value="NONE" ${curMod==='NONE'?'selected':''}>NONE (Disable hold modifier)</option>
          </select>
        </div>
        <button class="btn btn-primary" onclick="selectLayer('${targetLid}')">
          📂 Switch Editor to Layer ${targetLid} (Slot ${letters[s-1]})
        </button>
      `;
      return;
    }

    // B. Rotary Encoder Inspector
    if (selectedControl.type === 'encoder') {
      const e = selectedControl.index;
      const names = { 1: 'Right Gunmetal Knob (Encoder 1)', 2: 'Bottom-Left Black Knob (Encoder 2)', 3: 'Top-Left Green Knob (Encoder 3)' };
      box.innerHTML = `
        <h3 style="font-size:15px;">🎛️ ${names[e]}</h3>
        <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:10px; line-height:1.5;">
          <div><strong>🎙️ On Layer 2 (Discord Voice Call Mixer):</strong></div>
          <ul style="padding-left:18px; color:var(--text-muted);">
            <li><strong>Bottom-Left Black Knob:</strong> Turn to adjust <code>&gt;Target User</code> volume (0–200%) • Click to reset user to <strong>80%</strong></li>
            <li><strong>Top-Left Green Knob:</strong> Turn to adjust <strong>Discord Master Volume</strong> • Click to reset to <strong>80%</strong></li>
            <li><strong>Right Gunmetal Knob:</strong> Turn to adjust <strong>System Master Volume</strong> • Click to reset to <strong>80%</strong></li>
          </ul>
          <hr style="border:none; border-top:1px solid var(--border);">
          <div><strong>📐 On CAD &amp; Fusion 360 Layers (Layers 5–16):</strong></div>
          <ul style="padding-left:18px; color:var(--text-muted);">
            <li><strong>Right &amp; Top-Left Knobs:</strong> Smooth Mouse Wheel Zoom In / Out</li>
            <li><strong>Bottom-Left Knob:</strong> Turn CCW for <strong>Undo (Ctrl+Z)</strong> / CW for <strong>Redo (Ctrl+Y)</strong> • Click for <strong>Space (Repeat Command)</strong></li>
          </ul>
        </div>
      `;
      return;
    }

    // C. Left Fixed Column Keys (5, 9, 13)
    if (selectedControl.type === 'fixed') {
      const fid = selectedControl.index;
      const info = {
        5: { title: '☀️ Key 5 — Room Light & Layer Modifier', desc: 'Short Tap toggles your smart room lighting. Holding Key 5 activates the Layer Preset Modifier.' },
        9: { title: '🔊 Key 9 — Dynamic Auto-App Mode & HUD', desc: 'Short Tap toggles Auto-App Mode [A] ON/OFF (automatically switches layers when you focus Fusion 360, Discord, AutoCAD, or Photoshop). Holding Key 9 (≥420ms) opens the on-device Battery & Wi-Fi Status HUD.' },
        13: { title: '🔇 Key 13 — Discord Mic Mute & Audio Modifier', desc: 'Short Tap mutes/unmutes your Discord microphone from any app with live LED feedback. Holding Key 13 activates the instant Audio Output Switcher (Key 7 = Headphones, Key 8 = Speakers).' }
      }[fid];
      box.innerHTML = `
        <h3 style="font-size:15px;">${info.title}</h3>
        <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:12px; line-height:1.5; color:var(--text-muted);">
          ${info.desc}
        </div>
        ${fid === 9 ? `<button class="btn btn-green" onclick="toggleAutoAppMode()">🤖 Toggle Auto-App Mode Now</button>` : ''}
      `;
      return;
    }

    // D. 3x3 Dynamic Matrix Key (Cells 1..9) Inspector
    const cIdx = selectedControl.index;
    if (!lObj.cells) lObj.cells = [];
    while (lObj.cells.length < 9) {
      lObj.cells.push({ index: lObj.cells.length + 1, label: '', icon: '', action: '' });
    }
    const cell = lObj.cells[cIdx - 1];

    box.innerHTML = `
      <!-- Layer Name & Current Key Header -->
      <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding-bottom:8px; border-bottom:1px solid var(--border);">
        <div style="flex:1;">
          <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Layer ${selectedLayerId} Name</div>
          <input type="text" class="input-box" style="margin-top:3px; font-weight:700;" value="${escapeHtml(lObj.name || '')}" oninput="onLayerNameInput(this.value)">
        </div>
        <div style="text-align:right;">
          <span class="pill" style="background:rgba(0,229,255,0.15); color:var(--accent-cyan); border-color:var(--accent-cyan);">
            Editing Key #${cIdx}
          </span>
        </div>
      </div>

      ${Number(selectedLayerId) === 2 ? `
        <div style="background:rgba(179,136,255,0.12); border:1px solid rgba(179,136,255,0.4); border-radius:8px; padding:9px 10px; font-size:11.5px; line-height:1.45;">
          🎙️ <strong>Dynamic Discord Call Mode:</strong> When you are in a voice call, Keys 1–8 automatically display live call members:
          <div style="margin-top:4px; color:var(--accent-cyan);">• <strong>Quick Tap User:</strong> Select Target User (<code>&gt;</code>) • <strong>Hold User:</strong> Mute/Unmute</div>
          <div style="color:var(--accent-green);">• <strong>Btm-Left Knob:</strong> User Vol (Tap=80%) • <strong>Top-Left:</strong> Discord Vol • <strong>Right:</strong> Master Vol</div>
        </div>
      ` : ''}

      <!-- Key Label -->
      <div class="field-group">
        <label class="field-label">
          <span>Key #${cIdx} Screen Label</span>
          <span style="font-size:10px; color:var(--text-muted);">Max ~8 chars</span>
        </label>
        <input type="text" class="input-box" value="${escapeHtml(cell.label || '')}" placeholder="e.g. SKETCH" oninput="onCellLabelInput(this.value)">
      </div>

      <!-- Guided Tap Action Selector -->
      <div class="field-group">
        <label class="field-label">⚡ Quick Tap Action (Guided Picker)</label>
        <select class="select-box" onchange="onGuidedActionPick(this.value)">
          ${buildGuidedActionOptionsHtml(cell.action || '')}
        </select>
        <input type="text" id="raw-action-input" class="input-box" style="margin-top:4px; font-family:var(--font-mono); font-size:11px; color:var(--accent-cyan);" value="${escapeHtml(cell.action || '')}" placeholder="e.g. fusion:extrude or hotkey:CTRL+Z" oninput="onRawActionInput(this.value)">
      </div>

      <!-- Visual 24x24 Pixel-Art Icon Gallery -->
      <div class="field-group">
        <label class="field-label">
          <span>🖼️ Key Icon (Click to assign)</span>
          <span style="font-size:10px; color:var(--accent-cyan); cursor:pointer;" onclick="selectCellIcon('')">Clear Icon (Text Only)</span>
        </label>
        <div class="icon-picker-grid" id="inspector-icon-grid"></div>
      </div>

      <!-- Press & Hold Radial Pie Menu Builder -->
      <div class="radial-box">
        <label style="display:flex; align-items:center; justify-content:space-between; cursor:pointer;">
          <span style="font-weight:700; font-size:12px; color:var(--accent-cyan);">🥧 Hold (≥220ms) Radial Pie Menu</span>
          <input type="checkbox" ${cell.hold_enabled ? 'checked' : ''} onchange="toggleCellRadialHold(this.checked)" style="width:16px; height:16px; accent-color:var(--accent-cyan);">
        </label>
        <div id="radial-editor-area" style="display:${cell.hold_enabled ? 'flex' : 'none'}; flex-direction:column; gap:10px;">
          <div class="radial-wheel-wrap">
            <canvas id="radial-wheel-canvas" width="180" height="180" style="cursor:pointer;"></canvas>
          </div>
          <div id="radial-slices-list" style="display:flex; flex-direction:column; gap:6px;"></div>
          <button class="btn" onclick="addRadialSlice()">+ Add Radial Slice (Max 8)</button>
        </div>
      </div>

      <!-- Save & Push Footer -->
      <div style="display:flex; gap:8px; margin-top:4px;">
        <button class="btn btn-primary" style="flex:1;" onclick="saveCurrentLayer()">💾 Save &amp; Sync Layer ${selectedLayerId}</button>
      </div>
    `;

    renderIconGallery(cell.icon || '');
    if (cell.hold_enabled) {
      renderRadialEditor(cell);
    }
  }

  function renderIconGallery(selectedIconName) {
    const grid = document.getElementById('inspector-icon-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const names = Object.keys(iconsLibrary).sort();
    names.forEach(name => {
      const ic = iconsLibrary[name];
      const tile = document.createElement('div');
      tile.className = `icon-tile ${selectedIconName === name ? 'selected' : ''}`;
      tile.title = name;
      const cv = document.createElement('canvas');
      cv.style.cssText = 'width:22px; height:22px; image-rendering:pixelated;';
      drawIconHexOnCanvas(cv, ic.hex, selectedIconName === name ? '#00e5ff' : '#e5e9f0');
      const sp = document.createElement('span');
      sp.textContent = name.replace('cad_', '');
      tile.appendChild(cv);
      tile.appendChild(sp);
      tile.onclick = () => selectCellIcon(name);
      grid.appendChild(tile);
    });
  }

  function onLayerNameInput(val) {
    if (!layersStore[selectedLayerId]) return;
    layersStore[selectedLayerId].name = val;
    renderLayerRibbon();
    renderCheatsheet();
  }

  function onCellLabelInput(val) {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell) return;
    cell.label = val;
    renderHardwareCanvas();
    renderCheatsheet();
  }

  function onGuidedActionPick(val) {
    if (!val) return;
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell) return;
    cell.action = val;
    for (const grp of ACTION_CATALOG) {
      for (const it of grp.items) {
        if (it.val === val) {
          if (it.shortLabel) cell.label = it.shortLabel;
          if (it.icon) cell.icon = it.icon;
          break;
        }
      }
    }
    const rawInp = document.getElementById('raw-action-input');
    if (rawInp) rawInp.value = val;
    renderAll();
  }

  function onRawActionInput(val) {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell) return;
    cell.action = val.trim();
    renderHardwareCanvas();
  }

  function selectCellIcon(iconName) {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell) return;
    cell.icon = iconName;
    renderHardwareCanvas();
    renderIconGallery(iconName);
  }

  function toggleCellRadialHold(enabled) {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell) return;
    cell.hold_enabled = enabled;
    if (enabled && (!cell.radial_slices || cell.radial_slices.length === 0)) {
      cell.radial_title = cell.label || `KEY ${selectedControl.index}`;
      cell.radial_slices = [
        { label: "Option 1", sub: "", action: cell.action || "fusion:line" },
        { label: "Option 2", sub: "", action: "fusion:extrude" },
        { label: "Option 3", sub: "", action: "fusion:fillet" },
        { label: "Cancel", sub: "ESC", action: "cad_key:ESC" }
      ];
    }
    renderHardwareCanvas();
    renderInspector();
    renderCheatsheet();
  }

  function renderRadialEditor(cell) {
    const slices = cell.radial_slices || [];
    const canvas = document.getElementById('radial-wheel-canvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      const cx = 90, cy = 90, rOuter = 82, rInner = 28;
      ctx.clearRect(0, 0, 180, 180);
      const n = Math.max(1, slices.length);
      const step = (Math.PI * 2) / n;

      slices.forEach((s, i) => {
        const startAngle = -Math.PI / 2 - step / 2 + i * step;
        const endAngle = startAngle + step;
        ctx.beginPath();
        ctx.arc(cx, cy, rOuter, startAngle, endAngle);
        ctx.arc(cx, cy, rInner, endAngle, startAngle, true);
        ctx.closePath();
        ctx.fillStyle = (i === selectedRadialSliceIdx) ? 'rgba(0, 229, 255, 0.28)' : '#172033';
        ctx.fill();
        ctx.strokeStyle = (i === selectedRadialSliceIdx) ? '#00e5ff' : '#2c3a57';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        const mid = startAngle + step / 2;
        const tx = cx + Math.cos(mid) * 56;
        const ty = cy + Math.sin(mid) * 56;
        ctx.fillStyle = '#f0f4f8';
        ctx.font = 'bold 9px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const shortText = (s.label || `S${i+1}`).split('\n')[0].substring(0, 9);
        ctx.fillText(shortText, tx, ty);
      });

      ctx.beginPath();
      ctx.arc(cx, cy, rInner - 2, 0, Math.PI * 2);
      ctx.fillStyle = '#0b0f18';
      ctx.fill();
      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 9px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(cell.label || 'HOLD', cx, cy);
    }

    const listEl = document.getElementById('radial-slices-list');
    if (!listEl) return;
    listEl.innerHTML = '';
    slices.forEach((s, idx) => {
      const row = document.createElement('div');
      row.className = `slice-row ${idx === selectedRadialSliceIdx ? 'active-slice' : ''}`;
      row.innerHTML = `
        <span style="font-size:10px; font-family:var(--font-mono); color:var(--accent-cyan); text-align:center;">#${idx+1}</span>
        <input type="text" class="input-box" style="padding:4px 6px; font-size:11px;" value="${escapeHtml((s.label || '').replace(/\n/g, ' '))}" placeholder="Slice Label" oninput="updateRadialSlice(${idx}, 'label', this.value)">
        <select class="select-box" style="padding:4px 6px; font-size:11px;" onchange="updateRadialSlice(${idx}, 'action', this.value)">
          ${buildGuidedActionOptionsHtml(s.action || '')}
        </select>
        <button class="btn" style="padding:3px 6px; color:var(--accent-red);" onclick="removeRadialSlice(${idx})" title="Remove slice">✕</button>
      `;
      row.onclick = () => { selectedRadialSliceIdx = idx; renderRadialEditor(cell); };
      listEl.appendChild(row);
    });
  }

  function updateRadialSlice(idx, field, val) {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell || !cell.radial_slices || !cell.radial_slices[idx]) return;
    cell.radial_slices[idx][field] = val;
    renderRadialEditor(cell);
  }

  function addRadialSlice() {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell) return;
    if (!cell.radial_slices) cell.radial_slices = [];
    if (cell.radial_slices.length >= 8) {
      alert('Radial Pie Menus support up to 8 slices.');
      return;
    }
    cell.radial_slices.push({ label: `Slice ${cell.radial_slices.length + 1}`, sub: '', action: 'fusion:line' });
    renderRadialEditor(cell);
    renderHardwareCanvas();
  }

  function removeRadialSlice(idx) {
    const cell = layersStore[selectedLayerId]?.cells?.[selectedControl.index - 1];
    if (!cell || !cell.radial_slices) return;
    cell.radial_slices.splice(idx, 1);
    renderRadialEditor(cell);
    renderHardwareCanvas();
  }

  async function saveCurrentLayer() {
    const lObj = layersStore[selectedLayerId];
    if (!lObj) return;
    try {
      const res = await fetch(`/api/layers/${selectedLayerId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lObj)
      });
      if (res.ok) {
        await pushSelectedLayerToPad(true);
      }
    } catch (e) {
      alert('Error saving layer: ' + e);
    }
  }

  async function updateTopModifier(slot, modVal) {
    if (!appRulesConfig.top_modifiers) appRulesConfig.top_modifiers = {};
    appRulesConfig.top_modifiers[String(slot)] = modVal;
    renderHardwareCanvas();
    await fetch('/api/app_rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(appRulesConfig)
    });
  }

  // ================= 4. APP AUTO-SWITCH STUDIO TAB =================
  function renderAppRulesTab() {
    const box = document.getElementById('inspector-tab-apps');
    if (!box) return;
    const rules = appRulesConfig.rules || [];
    const layerIds = Object.keys(layersStore).sort((a, b) => Number(a) - Number(b));

    let rulesHtml = rules.map((r, idx) => {
      const tLayer = Number(r.target_layer || r.layer || 1);
      const mPat = r.exe_match || r.match || '';
      const opts = layerIds.map(lid => {
        const ln = layersStore[lid]?.name || `Layer ${lid}`;
        return `<option value="${lid}" ${Number(lid)===tLayer?'selected':''}>Layer ${lid}: ${escapeHtml(ln)}</option>`;
      }).join('');

      return `
        <div class="app-rule-card">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:8px;">
            <label style="display:flex; align-items:center; gap:6px; font-weight:700; cursor:pointer;">
              <input type="checkbox" ${r.enabled !== false ? 'checked' : ''} onchange="updateAppRuleField(${idx}, 'enabled', this.checked)" style="accent-color:var(--accent-green);">
              <input type="text" class="input-box" style="padding:4px 7px; font-weight:700; width:165px;" value="${escapeHtml(r.name || '')}" onchange="updateAppRuleField(${idx}, 'name', this.value)">
            </label>
            <button class="btn" style="padding:3px 7px; color:var(--accent-red);" onclick="deleteAppRule(${idx})">✕</button>
          </div>
          <div style="display:grid; grid-template-columns: 1fr 155px; gap:6px; align-items:center;">
            <input type="text" class="input-box" style="padding:5px 7px; font-family:var(--font-mono); font-size:11px;" value="${escapeHtml(mPat)}" placeholder="exe or window title" onchange="updateAppRuleField(${idx}, 'exe_match', this.value)">
            <select class="select-box" style="padding:5px 6px; font-size:11px;" onchange="updateAppRuleField(${idx}, 'target_layer', Number(this.value))">
              ${opts}
            </select>
          </div>
        </div>
      `;
    }).join('');

    const curExe = liveDeviceState.focused_exe || liveDeviceState.focused_app_exe || 'App';
    const curTitle = liveDeviceState.focused_title || liveDeviceState.focused_app_title || '';
    const curRule = liveDeviceState.matched_rule || liveDeviceState.active_app_rule || '';

    box.innerHTML = `
      <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:10px; font-size:12px; line-height:1.45;">
        🤖 When <strong>Auto-App Mode [A]</strong> is active, your MacroPad switches layers when you focus a tracked app—or displays the <strong>App Name + 8 Universal Shortcuts</strong> for untracked apps until you populate them.
      </div>
      <div style="background:var(--bg-input); border:1px solid var(--border-bright); border-radius:8px; padding:9px 11px;">
        <div style="font-size:10px; font-weight:800; color:var(--text-muted); text-transform:uppercase; margin-bottom:3px;">Live Focused Windows App:</div>
        <div id="studio-live-app-banner" style="font-family:var(--font-mono); font-size:12px; color:var(--accent-blue); font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
          ${escapeHtml(curExe !== 'App' ? `${curExe}${curTitle ? ' • "' + curTitle + '"' : ''}${curRule ? ' → ' + curRule : ''}` : 'Waiting for PC Bridge...')}
        </div>
      </div>
      <div style="display:flex; gap:8px;">
        <button id="btn-track-focused-app" class="btn btn-green" style="flex:1;" onclick="addFocusedAppRule()">+ Track Focused App (${escapeHtml(curExe)})</button>
        <button class="btn" onclick="addBlankRule()">+ Custom App</button>
      </div>
      <div style="display:flex; flex-direction:column; gap:8px;">
        ${rulesHtml}
      </div>
      <button class="btn btn-primary" onclick="saveAppRules()">💾 Save &amp; Sync App Rules</button>
    `;
  }

  function updateAppRuleField(idx, field, val) {
    if (!appRulesConfig.rules || !appRulesConfig.rules[idx]) return;
    appRulesConfig.rules[idx][field] = val;
    if (field === 'exe_match') appRulesConfig.rules[idx].match = val;
    if (field === 'target_layer') appRulesConfig.rules[idx].layer = val;
  }

  function addFocusedAppRule() {
    const exe = (liveDeviceState.focused_exe || liveDeviceState.focused_app_exe || 'app.exe').toLowerCase();
    const clean = exe.replace('.exe', '').toUpperCase();
    if (!appRulesConfig.rules) appRulesConfig.rules = [];
    appRulesConfig.rules.push({
      id: `app_${Date.now()}`,
      name: clean,
      exe_match: exe,
      match: exe,
      target_layer: Number(selectedLayerId) || 1,
      layer: Number(selectedLayerId) || 1,
      enabled: true
    });
    renderAppRulesTab();
  }

  function addBlankRule() {
    if (!appRulesConfig.rules) appRulesConfig.rules = [];
    appRulesConfig.rules.push({
      id: `app_${Date.now()}`,
      name: 'New App',
      exe_match: 'app.exe',
      match: 'app.exe',
      target_layer: Number(selectedLayerId) || 1,
      layer: Number(selectedLayerId) || 1,
      enabled: true
    });
    renderAppRulesTab();
  }

  function deleteAppRule(idx) {
    appRulesConfig.rules.splice(idx, 1);
    renderAppRulesTab();
  }

  async function saveAppRules() {
    await fetch('/api/app_rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(appRulesConfig)
    });
    renderLayerRibbon();
    renderCheatsheet();
  }

  async function toggleAutoAppMode() {
    const res = await fetch('/api/auto_app_mode/toggle', { method: 'POST' });
    const data = await res.json();
    liveDeviceState.auto_app_mode = data.auto_app_mode;
    appRulesConfig.auto_app_mode = data.auto_app_mode;
    updateTopStatusBar();
    renderHardwareCanvas();
  }

  // ================= 5. FULL 16-LAYER CHEAT-SHEET MATRIX =================
  function renderCheatsheet() {
    const grid = document.getElementById('all-layers-cheatsheet');
    if (!grid) return;
    grid.innerHTML = '';
    const slotLetters = ['A', 'B', 'C', 'D'];

    for (let lid = 1; lid <= 16; lid++) {
      const lStr = String(lid);
      const lObj = layersStore[lStr] || { name: `Layer ${lid}`, cells: [] };
      const bank = Math.floor((lid - 1) / 4) + 1;
      const slot = ((lid - 1) % 4) + 1;

      const card = document.createElement('div');
      card.className = `mini-layer-card ${String(selectedLayerId) === lStr ? 'active-edit' : ''}`;

      const cellsHtml = Array.from({ length: 9 }, (_, i) => {
        const c = (lObj.cells || [])[i] || { label: '-' };
        const hasRad = !!(c.hold_enabled && c.radial_slices && c.radial_slices.length > 0);
        return `<div class="mini-cell ${hasRad ? 'has-radial' : ''}" title="Key #${i+1}: ${escapeHtml(c.label || '')} (${escapeHtml(c.action || '')})">${escapeHtml(c.label || '-')}</div>`;
      }).join('');

      card.innerHTML = `
        <div class="mini-layer-hdr">
          <span><span style="color:var(--accent-cyan); font-family:var(--font-mono);">B${bank}·${slotLetters[slot-1]} (L${lid})</span> ${escapeHtml(lObj.name || '')}</span>
          ${getAppBadgeForLayer(lid)}
        </div>
        <div class="mini-3x3">${cellsHtml}</div>
      `;
      card.onclick = () => selectLayer(lStr);
      grid.appendChild(card);
    }
  }

  // ================= 6. MULTI-DRIVER HARVESTED APP LIBRARY & IMPORTER =================
  function getSourceIcon(src) {
    if (src === '3Dconnexion') return '🧊';
    if (src === 'Loupedeck') return '🎛️';
    if (src === 'TourBox') return '🎮';
    if (src === 'Wacom') return '✒️';
    if (src === 'PowerUser') return '⚡';
    return '📦';
  }

  function getSourceBadge(src) {
    let color = 'var(--text-muted)';
    let bg = 'rgba(255,255,255,0.06)';
    if (src === '3Dconnexion') { color = 'var(--accent-cyan)'; bg = 'rgba(0,229,255,0.12)'; }
    else if (src === 'Loupedeck') { color = 'var(--accent-pink)'; bg = 'rgba(255,64,129,0.12)'; }
    else if (src === 'TourBox') { color = 'var(--accent-amber)'; bg = 'rgba(255,171,0,0.12)'; }
    else if (src === 'Wacom') { color = '#b388ff'; bg = 'rgba(179,136,255,0.12)'; }
    else if (src === 'PowerUser') { color = 'var(--accent-green)'; bg = 'rgba(0,230,118,0.12)'; }
    return `<span style="font-size:9.5px; font-weight:700; padding:1px 5px; border-radius:3px; background:${bg}; color:${color};">${getSourceIcon(src)} ${escapeHtml(src)}</span>`;
  }

  function setTdxSourceFilter(src) {
    selectedTdxSourceFilter = src;
    document.querySelectorAll('.btn-src-filter').forEach(b => {
      if (b.getAttribute('data-src') === src) {
        b.classList.add('active');
        b.style.background = 'var(--accent-cyan)';
        b.style.color = '#000';
      } else {
        b.classList.remove('active');
        b.style.background = '';
        b.style.color = '';
      }
    });
    renderTdxAppList();
  }

  function selectDetailPresetSource(src) {
    selectedDetailPresetSource = src;
    renderTdxAppDetail();
  }

  async function setDefaultPresetForApp(appId, src) {
    try {
      const res = await fetch('/api/tdx/select_preset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: appId, source: src })
      });
      const data = await res.json();
      const app = tdxCatalogApps.find(a => a.id === appId);
      if (app) app.selected_preset_source = src;
      renderTdxAppDetail();
      renderTdxAppList();
      showToast(`Default preset for ${app ? app.name : appId} set to ${src}`);
    } catch (e) {
      console.error('Error selecting preset:', e);
    }
  }

  async function loadTdxCatalog() {
    try {
      const res = await fetch('/api/tdx/catalog');
      const data = await res.json();
      tdxCatalogApps = data.apps || [];
      tdxStats = data.stats || {};
      const subEl = document.getElementById('tdx-stats-subtitle');
      if (subEl && tdxStats.total_apps) {
        subEl.textContent = `${tdxStats.total_apps} Apps • ${tdxStats.total_preset_entries || 398} Driver Presets across 5 Hardware Sources • ${tdxStats.total_radial_menus || 427} Radial Pie Menus • ${tdxStats.total_icons || 3560} E-Ink Icons`;
      }
      for (const app of tdxCatalogApps) {
        if (!app.actions || app.actions.length === 0) continue;
        const grpName = `📦 ${app.name}`;
        if (!ACTION_CATALOG.some(g => g.group === grpName)) {
          ACTION_CATALOG.push({
            group: grpName,
            items: app.actions.map(a => ({
              label: `${a.name} (${a.action.replace(/^hotkey:|^cad_cmd:|^keyseq:/, '')})`,
              val: a.action,
              icon: a.icon,
              shortLabel: a.label
            }))
          });
        }
      }
    } catch (e) {
      console.warn('Could not load multi-driver catalog:', e);
    }
  }

  function openTdxLibraryModal() {
    const modal = document.getElementById('tdx-library-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    selectedDetailPresetSource = '';
    const focusedExe = (liveDeviceState.focused_app_exe || '').toLowerCase();
    if (focusedExe) {
      const matched = tdxCatalogApps.find(a => (a.exe_match || '').toLowerCase().includes(focusedExe));
      if (matched) selectedTdxAppId = matched.id;
    }
    renderTdxAppList();
    renderTdxAppDetail();
  }

  function closeTdxLibraryModal() {
    const modal = document.getElementById('tdx-library-modal');
    if (modal) modal.style.display = 'none';
  }

  function selectTdxApp(appId) {
    selectedTdxAppId = appId;
    selectedDetailPresetSource = '';
    renderTdxAppList();
    renderTdxAppDetail();
  }

  function renderTdxAppList() {
    const listEl = document.getElementById('tdx-app-list');
    if (!listEl) return;
    const q = (document.getElementById('tdx-search-input')?.value || '').trim().toLowerCase();
    const filtered = tdxCatalogApps.filter(a => {
      if (selectedTdxSourceFilter === 'multi') {
        if ((a.presets || []).length <= 1) return false;
      } else if (selectedTdxSourceFilter !== 'all') {
        const hasSource = (a.presets || []).some(p => p.source === selectedTdxSourceFilter) || a.source === selectedTdxSourceFilter;
        if (!hasSource) return false;
      }
      if (!q) return true;
      return (a.name || '').toLowerCase().includes(q) ||
             (a.exe_match || '').toLowerCase().includes(q) ||
             (a.id || '').toLowerCase().includes(q);
    });

    listEl.innerHTML = filtered.map(a => {
      const isSel = a.id === selectedTdxAppId;
      const presets = a.presets || [];
      const presetCount = presets.length;
      const activeSrc = a.selected_preset_source || (presets[0] ? presets[0].source : a.source) || '3Dconnexion';
      return `
        <div onclick="selectTdxApp('${escapeHtml(a.id)}')" style="padding:9px 11px; border-radius:8px; cursor:pointer; border:1px solid ${isSel ? 'var(--accent-cyan)' : 'var(--border)'}; background:${isSel ? 'rgba(0,229,255,0.12)' : 'var(--bg-card)'}; display:flex; flex-direction:column; gap:5px;">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:8px;">
            <div style="min-width:0;">
              <div style="font-size:12.5px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(a.name)}</div>
              <div style="font-size:10px; font-family:var(--font-mono); color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(a.exe_match || a.xml_file)}</div>
            </div>
            <div style="display:flex; gap:4px; flex-shrink:0;">
              ${presetCount > 1 ? `<span style="font-size:9.5px; font-weight:800; padding:2px 5px; border-radius:4px; background:rgba(255,171,0,0.18); color:var(--accent-amber);">🔀 ${presetCount}</span>` : ''}
              <span style="font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; background:${a.action_count > 0 ? 'rgba(0,230,118,0.15)' : 'rgba(255,255,255,0.06)'}; color:${a.action_count > 0 ? 'var(--accent-green)' : 'var(--text-muted)'};">${a.action_count} fn</span>
            </div>
          </div>
          <div style="display:flex; gap:3px; flex-wrap:wrap; align-items:center;">
            ${presets.map(p => {
              const isAct = p.source === activeSrc;
              return `<span style="font-size:8.5px; padding:1px 4px; border-radius:3px; background:${isAct ? 'rgba(0,229,255,0.2)' : 'rgba(255,255,255,0.06)'}; color:${isAct ? 'var(--accent-cyan)' : 'var(--text-muted)'}; font-weight:${isAct ? '700' : '400'};">${getSourceIcon(p.source)} ${escapeHtml(p.source)}</span>`;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  function renderTdxAppDetail() {
    const detailEl = document.getElementById('tdx-app-detail');
    if (!detailEl) return;
    const app = tdxCatalogApps.find(a => a.id === selectedTdxAppId) || tdxCatalogApps[0];
    if (!app) {
      detailEl.innerHTML = `<div style="color:var(--text-muted);">No driver profiles loaded.</div>`;
      return;
    }

    const presets = app.presets || [];
    let currentSource = selectedDetailPresetSource || app.selected_preset_source || (presets[0] ? presets[0].source : app.source) || '3Dconnexion';
    let matchedPreset = presets.find(p => p.source === currentSource) || presets[0] || null;
    if (matchedPreset) currentSource = matchedPreset.source;

    const recCells = (matchedPreset && matchedPreset.recommended_cells) ? matchedPreset.recommended_cells : (app.recommended_cells || []);
    const radials = (matchedPreset && matchedPreset.radial_menus) ? matchedPreset.radial_menus : (app.radial_menus || []);
    const actions = (matchedPreset && matchedPreset.actions) ? matchedPreset.actions : (app.actions || []);

    const layerOptions = Array.from({ length: 16 }, (_, i) => {
      const lid = i + 1;
      const bank = Math.floor(i / 4) + 1;
      const slot = ['A', 'B', 'C', 'D'][i % 4];
      const lName = (layersStore[String(lid)] || {}).name || `Layer ${lid}`;
      const sel = String(lid) === String(selectedLayerId) ? 'selected' : '';
      return `<option value="${lid}" ${sel}>Layer ${lid} (Bank ${bank}·${slot}) — ${escapeHtml(lName)}</option>`;
    }).join('');

    // Preset source tabs if app has multiple presets
    const presetSelectorHtml = presets.length > 1 ? `
      <div style="background:var(--bg-card); border:1px solid rgba(0,229,255,0.25); border-radius:10px; padding:10px 14px; display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="font-size:11px; font-weight:800; color:var(--text-muted); text-transform:uppercase;">Hardware Preset:</span>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            ${presets.map(p => {
              const isCur = p.source === currentSource;
              return `
                <button class="btn" onclick="selectDetailPresetSource('${escapeHtml(p.source)}')" style="padding:4px 10px; font-size:11px; font-weight:700; border-radius:6px; border:1px solid ${isCur ? 'var(--accent-cyan)' : 'var(--border)'}; background:${isCur ? 'var(--accent-cyan)' : 'var(--bg-panel)'}; color:${isCur ? '#000' : '#fff'};">
                  ${getSourceIcon(p.source)} ${escapeHtml(p.source)} <span style="font-size:9.5px; opacity:0.8;">(${p.action_count || (p.actions||[]).length} fn)</span>
                </button>
              `;
            }).join('')}
          </div>
        </div>
        <div>
          ${app.selected_preset_source === currentSource ? `
            <span style="font-size:11px; font-weight:700; color:var(--accent-green); display:flex; align-items:center; gap:4px;">
              <span>✓</span> Active Preset for Auto-App
            </span>
          ` : `
            <button class="btn" onclick="setDefaultPresetForApp('${escapeHtml(app.id)}', '${escapeHtml(currentSource)}')" style="padding:4px 10px; font-size:11px; font-weight:700; border-color:var(--accent-cyan); color:var(--accent-cyan);">
              ⭐ Set as Default for Auto-App
            </button>
          `}
        </div>
      </div>
    ` : '';

    const cellsPreviewHtml = recCells.map((c, idx) => {
      const hasRm = idx < radials.length;
      return `
        <div style="background:#dfe5e1; color:#111513; border-radius:6px; padding:6px 4px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px; position:relative; border:1px solid #99a39d;">
          <span style="position:absolute; top:2px; left:4px; font-size:8px; font-family:var(--font-mono); opacity:0.65;">#${idx+1}</span>
          ${hasRm ? `<span style="position:absolute; top:2px; right:4px; font-size:8px; background:#006064; color:#fff; padding:0 3px; border-radius:3px;">🎡</span>` : ''}
          <canvas id="tdx-prev-ico-${idx}" width="24" height="24" style="width:24px; height:24px; image-rendering:pixelated;"></canvas>
          <div style="font-size:9px; font-weight:800; font-family:var(--font-mono); text-align:center;">${escapeHtml(c.label)}</div>
          <div style="font-size:8px; color:#37474f; font-family:var(--font-mono); max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(c.action)}</div>
        </div>
      `;
    }).join('');

    const radialsHtml = radials.length > 0 ? radials.map((rm, rIdx) => `
      <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:8px 10px;">
        <div style="font-size:11px; font-weight:700; color:var(--accent-cyan); margin-bottom:5px;">🎡 Hold Key #${rIdx+1} Radial: ${escapeHtml(rm.name)} (${rm.slices.length} slices)</div>
        <div style="display:flex; flex-wrap:wrap; gap:5px;">
          ${rm.slices.map(s => `<span style="font-size:10px; background:rgba(255,255,255,0.06); padding:2px 7px; border-radius:4px; border:1px solid var(--border);"><strong>${escapeHtml(s.name)}</strong> <code style="color:var(--accent-amber);">${escapeHtml(s.action)}</code></span>`).join('')}
        </div>
      </div>
    `).join('') : `<div style="font-size:11px; color:var(--text-muted);">No custom Radial Pie Menus for this preset.</div>`;

    const allActionsHtml = (actions || []).map((a, aIdx) => `
      <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:7px 10px; display:flex; align-items:center; justify-content:space-between; gap:8px;">
        <div style="display:flex; align-items:center; gap:8px; min-width:0;">
          <canvas id="tdx-act-ico-${aIdx}" width="24" height="24" style="width:24px; height:24px; image-rendering:pixelated; background:#14171f; border-radius:4px; flex-shrink:0;"></canvas>
          <div style="min-width:0;">
            <div style="font-size:11.5px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(a.name)} <span style="font-size:9.5px; color:var(--accent-cyan); font-family:var(--font-mono);">[${escapeHtml(a.label)}]</span></div>
            <div style="font-size:10px; font-family:var(--font-mono); color:var(--accent-amber);">${escapeHtml(a.action)}</div>
          </div>
        </div>
        <button class="btn" style="padding:4px 8px; font-size:10px; flex-shrink:0;" onclick="assignTdxActionToCurrentKey(${aIdx})" title="Assign this function & icon to currently selected Keycap in Studio">
          ➕ To Key #${selectedControl.type === 'cell' ? selectedControl.index : 1}
        </button>
      </div>
    `).join('');

    detailEl.innerHTML = `
      <!-- Top Import Card -->
      <div style="background:var(--bg-card); border:1px solid rgba(0,229,255,0.35); border-radius:12px; padding:14px 16px; display:flex; flex-direction:column; gap:12px;">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:17px; font-weight:800; color:#fff;">${escapeHtml(app.name)}</span>
              ${getSourceBadge(currentSource)}
            </div>
            <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono); margin-top:2px;">
              Executable: <strong style="color:var(--accent-cyan);">${escapeHtml(app.exe_match || 'Manual Layer Only')}</strong> • Source: <strong>${escapeHtml(currentSource)}</strong>
            </div>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <select id="tdx-target-layer" class="input-field" style="width:245px; font-weight:700;">${layerOptions}</select>
            <button class="btn btn-primary" onclick="importSelectedTdxApp()" style="padding:8px 16px; font-weight:800;">
              🚀 1-Click Import to Layer
            </button>
          </div>
        </div>
        <div style="display:flex; gap:18px; flex-wrap:wrap; font-size:11.5px; color:var(--text-muted);">
          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="tdx-chk-radials" checked style="accent-color:var(--accent-cyan);">
            Include Radial Menus (${radials.length})
          </label>
          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="tdx-chk-autorule" checked style="accent-color:var(--accent-cyan);">
            Create Auto-App Switcher Rule (<code>${escapeHtml(app.exe_match || 'N/A')}</code>)
          </label>
          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="tdx-chk-push" checked style="accent-color:var(--accent-cyan);">
            Push immediately to MacroPad E-Ink Display
          </label>
        </div>
      </div>

      <!-- Preset Selector Bar (if multi-source) -->
      ${presetSelectorHtml}

      <!-- Middle: 3x3 E-Ink Preview + Radial Menus -->
      <div style="display:grid; grid-template-columns:230px 1fr; gap:16px; align-items:start;">
        <div>
          <div style="font-size:11px; font-weight:700; color:var(--text-muted); margin-bottom:6px; text-transform:uppercase;">3×3 E-Ink Layer Preview (${escapeHtml(currentSource)})</div>
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:5px; background:#14171f; padding:8px; border-radius:10px; border:1px solid var(--border);">
            ${cellsPreviewHtml}
          </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:8px;">
          <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Preset Radial Pie Menus (${radials.length})</div>
          ${radialsHtml}
        </div>
      </div>

      <!-- Bottom: All Harvested Functions for this Preset -->
      <div>
        <div style="font-size:11px; font-weight:700; color:var(--text-muted); margin-bottom:8px; text-transform:uppercase;">
          All Preset Functions (${(actions || []).length}) — Click "➕ To Key" to assign
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(290px, 1fr)); gap:8px;">
          ${allActionsHtml || '<div style="font-size:11px; color:var(--text-muted);">Standard universal shortcuts (Undo, Redo, Save, Copy, Paste, Fit View, Find, Escape).</div>'}
        </div>
      </div>
    `;

    // Render 24x24 icons
    recCells.forEach((c, idx) => {
      const cvs = document.getElementById(`tdx-prev-ico-${idx}`);
      const icoObj = iconsLibrary[c.icon];
      if (cvs && icoObj && icoObj.hex) {
        drawIconHexOnCanvas(cvs, icoObj.hex, '#111513', null);
      }
    });
    (actions || []).forEach((a, aIdx) => {
      const cvs = document.getElementById(`tdx-act-ico-${aIdx}`);
      const icoObj = iconsLibrary[a.icon];
      if (cvs && icoObj && icoObj.hex) {
        drawIconHexOnCanvas(cvs, icoObj.hex, '#00e5ff', null);
      }
    });
  }

  function assignTdxActionToCurrentKey(actIdx) {
    const app = tdxCatalogApps.find(a => a.id === selectedTdxAppId);
    if (!app) return;
    const presets = app.presets || [];
    let currentSource = selectedDetailPresetSource || app.selected_preset_source || (presets[0] ? presets[0].source : app.source) || '3Dconnexion';
    let matchedPreset = presets.find(p => p.source === currentSource) || presets[0] || null;
    const actions = (matchedPreset && matchedPreset.actions) ? matchedPreset.actions : (app.actions || []);
    if (!actions[actIdx]) return;
    const actObj = actions[actIdx];

    const targetIdx = selectedControl.type === 'cell' ? selectedControl.index : 1;
    selectedControl = { type: 'cell', index: targetIdx };
    const cell = layersStore[selectedLayerId]?.cells?.[targetIdx - 1];
    if (!cell) return;
    cell.label = actObj.label;
    cell.action = actObj.action;
    if (actObj.icon) cell.icon = actObj.icon;
    closeTdxLibraryModal();
    renderAll();
  }

  async function importSelectedTdxApp() {
    const app = tdxCatalogApps.find(a => a.id === selectedTdxAppId);
    if (!app) return;
    const presets = app.presets || [];
    let currentSource = selectedDetailPresetSource || app.selected_preset_source || (presets[0] ? presets[0].source : app.source) || '3Dconnexion';
    const targetLayer = Number(document.getElementById('tdx-target-layer')?.value || selectedLayerId || 15);
    const includeRadials = !!document.getElementById('tdx-chk-radials')?.checked;
    const addAutoRule = !!document.getElementById('tdx-chk-autorule')?.checked;
    const pushToDevice = !!document.getElementById('tdx-chk-push')?.checked;

    const res = await fetch('/api/tdx/import_layer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        app_id: app.id,
        preset_source: currentSource,
        target_layer: targetLayer,
        include_radials: includeRadials,
        add_auto_rule: addAutoRule,
        push_to_device: pushToDevice
      })
    });
    const data = await res.json();
    if (data.status === 'imported') {
      selectedLayerId = String(targetLayer);
      await loadAllConfig();
      closeTdxLibraryModal();
    }
  }

  initStudio();
</script>
</body>
</html>
"""
