#include <Wire.h>
#include <Adafruit_NeoPixel.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <GxEPD2_BW.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include <WebServer.h>
#include <Update.h>
#include "esp_sleep.h"
#include "driver/gpio.h"
#include "dashboard_html.h"

// ==========================================
// NETWORK CONFIGURATION
// ==========================================
const char* ssid = "tpwifi";
const char* password = "1234567890";
const char* mqtt_server = "192.168.1.62"; 
const char* mqtt_topic_pub = "macropad/input";
const char* mqtt_topic_sub = "macropad/display";
const char* mqtt_topic_status = "macropad/status";
const char* mqtt_topic_debug = "macropad/debug";

WiFiClient espClient;
PubSubClient mqttClient(espClient);
unsigned long lastReconnectAttempt = 0;
bool otaInitialized = false; 
bool isFirstMqttConnect = true;
unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_INTERVAL = 10000; 

// ==========================================
// ON-DEVICE WEBSERVER & RING BUFFER
// ==========================================
WebServer server(80);
bool webServerStarted = false;
bool stayAwakeMode = false;

struct LogEntry {
  uint32_t t;
  char lvl[5];  // INFO, WARN, ERR, INP, SYS, DISP
  char tag[8];  // BOOT, WAKE, SLEEP, KEY, ENC, MQTT, BATT
  char msg[60];
};
const int MAX_DEVICE_LOGS = 50;
LogEntry deviceLogs[MAX_DEVICE_LOGS];
int logCount = 0;
int logHead = 0;

void addDeviceLog(const char* lvl, const char* tag, const char* msg) {
  Serial.printf("[%s] [%s] %s\n", lvl, tag, msg);
  
  int idx;
  if (logCount < MAX_DEVICE_LOGS) {
    idx = logCount;
    logCount++;
  } else {
    idx = logHead;
    logHead = (logHead + 1) % MAX_DEVICE_LOGS;
  }
  
  deviceLogs[idx].t = millis();
  strncpy(deviceLogs[idx].lvl, lvl, sizeof(deviceLogs[idx].lvl) - 1);
  deviceLogs[idx].lvl[sizeof(deviceLogs[idx].lvl) - 1] = '\0';
  strncpy(deviceLogs[idx].tag, tag, sizeof(deviceLogs[idx].tag) - 1);
  deviceLogs[idx].tag[sizeof(deviceLogs[idx].tag) - 1] = '\0';
  strncpy(deviceLogs[idx].msg, msg, sizeof(deviceLogs[idx].msg) - 1);
  deviceLogs[idx].msg[sizeof(deviceLogs[idx].msg) - 1] = '\0';

  if (mqttClient.connected()) {
    String p = "{\"level\":\"" + String(lvl) + "\",\"tag\":\"" + String(tag) + "\",\"msg\":\"" + String(msg) + "\",\"heap\":" + String(ESP.getFreeHeap()) + "}";
    mqttClient.publish(mqtt_topic_debug, p.c_str());
  }
} 

// ==========================================
// PIN DEFINITIONS 
// ==========================================
#define MATRIX_SDA   4
#define MATRIX_SCL   5
#define MATRIX_INT   3    
#define PCF_MATRIX   0x20 
#define PCF_ENCODERS 0x24 

#define ENCODER_SW   9
#define ENCODER_CLK  20
#define ENCODER_DT   21

#define NEOPIXEL_PIN 1  
#define NUMPIXELS    18 

#define EPD_SCL  6    
#define EPD_SDA  7    
#define EPD_CS   10
#define EPD_DC   2
#define EPD_RST  -1   
#define EPD_BUSY 8    
#define BATTERY_PIN  0    

// ==========================================
// POWER, SLEEP & UI STATE
// ==========================================
unsigned long lastActivityTime = 0;
const unsigned long SLEEP_TIMEOUT = 600000; // 10 minutes idle -> sleep (prevents constant sleep while working)
const float LOW_BATTERY_THRESHOLD = 3.3;
const float USB_DETECT_THRESHOLD = 4.3;
const int BATTERY_CAPACITY_MAH = 4000;
const int CHARGE_CURRENT_MA = 1000;

struct LipoPoint {
  float v;
  int pct;
};

// Open-Circuit / Resting LiPo Voltage to State of Charge (SoC) lookup table
const LipoPoint lipoOcvTable[] = {
  {4.20f, 100},
  {4.13f, 90},
  {4.03f, 80},
  {3.93f, 70},
  {3.85f, 60},
  {3.80f, 50},
  {3.76f, 40},
  {3.72f, 30},
  {3.67f, 20},
  {3.58f, 10},
  {3.45f, 5},
  {3.30f, 0}
};
const int LIPO_TABLE_ENTRIES = sizeof(lipoOcvTable) / sizeof(lipoOcvTable[0]);

int getLipoPercentage(float volts) {
  if (volts >= lipoOcvTable[0].v) return 100;
  if (volts <= lipoOcvTable[LIPO_TABLE_ENTRIES - 1].v) return 0;
  for (int i = 0; i < LIPO_TABLE_ENTRIES - 1; i++) {
    if (volts <= lipoOcvTable[i].v && volts >= lipoOcvTable[i + 1].v) {
      float vHigh = lipoOcvTable[i].v;
      float vLow = lipoOcvTable[i + 1].v;
      int pHigh = lipoOcvTable[i].pct;
      int pLow = lipoOcvTable[i + 1].pct;
      float fraction = (volts - vLow) / (vHigh - vLow);
      return pLow + (int)(fraction * (pHigh - pLow));
    }
  }
  return 0;
}

int calculateTimeToFull(int pct) {
  if (pct >= 99) return 5;
  float remMah = (float)BATTERY_CAPACITY_MAH * (1.0f - ((float)pct / 100.0f));
  float hours = remMah / (float)CHARGE_CURRENT_MA;
  if (pct < 80) hours += 0.4f; // Add ~24 mins for CV phase taper
  else hours *= 1.3f;
  return max(1, (int)(hours * 60.0f));
}

RTC_DATA_ATTR int rtcBank = 0;
RTC_DATA_ATTR int rtcSlot = 0;
RTC_DATA_ATTR int rtcLayer = 1;
RTC_DATA_ATTR bool rtcWasDeepSleep = false;

int currentBank = 0; // 0 = Bank 1 (1-4), 1 = Bank 2 (5-8), 2 = Bank 3 (9-12), 3 = Bank 4 (13-16)
int currentSlot = 0; // 0..3 (representing keys 1, 2, 3, 4)
const int MAX_BANKS = 4;
int currentLayer = 1; // currentBank * 4 + currentSlot + 1 (1 to 16)

const int topRowKeyIDs[4] = {1, 2, 3, 4};

struct BankColor {
  uint8_t r, g, b;
};

const BankColor bankColors[MAX_BANKS] = {
  {0, 255, 0},    // Bank 1: Layers 1-4 (Green)
  {0, 100, 255},  // Bank 2: Layers 5-8 (Blue)
  {180, 0, 255},  // Bank 3: Layers 9-12 (Purple)
  {255, 120, 0}   // Bank 4: Layers 13-16 (Orange/Amber)
};

// Modifier and room light state (Key ID 5: Row 1, Col 0 - first button of second row)
unsigned long key5PressTime = 0;
unsigned long key5LastSeenTime = 0;
bool key5PhysicallyPressed = false;
bool key5Held = false;
bool isModifierHeld = false;
const unsigned long HOLD_MODIFIER_MS = 300;

// Audio Modifier and Discord Mic Mute (Key ID 13: Row 3, Col 0 - bottom-left corner)
unsigned long key13PressTime = 0;
unsigned long key13LastSeenTime = 0;
bool key13PhysicallyPressed = false;
bool key13Held = false;
bool isAudioModifierHeld = false;
bool isAudioModifierUsed = false;
bool isMicMuted = false;
bool inVoiceCall = false;

unsigned long screenMessageDismissTime = 0;
const unsigned long POPUP_TIMEOUT_MS = 2000;

// Dynamic 3x3 keys preset tracking (under modifier)
const int dynIdxToKeyID[10] = {0, 6, 7, 8, 10, 11, 12, 14, 15, 16};
unsigned long dynKeyPressTime[10] = {0};
bool dynKeyHeld[10] = {false};
const unsigned long PRESET_LONG_PRESS_MS = 600;
bool currentScanState[17] = {false};

int getHeld3x3UserKey() {
  for (int k = 1; k <= 9; k++) {
    int keyId = dynIdxToKeyID[k];
    if (currentScanState[keyId]) return k;
  }
  return 0;
}

