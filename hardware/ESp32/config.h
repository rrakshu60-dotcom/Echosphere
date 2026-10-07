#ifndef ECHOSPHERE_CONFIG_H
#define ECHOSPHERE_CONFIG_H

#if __has_include(<Arduino.h>)
#include <Arduino.h>
#endif

// ============================================================================
// EchoSphere ESP32 Smart Speaker & Live Notice Display Node Configuration
// Hardware: Classic 38-Pin ESP32 NodeMCU DevKit (ESP-WROOM-32)
// Audio:    MAX98357A I2S 3W Class-D Amplifier + 8Ω Speaker
// Display:  1.8" TFT LCD Screen 128x160 SPI (ST7735)
// ============================================================================

// ----------------------------------------------------------------------------
// 1. Wi-Fi Configuration
// ----------------------------------------------------------------------------
#define WIFI_SSID "Rakshitha"    // Your Router / Mobile Hotspot SSID
#define WIFI_PASSWORD "12345678" // Your Router / Mobile Hotspot Password
#define WIFI_TIMEOUT_MS 20000    // Wi-Fi connection timeout in ms

// ----------------------------------------------------------------------------
// 2. EchoSphere Backend Server URL
// ----------------------------------------------------------------------------
// Default: Live cloud deployment on Render (matches frontend app directly)
// Local testing: "http://192.168.1.xxx:8000" (replace with PC LAN IP)
#define SERVER_URL "https://echosphere-backend-9lv8.onrender.com"

// ----------------------------------------------------------------------------
// 3. Node Profile Selector
// ----------------------------------------------------------------------------
// 1 = Node 1: "Hardware Speaker Client 1" (Auditorium / Campus, MAC:
// D4:F3:2D:22:2A:CB) 2 = Node 2: "Hardware Speaker Client 2" (Block B - AI Lab,
// MAC: D4:F3:2D:22:2A:CC) 0 = Auto-detect: Uses real ESP32 Hardware Wi-Fi MAC
// address
#define SELECTED_NODE_PROFILE 0

#if SELECTED_NODE_PROFILE == 1
#define NODE_NAME "Hardware Speaker Client 1"
#define NODE_MAC "D4:F3:2D:22:2A:CB"
#define NODE_ZONE "Auditorium / Campus"
#define NODE_DEPARTMENT "College-Wide"
#define NODE_DEFAULT_VOL 90
#elif SELECTED_NODE_PROFILE == 2
#define NODE_NAME "Hardware Speaker Client 2"
#define NODE_MAC "D4:F3:2D:22:2A:CC"
#define NODE_ZONE "Block B - AI Lab"
#define NODE_DEPARTMENT "AIML"
#define NODE_DEFAULT_VOL 90
#else
#define NODE_NAME "ESP32 Smart Speaker & Live Display"
#define NODE_MAC "D4:F3:2D:22:2A:CD"
#define NODE_ZONE "Campus Main Corridor"
#define NODE_DEPARTMENT "College-Wide"
#define NODE_DEFAULT_VOL 90
#endif

// ----------------------------------------------------------------------------
// 4. Strict Hardware Pinout for Classic 38-Pin ESP32 NodeMCU
// ----------------------------------------------------------------------------
// CRITICAL PINOUT CONSTRAINT:
// GPIOs 32, 33, 34, 35, 36 (VP), and 39 (VN) must NEVER be assigned as outputs.
// (34, 35, 36, 39 are input-only GPI pins lacking output drivers).
// All peripheral outputs are strictly assigned to safe general-purpose GPIOs
// < 32.

// --- A. MAX98357A I2S Audio Amplifier Pins (Outputs < 32) ---
#define PIN_I2S_BCLK 26 // I2S Bit Clock (BCLK)
#define PIN_I2S_LRC 25  // I2S Left/Right Clock / Word Select (LRC / WS)
#define PIN_I2S_DIN 27  // I2S Serial Data In (DIN)

