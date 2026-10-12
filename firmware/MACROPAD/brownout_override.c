#include "esp_err.h"

// Override ESP-IDF brownout detector symbols to completely prevent
// the hardware BOD comparator interrupt from being registered on early boot.
// This completely supersedes brownout.c.obj from libesp_hw_support.a and
// permanently eliminates brownout reset loops on ESP32-C3 SuperMini modules.

void esp_brownout_init(void) {
  // Stub out IDF brownout initialization completely
}

void esp_brownout_disable(void) {
  // Stub
}