bool fullRefreshNeeded = true;
bool screenNeedsUpdate = true;
unsigned long screenUpdateScheduledTime = 0;
String screenMessage = "BOOTING...";
String gridLabels[9] = {"ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "ACT 7", "ACT 8", "ACT 9"};
bool isHudActive = false;
unsigned long hudAutoDismissTime = 0;
bool isScreenBlackTestActive = false;

void requestScreenUpdate(bool fullRefresh = false, unsigned long delayMs = 300) {
  if (fullRefresh) fullRefreshNeeded = true;
  screenNeedsUpdate = true;
  screenUpdateScheduledTime = millis() + delayMs;
}

// ==========================================
// COMPONENT SETUP & MAPPING
// ==========================================
Adafruit_NeoPixel strip(NUMPIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
GxEPD2_BW<GxEPD2_154_D67, GxEPD2_154_D67::HEIGHT> display(GxEPD2_154_D67(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// Ben Buxton's Rotary Encoder Algorithm (100% bounce-immune)
#define DIR_NONE 0x00
#define DIR_CW   0x10
#define DIR_CCW  0x20

#define R_START     0x0
#define R_CW_FINAL  0x1
#define R_CW_BEGIN  0x2
#define R_CW_NEXT   0x3
#define R_CCW_BEGIN 0x4
#define R_CCW_FINAL 0x5
#define R_CCW_NEXT  0x6

const unsigned char ttable[7][4] = {
  // R_START
  {R_START,    R_CW_BEGIN,  R_CCW_BEGIN, R_START},
  // R_CW_FINAL
  {R_CW_NEXT,  R_START,     R_CW_FINAL,  R_START | DIR_CW},
  // R_CW_BEGIN
  {R_CW_NEXT,  R_CW_BEGIN,  R_START,     R_START},
  // R_CW_NEXT
  {R_CW_NEXT,  R_CW_BEGIN,  R_CW_FINAL,  R_START},
  // R_CCW_BEGIN
  {R_CCW_NEXT, R_START,     R_CCW_BEGIN, R_START},
  // R_CCW_FINAL
  {R_CCW_NEXT, R_CCW_FINAL, R_START,     R_START | DIR_CCW},
  // R_CCW_NEXT
  {R_CCW_NEXT, R_CCW_FINAL, R_CCW_BEGIN, R_START},
};

volatile uint8_t enc1_state = R_START;
volatile int enc1_raw_steps = 0;

bool lastState[17] = {false};
bool isPollingMatrix = false; 
unsigned long lastMatrixScan = 0;
unsigned long lastI2cEncScan = 0; 

unsigned long lastEnc2Trigger = 0;
unsigned long lastEnc3Trigger = 0;
const int ENC_DEBOUNCE = 6; 

byte lastI2cEncState = 0xFF;
bool enc2ButtonState = false;
bool enc3ButtonState = false;
unsigned long enc3PressTime = 0;
bool enc3LongTriggered = false;
const unsigned long ENC_LONG_PRESS_MS = 500;

const int keyIDs[4][4] = {
  {1,   5,   9,  13},
  {2,   6,  10,  14},
  {3,   7,  11,  15},
  {4,   8,  12,  16}
};

const int keyToLedMap[17] = {
  -1,             
  12, 13, 14, 15, 
  11, 10,  9,  8, 
   4,  5,  6,  7, 
   3,  2,  1,  0  
};

unsigned long ledTurnOffTime[16] = {0}; 
bool displayLedsActive = false;
bool isRainbowSwirl = false;
unsigned long swirlStartTime = 0;
uint16_t swirlHue = 0;

// LED 17 Screen Update Dimming Animation
bool isScreenFadeActive = false;
unsigned long screenUpdateFadeStart = 0;
const unsigned long SCREEN_FADE_DURATION = 6000; // 6 seconds fade

// Boot and Wake Animations
enum AnimState { ANIM_NONE, ANIM_BOOT, ANIM_WAKE };
AnimState currentAnimation = ANIM_NONE;
unsigned long animStartTime = 0;

// Forward declarations
void sendPayload(String payload);
void flushMqttQueue();
void updateLayerLEDs(bool doShow = true);
void selectLayerSlot(int slot);
void cycleBank();
void resetToB1L1();
int getDynamicIndex(int keyId);
void showBatteryCalibration();
void startBootAnimation();
void startWakeAnimation();
void handleAnimations(unsigned long now);

// ==========================================
// INTERRUPT SERVICE ROUTINES
// ==========================================
void IRAM_ATTR encoder1ISR() {
  uint8_t pinstate = (digitalRead(ENCODER_CLK) << 1) | digitalRead(ENCODER_DT);
  enc1_state = ttable[enc1_state & 0x0F][pinstate];
  uint8_t result = enc1_state & 0x30;
  if (result == DIR_CW) {
    enc1_raw_steps++;
  } else if (result == DIR_CCW) {
    enc1_raw_steps--;
  }
}

// ==========================================
// HARDWARE CONTROL 
// ==========================================
void recoverI2CBus() {
  pinMode(MATRIX_SDA, INPUT_PULLUP);
  pinMode(MATRIX_SCL, OUTPUT);
  for (int i = 0; i < 9; i++) {
    digitalWrite(MATRIX_SCL, HIGH);
    delayMicroseconds(5);
    digitalWrite(MATRIX_SCL, LOW);
    delayMicroseconds(5);
  }
  pinMode(MATRIX_SDA, OUTPUT);
  digitalWrite(MATRIX_SDA, LOW);
  delayMicroseconds(5);
  digitalWrite(MATRIX_SCL, HIGH);
  delayMicroseconds(5);
  digitalWrite(MATRIX_SDA, HIGH);
  delayMicroseconds(5);
  pinMode(MATRIX_SDA, INPUT_PULLUP);
  pinMode(MATRIX_SCL, INPUT_PULLUP);
}

void setMatrixIdle() {
  Wire.beginTransmission(PCF_MATRIX);
  Wire.write(0xF0); 
  byte err = Wire.endTransmission();
  if (err != 0) {
    recoverI2CBus();
    Wire.begin(MATRIX_SDA, MATRIX_SCL);
    Wire.setClock(100000);
    return;
  }
  Wire.requestFrom(PCF_MATRIX, 1);
  if (Wire.available()) Wire.read();
}

void setKeyLED(int keyID, uint32_t color, int duration = 100) {
  if (keyID >= 1 && keyID <= 16 && !isRainbowSwirl) {
    int px = keyToLedMap[keyID];
    strip.setPixelColor(px, color);
    strip.show();
    ledTurnOffTime[px] = millis() + duration; 
  }
}

void refreshDisplayLeds() {
  uint32_t c = displayLedsActive ? strip.Color(255, 255, 255) : strip.Color(0, 0, 0);
  if (!isScreenFadeActive) {
    strip.setPixelColor(16, c); 
    strip.setPixelColor(17, c); 
    strip.show();
  }
}

void toggleDisplayLeds() {
  displayLedsActive = !displayLedsActive;
  refreshDisplayLeds();
}

uint32_t getRawBatteryADC() {
  uint32_t sum = 0;
  for (int i = 0; i < 32; i++) {
    sum += analogRead(BATTERY_PIN);
    delayMicroseconds(100);
  }
  return sum / 32;
}

uint32_t getBatteryMilliVolts() {
  uint32_t sum = 0;
  for (int i = 0; i < 32; i++) {
    sum += analogReadMilliVolts(BATTERY_PIN);
    delayMicroseconds(100);
  }
  return sum / 32;
}

float readBatteryVoltage() {
  // Calibrated with multimeter: 3.866V @ 1890mV (divider ratio = 2.0455026)
  return (float)getBatteryMilliVolts() * 0.0020455f; 
}

void showBatteryCalibration() {
  uint32_t raw = getRawBatteryADC();
  uint32_t mv = getBatteryMilliVolts();
  float currV = (float)raw * 0.001603f;
  float newFactor = 3.866f / (float)raw;
  
  screenMessage = "ADC: " + String(raw) + "\neFuse: " + String(mv) + "mV";
  gridLabels[0] = "A:" + String(raw);
  screenNeedsUpdate = true;
  fullRefreshNeeded = true;
  
  String payload = "{\"device\":\"macropad\", \"action\":\"battery_calib\", \"multimeter_v\":3.866, \"raw_adc\":" + String(raw) + ", \"pin_mv\":" + String(mv) + ", \"curr_calc_v\":" + String(currV, 3) + ", \"new_factor\":" + String(newFactor, 7) + "}";
  sendPayload(payload);
  Serial.println(payload);
}

// ==========================================
// E-INK RENDERER UI
// ==========================================
void drawTopBar() {
  display.setFont();
  display.setTextSize(1);
  display.setTextColor(GxEPD_BLACK);
  
  float volts = readBatteryVoltage();
  bool usbPwr = (volts >= USB_DETECT_THRESHOLD);
  bool isCharging = (!usbPwr && volts >= 4.00f);
  float effVolts = isCharging ? max(3.30f, volts - 0.24f) : volts;
  int battPct = getLipoPercentage(effVolts);
  bool wifiOk = (WiFi.status() == WL_CONNECTED);
  bool mqttOk = mqttClient.connected();

  display.setCursor(5, 5);
  display.print("B" + String(currentBank + 1) + ":L" + String(currentLayer) + (wifiOk ? " W:OK" : " W:--"));
  display.setCursor(75, 5);
  display.print(mqttOk ? "M:OK" : "M:--");
  
  display.setCursor(130, 5);
  if (usbPwr) display.print("USB PWR");
  else if (isCharging) display.print("CHG " + String(battPct) + "%");
  else display.print("BAT:" + String(volts, 2) + "V");
  
  display.drawLine(0, 16, 200, 16, GxEPD_BLACK);
}

void drawGrid() {
  display.setFont(&FreeSansBold9pt7b); 
  display.setTextSize(1);
  
  display.drawLine(66, 16, 66, 200, GxEPD_BLACK);
  display.drawLine(133, 16, 133, 200, GxEPD_BLACK);
  display.drawLine(0, 77, 200, 77, GxEPD_BLACK);
  display.drawLine(0, 138, 200, 138, GxEPD_BLACK);

  int index = 0;
  for (int row = 0; row < 3; row++) {
    for (int col = 0; col < 3; col++) {
      int cellX = col * 66;
      int cellY = 16 + (row * 61);
      
      String lbl = gridLabels[index];
      bool isActive = false;
      if (lbl.startsWith("*")) {
        isActive = true;
        lbl = lbl.substring(1); 
      }

      int newlineIdx = lbl.indexOf('\n');
      if (newlineIdx >= 0) {
        String l1 = lbl.substring(0, newlineIdx);
        String l2 = lbl.substring(newlineIdx + 1);
        if (l1.length() > 6) l1 = l1.substring(0, 5) + ".";
        display.setFont(&FreeSansBold9pt7b);
        display.setTextSize(1);
        display.setCursor(cellX + 4, cellY + 28);
        display.print(l1);
        display.setFont();
        display.setTextSize(1);
        display.setCursor(cellX + 6, cellY + 44);
        display.print(l2);
      } else {
        display.setFont(&FreeSansBold9pt7b);
        display.setTextSize(1);
        int textX = cellX + 4; 
        int textY = cellY + 45; 
        display.setCursor(textX, textY);
        if (lbl.length() > 6) lbl = lbl.substring(0, 5) + ".";
        display.print(lbl);
      }
      
      if (isActive) {
        int sx = cellX + 46; 
        int sy = cellY + 8;  
        display.fillRect(sx, sy + 3, 3, 4, GxEPD_BLACK);
        display.fillTriangle(sx + 2, sy + 5, sx + 7, sy, sx + 7, sy + 10, GxEPD_BLACK);
        display.drawFastVLine(sx + 10, sy + 2, 6, GxEPD_BLACK);
        display.drawFastVLine(sx + 13, sy, 10, GxEPD_BLACK);
      }
      index++;
    }
  }
}

void drawHud() {
  // 1. Header Banner
  display.fillRect(0, 0, 200, 22, GxEPD_BLACK);
  display.setFont(&FreeSansBold9pt7b);
  display.setTextColor(GxEPD_WHITE);
  display.setCursor(18, 16);
  display.print("STATUS HUD");

  // 2. Telemetry items
  display.setFont();
  display.setTextSize(1);
  display.setTextColor(GxEPD_BLACK);

  float volts = readBatteryVoltage();
  bool usbPwr = (volts >= USB_DETECT_THRESHOLD);
  bool isCharging = (!usbPwr && volts >= 4.00f);
  float effVolts = isCharging ? max(3.30f, volts - 0.24f) : volts;
  int battPct = getLipoPercentage(effVolts);
  int minsLeft = isCharging ? calculateTimeToFull(battPct) : 0;

  int y = 28;
  // Battery line 1: Voltage and State
  display.setCursor(8, y);
  display.print("POWER : ");
  if (usbPwr) {
    display.print("USB 5V DIRECT ("); display.print(volts, 2); display.print("V)");
  } else if (isCharging) {
    display.print(volts, 2); display.print("V ["); display.print(battPct); display.print("%] CHARGING");
  } else {
    display.print(volts, 2); display.print("V ["); display.print(battPct); display.print("%] BATTERY");
  }

  // Battery bar graph
  y += 10;
  display.drawRect(8, y, 184, 7, GxEPD_BLACK);
  int fillW = usbPwr ? 180 : (int)(180.0f * (battPct / 100.0f));
  if (fillW > 0) display.fillRect(10, y + 2, fillW, 3, GxEPD_BLACK);

  // Time remaining line
  y += 11;
  display.setCursor(8, y);
  if (usbPwr) {
    display.print("RATE  : Continuous USB Power");
  } else if (isCharging) {
    int h = minsLeft / 60;
    int m = minsLeft % 60;
    display.print("FULLIN: ~");
    if (h > 0) { display.print(h); display.print("h "); }
    display.print(m); display.print("m (1A TP4056)");
  } else {
    // Estimating runtime on 4000mAh battery assuming ~35mA avg active/sleep mix
    int runHours = (int)(((float)BATTERY_CAPACITY_MAH * (battPct / 100.0f)) / 35.0f);
    display.print("EST.RT: ~"); display.print(runHours); display.print("h remaining (@35mA)");
  }

  // Network & RSSI
  y += 12;
  display.setCursor(8, y);
  display.print("WIFI  : ");
  if (WiFi.status() == WL_CONNECTED) {
    display.print("CONNECTED ("); display.print(WiFi.RSSI()); display.print(" dBm)");
  } else {
    display.print("DISCONNECTED");
  }

  // MQTT
  y += 11;
  display.setCursor(8, y);
  display.print("MQTT  : ");
  if (mqttClient.connected()) {
    display.print("ONLINE (192.168.1.62)");
  } else {
    display.print("DISCONNECTED");
  }

  // Active Profile / Bank / Layer
  y += 11;
  display.setCursor(8, y);
  display.print("LAYER : Bank "); display.print(currentBank + 1);
  display.print(" | Slot "); display.print(currentSlot + 1);
  display.print(" (L"); display.print(currentLayer); display.print(")");

  // Uptime & Heap
  y += 11;
  unsigned long s = millis() / 1000;
  unsigned long m = s / 60;
  unsigned long h = m / 60;
  display.setCursor(8, y);
  display.print("UPTIME: ");
  if (h > 0) { display.print(h); display.print("h "); }
  display.print(m % 60); display.print("m ");
  display.print(s % 60); display.print("s");
  display.print(" | Heap "); display.print(ESP.getFreeHeap() / 1024); display.print("KB");

  // Discord Mic State
  y += 11;
  display.setCursor(8, y);
  display.print("MIC   : ");
  display.print(isMicMuted ? "[MUTED]" : "[LIVE]");
  if (isAudioModifierHeld) display.print(" | AUD MOD");

  // Quick Help
  y += 13;
  display.drawFastHLine(0, y, 200, GxEPD_BLACK);
  y += 5;
  display.setCursor(8, y);
  display.print("AudMod+7: Logitech G321");
  y += 9;
  display.setCursor(8, y);
  display.print("AudMod+8: Edifier Speakers");

  // Bottom prompt
  display.fillRect(0, 184, 200, 16, GxEPD_BLACK);
  display.setTextColor(GxEPD_WHITE);
  display.setCursor(20, 188);
  display.print("[KEY 9] Exit HUD Peek");
}

void toggleHud() {
  isHudActive = !isHudActive;
  lastActivityTime = millis();
  if (isHudActive) {
    hudAutoDismissTime = millis() + 10000;
    setKeyLED(9, strip.Color(0, 240, 255), 10000);
    addDeviceLog("SYS", "HUD", "Opened Status HUD");
  } else {
    hudAutoDismissTime = 0;
    setKeyLED(9, strip.Color(0, 0, 0), 1);
    addDeviceLog("SYS", "HUD", "Closed Status HUD");
  }
  requestScreenUpdate(false, 50);
}

void updateScreen() {
  if (isScreenBlackTestActive) {
    display.fillScreen(GxEPD_BLACK);
  } else {
    display.fillScreen(GxEPD_WHITE);
    if (isHudActive) {
      drawHud();
    } else {
      drawTopBar();
      drawGrid();

      if (screenMessage != "") {
        display.fillRect(10, 68, 180, 62, GxEPD_WHITE);
        display.drawRect(10, 68, 180, 62, GxEPD_BLACK);
        display.setFont(&FreeSansBold9pt7b);
        display.setTextColor(GxEPD_BLACK);
        int newlineIdx = screenMessage.indexOf('\n');
        if (newlineIdx >= 0) {
          String line1 = screenMessage.substring(0, newlineIdx);
          String line2 = screenMessage.substring(newlineIdx + 1);
          display.setCursor(20, 93);
          display.print(line1);
          display.setCursor(20, 118);
          display.print(line2);
        } else {
          int cursorX = (screenMessage.length() < 10) ? 40 : 25;
          display.setCursor(cursorX, 105);
          display.print(screenMessage);
        }
      }
    }
  }
  display.display(!fullRefreshNeeded);
  fullRefreshNeeded = false;

  // Actual screen update completed: light up display LEDs (16 & 17) and start 6s dimming
  isScreenFadeActive = true;
  screenUpdateFadeStart = millis();
  strip.setPixelColor(16, strip.Color(255, 255, 255));
  strip.setPixelColor(17, strip.Color(255, 255, 255));
  strip.show();
}

// ==========================================
// OTA SETUP FUNCTION
// ==========================================
void setupOTA() {
  ArduinoOTA.setHostname("C3-MacroPad");

  ArduinoOTA.onStart([]() {
    screenMessage = "OTA UPDATE";
    screenNeedsUpdate = true;
    updateScreen();
    strip.clear();
    strip.show();
  });

  ArduinoOTA.onEnd([]() {
    for(int i = 0; i < NUMPIXELS; i++) strip.setPixelColor(i, strip.Color(0, 255, 0));
    strip.show();
    delay(1000);
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    int percent = (progress / (total / 100));
    int ledCount = (percent * 16) / 100; 

    for(int i = 0; i < 16; i++) {
      if (i < ledCount) strip.setPixelColor(keyToLedMap[i+1], strip.Color(0, 0, 255)); 
    }
    strip.show();
    lastActivityTime = millis(); 
  });

  ArduinoOTA.begin();
}

// ==========================================
// SLEEP & MQTT FUNCTIONS
// ==========================================
void enterDeepSleep(bool isLowBattery) {
  rtcBank = currentBank;
  rtcSlot = currentSlot;
  rtcLayer = currentLayer;
  rtcWasDeepSleep = true;

  if (webServerStarted) {
    server.stop();
    webServerStarted = false;
  }

  if (isLowBattery) {
    addDeviceLog("SYS", "PWR", "Low battery deep sleep cutoff...");
    screenMessage = "! LOW BATT SLEEP !";
    screenMessageDismissTime = 0;
    fullRefreshNeeded = true;
    updateScreen();
  } else {
    addDeviceLog("SYS", "SLEEP", "Entering idle deep sleep (display preserved)...");
  }

  // Gracefully power down display controller and LEDs
  display.powerOff();
  strip.clear();
  strip.show();

  if (mqttClient.connected()) {
    float vbat = readBatteryVoltage();
    String sleepMsg = "{\"device\":\"macropad\",\"state\":\"deep_sleeping\",\"reason\":\"" + String(isLowBattery ? "low_battery" : "idle_timeout") + "\",\"vbat\":" + String(vbat, 2) + "}";
    mqttClient.publish(mqtt_topic_status, sleepMsg.c_str());
    mqttClient.loop();
    delay(20);
    mqttClient.disconnect();
  }
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);

  // Arm PCF8574 expanders and clear interrupt line
  setMatrixIdle();
  esp_deep_sleep_enable_gpio_wakeup(1ULL << MATRIX_INT, ESP_GPIO_WAKEUP_GPIO_LOW);
  esp_deep_sleep_start();
}

void handlePowerManagement() {
  if (stayAwakeMode) {
    return; // Stay awake mode active: do not sleep
  }
  static unsigned long lastBattCheck = 0;
  static float cachedVolts = 3.8f;
  unsigned long now = millis();
  if (now - lastBattCheck >= 5000 || lastBattCheck == 0) {
    lastBattCheck = now;
    cachedVolts = readBatteryVoltage();
  }
  if (cachedVolts >= USB_DETECT_THRESHOLD) {
    return; // External USB power: do not sleep
  }
  if (now - lastActivityTime > SLEEP_TIMEOUT) {
    if (cachedVolts <= LOW_BATTERY_THRESHOLD) {
      enterDeepSleep(true); // Cutoff with ! LOW BATT SLEEP ! banner
    } else {
      enterDeepSleep(false); // Idle sleep: retains existing macro grid image at 0.0uA
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) message += (char)payload[i];
  
  JsonDocument doc;
  if (deserializeJson(doc, message)) return;

  if (doc.containsKey("in_call")) {
    inVoiceCall = doc["in_call"].as<bool>();
  }
  if (doc["labels"].is<JsonArray>()) {
    JsonArray newLabels = doc["labels"].as<JsonArray>();
    for (size_t i = 0; i < 9 && i < newLabels.size(); i++) gridLabels[i] = newLabels[i].as<String>();
    if (millis() >= screenMessageDismissTime) {
      screenMessage = ""; 
    }
    bool fast = doc.containsKey("fast") && doc["fast"].as<bool>();
    if (fast || inVoiceCall) {
      requestScreenUpdate(false, 50); // Fast partial refresh for dynamic voice call & modifier transitions
    } else {
      requestScreenUpdate(true, 50); // New labels -> full refresh to eliminate ghosting
    }
  }
  if (doc.containsKey("popup")) {
    screenMessage = doc["popup"].as<String>();
    screenMessageDismissTime = millis() + POPUP_TIMEOUT_MS;
    requestScreenUpdate(false, 50); // Popups use partial refresh
  }
  if (doc.containsKey("bank")) {
    int b = doc["bank"].as<int>() - 1;
    if (b >= 0 && b < MAX_BANKS) {
      currentBank = b;
      currentLayer = (currentBank * 4) + currentSlot + 1;
      updateLayerLEDs(true);
      requestScreenUpdate(false, 300); // Partial refresh after rapid bank switching stops
    }
  }
  if (doc.containsKey("layer")) {
    int l = doc["layer"].as<int>();
    if (l >= 1 && l <= MAX_BANKS * 4) {
      currentBank = (l - 1) / 4;
      currentSlot = (l - 1) % 4;
      currentLayer = l;
      updateLayerLEDs(true);
      requestScreenUpdate(false, 300); // Partial refresh after rapid layer switching stops
    }
  }
  if (doc.containsKey("mic_muted")) {
    isMicMuted = doc["mic_muted"].as<bool>();
    int px = keyToLedMap[13];
    strip.setPixelColor(px, isMicMuted ? strip.Color(255, 0, 0) : strip.Color(0, 0, 0));
    strip.show();
  }
}

const char* getResetReasonString(esp_reset_reason_t reason) {
  switch (reason) {
    case ESP_RST_POWERON:   return "Power-On Reset";
    case ESP_RST_EXT:       return "External Pin Reset";
    case ESP_RST_SW:        return "Software Reset";
    case ESP_RST_PANIC:     return "Software Panic / Crash";
    case ESP_RST_INT_WDT:   return "Interrupt Watchdog Timeout";
    case ESP_RST_TASK_WDT:  return "Task Watchdog Timeout";
    case ESP_RST_WDT:       return "Other Watchdog Reset";
    case ESP_RST_DEEPSLEEP: return "Deep Sleep Wakeup";
    case ESP_RST_BROWNOUT:  return "BROWNOUT RESET (Voltage Sag)";
    case ESP_RST_SDIO:      return "SDIO Reset";
    default:                return "Unknown Reset";
  }
}

void sendHeartbeat() {
  if (!mqttClient.connected()) return;
  float vbat = readBatteryVoltage();
  bool usbPwr = (vbat >= USB_DETECT_THRESHOLD);
  bool isCharging = (!usbPwr && vbat >= 4.00f);
  float effVolts = isCharging ? max(3.30f, vbat - 0.24f) : vbat;
  int battPct = getLipoPercentage(effVolts);
  int minsToFull = isCharging ? calculateTimeToFull(battPct) : 0;
  int rssi = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
  uint32_t freeHeap = ESP.getFreeHeap();
  uint32_t minHeap = ESP.getMinFreeHeap();
  
  String payload = "{\"device\":\"macropad\",\"state\":\"online\",\"vbat\":" + String(vbat, 2) + 
                   ",\"batt_pct\":" + String(battPct) +
                   ",\"charging\":" + (isCharging ? "true" : "false") +
                   ",\"mins_to_full\":" + String(minsToFull) +
                   ",\"rssi\":" + String(rssi) + 
                   ",\"heap\":" + String(freeHeap) + 
                   ",\"min_heap\":" + String(minHeap) + 
                   ",\"uptime\":" + String(millis()) + 
                   ",\"bank\":" + String(currentBank + 1) + 
                   ",\"slot\":" + String(currentSlot + 1) + 
                   ",\"layer\":" + String(currentLayer) + 
                   ",\"reset_reason\":\"" + String(getResetReasonString(esp_reset_reason())) + "\"" +
                   ",\"modifier\":" + (isModifierHeld ? "true" : "false") + "}";
  mqttClient.publish(mqtt_topic_status, payload.c_str());
}

void sendDebugLog(const char* level, const char* tag, const String& msg) {
  addDeviceLog(level, tag, msg.c_str());
}

void setupWebServer() {
  server.on("/", HTTP_GET, []() {
    lastActivityTime = millis();
    server.send(200, "text/html", INDEX_HTML);
  });

  server.on("/api/status", HTTP_GET, []() {
    float vbat = readBatteryVoltage();
    bool usbPwr = (vbat >= USB_DETECT_THRESHOLD);
    bool isCharging = (!usbPwr && vbat >= 4.00f);
    float effVolts = isCharging ? max(3.30f, vbat - 0.24f) : vbat;
    int battPct = getLipoPercentage(effVolts);
    int minsToFull = isCharging ? calculateTimeToFull(battPct) : 0;
    int rssi = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
    String json = "{\"device\":\"macropad\",\"vbat\":" + String(vbat, 2) + 
                  ",\"batt_pct\":" + String(battPct) +
                  ",\"charging\":" + (isCharging ? "true" : "false") +
                  ",\"mins_to_full\":" + String(minsToFull) +
                  ",\"rssi\":" + String(rssi) + 
                  ",\"heap\":" + String(ESP.getFreeHeap()) + 
                  ",\"min_heap\":" + String(ESP.getMinFreeHeap()) + 
                  ",\"uptime\":" + String(millis()) + 
                  ",\"bank\":" + String(currentBank + 1) + 
                  ",\"slot\":" + String(currentSlot + 1) + 
                  ",\"layer\":" + String(currentLayer) + 
                  ",\"modifier\":" + (isModifierHeld ? "true" : "false") + 
                  ",\"reset_reason\":\"" + String(getResetReasonString(esp_reset_reason())) + "\"" + 
                  ",\"screen_msg\":\"" + screenMessage + "\"" + 
                  ",\"stay_awake\":" + (stayAwakeMode ? "true" : "false") + "}";
    server.send(200, "application/json", json);
  });

  server.on("/api/logs", HTTP_GET, []() {
    String json = "[";
    for (int i = 0; i < logCount; i++) {
      int idx = (logHead + i) % MAX_DEVICE_LOGS;
      if (i > 0) json += ",";
      json += "{\"t\":" + String(deviceLogs[idx].t) + 
              ",\"lvl\":\"" + String(deviceLogs[idx].lvl) + "\"" + 
              ",\"tag\":\"" + String(deviceLogs[idx].tag) + "\"" + 
              ",\"msg\":\"" + String(deviceLogs[idx].msg) + "\"}";
    }
    json += "]";
    server.send(200, "application/json", json);
  });

  server.on("/api/send_popup", HTTP_POST, []() {
    if (server.hasArg("msg")) {
      screenMessage = server.arg("msg");
      screenMessageDismissTime = millis() + POPUP_TIMEOUT_MS;
      requestScreenUpdate(false, 50);
      addDeviceLog("DISP", "POPUP", screenMessage.c_str());
      server.send(200, "text/plain", "OK");
    } else {
      server.send(400, "text/plain", "Missing msg");
    }
  });

  server.on("/api/set_layer", HTTP_POST, []() {
    if (server.hasArg("bank")) {
      int b = server.arg("bank").toInt() - 1;
      if (b >= 0 && b < MAX_BANKS) {
        currentBank = b;
        currentLayer = (currentBank * 4) + currentSlot + 1;
        updateLayerLEDs(true);
        requestScreenUpdate(false, 300);
        addDeviceLog("SYS", "LAYER", ("Bank changed to " + String(b + 1)).c_str());
        server.send(200, "text/plain", "OK");
        return;
      }
    }
    server.send(400, "text/plain", "Invalid bank");
  });

  server.on("/api/toggle_stay_awake", HTTP_POST, []() {
    stayAwakeMode = !stayAwakeMode;
    if (stayAwakeMode) {
      addDeviceLog("SYS", "POWER", "Stay Awake: ON (Sleep disabled)");
    } else {
      addDeviceLog("SYS", "POWER", "Stay Awake: OFF (Sleep enabled)");
    }
    server.send(200, "text/plain", stayAwakeMode ? "ON" : "OFF");
  });

  server.on("/update", HTTP_POST, []() {
    server.sendHeader("Connection", "close");
    server.send(200, "text/plain", (Update.hasError()) ? "FAIL" : "OK");
    delay(500);
    ESP.restart();
  }, []() {
    HTTPUpload& upload = server.upload();
    if (upload.status == UPLOAD_FILE_START) {
      addDeviceLog("SYS", "OTA", "Web HTTP OTA firmware upload started");
      if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
        Update.printError(Serial);
      }
    } else if (upload.status == UPLOAD_FILE_WRITE) {
      if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
        Update.printError(Serial);
      }
    } else if (upload.status == UPLOAD_FILE_END) {
      if (Update.end(true)) {
        addDeviceLog("SYS", "OTA", "Web HTTP OTA successful! Rebooting...");
      }
    }
  });

  server.on("/api/reboot", HTTP_POST, []() {
    server.send(200, "text/plain", "Rebooting...");
    delay(500);
    ESP.restart();
  });

  server.on("/api/test_deep_sleep", HTTP_POST, []() {
    server.send(200, "text/plain", "Entering deep sleep...");
    delay(500);
    enterDeepSleep(false);
  });

  server.begin();
  webServerStarted = true;
  addDeviceLog("SYS", "HTTP", "On-device Web Dashboard live at port 80");
}

void setupNetwork() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false); // High-performance Wi-Fi while awake (zero DTIM latency spikes)
  WiFi.setTxPower(WIFI_POWER_15dBm); // Prevents battery voltage brownouts on peak RF bursts
  WiFi.begin(ssid, password);
  mqttClient.setServer(mqtt_server, 1883);
  mqttClient.setSocketTimeout(1); // 1-second timeout (prevents 15s connection hangs)
  mqttClient.setCallback(mqttCallback);
}

