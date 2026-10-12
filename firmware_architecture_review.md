# ESP32-C3 MacroPad Firmware & Embedded Architecture Review

---

## 1) Critical Firmware Bugs & Hardware Safety Risks

### 1.1 `esp_brownout_disable()` & Hardware Flash Corruption
* **Code Anchor:** [`MACROPAD.ino:1912`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1912)
  ```cpp
  esp_brownout_disable(); // Properly disables IDF brownout detection
  ```
* **Hardware Reality:** On the single-core ESP32-C3 RISC-V SoC, calibration bursts from the 2.4GHz internal RF PA draw instantaneous current spikes exceeding **350–420mA**. When running off a single LiPo cell under low state-of-charge ($V_{cell} \le 3.4\text{V}$) with battery internal resistance (ESR) plus onboard LDO dropout, the $V_{DD}$ rail sags below the flash memory operating floor ($2.7\text{V}$).
* **Failure Mode:** By disabling the BOD (Brownout Detector), the CPU does not cleanly reset. Instead, the flash controller executes corrupted instructions or experiences write/erase interrupts during SPI flash transactions, resulting in **SPI Flash file table corruption, corrupted RTC data, and unrecoverable boot loops**.
* **Remedy:** Re-enable the hardware brownout detector at its lowest safe trip level (Threshold 7 on ESP32-C3: $\sim 2.51\text{V}$) and throttle RF TX power dynamically under low voltage, rather than disabling hardware safety.

### 1.2 Cold-Boot Wakeup Drop: Lost Keypress on Cold Boot
* **Code Anchor:** [`MACROPAD.ino:885-887`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L885-L887), [`MACROPAD.ino:1916-1939`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1916-L1939)
  ```cpp
  setMatrixIdle();
  esp_deep_sleep_enable_gpio_wakeup(1ULL << MATRIX_INT, ESP_GPIO_WAKEUP_GPIO_LOW);
  esp_deep_sleep_start();
  ```
* **Failure Mode:** When waking from deep sleep via `MATRIX_INT` (GPIO 3 pulled LOW by PCF8574 open-drain INT on switch press), the ESP32-C3 performs a full system cold boot through ROM and executes `setup()`.
  Inside `setup()`, there is **no initial scan of the matrix**. Instead, `setup()` performs:
  1. NeoPixel clear & wake animation ([`L1943-1951`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1943-L1951))
  2. SPI display initialization ([`L1953-1955`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1953-L1955))
  3. Blocking Wi-Fi and network setup ([`L1962`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1962))
  4. Matrix expander reset: `setMatrixIdle()` ([`L1985`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1985)), which writes `0xF0` to PCF8574 and reads back, **clearing the interrupt latch**.
* **Impact:** By the time `loop()` executes its first scan ([`L2317`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L2317)), hundreds of milliseconds have elapsed. If the mechanical key tap was $\le 150\text{ms}$, the switch has physically opened. The keystroke that woke the device is **silently lost**.

### 1.3 Dead Power Path in Sleep Policy
* **Code Anchor:** [`MACROPAD.ino:890-910`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L890-L910)
  ```cpp
  void handlePowerManagement() {
    ...
    if (cachedVolts >= USB_DETECT_THRESHOLD) {
      return; // External USB power: do not sleep
    }
    if (cachedVolts <= LOW_BATTERY_THRESHOLD && cachedVolts > 0.5f) {
      enterDeepSleep(true);
    }
  }
  ```
* **Failure Mode:** `SLEEP_TIMEOUT` ($600{,}000\text{ms}$ / 10 minutes) is defined at line 109, but **it is never checked anywhere in `loop()` or `handlePowerManagement()`**.
* **Impact:** When running on battery without USB plugged in, unless the battery sags below $3.3\text{V}$, **the device never enters deep sleep**. The 10-minute idle sleep timeout is an inert dead path. The device runs at $\sim 115\text{mA}$ indefinitely until the battery drops into critical cutoff.

---

## 2) Real-Time Latency & Peripheral Contention (E-Ink vs I2C/Encoders)

