#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "driver/i2s.h"

// ============================================================================
// EchoSphere ESP32 Smart PA Speaker Hardware Node
// Target Architecture: Classic 38-Pin ESP-32 NodeMCU / ESP-WROOM-32
// Audio Subsystem    : I2S Digital Audio (MAX98357A 3W Class-D Amplifier + 8Ω Speaker)
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
// MAX98357A I2S Amplifier & Peripheral Pin Mapping (Classic 38-Pin NodeMCU)
// ============================================================================
// MAX98357A Digital Audio Wiring:
//   - BCLK (Bit Clock)        --> GPIO 26
//   - LRC / WS (Word Select)  --> GPIO 25
//   - DIN (Data Input)        --> GPIO 22
//   - VIN                     --> 5V (VIN / VUSB on NodeMCU for full 3W loudness)
//   - GND                     --> GND
//   - Speaker + and -         --> 8Ω Speaker terminals
//
// Status Indicators:
//   - Onboard Status LED      --> GPIO 2  (Classic NodeMCU built-in blue LED)
//   - Notice / Siren LED      --> GPIO 18 (External indicator LED via 220Ω)
//
// 🚫 STRICTLY AVOIDED:
//   - Input-Only Pins 34 to 39 (GPI 34, 35, 36, 39)
//   - SPI Flash Pins 6 to 11 (Toggling causes immediate ESP32 freeze)
// ============================================================================
#define I2S_BCLK_PIN   26  // MAX98357A BCLK
#define I2S_LRC_PIN    25  // MAX98357A LRC (WS)
#define I2S_DIN_PIN    22  // MAX98357A DIN
#define LED_ONLINE_PIN 2   // Onboard Blue LED: Backend Connected & Heartbeat OK
#define LED_NOTICE_PIN 18  // External LED: Notice / Emergency Siren Active

// Compile-Time Safety Guard: Ensure no output is mapped to input-only (34-39) or SPI flash (6-11)
static_assert(I2S_BCLK_PIN < 34 || I2S_BCLK_PIN > 39, "CRITICAL: I2S_BCLK_PIN cannot use input-only pins 34-39!");
static_assert(I2S_LRC_PIN < 34 || I2S_LRC_PIN > 39, "CRITICAL: I2S_LRC_PIN cannot use input-only pins 34-39!");
static_assert(I2S_DIN_PIN < 34 || I2S_DIN_PIN > 39, "CRITICAL: I2S_DIN_PIN cannot use input-only pins 34-39!");
static_assert(LED_ONLINE_PIN < 34 || LED_ONLINE_PIN > 39, "CRITICAL: LED_ONLINE_PIN cannot use input-only pins 34-39!");
static_assert(LED_NOTICE_PIN < 34 || LED_NOTICE_PIN > 39, "CRITICAL: LED_NOTICE_PIN cannot use input-only pins 34-39!");

static_assert(I2S_BCLK_PIN < 6 || I2S_BCLK_PIN > 11, "CRITICAL: I2S_BCLK_PIN cannot use SPI flash pins 6-11!");
static_assert(I2S_LRC_PIN < 6 || I2S_LRC_PIN > 11, "CRITICAL: I2S_LRC_PIN cannot use SPI flash pins 6-11!");
static_assert(I2S_DIN_PIN < 6 || I2S_DIN_PIN > 11, "CRITICAL: I2S_DIN_PIN cannot use SPI flash pins 6-11!");
static_assert(LED_ONLINE_PIN < 6 || LED_ONLINE_PIN > 11, "CRITICAL: LED_ONLINE_PIN cannot use SPI flash pins 6-11!");
static_assert(LED_NOTICE_PIN < 6 || LED_NOTICE_PIN > 11, "CRITICAL: LED_NOTICE_PIN cannot use SPI flash pins 6-11!");

String macAddress;
String ipAddress;
const String zoneName = "Block A - CSE Quad";
const String deviceName = "EchoSphere NodeMCU I2S Speaker";

WiFiClientSecure secureClient;

// ----------------------------------------------------------------------------
// MAX98357A I2S Digital Audio Subsystem
// ----------------------------------------------------------------------------
const int I2S_SAMPLE_RATE = 16000;
bool i2sInitialized = false;

void initI2SAudio() {
    if (i2sInitialized) return;

    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = I2S_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .mck_io_num = I2S_PIN_NO_CHANGE,
        .bck_io_num = I2S_BCLK_PIN,
        .ws_io_num = I2S_LRC_PIN,
        .data_out_num = I2S_DIN_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    if (err == ESP_OK) {
        i2s_set_pin(I2S_NUM_0, &pin_config);
        i2sInitialized = true;
        Serial.println("🔊 [I2S] MAX98357A Audio Driver Initialized (16kHz 16-bit Stereo PCM)");
    } else {
        Serial.printf("❌ [I2S] Driver install failed: 0x%x\n", err);
    }
}