void handleNetwork() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!otaInitialized) {
      setupOTA();
      otaInitialized = true;
    }
    ArduinoOTA.handle();
    if (!webServerStarted) {
      setupWebServer();
    }
    server.handleClient();
  }
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    unsigned long reconnectInterval = (WiFi.status() == WL_CONNECTED) ? 1000 : 5000;
    if (now - lastReconnectAttempt > reconnectInterval) {
      lastReconnectAttempt = now;
      if (WiFi.status() == WL_CONNECTED && mqttClient.connect("C3_MacroPad")) {
        mqttClient.subscribe(mqtt_topic_sub);
        flushMqttQueue();
        if (isFirstMqttConnect) {
          isFirstMqttConnect = false;
          screenMessage = "";
          screenMessageDismissTime = 0;
          sendHeartbeat();
          sendDebugLog("INFO", "BOOT", "MacroPad boot complete. Reason: " + String(getResetReasonString(esp_reset_reason())) + ", Vbat: " + String(readBatteryVoltage(), 2) + "V");
          if (esp_reset_reason() != ESP_RST_DEEPSLEEP) {
            requestScreenUpdate(true, 50); // Initial clean screen refresh on cold power-on boot
          }
        } else {
          sendHeartbeat();
          sendDebugLog("INFO", "MQTT", "Reconnected to MQTT broker");
        }
      }
    }
  } else {
    mqttClient.loop();
    flushMqttQueue();
    unsigned long now = millis();
    if (now - lastHeartbeatTime > HEARTBEAT_INTERVAL) {
      lastHeartbeatTime = now;
      sendHeartbeat();
    }
  }
}

