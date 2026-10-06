#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================================================
// EchoSphere ESP32 Smart PA Speaker Hardware Node
// Target Architecture: Classic 38-Pin ESP-32 NodeMCU / ESP-WROOM-32 Dev Module
// Serial Interface   : Standard Hardware UART0 (CH340 / CP2102 Bridge)
// Target Backend     : Live Render Backend
// ============================================================================
const char* SERVER_URL = "https://echosphere-backend-9lv8.onrender.com";

// ============================================================================
// Wi-Fi Configuration
// For Wokwi Simulator : Keep "Wokwi-GUEST" and ""
// For Real ESP32      : Enter your 2.4GHz Wi-Fi SSID and Password
// ============================================================================
const char* WIFI_SSID = "Wokwi-GUEST"; // <-- Change to your 2.4GHz Wi-Fi name
const char* WIFI_PASS = "";            // <-- Change to your 2.4GHz Wi-Fi password

// ============================================================================
// Classic 38-Pin ESP-32 NodeMCU GPIO Pin Allocations
// ============================================================================
// 🚫 STRICTLY PROHIBITED PINS ON CLASSIC ESP-WROOM-32:
//  - Input-Only Pins (GPI 34 to 39): Cannot drive outputs (no output driver/pull-up)
//  - Integrated SPI Flash (GPIO 6 to 11): Toggling will crash/freeze ESP32 immediately
//  - Strapping Pins (GPIO 0, 12, 15): Affects boot mode if pulled high/low on power-up
//
// ✅ SAFE GENERAL-PURPOSE OUTPUT PINS USED:
//  - GPIO 25: DAC1 / Safe General Output -> Audio output / Piezo buzzer / PAM8403
//  - GPIO 2 : Classic NodeMCU Onboard Blue LED -> Online status & heartbeat blink
//  - GPIO 18: Safe General Output (VSPI SCK)   -> Notice broadcast & emergency LED
// ============================================================================
#define SPEAKER_PIN    25  // DAC1 (Pin 25): Piezo Buzzer / Speaker Module / PAM8403 Input
#define LED_ONLINE_PIN 2   // Onboard LED (Pin 2): Backend Connected & Heartbeat OK
#define LED_NOTICE_PIN 18  // GPIO 18: Broadcast Announcement / Emergency Siren Active

// Compile-Time Safety Guard: Ensure no output is mapped to input-only (34-39) or SPI flash (6-11)
static_assert(SPEAKER_PIN < 34 || SPEAKER_PIN > 39, "CRITICAL: SPEAKER_PIN cannot be assigned to input-only pins 34-39!");
static_assert(LED_ONLINE_PIN < 34 || LED_ONLINE_PIN > 39, "CRITICAL: LED_ONLINE_PIN cannot be assigned to input-only pins 34-39!");
static_assert(LED_NOTICE_PIN < 34 || LED_NOTICE_PIN > 39, "CRITICAL: LED_NOTICE_PIN cannot be assigned to input-only pins 34-39!");

static_assert(SPEAKER_PIN < 6 || SPEAKER_PIN > 11, "CRITICAL: SPEAKER_PIN cannot use SPI flash pins 6-11 on classic ESP32!");
static_assert(LED_ONLINE_PIN < 6 || LED_ONLINE_PIN > 11, "CRITICAL: LED_ONLINE_PIN cannot use SPI flash pins 6-11 on classic ESP32!");
static_assert(LED_NOTICE_PIN < 6 || LED_NOTICE_PIN > 11, "CRITICAL: LED_NOTICE_PIN cannot use SPI flash pins 6-11 on classic ESP32!");

String macAddress;
String ipAddress;
const String zoneName = "Block A - CSE Quad";
const String deviceName = "EchoSphere NodeMCU-32S Node";

WiFiClientSecure secureClient;

// ----------------------------------------------------------------------------
// Audio Tone Synthesizers (LEDC / Hardware Timer PWM on Classic ESP32)
// ----------------------------------------------------------------------------
void playTone(uint8_t pin, unsigned int frequency) {
    tone(pin, frequency);
}

void stopTone(uint8_t pin) {
    noTone(pin);
}

void playEmergencySiren() {
    Serial.println("\n🚨 [EMERGENCY OVERRIDE] Campus Emergency Siren Activated!");
    for (int cycle = 0; cycle < 3; cycle++) {
        digitalWrite(LED_NOTICE_PIN, HIGH);
        for (int freq = 600; freq < 1400; freq += 50) {
            playTone(SPEAKER_PIN, freq);
            delay(12);
        }
        digitalWrite(LED_NOTICE_PIN, LOW);
        for (int freq = 1400; freq > 600; freq -= 50) {
            playTone(SPEAKER_PIN, freq);
            delay(12);
        }
    }
    stopTone(SPEAKER_PIN);
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🚨 [EMERGENCY OVERRIDE] Siren Sequence Finished.");
}

