/*
 * ============================================================================
 * EchoSphere ESP32 Smart Speaker & Live Notice Display Node
 * ============================================================================
 * 
 * Hardware Setup:
 * 1. Classic 38-Pin ESP32 NodeMCU DevKit (ESP-WROOM-32)
 * 2. MAX98357A I2S 3W Class-D Amplifier + 8Ω Speaker
 * 3. 1.8" Color TFT LCD Screen 128x160 SPI (ST7735)
 * 4. Notice Broadcasting LED & Server Online Heartbeat LED
 * 
 * Hardware Functions:
 * 1. Smart Speaker Client: Replaces python speaker_node_client.py with native ESP32 firmware.
 *    - Connects directly to EchoSphere cloud backend over Wi-Fi / HTTPS.
 *    - Registers identity as Speaker Client 1 (or 2) in the campus PA network.
 *    - Sends 3-second heartbeat telemetry to keep node active and ONLINE.
 *    - Plays attention chimes (587Hz -> 880Hz), emergency siren sweeps, and broadcast melodies
 *      over hardware I2S to the MAX98357A 3W amplifier and 8-ohm speaker.
 *    - Automatically reports completion back to the backend queue to auto-advance.
 * 
 * 2. Smart Notice Display & LED System:
 *    - When PLAYING: Displays currently broadcasting notice title with smooth scrolling ticker,
 *      priority badge, department, and dynamic 16-bar color audio visualizer.
 *      Illuminates Broadcasting LED on GPIO 21 (strobe flash in emergency).
 *    - When IDLE: Cycles smoothly through today's important notices from the app on the TFT screen.
 *      GPIO 21 remains off, and GPIO 22 pulses on each backend heartbeat.
 *    - Supports 1.8" Color TFT ST7735 SPI and prints visual ASCII frames to Serial at 115200 baud.
 * 
 * Safe Pinout Allocation (38-Pin NodeMCU):
 * - GPIO 26: I2S Bit Clock (BCLK) -> MAX98357A BCLK             [< 32, Output Safe]
 * - GPIO 25: I2S Left/Right Clock (LRC) -> MAX98357A LRC        [< 32, Output Safe]
 * - GPIO 27: I2S Serial Data (DIN) -> MAX98357A DIN             [< 32, Output Safe]
 * - GPIO 18: SPI SCLK -> 1.8" TFT SCLK / SCK                    [< 32, Output Safe]
 * - GPIO 23: SPI MOSI -> 1.8" TFT SDA / MOSI                    [< 32, Output Safe]
 * - GPIO  5: SPI CS -> 1.8" TFT CS                              [< 32, Output Safe]
 * - GPIO  4: TFT DC / A0 -> 1.8" TFT DC                         [< 32, Output Safe]
 * - GPIO 15: TFT RST / RES -> 1.8" TFT RES                      [< 32, Output Safe]
 * - GPIO 21: Notice Broadcasting LED Indicator                  [< 32, Output Safe]
 * - GPIO 22: Heartbeat & Online Status LED                      [< 32, Output Safe]
 * - GPIO  2: DevKit Onboard Blue LED                            [< 32, Output Safe]
 * - GPIO 34: Optional Local Test Pushbutton                     [Input Only Pin, Safe]
 * 
 * STRICT PINOUT RULE ENFORCED:
 * Pins 32, 33, 34, 35, 36, 39 are NEVER assigned as outputs!
 * ============================================================================
 */

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <driver/i2s.h>
#include <Audio.h>

#include "config.h"
#include "display_manager.h"
#include "audio_manager.h"
#include "network_manager.h"

// Optional ESP32-audioI2S diagnostic callbacks for Serial Monitor inspection
void audio_info(const char *info) {
  Serial.print(F("ℹ️ [AUDIO INFO] "));
  Serial.println(info);
}

void audio_eof_mp3(const char *info) {
  Serial.println(F("⏹️ [AUDIO EOF] MP3 stream playback completed."));
}

// Instantiate Subsystems
DisplayManager displayManager;
AudioManager audioManager;
EchoNetworkManager networkManager(displayManager, audioManager);

// Button debounce tracking (Optional physical test button on input-only GPIO 34)
unsigned long lastButtonPress = 0;

void setup() {
  // 1. Immediate Hardware Power & LED Self-Test
  // Configures and illuminates all LEDs right away to prove power, chip life, and correct resistor/LED polarity!
  pinMode(PIN_LED_BROADCAST, OUTPUT);
  pinMode(PIN_LED_ONLINE, OUTPUT);
  pinMode(PIN_LED_ONBOARD, OUTPUT);

  // Turn ALL LEDs ON immediately for visual confirmation
  digitalWrite(PIN_LED_BROADCAST, HIGH);
  digitalWrite(PIN_LED_ONLINE, HIGH);
  digitalWrite(PIN_LED_ONBOARD, HIGH);

  // 2. Initialize Serial communication
  Serial.begin(115200);
  delay(1200); // 1.2s solid burn so LEDs are clearly visible

  // Quick double-blink confirmation
  digitalWrite(PIN_LED_BROADCAST, LOW);
  digitalWrite(PIN_LED_ONLINE, LOW);
  digitalWrite(PIN_LED_ONBOARD, LOW);
  delay(150);
  digitalWrite(PIN_LED_BROADCAST, HIGH);
  digitalWrite(PIN_LED_ONLINE, HIGH);
  digitalWrite(PIN_LED_ONBOARD, HIGH);
  delay(150);
  digitalWrite(PIN_LED_BROADCAST, LOW);
  digitalWrite(PIN_LED_ONLINE, LOW);
  digitalWrite(PIN_LED_ONBOARD, LOW);

  Serial.println(F("\n========================================================"));
  Serial.println(F("⚡ EchoSphere ESP32 Smart Speaker & Notice Display Booting"));
  Serial.println(F("========================================================"));

  // 3. Configure optional test button (Safe input-only pin GPIO 34)
  #ifdef PIN_BUTTON_TEST
    pinMode(PIN_BUTTON_TEST, INPUT);
  #endif

  // 4. Initialize Audio subsystem on safe GPIO 25
  audioManager.begin();

  // 5. Initialize Display & LEDs on safe GPIOs 21, 22, 18, 19, 2
  displayManager.begin();

  // 6. Connect to Wi-Fi and register node with EchoSphere backend
  networkManager.begin();

  // 7. Play startup chime to confirm audio path
  audioManager.playAttentionChime();
  Serial.println(F("🚀 [BOOT COMPLETE] EchoSphere ESP32 Node is LIVE and LISTENING."));
}

void loop() {
  // 1. Update Display ticker, animations, and LED states
  displayManager.update();

  // 2. Handle Network tasks: Wi-Fi maintainer, 3s heartbeat, command execution, and queue sync
  networkManager.update();

  // 3. Optional local hardware test button check (on GPIO 34)
  #ifdef PIN_BUTTON_TEST
    if (digitalRead(PIN_BUTTON_TEST) == HIGH) {
      if (millis() - lastButtonPress > 1500) {
        lastButtonPress = millis();
        Serial.println(F("🔘 [BUTTON] Local diagnostic test triggered."));
        audioManager.playDiagnosticTest();
      }
    }
  #endif

  // Small cooperative yield for ESP32 FreeRTOS watchdog
  delay(10);
}