// Outgoing MQTT message queue to guarantee zero lost clicks during reconnect
const int MQTT_QUEUE_SIZE = 8;
String mqttQueue[MQTT_QUEUE_SIZE];
int mqttQueueHead = 0;
int mqttQueueTail = 0;
int mqttQueueCount = 0;

void queuePayload(String payload) {
  if (mqttQueueCount < MQTT_QUEUE_SIZE) {
    mqttQueue[mqttQueueTail] = payload;
    mqttQueueTail = (mqttQueueTail + 1) % MQTT_QUEUE_SIZE;
    mqttQueueCount++;
  }
}

void flushMqttQueue() {
  while (mqttQueueCount > 0 && mqttClient.connected()) {
    String p = mqttQueue[mqttQueueHead];
    mqttQueueHead = (mqttQueueHead + 1) % MQTT_QUEUE_SIZE;
    mqttQueueCount--;
    mqttClient.publish(mqtt_topic_pub, p.c_str());
    addDeviceLog("SYS", "QUEUE", "Sent buffered click");
  }
}

void sendPayload(String payload) {
  if (mqttClient.connected()) {
    mqttClient.publish(mqtt_topic_pub, payload.c_str());
  } else {
    queuePayload(payload);
    addDeviceLog("SYS", "QUEUE", "Buffered click (queued)");
  }
}

