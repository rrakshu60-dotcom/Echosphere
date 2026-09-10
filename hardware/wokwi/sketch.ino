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
const String deviceName = "Wokwi ESP32 Speaker Node";

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
    Serial.println("\n🎛️ [DIAGNOSTIC TEST] Crisp PA Diagnostic Chime...");
    digitalWrite(LED_NOTICE_PIN, HIGH);
    tone(SPEAKER_PIN, 950);
    delay(120);
    tone(SPEAKER_PIN, 1350);
    delay(160);
    noTone(SPEAKER_PIN);
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
            Serial.println("✅ [REGISTER] ESP32 Speaker Node Registered & ONLINE!");
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
        noTone(SPEAKER_PIN);
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "RESUME") {
        Serial.println("▶️ [RESUME] Speaker playback resumed.");
        digitalWrite(LED_NOTICE_PIN, HIGH);
        delay(100);
        digitalWrite(LED_NOTICE_PIN, LOW);
    } else if (action == "STOP" || action == "CANCEL" || action == "SKIP") {
        Serial.println("⏹️ [STOP/SKIP] Playback terminated.");
        noTone(SPEAKER_PIN);
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
        macAddress = "24:0A:C4:00:01:10";
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
        macAddress = "24:0A:C4:00:01:10";
        ipAddress = "10.0.1.15";
        digitalWrite(LED_ONLINE_PIN, HIGH);
        sendHeartbeat();
    }
}

unsigned long lastCycle = 0;

void loop() {
    // 3-second heartbeat cycle keeps node alive and checks for commands
    if (millis() - lastCycle >= 3000) {
        sendHeartbeat();
        lastCycle = millis();
    }
    delay(25);
}