### 2.1 E-Ink Blocking SPI Duration & Loop Freezing
* **Code Anchor:** [`MACROPAD.ino:799-800`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L799-L800)
  ```cpp
  display.display(!fullRefreshNeeded);
  fullRefreshNeeded = false;
  ```
* **Timing Characteristics:**
  * SSD1680 controller SPI frame write (200x200 1-bit = 5,000 bytes) at hardware SPI: $\sim 15\text{–}25\text{ms}$.
  * GxEPD2 blocking wait: `display.display()` waits on `_waitWhileBusy()` which asserts `EPD_BUSY` (GPIO 8).
  * **Partial Refresh Gate Time:** $300\text{–}450\text{ms}$ hardware refresh cycle.
  * **Full Refresh Gate Time:** $1{,}200\text{–}1{,}800\text{ms}$ multi-phase refresh waveform cycle.
* **Per-Loop Freeze:** Because GxEPD2 polls `digitalRead(EPD_BUSY)` synchronously in a `while` loop on the single core, the main execution thread completely stops servicing all other routines for up to $1.8\text{ seconds}$.

```
Loop Timeline:
|-- scanMatrix (I2C) --|-- updateScreen() [BLOCKING SPI & E-INK BUSY] --|-- missed enc ticks --|
0ms                   10ms                                            1450ms
                               ▲
                 CPU STALLED HERE FOR ~1440ms
           (No I2C Reads, No MQTT loop, No Network Polling)
```

### 2.2 Encoder 1 (Hardware ISR) vs Encoders 2 & 3 (PCF8574 Polling)
* **Encoder 1 (Hardware GPIOs 20, 21):**
  Uses Ben Buxton’s quadrature state machine inside an ISR ([`L406-415`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L406-L415)). During `updateScreen()`, interrupt execution remains active, but `enc1_raw_steps` accumulates while `loop()` cannot dispatch or drain it.
* **Encoders 2 and 3 (PCF8574 at 0x24 via I2C):**
  * Read via synchronous polling in `loop()` at line 2189:
    ```cpp
    unsigned long encScanInterval = (now - lastActivityTime < 3000) ? 4 : 20;
    if (now - lastI2cEncScan > encScanInterval) {
      Wire.requestFrom(PCF_ENCODERS, 1);
      ...
      if (last_e2Clk == HIGH && e2Clk == LOW) { ... }
    }
    ```
  * **Vulnerabilities:**
    1. **Missed Detents During Display Update:** If the user turns Encoder 2 or 3 while the display is updating ($300\text{–}1800\text{ms}$), all intermediate transition edges are lost. When the display completes, the PCF8574 holds only the steady-state value.
    2. **Half-Step Edge Sensitivity:** The firmware only samples `last_e2Clk == HIGH && e2Clk == LOW` (falling edge on Clock) and checks DT state. This is a 1X quadrature decoder. If contact chatter occurs or detent centering settles on an edge, this logic experiences **direction inversion** or double-triggering. Unlike Buxton's 4-state table used for Encoder 1, Encoders 2 and 3 have **zero bounce rejection**.
    3. **I2C Clock Contention:** `Wire.setClock(100000)` (100kHz standard mode). An 8-bit read from PCF8574 takes $\sim 250\mu\text{s}$. If an I2C transaction stalls or hits bus arbitration while recovering from screen wake, `Wire.setTimeOut(20)` blocks the loop for an additional $20\text{ms}$.

---

## 3) Heap Fragmentation & Memory Audit

### 3.1 Arduino `String` Concatenation in High-Frequency Paths
* **Code Anchor:** [`MACROPAD.ino:76`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L76), [`MACROPAD.ino:1098-1112`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1098-L1112), [`MACROPAD.ino:1129-1144`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1129-L1144), [`MACROPAD.ino:1177-1190`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1177-L1190)
* **Mechanisms:**
  1. **`sendHeartbeat()` (every 10s):**
     ```cpp
     String payload = "{\"device\":\"macropad\",\"state\":\"online\",\"vbat\":" + String(vbat, 2) + ...
     ```
     Creates 14 transient `String` heap allocations on every heartbeat.
  2. **WebServer `/api/logs` Route:**
     ```cpp
     String json = "[";
     for (int i = 0; i < logCount; i++) {
       ...
       json += "{\"t\":" + String(deviceLogs[idx].t) + ...
     }
     ```
     Iteratively reallocates the buffer up to 50 times inside DRAM, triggering `realloc` memory fragmentation across heap blocks.
  3. **MQTT Publish Queue (`mqttQueue` array of `String`):**
     Each queued element reallocates dynamic storage in the heap pool.