int getDynamicIndex(int keyId) {
  switch (keyId) {
    case 6:  return 1;
    case 7:  return 2;
    case 8:  return 3;
    case 10: return 4;
    case 11: return 5;
    case 12: return 6;
    case 14: return 7;
    case 15: return 8;
    case 16: return 9;
    default: return 0;
  }
}

void updateLayerLEDs(bool doShow) {
  if (isRainbowSwirl) return;
  BankColor bc = bankColors[currentBank];
  for (int i = 0; i < 4; i++) {
    int px = keyToLedMap[topRowKeyIDs[i]];
    if (i == currentSlot) {
      strip.setPixelColor(px, strip.Color(bc.r, bc.g, bc.b));
    } else {
      strip.setPixelColor(px, strip.Color(bc.r / 16, bc.g / 16, bc.b / 16));
    }
  }
  if (isHudActive) {
    strip.setPixelColor(keyToLedMap[9], strip.Color(0, 240, 255));
  }
  if (doShow) strip.show();
}

void selectLayerSlot(int slot) {
  if (isScreenBlackTestActive) {
    isScreenBlackTestActive = false;
    fullRefreshNeeded = true;
  }
  currentSlot = slot;
  currentLayer = (currentBank * 4) + currentSlot + 1;
  rtcBank = currentBank;
  rtcSlot = currentSlot;
  rtcLayer = currentLayer;
  updateLayerLEDs(true);
  screenMessage = "LAYER " + String(currentLayer);
  screenMessageDismissTime = millis() + POPUP_TIMEOUT_MS;
  requestScreenUpdate(false, 300); // Fast partial refresh, debounced so multiple rapid presses don't block
  sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"bank\":" + String(currentBank + 1) + ", \"slot\":" + String(currentSlot + 1) + ", \"action\":\"layer_change\"}");
  addDeviceLog("INP", "SLOT", ("Selected Slot " + String(slot + 1) + " (Layer " + String(currentLayer) + ")").c_str());
}

void cycleBank() {
  if (isScreenBlackTestActive) {
    isScreenBlackTestActive = false;
    fullRefreshNeeded = true;
  }
  currentBank = (currentBank + 1) % MAX_BANKS;
  currentLayer = (currentBank * 4) + currentSlot + 1;
  rtcBank = currentBank;
  rtcSlot = currentSlot;
  rtcLayer = currentLayer;
  updateLayerLEDs(true);
  screenMessage = "BANK " + String(currentBank + 1) + " L" + String(currentLayer);
  screenMessageDismissTime = millis() + POPUP_TIMEOUT_MS;
  requestScreenUpdate(false, 300); // Fast partial refresh, debounced so rapid encoder clicks cycle instantly without lag
  sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"bank\":" + String(currentBank + 1) + ", \"slot\":" + String(currentSlot + 1) + ", \"action\":\"encoder_click\", \"id\":3, \"modifier\":" + (isModifierHeld ? "true" : "false") + "}");
  addDeviceLog("SYS", "BANK", ("Bank cycled to " + String(currentBank + 1)).c_str());
}

void resetToB1L1() {
  if (isScreenBlackTestActive) {
    isScreenBlackTestActive = false;
    fullRefreshNeeded = true;
  }
  currentBank = 0;
  currentSlot = 0;
  currentLayer = 1;
  rtcBank = 0;
  rtcSlot = 0;
  rtcLayer = 1;
  updateLayerLEDs(true);
  screenMessage = "HOME: B1 L1";
  screenMessageDismissTime = millis() + POPUP_TIMEOUT_MS;
  requestScreenUpdate(false, 100);
  sendPayload("{\"device\":\"macropad\", \"layer\":1, \"bank\":1, \"slot\":1, \"action\":\"layer_reset\"}");
  addDeviceLog("SYS", "LAYER", "Quick Return: B1L1 (Enc2 Long Press)");
  setKeyLED(1, strip.Color(0, 255, 100), 300);
}

// ==========================================
// BOOT & WAKE ANIMATIONS (NON-BLOCKING)
// ==========================================
void startBootAnimation() {
  currentAnimation = ANIM_BOOT;
  animStartTime = millis();
}

void startWakeAnimation() {
  currentAnimation = ANIM_WAKE;
  animStartTime = millis();
}