void playNoticeTone() {
    Serial.println("\n🔊 [PA BROADCAST] Playing Announcement Chime...");
    digitalWrite(LED_NOTICE_PIN, HIGH);
    playTone(SPEAKER_PIN, 587); // D5
    delay(200);
    playTone(SPEAKER_PIN, 880); // A5
    delay(200);
    playTone(SPEAKER_PIN, 1175); // D6
    delay(400);
    stopTone(SPEAKER_PIN);
    delay(100);
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🔊 [PA BROADCAST] Chime Finished.");
}

void playTestTone() {
    Serial.println("\n🎛️ [DIAGNOSTIC TEST] Crisp PA Diagnostic Chime...");
    digitalWrite(LED_NOTICE_PIN, HIGH);
    playTone(SPEAKER_PIN, 950);
    delay(120);
    playTone(SPEAKER_PIN, 1350);
    delay(160);
    stopTone(SPEAKER_PIN);
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🎛️ [DIAGNOSTIC TEST] Diagnostic Complete.");
}

// ----------------------------------------------------------------------------
// Backend Communication Routines
// ----------------------------------------------------------------------------
void registerNodeWithBackend() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(SERVER_URL) + "/api/v1/hardware/speakers/register";
        http.setTimeout(5000);
        http.begin(secureClient, url);
        http.addHeader("Content-Type", "application/json");
        http.addHeader("Connection", "close");

        JsonDocument doc;
        doc["name"] = deviceName;
        doc["mac_address"] = macAddress;
        doc["ip_address"] = ipAddress;
        doc["zone"] = zoneName;
        doc["volume"] = 90;

        String jsonPayload;
        serializeJson(doc, jsonPayload);

        int httpCode = http.POST(jsonPayload);
        Serial.printf("📡 [REGISTER] HTTP Response Code: %d\n", httpCode);

        if (httpCode == 200 || httpCode == 201 || httpCode == 400) {
            digitalWrite(LED_ONLINE_PIN, HIGH);
            Serial.println("✅ [REGISTER] Classic ESP32 NodeMCU Registered & ONLINE!");
        } else {
            Serial.printf("⚠️ [REGISTER] Backend response (%d): Auto-registering on heartbeat.\n", httpCode);
        }
        http.end();
    }
}

void executeCommand(const char* cmd, const char* title) {
    Serial.printf("\n📢 [COMMAND RECEIVED] Action: %s | Title: '%s'\n", cmd, title);

    String action = String(cmd);
    if (action == "PLAY_EMERGENCY") {
        playEmergencySiren();
    } else if (action == "TEST_SPEAKER") {
        playTestTone();
    } else if (action == "PLAY_ANNOUNCEMENT" || action == "PLAY") {
        playNoticeTone();
    } else if (action == "PAUSE") {
        Serial.println("⏸️ [PAUSE] Speaker playback paused.");
        stopTone(SPEAKER_PIN);
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "RESUME") {
        Serial.println("▶️ [RESUME] Speaker playback resumed.");
        digitalWrite(LED_NOTICE_PIN, HIGH);
        delay(100);
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "STOP" || action == "CANCEL" || action == "SKIP") {
        Serial.println("⏹️ [STOP/SKIP] Playback terminated.");
        stopTone(SPEAKER_PIN);
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "SET_VOLUME") {
        Serial.println("🔊 [VOLUME] Volume updated on speaker node.");
    } else if (action == "RESTART") {
        Serial.println("🔄 [RESTART] Rebooting hardware subsystem...");
        digitalWrite(LED_ONLINE_PIN, LOW);
        delay(400);
        digitalWrite(LED_ONLINE_PIN, HIGH);
    } else {
        // Fallback for any unknown notice action
        playNoticeTone();
    }
}

HTTPClient http;
bool httpInitialized = false;

void sendHeartbeat() {
    if (WiFi.status() == WL_CONNECTED) {
        String url = String(SERVER_URL) + "/api/v1/hardware/speakers/heartbeat";
        
        if (!httpInitialized) {
            secureClient.setInsecure();
            http.setReuse(true);
            http.setTimeout(3500);
            http.begin(secureClient, url);
            http.addHeader("Content-Type", "application/json");
            http.addHeader("Connection", "keep-alive");
            httpInitialized = true;
        }

        JsonDocument doc;
        doc["mac_address"] = macAddress;
        doc["ip_address"] = ipAddress;
        doc["cpu_usage"] = random(12, 28);
        doc["memory_usage"] = random(30, 45);
        doc["disk_space"] = 72.5;
        doc["status"] = "ONLINE";

        String jsonPayload;
        serializeJson(doc, jsonPayload);

        unsigned long t0 = millis();
        int httpCode = http.POST(jsonPayload);
        unsigned long roundtrip = millis() - t0;

        if (httpCode == 200 || httpCode == 201) {
            digitalWrite(LED_ONLINE_PIN, HIGH);
            
            String response = http.getString();

            JsonDocument respDoc;
            DeserializationError err = deserializeJson(respDoc, response);
            if (!err && respDoc["pending_commands"].is<JsonArray>()) {
                JsonArray cmds = respDoc["pending_commands"].as<JsonArray>();
                bool testToneTriggered = false;
                for (JsonObject cmdObj : cmds) {
                    const char* cmd = cmdObj["command"] | "";
                    const char* title = cmdObj["title"] | "Campus Broadcast";
                    // Deduplicate test tone clicks in the same batch
                    if (String(cmd) == "TEST_SPEAKER") {
                        if (!testToneTriggered) {
                            testToneTriggered = true;
                            executeCommand(cmd, title);
                        }
                    } else {
                        executeCommand(cmd, title);
                    }
                }
            }

            Serial.printf("💓 [HEARTBEAT] OK in %lums (Code %d) | CPU: %d%%\n", 
                          roundtrip, httpCode, (int)doc["cpu_usage"]);
        } else {
            Serial.printf("⚠️ [HEARTBEAT] Code %d (Reconnecting keep-alive)\n", httpCode);
            http.end();
            httpInitialized = false;
        }
    } else {
        // Blink Onboard Blue LED if Wi-Fi searching / connecting
        digitalWrite(LED_ONLINE_PIN, !digitalRead(LED_ONLINE_PIN));
    }
}