// --- B. 1.8" TFT LCD Screen 128x160 SPI ST7735 Pins (Outputs < 32) ---
#define PIN_TFT_MOSI 23 // SPI Master Out Slave In / SDA
#define PIN_TFT_SCLK 18 // SPI Serial Clock / SCK / SCL
#define PIN_TFT_CS 5    // TFT Chip Select (CS)
#define PIN_TFT_DC 4    // TFT Data / Command (DC / A0)
#define PIN_TFT_RST 15  // TFT Reset (RES / RST)
#define PIN_TFT_BL -1   // Backlight (BLK / LED) -> Wire to 3.3V or safe GPIO

// --- C. Discrete Status LEDs (Outputs < 32) ---
#define PIN_LED_BROADCAST                                                      \
  21 // Notice Broadcasting LED (Lights up during playback, flashes in
     // emergency)
#define PIN_LED_ONLINE                                                         \
  22 // Server Heartbeat & Status LED (Pulses on 3s heartbeats)
#define PIN_LED_ONBOARD 2 // ESP32 DevKit Onboard Blue LED

// --- D. Optional Test Pushbutton (Safe Input-Only Pin) ---
#define PIN_BUTTON_TEST                                                        \
  34 // Optional input button for local speaker/display test

// Compile-Time Safety Guard: Ensure ZERO outputs are assigned to pins 32 - 39
static_assert(PIN_I2S_BCLK < 32,
              "CRITICAL: PIN_I2S_BCLK cannot be in pins 32-39!");
static_assert(PIN_I2S_LRC < 32,
              "CRITICAL: PIN_I2S_LRC cannot be in pins 32-39!");
static_assert(PIN_I2S_DIN < 32,
              "CRITICAL: PIN_I2S_DIN cannot be in pins 32-39!");
static_assert(PIN_TFT_MOSI < 32,
              "CRITICAL: PIN_TFT_MOSI cannot be in pins 32-39!");
static_assert(PIN_TFT_SCLK < 32,
              "CRITICAL: PIN_TFT_SCLK cannot be in pins 32-39!");
static_assert(PIN_TFT_CS < 32, "CRITICAL: PIN_TFT_CS cannot be in pins 32-39!");
static_assert(PIN_TFT_DC < 32, "CRITICAL: PIN_TFT_DC cannot be in pins 32-39!");
static_assert(PIN_TFT_RST < 32,
              "CRITICAL: PIN_TFT_RST cannot be in pins 32-39!");
static_assert(PIN_LED_BROADCAST < 32,
              "CRITICAL: PIN_LED_BROADCAST cannot be in pins 32-39!");
static_assert(PIN_LED_ONLINE < 32,
              "CRITICAL: PIN_LED_ONLINE cannot be in pins 32-39!");
static_assert(PIN_LED_ONBOARD < 32,
              "CRITICAL: PIN_LED_ONBOARD cannot be in pins 32-39!");

// ----------------------------------------------------------------------------
// 5. Display Configuration (1.8" TFT 128x160 SPI ST7735)
// ----------------------------------------------------------------------------
#define TFT_WIDTH 160  // Landscape width in pixels
#define TFT_HEIGHT 128 // Landscape height in pixels
#define TFT_ROTATION 1 // 1 or 3 for 160x128 landscape mode

#define DAILY_NOTICE_ROTATE_INTERVAL_MS                                        \
  5000 // Rotate through daily notices every 5 seconds when idle
#define TICKER_SCROLL_SPEED_MS 50 // Horizontal scrolling step interval in ms

// ----------------------------------------------------------------------------
// 6. Timing & Polling Settings
// ----------------------------------------------------------------------------
#define HEARTBEAT_INTERVAL_MS                                                  \
  3000 // Periodic heartbeat interval to backend in ms
#define QUEUE_POLL_INTERVAL_MS 2500 // Queue check interval in ms
#define LED_PULSE_DURATION_MS 60    // Heartbeat LED flash duration in ms

#endif // ECHOSPHERE_CONFIG_H