void handleAnimations(unsigned long now) {
  if (currentAnimation == ANIM_NONE) return;

  unsigned long elapsed = now - animStartTime;

  if (currentAnimation == ANIM_BOOT) {
    // 7 diagonal steps + 2 fade steps across 4x4 matrix (~320ms total)
    const int stepDuration = 35;
    int step = elapsed / stepDuration;

    if (step >= 9) {
      currentAnimation = ANIM_NONE;
      strip.clear();
      updateLayerLEDs(true);
      refreshDisplayLeds();
      return;
    }

    const int diagCount[7] = {1, 2, 3, 4, 3, 2, 1};
    const int diagLeds[7][4] = {
      {12},
      {13, 11},
      {14, 10, 4},
      {15, 9, 5, 3},
      {8, 6, 2},
      {7, 1},
      {0}
    };

    strip.clear();
    for (int d = 0; d < 7; d++) {
      if (d <= step && step - d < 3) {
        uint8_t bright = 255 >> (step - d);
        for (int i = 0; i < diagCount[d]; i++) {
          strip.setPixelColor(diagLeds[d][i], strip.Color(0, bright, bright)); // Cyan diagonal sweep
        }
      }
    }
    // Briefly flash display LEDs during mid-sweep
    if (step >= 2 && step <= 5) {
      strip.setPixelColor(16, strip.Color(0, 150, 150));
      strip.setPixelColor(17, strip.Color(0, 150, 150));
    }
    strip.show();
  }
  else if (currentAnimation == ANIM_WAKE) {
    // Radial expand: Center 4 keys -> Outer 12 keys (~220ms total)
    const int wakeDuration = 220;
    if (elapsed >= wakeDuration) {
      currentAnimation = ANIM_NONE;
      strip.clear();
      updateLayerLEDs(true);
      refreshDisplayLeds();
      return;
    }

    const int centerLeds[4] = {10, 9, 5, 6};
    const int outerLeds[12] = {12, 13, 14, 15, 11, 8, 4, 7, 3, 2, 1, 0};

    strip.clear();
    if (elapsed < 80) {
      // Phase 1: Center 4 keys burst bright white/cyan
      uint8_t b = (uint8_t)(255 * (1.0f - (float)elapsed / 80.0f));
      for (int i = 0; i < 4; i++) strip.setPixelColor(centerLeds[i], strip.Color(b, b, b));
    } else {
      // Phase 2: Ring ripple outward in active bank color
      float p = (float)(elapsed - 80) / 140.0f;
      uint8_t b = (uint8_t)(220 * (1.0f - p));
      BankColor bc = bankColors[currentBank];
      for (int i = 0; i < 12; i++) {
        strip.setPixelColor(outerLeds[i], strip.Color((bc.r * b) / 255, (bc.g * b) / 255, (bc.b * b) / 255));
      }
    }
    strip.show();
  }
}