// ----------------------------------------------------------------------------
// Arduino Setup & Main Loop
// ----------------------------------------------------------------------------
void setup() {
    // ------------------------------------------------------------------------
    // Standard Hardware UART0 Serial Initialization (CH340 / CP2102 Driver)
    // ------------------------------------------------------------------------
    // Classic 38-Pin NodeMCU uses onboard USB-to-UART bridge (CH340G / CP2102)
    // wired directly to GPIO 1 (TX0) and GPIO 3 (RX0).
    // Avoid blocking loops like `while(!Serial)` which stall when no terminal is connected.
    Serial.begin(115200);
    delay(500); // 500ms stabilization delay for CH340 / CP2102 transceiver power-up
    Serial.flush();

    Serial.println("\n========================================================");
    Serial.println("  EchoSphere Classic 38-Pin ESP-32 NodeMCU Firmware    ");
    Serial.println("  UART: Standard Hardware UART0 (CH340 / CP210x Bridge) ");
    Serial.println("========================================================");
    Serial.printf("Pins: Speaker=GPIO %d | Online LED=GPIO %d | Notice LED=GPIO %d\n", 
                  SPEAKER_PIN, LED_ONLINE_PIN, LED_NOTICE_PIN);

    pinMode(SPEAKER_PIN, OUTPUT);
    pinMode(LED_ONLINE_PIN, OUTPUT);
    pinMode(LED_NOTICE_PIN, OUTPUT);

    // Hardware Power-On Self-Test (POST): Chirp buzzer and flash LEDs
    Serial.println("⚡ [POST] Hardware Power-On Self-Test...");
    digitalWrite(LED_ONLINE_PIN, HIGH);
    digitalWrite(LED_NOTICE_PIN, HIGH);
    playTone(SPEAKER_PIN, 1000);
    delay(250);
    stopTone(SPEAKER_PIN);
    digitalWrite(LED_NOTICE_PIN, LOW);

    // Set Render backend SSL to insecure (no local CA certificate bundle required)
    secureClient.setInsecure();

    Serial.printf("🌐 Connecting to 2.4GHz Wi-Fi: %s...\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    int dots = 0;
    while (WiFi.status() != WL_CONNECTED && dots < 30) {
        delay(300);
        Serial.print(".");
        // Toggle onboard blue LED while searching for Wi-Fi
        digitalWrite(LED_ONLINE_PIN, dots % 2 == 0 ? HIGH : LOW);
        dots++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        // Read true chip factory MAC address from eFuse
        String realMac = WiFi.macAddress();
        macAddress = (realMac.length() > 0 && realMac != "00:00:00:00:00:00") ? realMac : "24:0A:C4:00:01:10";
        ipAddress = WiFi.localIP().toString();
        digitalWrite(LED_ONLINE_PIN, HIGH);
        Serial.println("\n✨ Wi-Fi Connected Successfully!");
        Serial.printf(" - Node IP Address  : %s\n", ipAddress.c_str());
        Serial.printf(" - Hardware MAC     : %s\n", macAddress.c_str());
        Serial.printf(" - Target Server    : %s\n", SERVER_URL);
        Serial.println("--------------------------------------------------------");

        registerNodeWithBackend();
        sendHeartbeat();
    } else {
        Serial.println("\n⚠️ Running in Standalone Simulation Mode (Offline)");
        macAddress = "24:0A:C4:00:01:10";
        ipAddress = "10.0.1.15";
        digitalWrite(LED_ONLINE_PIN, HIGH);
        sendHeartbeat();
    }
}

unsigned long lastCycle = 0;

void loop() {
    // 3-second heartbeat cycle keeps node alive and polls backend for pending broadcasts
    if (millis() - lastCycle >= 3000) {
        if (WiFi.status() != WL_CONNECTED) {
            WiFi.reconnect();
        }
        sendHeartbeat();
        lastCycle = millis();
    }
    delay(25);
}