### 3.2 ArduinoJson Buffer Pressure in `mqttCallback`
* **Code Anchor:** [`MACROPAD.ino:923-927`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L923-L927)
  ```cpp
  String message;
  for (unsigned int i = 0; i < length; i++) message += (char)payload[i];
  
  JsonDocument doc;
  if (deserializeJson(doc, message)) return;
  ```
* **Heap Failure Mode:**
  1. The MQTT incoming buffer is sized to $2048\text{ bytes}$ via `mqttClient.setBufferSize(2048)`.
  2. In `mqttCallback`, copying `payload` byte-by-byte into `String message` allocates a contiguous $2\text{KB}$ heap buffer.
  3. `deserializeJson(doc, message)` with dynamic `JsonDocument` allocates another $2\text{–}3\text{KB}$ heap structure for the AST (labels array + 9 icon strings of 144 characters each $\approx 1{,}300\text{ bytes}$ of raw string pointers).
  4. Both allocations exist in DRAM simultaneously. Over multiple incoming layer switches, this repetitive large-block allocation and deallocation quickly fragments the ESP32-C3's small $\sim 300\text{KB}$ internal SRAM, leading to `deserializeJson` failing with `NoMemory`.

---

## 4) Sleep, Power, and Battery Subsystem Evaluation

### 4.1 Missing Idle Sleep Timeout
* **Issue:** As identified in Section 1.3, `SLEEP_TIMEOUT` is declared as $600{,}000\text{ms}$ ($10\text{ min}$), but there is no conditional evaluating `now - lastActivityTime > SLEEP_TIMEOUT` inside `loop()` or `handlePowerManagement()`.
* **Consequence:** Deep sleep is unreachable during regular operation. The only sleep entry points are:
  - Critical voltage sag: `cachedVolts <= LOW_BATTERY_THRESHOLD` ([`L907`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L907))
  - Debug mode Key 8: `enterDeepSleep(false)` ([`L2445`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L2445))
  - Web API endpoint: `/api/test_deep_sleep` ([`L1289`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L1289))