// ==========================================
// MAIN SETUP
// ==========================================
void setup() {
  Serial.begin(115200);

  bool wokeFromDeepSleep = (esp_reset_reason() == ESP_RST_DEEPSLEEP) && rtcWasDeepSleep;

  if (wokeFromDeepSleep) {
    currentBank = rtcBank;
    currentSlot = rtcSlot;
    currentLayer = rtcLayer;
    isFirstMqttConnect = false;
    screenNeedsUpdate = false;
    screenMessage = "";
    screenMessageDismissTime = 0;
    addDeviceLog("SYS", "WAKE", ("Woke from Deep Sleep. Restored B" + String(currentBank + 1) + " L" + String(currentLayer)).c_str());
  } else {
    rtcBank = 0;
    rtcSlot = 0;
    rtcLayer = 1;
    rtcWasDeepSleep = false;
    screenMessage = "BOOTING...";
    screenMessageDismissTime = millis() + 4000;
    addDeviceLog("SYS", "BOOT", ("System Boot: " + String(getResetReasonString(esp_reset_reason()))).c_str());
  }

  pinMode(BATTERY_PIN, INPUT);
  analogSetAttenuation(ADC_11db); 

  strip.begin();
  strip.setBrightness(100); 
  strip.clear();
  strip.show(); 
  if (wokeFromDeepSleep) {
    startWakeAnimation();
  } else {
    startBootAnimation();
  }

  SPI.begin(EPD_SCL, -1, EPD_SDA, EPD_CS);
  display.init(115200, true, 2, false); 
  display.setRotation(2); 
  display.setTextColor(GxEPD_BLACK);
  pinMode(EPD_BUSY, INPUT);

  setupNetwork(); 

  pinMode(ENCODER_CLK, INPUT_PULLUP);
  pinMode(ENCODER_DT, INPUT_PULLUP);
  pinMode(ENCODER_SW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCODER_CLK), encoder1ISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCODER_DT),  encoder1ISR, CHANGE);

  pinMode(MATRIX_SDA, INPUT_PULLUP);
  pinMode(MATRIX_SCL, INPUT_PULLUP);
  recoverI2CBus();
  Wire.begin(MATRIX_SDA, MATRIX_SCL);
  Wire.setClock(100000); 
  Wire.setTimeOut(20); 
  
  pinMode(MATRIX_INT, INPUT_PULLUP);
  
  Wire.beginTransmission(PCF_ENCODERS);
  Wire.write(0xFF); 
  Wire.endTransmission();
  Wire.requestFrom(PCF_ENCODERS, 1);
  if (Wire.available()) lastI2cEncState = Wire.read();

  setMatrixIdle();
  updateLayerLEDs(true);
  lastActivityTime = millis();
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
  handleNetwork(); 
  handlePowerManagement();

  unsigned long now = millis();
  
  // --- NON-BLOCKING LED ANIMATION HANDLERS ---
  if (currentAnimation != ANIM_NONE) {
    handleAnimations(now);
  } else if (isRainbowSwirl) {
    if (now - swirlStartTime > 2500) {
      isRainbowSwirl = false;
      strip.clear();
      refreshDisplayLeds(); 
      updateLayerLEDs(false);
      strip.show();
    } else {
      for(int i = 0; i < 16; i++) {
        int px = keyToLedMap[i+1];
        strip.setPixelColor(px, strip.ColorHSV(swirlHue + (i * 65536 / 16), 255, 255));
      }
      strip.show();
      swirlHue += 3000; 
    }
  } else {
    bool ledsChanged = false;
    for(int i = 0; i < 16; i++) {
      if(ledTurnOffTime[i] > 0 && now > ledTurnOffTime[i]) {
        ledTurnOffTime[i] = 0;
        ledsChanged = true;

        bool isTopRow = false;
        for (int k = 0; k < 4; k++) {
          if (keyToLedMap[topRowKeyIDs[k]] == i) {
            isTopRow = true;
            break;
          }
        }
        if (!isTopRow) {
          if (keyToLedMap[5] == i && isModifierHeld) {
            strip.setPixelColor(i, strip.Color(0, 200, 255));
          } else if (keyToLedMap[9] == i && isHudActive) {
            strip.setPixelColor(i, strip.Color(0, 240, 255));
          } else if (keyToLedMap[13] == i) {
            if (isAudioModifierHeld) {
              strip.setPixelColor(i, strip.Color(180, 0, 255));
            } else if (isMicMuted) {
              strip.setPixelColor(i, strip.Color(255, 0, 0));
            } else {
              strip.setPixelColor(i, strip.Color(0, 0, 0));
            }
          } else {
            strip.setPixelColor(i, strip.Color(0, 0, 0));
          }
        }
      }
    }
    if(ledsChanged) {
      updateLayerLEDs(false);
      strip.show();
    }
  }

  // --- NON-BLOCKING SCREEN UPDATE FADE (LED 16 & 17) ---
  static unsigned long lastFadeStep = 0;
  if (isScreenFadeActive && (now - lastFadeStep >= 25)) {
    lastFadeStep = now;
    unsigned long elapsed = now - screenUpdateFadeStart;
    if (elapsed >= SCREEN_FADE_DURATION) {
      isScreenFadeActive = false;
      uint8_t finalB = displayLedsActive ? 255 : 0;
      strip.setPixelColor(16, strip.Color(finalB, finalB, finalB));
      strip.setPixelColor(17, strip.Color(finalB, finalB, finalB));
      strip.show();
    } else {
      float factor = 1.0f - ((float)elapsed / (float)SCREEN_FADE_DURATION);
      // Quadratic decay for a smooth, natural dimming effect
      uint8_t b = (uint8_t)(255.0f * factor * factor);
      strip.setPixelColor(16, strip.Color(b, b, b));
      strip.setPixelColor(17, strip.Color(b, b, b));
      strip.show();
    }
  }

  // 1. HARDWARE ENCODER (ID: 1) WITH ACCELERATION & COALESCING
  static unsigned long lastEnc1StepTime = 0;
  static unsigned long lastEnc1SendTime = 0;
  static int enc1PendingDelta = 0;

  int steps = 0;
  noInterrupts();
  if (enc1_raw_steps != 0) {
    steps = enc1_raw_steps;
    enc1_raw_steps = 0;
  }
  interrupts();

  if (steps != 0) {
    lastActivityTime = now;
    unsigned long timeSinceLast = now - lastEnc1StepTime;
    lastEnc1StepTime = now;

    // Dynamic Acceleration:
    // Slow turning (>80ms): 1x (fine control)
    // Moderate turning (40-80ms): 2x
    // Fast turning (20-40ms): 4x
    // Rapid flick (<20ms): 7x
    int mult = 1;
    if (timeSinceLast < 20) {
      mult = 7;
    } else if (timeSinceLast < 40) {
      mult = 4;
    } else if (timeSinceLast < 80) {
      mult = 2;
    }

    enc1PendingDelta += steps * mult;
  }

  // Rate-limited emission: stream at most once every 50ms, or immediately after 25ms pause
  if (enc1PendingDelta != 0) {
    bool intervalPassed = (now - lastEnc1SendTime >= 50);
    bool motionPaused = (now - lastEnc1StepTime >= 25);
    if (intervalPassed || motionPaused) {
      int sendVal = enc1PendingDelta;
      enc1PendingDelta = 0;
      lastEnc1SendTime = now;
      if (isAudioModifierHeld) {
        isAudioModifierUsed = true;
        int heldUser = getHeld3x3UserKey();
        if (heldUser > 0 && inVoiceCall) {
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"discord_user_volume\", \"user_index\":" + String(heldUser) + ", \"delta\":" + String(sendVal) + "}");
          addDeviceLog("INP", "CALL", ("User #" + String(heldUser) + " Vol: " + String(sendVal)).c_str());
        } else {
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"audio_master_volume\", \"id\":1, \"delta\":" + String(sendVal) + "}");
          addDeviceLog("INP", "AUDIO", ("Master Vol: " + String(sendVal)).c_str());
        }
      } else {
        sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"encoder_scroll\", \"id\":1, \"delta\":" + String(sendVal) + ", \"modifier\":" + (isModifierHeld ? "true" : "false") + "}");
      }
    }
  }

  static unsigned long lastEnc1ClickTime = 0;
  if (digitalRead(ENCODER_SW) == LOW) {
    if (now - lastEnc1ClickTime > 250) {
      lastEnc1ClickTime = now;
      lastActivityTime = now; 
      if (isAudioModifierHeld) {
        isAudioModifierUsed = true;
        sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"audio_master_reset\", \"id\":1, \"volume\":80}");
        addDeviceLog("INP", "AUDIO", "Master Vol Reset 80%");
      } else {
        if (!isModifierHeld) {
          toggleDisplayLeds(); 
        }
        sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"encoder_click\", \"id\":1, \"modifier\":" + (isModifierHeld ? "true" : "false") + "}");
      }
    }
  }

  // ==========================================
  // 2. THE FAST LANE: I2C ENCODERS
  // ==========================================
  if (now - lastI2cEncScan > 4) {
    lastI2cEncScan = now;
    Wire.requestFrom(PCF_ENCODERS, 1);
    if (Wire.available()) {
      byte encData = Wire.read();
      
      bool e2Clk = (encData & 0x01) != 0; 
      bool e2Dt  = (encData & 0x02) != 0; 
      bool e2Sw  = (encData & 0x04) == 0; 

      bool e3Clk = (encData & 0x08) != 0; 
      bool e3Dt  = (encData & 0x10) != 0; 
      bool e3Sw  = (encData & 0x20) == 0; 

      bool last_e2Clk = (lastI2cEncState & 0x01) != 0;
      bool last_e3Clk = (lastI2cEncState & 0x08) != 0;

      // Encoder 1 (Bottom Left: Discord Volume / Reset 80%)
      if (last_e2Clk == HIGH && e2Clk == LOW) {
        if (now - lastEnc2Trigger > ENC_DEBOUNCE) { 
          int delta = (e2Dt == HIGH) ? 1 : -1;
          if (isAudioModifierHeld) {
            isAudioModifierUsed = true;
            int heldUser = getHeld3x3UserKey();
            if (heldUser > 0 && inVoiceCall) {
              sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"discord_user_volume\", \"user_index\":" + String(heldUser) + ", \"delta\":" + String(delta) + "}");
              addDeviceLog("INP", "CALL", ("User #" + String(heldUser) + " Vol: " + String(delta)).c_str());
            } else {
              sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"audio_discord_volume\", \"id\":2, \"delta\":" + String(delta) + "}");
              addDeviceLog("INP", "AUDIO", ("Discord Vol: " + String(delta)).c_str());
            }
          } else {
            sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"encoder_scroll\", \"id\":2, \"delta\":" + String(delta) + ", \"modifier\":" + (isModifierHeld ? "true" : "false") + "}");
          }
          lastActivityTime = now;
          lastEnc2Trigger = now;
        }
      }
      if (e2Sw && !enc2ButtonState) {
        lastActivityTime = now;
        if (isAudioModifierHeld) {
          isAudioModifierUsed = true;
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"audio_discord_reset\", \"id\":2, \"volume\":80}");
          addDeviceLog("INP", "AUDIO", "Discord Vol Reset 80%");
        } else {
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"encoder_click\", \"id\":2, \"modifier\":" + (isModifierHeld ? "true" : "false") + "}");
        }
      }
      enc2ButtonState = e2Sw;

      // Encoder 2 (Top Left: App Volume / Target Toggle & Long-Press Quick Return to B1L1)
      if (last_e3Clk == HIGH && e3Clk == LOW) {
        if (now - lastEnc3Trigger > ENC_DEBOUNCE) { 
          int delta = (e3Dt == HIGH) ? 1 : -1;
          if (isAudioModifierHeld) {
            isAudioModifierUsed = true;
            int heldUser = getHeld3x3UserKey();
            if (heldUser > 0 && inVoiceCall) {
              sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"discord_user_volume\", \"user_index\":" + String(heldUser) + ", \"delta\":" + String(delta) + "}");
              addDeviceLog("INP", "CALL", ("User #" + String(heldUser) + " Vol: " + String(delta)).c_str());
            } else {
              sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"audio_app_volume\", \"id\":3, \"delta\":" + String(delta) + "}");
              addDeviceLog("INP", "AUDIO", ("App Vol: " + String(delta)).c_str());
            }
          } else {
            sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"encoder_scroll\", \"id\":3, \"delta\":" + String(delta) + ", \"modifier\":" + (isModifierHeld ? "true" : "false") + "}");
          }
          lastActivityTime = now;
          lastEnc3Trigger = now;
        }
      }
      if (e3Sw && !enc3ButtonState) {
        // Just pressed down
        enc3PressTime = now;
        enc3LongTriggered = false;
        lastActivityTime = now;
      } else if (e3Sw && enc3ButtonState) {
        // Still held down -> check for long-press threshold
        if (!enc3LongTriggered && (now - enc3PressTime >= ENC_LONG_PRESS_MS)) {
          enc3LongTriggered = true;
          lastActivityTime = now;
          resetToB1L1();
        }
      } else if (!e3Sw && enc3ButtonState) {
        // Just released
        lastActivityTime = now;
        if (!enc3LongTriggered) {
          // Short tap (< 500ms)
          if (isAudioModifierHeld) {
            isAudioModifierUsed = true;
            sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"audio_app_toggle\", \"id\":3}");
            addDeviceLog("INP", "AUDIO", "App Target Toggle");
          } else if (isModifierHeld) {
            sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"encoder_click\", \"id\":3, \"modifier\":true}");
          } else {
            cycleBank();
          }
        }
        enc3PressTime = 0;
        enc3LongTriggered = false;
      }
      enc3ButtonState = e3Sw;

      lastI2cEncState = encData;
    }
  }

  // ==========================================
  // 3. THE SLOW LANE: I2C KEY MATRIX
  // ==========================================
  bool intLow = (digitalRead(MATRIX_INT) == LOW);
  bool scanDue = (now - lastMatrixScan > 20);
  bool periodicSweep = (now - lastMatrixScan > 60); // 60ms fallback sweep guarantees keys are never missed

  if ((intLow || isPollingMatrix || periodicSweep) && scanDue) {
    lastMatrixScan = now;

    memset(currentScanState, 0, sizeof(currentScanState));
    int totalActiveKeys = 0;
    
    for (int row = 0; row < 4; row++) {
      Wire.beginTransmission(PCF_MATRIX);
      Wire.write(~(1 << row));
      Wire.endTransmission();
      Wire.requestFrom(PCF_MATRIX, 1);
      
      if (Wire.available()) {
        byte readData = Wire.read();
        for (int col = 0; col < 4; col++) {
          int mappedCol = 3 - col; 
          int id = keyIDs[row][mappedCol];
          if ((readData & (1 << (col + 4))) == 0) {
            currentScanState[id] = true;
            totalActiveKeys++;
            
            if (!lastState[id]) {
              lastActivityTime = now; 
              
              // Top Row: Quick Layer Select 1-4
              if (id == 1) selectLayerSlot(0);
              else if (id == 2) selectLayerSlot(1);
              else if (id == 3) selectLayerSlot(2);
              else if (id == 4) selectLayerSlot(3);
              
              // Fixed Key 9 in Left Column -> Full Screen Status HUD Peek
              else if (id == 9) {
                toggleHud();
              }
              
              // 3x3 Dynamic Matrix Keys (Mirrors E-Ink Screen)
              else if (id != 5 && id != 13) {
                bool audioModActive = isAudioModifierHeld || currentScanState[13] || key13PhysicallyPressed;
                if (audioModActive) {
                  isAudioModifierHeld = true;
                  key13Held = true;
                  isAudioModifierUsed = true;

                  if (id == 7) {
                    sendPayload("{\"device\":\"macropad\", \"action\":\"audio_device_select\", \"target\":\"headphones\"}");
                    addDeviceLog("INP", "AUDIO", "Output -> Logitech G321");
                    setKeyLED(7, strip.Color(0, 240, 255), 400); // Bright cyan confirmation
                    screenMessage = "AUDIO:\nHEADPHONES";
                    screenMessageDismissTime = millis() + 2000;
                    requestScreenUpdate(false, 50);
                  } else if (id == 8 || id == 10) {
                    sendPayload("{\"device\":\"macropad\", \"action\":\"audio_device_select\", \"target\":\"speakers\"}");
                    addDeviceLog("INP", "AUDIO", "Output -> Edifier Speakers");
                    setKeyLED(id, strip.Color(255, 180, 0), 400); // Bright amber confirmation
                    screenMessage = "AUDIO:\nEDIFIER SPK";
                    screenMessageDismissTime = millis() + 2000;
                    requestScreenUpdate(false, 50);
                  } else if (inVoiceCall && id == 15) { // Key 15 = Cell 8 = Page Down / PREV
                    sendPayload("{\"device\":\"macropad\", \"action\":\"discord_page_down\"}");
                    setKeyLED(15, strip.Color(0, 200, 255), 150);
                    addDeviceLog("INP", "CALL", "Page Prev");
                  } else if (inVoiceCall && id == 16) { // Key 16 = Cell 9 = Page Up / NEXT
                    sendPayload("{\"device\":\"macropad\", \"action\":\"discord_page_up\"}");
                    setKeyLED(16, strip.Color(0, 200, 255), 150);
                    addDeviceLog("INP", "CALL", "Page Next");
                  } else {
                    int dynIdx = getDynamicIndex(id);
                    if (dynIdx > 0) {
                      setKeyLED(id, strip.Color(0, 255, 120), 200); // Greenish touch feedback for held user
                    }
                  }
                } else {
                  int dynIdx = getDynamicIndex(id);
                  if (dynIdx > 0) {
                    bool modActive = isModifierHeld || currentScanState[5] || key5PhysicallyPressed;
                    if (modActive) {
                      isModifierHeld = true;
                      key5Held = true;
                      dynKeyPressTime[dynIdx] = now;
                      dynKeyHeld[dynIdx] = false;
                      setKeyLED(id, strip.Color(0, 150, 255), 100); // Visual touch feedback (blue)
                    } else {
                      if (currentLayer == 1 && dynIdx == 1) {
                        isScreenBlackTestActive = !isScreenBlackTestActive;
                        requestScreenUpdate(true, 50);
                        addDeviceLog("DISP", "TEST", isScreenBlackTestActive ? "Screen Alignment: SOLID BLACK" : "Screen Alignment: NORMAL");
                        setKeyLED(id, isScreenBlackTestActive ? strip.Color(255, 0, 255) : strip.Color(0, 255, 0), 400);
                        sendPayload("{\"device\":\"macropad\", \"layer\":1, \"action\":\"macro\", \"index\":1, \"label\":\"ACT 1\", \"black_test\":" + String(isScreenBlackTestActive ? "true" : "false") + "}");
                      } else {
                        if (isScreenBlackTestActive) {
                          isScreenBlackTestActive = false;
                          requestScreenUpdate(true, 50);
                        }
                        if (screenMessage != "") {
                          screenMessage = ""; 
                          screenMessageDismissTime = 0;
                          requestScreenUpdate(false, 300);
                        }
                        String lbl = gridLabels[dynIdx - 1];
                        sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"macro\", \"index\":" + String(dynIdx) + ", \"label\":\"" + lbl + "\"}");
                        addDeviceLog("INP", "MACRO", ("Key #" + String(dynIdx) + " (" + lbl + ")").c_str());
                        setKeyLED(id, strip.Color(0, 255, 0), 100);
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }

    // Check 3x3 dynamic keys under modifier for long-press save and short-tap recall
    for (int k = 1; k <= 9; k++) {
      int keyId = dynIdxToKeyID[k];
      
      // If currently physically pressed down with modifier held
      if (currentScanState[keyId] && isModifierHeld) {
        if (!dynKeyHeld[k] && dynKeyPressTime[k] > 0 && (now - dynKeyPressTime[k] >= PRESET_LONG_PRESS_MS)) {
          dynKeyHeld[k] = true;
          // Long press reached -> SAVE PRESET
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"preset_save\", \"index\":" + String(k) + ", \"modifier\":true}");
          addDeviceLog("INP", "PRESET", ("Saved Preset #" + String(k)).c_str());
          setKeyLED(keyId, strip.Color(255, 0, 255), 400); // Bright magenta confirmation
        }
      }
      
      // If key was just released
      if (lastState[keyId] && !currentScanState[keyId]) {
        if (dynKeyPressTime[k] > 0) {
          if (!dynKeyHeld[k] && isModifierHeld) {
            // Released before long press threshold -> SHORT TAP -> RECALL PRESET
            sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"preset_recall\", \"index\":" + String(k) + ", \"modifier\":true}");
            addDeviceLog("INP", "PRESET", ("Recalled Preset #" + String(k)).c_str());
            setKeyLED(keyId, strip.Color(0, 255, 100), 200); // Cyan/green confirmation
          }
          dynKeyPressTime[k] = 0;
          dynKeyHeld[k] = false;
        }
      }
    }
    
    // Check Key 5 (Room Light / Modifier) State with 80ms Release Debounce
    if (currentScanState[5]) {
      key5LastSeenTime = now;
      if (!key5PhysicallyPressed) {
        key5PhysicallyPressed = true;
        key5PressTime = now;
        key5Held = false;
      } else if (!key5Held && (now - key5PressTime >= HOLD_MODIFIER_MS)) {
        key5Held = true;
        isModifierHeld = true;
        addDeviceLog("INP", "MOD", "Modifier held active");
        int px = keyToLedMap[5];
        strip.setPixelColor(px, strip.Color(0, 200, 255)); // Cyan indicates modifier active
        strip.show();
      }
    } else {
      // Key 5 not seen on this scan. Only declare released after 80ms of continuous absence (filters out contact chatter and I2C glitches)
      if (key5PhysicallyPressed && (now - key5LastSeenTime > 80)) {
        key5PhysicallyPressed = false;
        if (key5Held) {
          // Was held as modifier -> cleanly release
          isModifierHeld = false;
          key5Held = false;
          addDeviceLog("INP", "MOD", "Modifier released");
          int px = keyToLedMap[5];
          strip.setPixelColor(px, strip.Color(0, 0, 0));
          strip.show();
        } else {
          // Was a short tap (< HOLD_MODIFIER_MS) -> Toggle Room Light
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"light_toggle\"}");
          addDeviceLog("INP", "LIGHT", "Key 5 tap: Room Light Toggle");
          setKeyLED(5, strip.Color(255, 180, 0), 180); // Amber flash feedback
        }
      }
    }
    
    // Check Key 13 (Discord Mic Mute / Audio Modifier) State with 80ms Release Debounce
    if (currentScanState[13]) {
      key13LastSeenTime = now;
      if (!key13PhysicallyPressed) {
        key13PhysicallyPressed = true;
        key13PressTime = now;
        key13Held = false;
        isAudioModifierUsed = false;
      } else if (!key13Held && (now - key13PressTime >= HOLD_MODIFIER_MS)) {
        key13Held = true;
        isAudioModifierHeld = true;
        addDeviceLog("INP", "MOD2", "Audio Modifier held active");
        sendPayload("{\"device\":\"macropad\", \"action\":\"audio_modifier\", \"active\":true}");
        int px = keyToLedMap[13];
        strip.setPixelColor(px, strip.Color(180, 0, 255)); // Purple indicates audio modifier active
        strip.setPixelColor(keyToLedMap[7], strip.Color(0, 100, 200)); // Cyan hint: Logitech G321
        strip.setPixelColor(keyToLedMap[8], strip.Color(200, 100, 0));  // Amber hint: Edifier Speakers
        strip.show();
      }
    } else {
      // Key 13 not seen on this scan. Only declare released after 80ms of continuous absence
      if (key13PhysicallyPressed && (now - key13LastSeenTime > 80)) {
        key13PhysicallyPressed = false;
        bool wasHeldAsMod = key13Held;
        if (key13Held) {
          isAudioModifierHeld = false;
          key13Held = false;
          sendPayload("{\"device\":\"macropad\", \"action\":\"audio_modifier\", \"active\":false}");
          int px = keyToLedMap[13];
          strip.setPixelColor(px, isMicMuted ? strip.Color(255, 0, 0) : strip.Color(0, 0, 0));
          strip.setPixelColor(keyToLedMap[7], strip.Color(0, 0, 0));
          strip.setPixelColor(keyToLedMap[8], strip.Color(0, 0, 0));
          strip.setPixelColor(keyToLedMap[10], strip.Color(0, 0, 0));
          strip.show();
        }

        // Only short tap (< HOLD_MODIFIER_MS) triggers mic mute toggle
        if (!wasHeldAsMod) {
          sendPayload("{\"device\":\"macropad\", \"layer\":" + String(currentLayer) + ", \"action\":\"mic_mute_toggle\"}");
          addDeviceLog("INP", "MIC", "Toggled Mic Mute (request sent to PC)");
          setKeyLED(13, strip.Color(255, 180, 0), 120); // Amber touch feedback while waiting for PC sync
        } else {
          addDeviceLog("INP", "MOD2", "Audio Modifier released");
        }
      }
    }
    
    for (int i = 1; i <= 16; i++) lastState[i] = currentScanState[i];
    
    if (totalActiveKeys > 0 || key5PhysicallyPressed || key13PhysicallyPressed) isPollingMatrix = true; 
    else {
      isPollingMatrix = false; 
      setMatrixIdle();         
    }
  }

  // ==========================================
  // 4. SCREEN REFRESH (Render on Idle, Partial Refresh)
  // ==========================================
  // Auto-dismiss transient popup after timeout to restore normal grid
  if (screenMessage != "" && screenMessageDismissTime > 0 && now >= screenMessageDismissTime) {
    screenMessage = "";
    screenMessageDismissTime = 0;
    requestScreenUpdate(false, 50); // fast partial refresh to clear popup box
  } else if (screenMessage == "BOOTING..." && now > 4500) {
    screenMessage = "";
    screenMessageDismissTime = 0;
    requestScreenUpdate(false, 50);
  }

  // Auto-dismiss Status HUD after timeout
  if (isHudActive && hudAutoDismissTime > 0 && now >= hudAutoDismissTime) {
    isHudActive = false;
    hudAutoDismissTime = 0;
    setKeyLED(9, strip.Color(0, 0, 0), 1);
    requestScreenUpdate(false, 50);
    addDeviceLog("SYS", "HUD", "HUD auto-dismissed");
  }

  // Never freeze the CPU while keys/encoders are active or within 800ms of any user action
  if (screenNeedsUpdate && (now >= screenUpdateScheduledTime) && (now - lastActivityTime >= 800)) {
    updateScreen();
    screenNeedsUpdate = false;
  }
}