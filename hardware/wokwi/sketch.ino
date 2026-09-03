#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================================================
// EchoSphere ESP32 Smart Speaker Hardware Node
// Target Backend: Live Render Backend
// ============================================================================
const char* SERVER_URL = "https://echosphere-backend-9lv8.onrender.com";

// Hardware Pin Mappings (Matches original diagram.json board-esp32-s3-devkitc-1)
#define SPEAKER_PIN    4   // Piezo Buzzer / PA Speaker (GPIO 4, bz1)
#define LED_ONLINE_PIN 5   // Green LED: Backend Connected & Heartbeat OK (GPIO 5, led2)
#define LED_NOTICE_PIN 6   // Magenta LED: Broadcast Announcement / Emergency (GPIO 6, led1)

String macAddress;
String ipAddress;
const String zoneName = "Block A - CSE Quad";
const String deviceName = "Wokwi ESP32 Speaker Node #1";

WiFiClientSecure secureClient;

// ----------------------------------------------------------------------------
// Audio Tone Synthesizers (Simulated PA Audio Output)
// ----------------------------------------------------------------------------
void playEmergencySiren() {
    Serial.println("\n🚨 [EMERGENCY OVERRIDE] Campus Emergency Siren Activated!");
    for (int cycle = 0; cycle < 3; cycle++) {
        digitalWrite(LED_NOTICE_PIN, HIGH);
        for (int freq = 600; freq < 1400; freq += 50) {
            tone(SPEAKER_PIN, freq);
            delay(12);
        }
        digitalWrite(LED_NOTICE_PIN, LOW);
        for (int freq = 1400; freq > 600; freq -= 50) {
            tone(SPEAKER_PIN, freq);
            delay(12);
        }
    }
    noTone(SPEAKER_PIN);
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🚨 [EMERGENCY OVERRIDE] Siren Sequence Finished.");
}

void playNoticeTone() {
    Serial.println("\n🔊 [PA BROADCAST] Playing Announcement Chime...");
    digitalWrite(LED_NOTICE_PIN, HIGH);
    tone(SPEAKER_PIN, 587); // D5
    delay(200);
    tone(SPEAKER_PIN, 880); // A5
    delay(200);
    tone(SPEAKER_PIN, 1175); // D6
    delay(400);
    noTone(SPEAKER_PIN);
    delay(100);
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🔊 [PA BROADCAST] Chime Finished.");
}

void playTestTone() {
    Serial.println("\n🎛️ [DIAGNOSTIC TEST] Running 3-Tone PA Speaker Diagnostic...");
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_NOTICE_PIN, HIGH);
        tone(SPEAKER_PIN, 800 + (i * 300));
        delay(350);
        noTone(SPEAKER_PIN);
        digitalWrite(LED_NOTICE_PIN, LOW);
        delay(150);
    }
    digitalWrite(LED_NOTICE_PIN, LOW);
    Serial.println("🎛️ [DIAGNOSTIC TEST] Speaker & Purple LED Test Complete.");
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
            Serial.println("✅ [REGISTER] ESP32 Speaker Node Registered & ONLINE!");
        } else {
            Serial.printf("⚠️ [REGISTER] Backend response (%d): Auto-registering on heartbeat.\n", httpCode);
        }
        http.end();
    }
}

void executeCommand(const char* cmd, const char* title) {
    Serial.printf("\n📢 [COMMAND RECEIVED] Action: %s | Title: '%s'\n", cmd, title);

    if (String(cmd) == "PLAY_EMERGENCY") {
        playEmergencySiren();
    } else if (String(cmd) == "TEST_SPEAKER") {
        playTestTone();
    } else if (String(cmd) == "RESTART") {
        Serial.println("🔄 [RESTART] Rebooting hardware subsystem...");
        digitalWrite(LED_ONLINE_PIN, LOW);
        delay(400);
        digitalWrite(LED_ONLINE_PIN, HIGH);
    } else {
        playNoticeTone();
    }
}