### 4.2 OCV Lookup Interpolation vs Voltage Sag
* **Code Anchor:** [`MACROPAD.ino:138-152`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L138-L152), [`MACROPAD.ino:517-520`](file:///c:/Users/Uzzo/Desktop/MACROPAD/firmware/MACROPAD/MACROPAD.ino#L517-L520)
* **Design Flaw:** The OCV table calculates percentage based on *open-circuit / resting* cell voltage. However, `readBatteryVoltage()` measures the cell while the system is under load ($115\text{mA}$ active Wi-Fi transmit load + NeoPixel current).
* Under active transmit, a $4000\text{mAh}$ LiPo cell with internal and trace resistance can sag by $80\text{–}150\text{mV}$. Reading the ADC under active RF bursts causes the reported battery percentage to drop by up to $15\text{–}20\%$ momentarily, and can prematurely trigger low-battery deep sleep cutoff when the resting cell actually holds $\sim 3.42\text{V}$.

---

## 5) Key Matrix & MQTT State Discrepancies

### 5.1 Top-Row Keys (Keys 1–4): Missing Hold Modifiers
* **Architecture Specification:** The Pi Hub (`layer_manager.py`) and PC Bridge (`macropad_bridge.py`) implement top-row hold modifiers:
  - Key 1 Hold = `SHIFT`
  - Key 2 Hold = `CTRL`
  - Key 3 Hold = `ALT`
  - Key 4 Hold = `ORBIT_CLUTCH`
  - The PC Bridge explicitly listens for `top_mod_hold` and `top_mod_release` with a `slot` parameter ([`macropad_bridge.py:1760-1770`](file:///c:/Users/Uzzo/Desktop/MACROPAD/pc_app/macropad_bridge.py#L1760-L1770)).
* **Firmware Reality:** In `MACROPAD.ino` lines 2349–2352:
  ```cpp
  if (id == 1) selectLayerSlot(0);
  else if (id == 2) selectLayerSlot(1);
  else if (id == 3) selectLayerSlot(2);
  else if (id == 4) selectLayerSlot(3);
  ```
  Top-row keys immediately invoke `selectLayerSlot()` on the initial press down edge. There is **no press-duration measurement, no hold threshold, and zero emission of `top_mod_hold` or `top_mod_release`**. The Mod-Tap behavior configured in the Hub is completely absent from the firmware.

### 5.2 Key 9: HUD vs Auto-App Mode Discrepancy
* **Architecture Specification:** Key 9 is designated as the multi-role Auto-App / Mode toggle button:
  - Short Tap = Toggle Auto-App Mode (`{"action":"auto_app_mode", ...}`)
  - Long Hold ($\ge 420\text{ms}$) = Open Status HUD
* **Firmware Reality:** In `MACROPAD.ino` lines 2746–2753:
  ```cpp
  else if (key9PressTime > 0 && (now - key9LastSeenTime > 45)) {
    if (!key9LongTriggered) {
      // Physical Key 9 toggles Status/Battery HUD peek (mode switching handled in Web Dashboard)
      toggleHud();
    }
    key9PressTime = 0;
    key9LongTriggered = false;
  }
  ```
  Both the short tap and the long hold trigger `toggleHud()`. Short tap does **not** send `auto_app_mode` or `mode_change` over MQTT. The hardware cannot toggle Auto-App Mode locally.

---

## 6) Surgical C++ Refactoring Snippets

### 6.1 Fix 1: Non-Blocking Idle Sleep Timeout & Safe BOD Initialization

Add the missing idle sleep timeout in `handlePowerManagement()` and replace `esp_brownout_disable()` with a proper hardware-safe initialization:

```cpp
// --- REPLACEMENT: in setup() line 1912 ---
// Replaces: esp_brownout_disable();
// Configure BOD to safe minimum threshold rather than disabling hardware protection
#if defined(CONFIG_ESP32C3_BROWNOUT_DET)
  // Ensure IDF brownout detector is active with standard threshold
  brownout_hal_config_t cfg = {
    .threshold = 7, // Lowest safe trip level (~2.51V) preventing flash corruption
    .enabled = true,
    .reset_ena = true
  };
  brownout_hal_config(&cfg);
#endif
```

```cpp
// --- REPLACEMENT: in handlePowerManagement() lines 900-910 ---
  if (cachedVolts >= USB_DETECT_THRESHOLD) {
    return; // External USB power: do not sleep
  }

  // 1. Critical Low-Battery Safety Cutoff
  if (cachedVolts <= LOW_BATTERY_THRESHOLD && cachedVolts > 0.5f) {
    enterDeepSleep(true);
    return;
  }

  // 2. Idle Sleep Timeout (10 minutes of inactivity on battery)
  if (!stayAwakeMode && (now - lastActivityTime >= SLEEP_TIMEOUT)) {
    addDeviceLog("SYS", "PWR", "Idle timeout reached on battery. Entering deep sleep.");
    enterDeepSleep(false);
  }
```

---

### 6.2 Fix 2: Zero-Heap `deserializeJson` in `mqttCallback`

Eliminate dynamic `String` reallocations by parsing MQTT payloads directly in-place from the raw byte buffer:

```cpp
// --- REPLACEMENT: in mqttCallback() lines 923-927 ---
// Replaces:
//   String message;
//   for (unsigned int i = 0; i < length; i++) message += (char)payload[i];
//   JsonDocument doc;
//   if (deserializeJson(doc, message)) return;

  // Zero-copy in-place deserialization avoiding dynamic String heap fragmentation
  StaticJsonDocument<2048> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    addDeviceLog("ERR", "JSON", err.c_str());
    return;
  }
```

---

### 6.3 Fix 3: Snappy Non-Blocking Screen Refresh Guard

Prevent `updateScreen()` from starving the I2C expanders by checking for active matrix transitions before executing the blocking GxEPD2 paint:

```cpp
// --- REPLACEMENT: in loop() lines 2833-2836 ---
  // Guard E-Ink refresh: only update if no keys are currently held,
  // no encoder transitions are pending, and loop is settled
  bool inputsQuiet = (!isPollingMatrix && enc1_raw_steps == 0 && (now - lastActivityTime >= 400));
  if (screenNeedsUpdate && (now >= screenUpdateScheduledTime) && inputsQuiet) {
    updateScreen();
    screenNeedsUpdate = false;
  }
```

---

### 6.4 Fix 4: Implement Top-Row (Keys 1–4) Hold Modifiers

Implement Mod-Tap for Keys 1–4 so that holding a key emits the appropriate modifier to the PC Bridge while short-tapping selects the layer slot:

```cpp
// --- ADD TO GLOBALS (around line 174) ---
unsigned long topRowPressTime[4] = {0};
bool topRowHoldActive[4] = {false};
const unsigned long TOP_ROW_HOLD_THRESHOLD_MS = 190;
```

```cpp
// --- REPLACEMENT: in scanMatrix() lines 2348-2352 ---
// Replaces:
//   if (id == 1) selectLayerSlot(0);
//   else if (id == 2) selectLayerSlot(1);
//   else if (id == 3) selectLayerSlot(2);
//   else if (id == 4) selectLayerSlot(3);

  // Top Row Keys 1-4: Mod-Tap handling (Hold = Modifier, Tap = Select Slot)
  if (id >= 1 && id <= 4) {
    int slotIdx = id - 1;
    topRowPressTime[slotIdx] = now;
    topRowHoldActive[slotIdx] = false;
  }
```

```cpp
// --- ADD TO loop() matrix check (inside key state evaluation, around line 2580) ---
  // Evaluate hold states for Top-Row Keys 1-4
  for (int s = 0; s < 4; s++) {
    int keyId = topRowKeyIDs[s];
    if (currentScanState[keyId]) {
      if (!topRowHoldActive[s] && topRowPressTime[s] > 0 && (now - topRowPressTime[s] >= TOP_ROW_HOLD_THRESHOLD_MS)) {
        topRowHoldActive[s] = true;
        sendPayload("{\"device\":\"macropad\", \"action\":\"top_mod_hold\", \"slot\":" + String(s + 1) + "}");
        setKeyLED(keyId, strip.Color(255, 0, 150), 300);
      }
    } else if (lastState[keyId] && !currentScanState[keyId]) {
      // Key released
      if (topRowHoldActive[s]) {
        sendPayload("{\"device\":\"macropad\", \"action\":\"top_mod_release\", \"slot\":" + String(s + 1) + "}");
        setKeyLED(keyId, strip.Color(0, 0, 0), 1);
      } else if (topRowPressTime[s] > 0) {
        // Short tap: switch layer slot
        selectLayerSlot(s);
      }
      topRowPressTime[s] = 0;
      topRowHoldActive[s] = false;
    }
  }
```

---

### 6.5 Fix 5: Restore Key 9 Short Tap Auto-App Toggle

Fix Key 9 release evaluation so short tap toggles Auto-App mode and updates the Pi Hub and PC Bridge:

```cpp
// --- REPLACEMENT: in scanMatrix() lines 2746-2753 ---
    } else if (key9PressTime > 0 && (now - key9LastSeenTime > 45)) {
      if (!key9LongTriggered) {
        // Short Tap: Toggle Auto-App Mode vs Manual Mode
        isAutoAppMode = !isAutoAppMode;
        deviceMode = isAutoAppMode ? MODE_AUTO : MODE_MANUAL;
        rtcDeviceMode = (int)deviceMode;
        updateLayerLEDs(true);
        sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"auto_app_mode\", \"enabled\":" + (isAutoAppMode ? "true" : "false") + "}");
        addDeviceLog("INP", "MODE", isAutoAppMode ? "Key 9: Auto-App Mode ON" : "Key 9: Manual Mode");
        setKeyLED(9, isAutoAppMode ? strip.Color(0, 255, 120) : strip.Color(255, 80, 0), 200);
      }
      key9PressTime = 0;
      key9LongTriggered = false;
    }
```