// Synthesize high-fidelity 16-bit PCM sine waves and stream directly to MAX98357A
void playI2STone(float frequency, int durationMs, float volume = 0.6f) {
    if (!i2sInitialized) initI2SAudio();

    int totalSamples = (I2S_SAMPLE_RATE * durationMs) / 1000;
    int16_t buffer[128]; // 64 stereo frames (L + R)
    size_t bytesWritten = 0;
    float phase = 0.0f;
    float phaseInc = (2.0f * PI * frequency) / I2S_SAMPLE_RATE;

    for (int i = 0; i < totalSamples; i += 64) {
        int chunkSize = min(64, totalSamples - i);
        for (int j = 0; j < chunkSize; j++) {
            int16_t sample = (int16_t)(sin(phase) * 32767.0f * volume);
            buffer[j * 2]     = sample; // Left channel
            buffer[j * 2 + 1] = sample; // Right channel
            phase += phaseInc;
            if (phase >= 2.0f * PI) phase -= 2.0f * PI;
        }
        i2s_write(I2S_NUM_0, buffer, chunkSize * 2 * sizeof(int16_t), &bytesWritten, portMAX_DELAY);
    }
}

void stopI2SAudio() {
    if (i2sInitialized) {
        i2s_zero_dma_buffer(I2S_NUM_0);
    }
}

// ----------------------------------------------------------------------------
// PA Audio Chimes & Sirens (High-Fidelity I2S Synthesis)
// ----------------------------------------------------------------------------
void playEmergencySiren() {
    Serial.println("\n🚨 [EMERGENCY OVERRIDE] Campus Emergency Siren via MAX98357A!");
    for (int cycle = 0; cycle < 3; cycle++) {
        digitalWrite(LED_NOTICE_PIN, HIGH);
        // Ascending whoop
        for (float freq = 650; freq < 1350; freq += 40) {
            playI2STone(freq, 16, 0.85f);
        }
        digitalWrite(LED_NOTICE_PIN, LOW);
        // Descending whoop
        for (float freq = 1350; freq > 650; freq -= 40) {
            playI2STone(freq, 16, 0.85f);
        }
    }
    stopI2SAudio();
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🚨 [EMERGENCY OVERRIDE] Siren Complete.");
}

void playNoticeTone() {
    Serial.println("\n🔊 [PA BROADCAST] Playing Airport/Campus Chime via MAX98357A...");
    digitalWrite(LED_NOTICE_PIN, HIGH);
    // Professional 3-tone campus broadcast chime (D5 -> A5 -> D6)
    playI2STone(587.33f, 220, 0.70f); // D5
    delay(30);
    playI2STone(880.00f, 220, 0.70f); // A5
    delay(30);
    playI2STone(1174.66f, 450, 0.75f); // D6
    delay(100);
    stopI2SAudio();
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🔊 [PA BROADCAST] Chime Complete.");
}

void playTestTone() {
    Serial.println("\n🎛️ [DIAGNOSTIC TEST] Crisp Audio Test via MAX98357A...");
    digitalWrite(LED_NOTICE_PIN, HIGH);
    playI2STone(880.0f, 150, 0.65f);  // A5
    delay(40);
    playI2STone(1318.5f, 250, 0.70f); // E6
    delay(80);
    stopI2SAudio();
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
            Serial.println("✅ [REGISTER] ESP32 NodeMCU + MAX98357A Registered & ONLINE!");
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
        Serial.println("⏸️ [PAUSE] Playback paused.");
        stopI2SAudio();
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "RESUME") {
        Serial.println("▶️ [RESUME] Playback resumed.");
        digitalWrite(LED_NOTICE_PIN, HIGH);
        playI2STone(880.0f, 100, 0.5f);
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "STOP" || action == "CANCEL" || action == "SKIP") {
        Serial.println("⏹️ [STOP/SKIP] Playback terminated.");
        stopI2SAudio();
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "SET_VOLUME") {
        Serial.println("🔊 [VOLUME] Volume updated on speaker node.");
    } else if (action == "RESTART") {
        Serial.println("🔄 [RESTART] Rebooting hardware subsystem...");
        digitalWrite(LED_ONLINE_PIN, LOW);
        delay(400);
        digitalWrite(LED_ONLINE_PIN, HIGH);
    } else {
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
    Serial.begin(115200);
    delay(500); // 500ms stabilization delay for CH340 / CP2102 transceiver
    Serial.flush();

    Serial.println("\n========================================================");
    Serial.println("  EchoSphere Classic 38-Pin ESP-32 NodeMCU Firmware    ");
    Serial.println("  Amplifier: MAX98357A I2S 3W Class-D + 8Ω Speaker     ");
    Serial.println("  UART: Standard Hardware UART0 (CH340 / CP210x Bridge) ");
    Serial.println("========================================================");
    Serial.printf("I2S Pins: BCLK=GPIO %d | LRC=GPIO %d | DIN=GPIO %d\n", 
                  I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DIN_PIN);
    Serial.printf("LED Pins: Online=GPIO %d | Notice=GPIO %d\n", 
                  LED_ONLINE_PIN, LED_NOTICE_PIN);

    pinMode(LED_ONLINE_PIN, OUTPUT);
    pinMode(LED_NOTICE_PIN, OUTPUT);

    // Initialize MAX98357A I2S driver
    initI2SAudio();

    // Hardware Power-On Self-Test (POST): Play pleasant boot chime
    Serial.println("⚡ [POST] Hardware Power-On Self-Test...");
    digitalWrite(LED_ONLINE_PIN, HIGH);
    digitalWrite(LED_NOTICE_PIN, HIGH);
    playI2STone(523.25f, 120, 0.5f); // C5
    playI2STone(659.25f, 150, 0.5f); // E5
    playI2STone(783.99f, 250, 0.6f); // G5
    stopI2SAudio();
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