void sendHeartbeat() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(SERVER_URL) + "/api/v1/hardware/speakers/heartbeat";
        
        secureClient.setInsecure();
        http.setTimeout(4000);
        http.begin(secureClient, url);
        http.addHeader("Content-Type", "application/json");
        http.addHeader("Connection", "close");

        JsonDocument doc;
        doc["mac_address"] = macAddress;
        doc["ip_address"] = ipAddress;
        doc["cpu_usage"] = random(12, 28);
        doc["memory_usage"] = random(30, 45);
        doc["disk_space"] = 72.5;
        doc["status"] = "ONLINE";

        String jsonPayload;
        serializeJson(doc, jsonPayload);

        int httpCode = http.POST(jsonPayload);
        if (httpCode == 200 || httpCode == 201) {
            digitalWrite(LED_ONLINE_PIN, HIGH);
            
            String response = http.getString();
            http.end(); // Close connection immediately before executing tone delays

            JsonDocument respDoc;
            DeserializationError err = deserializeJson(respDoc, response);
            if (!err && respDoc["pending_commands"].is<JsonArray>()) {
                JsonArray cmds = respDoc["pending_commands"].as<JsonArray>();
                for (JsonObject cmdObj : cmds) {
                    const char* cmd = cmdObj["command"] | "";
                    const char* title = cmdObj["title"] | "Campus Broadcast";
                    executeCommand(cmd, title);
                }
            }

            Serial.printf("💓 [HEARTBEAT] Telemetry OK (Code %d) | CPU: %d%% | RAM: %d%%\n", 
                          httpCode, (int)doc["cpu_usage"], (int)doc["memory_usage"]);
        } else {
            Serial.printf("⚠️ [HEARTBEAT] Telemetry Code %d (Retrying next cycle)\n", httpCode);
            http.end();
        }
    } else {
        // Blink Green LED if searching Wi-Fi
        digitalWrite(LED_ONLINE_PIN, !digitalRead(LED_ONLINE_PIN));
    }
}

// ----------------------------------------------------------------------------
// Arduino Setup & Main Loop
// ----------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(300);

    Serial.println("\n==================================================");
    Serial.println("  EchoSphere ESP32 Smart PA Speaker Node Firmware ");
    Serial.println("==================================================");

    pinMode(SPEAKER_PIN, OUTPUT);
    pinMode(LED_ONLINE_PIN, OUTPUT);
    pinMode(LED_NOTICE_PIN, OUTPUT);

    // Hardware Self-Test: Flash LEDs and Chirp Buzzer on Boot
    Serial.println("⚡ [POST] Hardware Power-On Self-Test...");
    digitalWrite(LED_ONLINE_PIN, HIGH);
    digitalWrite(LED_NOTICE_PIN, HIGH);
    tone(SPEAKER_PIN, 1000);
    delay(250);
    noTone(SPEAKER_PIN);
    digitalWrite(LED_NOTICE_PIN, LOW);

    // Disable SSL Certificate validation for Render backend
    secureClient.setInsecure();

    Serial.println("🌐 Connecting to Wokwi-GUEST Virtual Wi-Fi...");
    WiFi.begin("Wokwi-GUEST", "");

    int dots = 0;
    while (WiFi.status() != WL_CONNECTED && dots < 20) {
        delay(300);
        Serial.print(".");
        // Toggle green LED while connecting
        digitalWrite(LED_ONLINE_PIN, dots % 2 == 0 ? HIGH : LOW);
        dots++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        macAddress = WiFi.macAddress();
        ipAddress = WiFi.localIP().toString();
        digitalWrite(LED_ONLINE_PIN, HIGH);
        Serial.println("\n✨ Wi-Fi Connected Successfully!");
        Serial.printf(" - Node IP Address  : %s\n", ipAddress.c_str());
        Serial.printf(" - Node MAC Address : %s\n", macAddress.c_str());
        Serial.printf(" - Target Server    : %s\n", SERVER_URL);
        Serial.println("--------------------------------------------------");

        registerNodeWithBackend();
        sendHeartbeat();
    } else {
        Serial.println("\n⚠️ Running in Standalone Simulation Mode");
        macAddress = "24:0A:C4:00:11:22";
        ipAddress = "10.0.1.15";
        digitalWrite(LED_ONLINE_PIN, HIGH);
        sendHeartbeat();
    }
}

unsigned long lastCycle = 0;

void loop() {
    // Single unified heartbeat & command fetch cycle every 1.5 seconds (Ultra-Low Latency)
    if (millis() - lastCycle >= 1500) {
        sendHeartbeat();
        lastCycle = millis();
    }
    delay(50);
}
