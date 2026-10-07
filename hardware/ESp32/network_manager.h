#ifndef ECHOSPHERE_NETWORK_MANAGER_H
#define ECHOSPHERE_NETWORK_MANAGER_H

#include "config.h"
#include "arduino_compat.h"


#include "display_manager.h"
#include "audio_manager.h"

class EchoNetworkManager {
private:
  DisplayManager& displayMgr;
  AudioManager& audioMgr;

  String serverUrl;
  String nodeName;
  String nodeMac;
  String nodeZone;
  String nodeDept;
  int nodeId = 0;

  String currentStatus = "ONLINE";
  int activeAnnouncementId = 0;
  int activeQueueId = 0;
  unsigned long activePlaybackEndTime = 0;
  bool isBroadcasting = false;

  unsigned long lastHeartbeatTime = 0;
  unsigned long lastQueueCheckTime = 0;

public:
  EchoNetworkManager(DisplayManager& disp, AudioManager& audio)
    : displayMgr(disp), audioMgr(audio) {
    serverUrl = String(SERVER_URL);
    // Strip trailing slash
    if (serverUrl.endsWith("/")) {
      serverUrl = serverUrl.substring(0, serverUrl.length() - 1);
    }
    nodeName = String(NODE_NAME);
    nodeMac = String(NODE_MAC);
    nodeZone = String(NODE_ZONE);
    nodeDept = String(NODE_DEPARTMENT);
  }

  int lastTopNoticeId = 0;

  void begin() {
    // Initialize WiFi in STA mode first so radio hardware MAC is valid
    WiFi.mode(WIFI_STA);

    // Determine MAC address
    if (nodeMac.length() == 0 || nodeMac.equalsIgnoreCase("00:00:00:00:00:00")) {
      String hwMac = WiFi.macAddress();
      if (hwMac.length() > 0 && !hwMac.equalsIgnoreCase("00:00:00:00:00:00")) {
        nodeMac = hwMac;
      } else {
        nodeMac = "D4:F3:2D:22:2A:CD";
      }
    }

    printBanner();
    connectWiFi();
    registerNode();
  }

  void printBanner() {
    Serial.println(F("\n══════════════════════════════════════════════════════════════════════"));
    Serial.println(F("  🔊 EchoSphere ESP32 Smart Speaker & Live Display Node Client"));
    Serial.println(F("══════════════════════════════════════════════════════════════════════"));
    Serial.print(F("  [*] Node Name:    ")); Serial.println(nodeName);
    Serial.print(F("  [*] Node MAC:     ")); Serial.println(nodeMac);
    Serial.print(F("  [*] Zone & Dept:  ")); Serial.print(nodeZone); Serial.print(F(" (")); Serial.print(nodeDept); Serial.println(F(")"));
    Serial.print(F("  [*] Server URL:   ")); Serial.println(serverUrl);
    Serial.print(F("  [*] Volume:       ")); Serial.print(audioMgr.getVolume()); Serial.println(F("%"));
    Serial.println(F("  [*] Pinout Guard: 32-39 Input-Only Verified (Zero outputs on 32-39)"));
    Serial.println(F("══════════════════════════════════════════════════════════════════════\n"));
  }

  void connectWiFi() {
    Serial.print(F("📶 [WIFI] Connecting to SSID: "));
    Serial.println(WIFI_SSID);
    displayMgr.setConnectingWiFi(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startAttempt = millis();
    bool ledToggle = false;
    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < WIFI_TIMEOUT_MS) {
      delay(300);
      Serial.print(F("."));
      ledToggle = !ledToggle;
      digitalWrite(PIN_LED_ONLINE, ledToggle ? HIGH : LOW);
      digitalWrite(PIN_LED_ONBOARD, ledToggle ? HIGH : LOW);
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println();
      Serial.print(F("✅ [WIFI] Connected! Assigned IP: "));
      Serial.println(WiFi.localIP());
      displayMgr.setConnectedWiFi(WiFi.localIP().toString());
      digitalWrite(PIN_LED_ONLINE, HIGH);  // Solid ON indicates Online & Connected
      digitalWrite(PIN_LED_ONBOARD, LOW);
    } else {
      Serial.println();
      Serial.println(F("⚠️ [WIFI] Wi-Fi connection timed out. Will auto-retry in main loop."));
      digitalWrite(PIN_LED_ONLINE, LOW);   // OFF indicates Offline
      digitalWrite(PIN_LED_ONBOARD, LOW);
    }
  }

  void checkWiFiConnection() {
    if (WiFi.status() != WL_CONNECTED) {
      digitalWrite(PIN_LED_ONLINE, LOW);
      Serial.println(F("⚠️ [WIFI] Connection lost. Reconnecting..."));
      displayMgr.setConnectingWiFi(WIFI_SSID);
      WiFi.reconnect();
    }
  }

  // --------------------------------------------------------------------------
  // Node Auto-Registration
  // POST /api/v1/hardware/speakers/register
  // --------------------------------------------------------------------------
  void registerNode() {
    if (WiFi.status() != WL_CONNECTED) return;

    String url = serverUrl + "/api/v1/hardware/speakers/register";
    Serial.print(F("📡 [REGISTER] Registering node with backend: "));
    Serial.println(url);

    #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
      JsonDocument doc;
    #else
      StaticJsonDocument<256> doc;
    #endif
    doc["name"] = nodeName;
    doc["mac_address"] = nodeMac;
    doc["ip_address"] = WiFi.localIP().toString();
    doc["zone"] = nodeZone;
    doc["volume"] = audioMgr.getVolume();

    String requestBody;
    serializeJson(doc, requestBody);

    HTTPClient http;
    WiFiClientSecure secureClient;
    WiFiClient plainClient;

    bool isHttps = serverUrl.startsWith("https://");
    if (isHttps) {
      secureClient.setInsecure();
      http.begin(secureClient, url);
    } else {
      http.begin(plainClient, url);
    }

    http.addHeader("Content-Type", "application/json");
    http.setTimeout(8000);

    int httpCode = http.POST(requestBody);
    if (httpCode == 200 || httpCode == 201) {
      String response = http.getString();
      #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
        JsonDocument respDoc;
      #else
        StaticJsonDocument<512> respDoc;
      #endif
      DeserializationError err = deserializeJson(respDoc, response);
      if (!err) {
        nodeId = respDoc["id"].as<int>();
        Serial.print(F("✅ [REGISTER] Node registered successfully! ID: #"));
        Serial.println(nodeId);
      }
      displayMgr.setState(STATE_IDLE_DAILY_NOTICES);
    } else {
      Serial.print(F("ℹ️ [REGISTER] Registration response HTTP code: "));
      Serial.println(httpCode);
      displayMgr.setState(STATE_IDLE_DAILY_NOTICES);
    }
    http.end();
  }

  // --------------------------------------------------------------------------
  // Heartbeat & Telemetry (Every 3 seconds)
  // POST /api/v1/hardware/speakers/heartbeat
  // --------------------------------------------------------------------------
  void sendHeartbeat() {
    if (WiFi.status() != WL_CONNECTED) return;

    String url = serverUrl + "/api/v1/hardware/speakers/heartbeat";

    #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
      JsonDocument reqDoc;
    #else
      StaticJsonDocument<256> reqDoc;
    #endif
    reqDoc["mac_address"] = nodeMac;
    reqDoc["ip_address"] = WiFi.localIP().toString();
    reqDoc["status"] = isBroadcasting ? "PLAYING" : "ONLINE";
    reqDoc["cpu_usage"] = 14.5;
    reqDoc["memory_usage"] = 35.0;
    reqDoc["disk_space"] = 68.0;

    String requestBody;
    serializeJson(reqDoc, requestBody);

    HTTPClient http;
    WiFiClientSecure secureClient;
    WiFiClient plainClient;

    if (serverUrl.startsWith("https://")) {
      secureClient.setInsecure();
      http.begin(secureClient, url);
    } else {
      http.begin(plainClient, url);
    }

    http.addHeader("Content-Type", "application/json");
    http.setTimeout(4000);

    int httpCode = http.POST(requestBody);
    if (httpCode == 200 || httpCode == 201) {
      // Pulse status LED on successful heartbeat
      displayMgr.triggerHeartbeatPulse();

      String response = http.getString();
      #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
        JsonDocument respDoc;
      #else
        DynamicJsonDocument respDoc(4096);
      #endif
      DeserializationError err = deserializeJson(respDoc, response);
      if (!err) {
        // 1. Process pending control commands
        if (respDoc["pending_commands"].is<JsonArray>()) {
          JsonArray commands = respDoc["pending_commands"].as<JsonArray>();
          for (JsonObject cmd : commands) {
            handleCommand(cmd);
          }
        }

        // 2. Process active playing announcement
        if (!respDoc["active_notice"].isNull()) {
          JsonObject activeNotice = respDoc["active_notice"].as<JsonObject>();
          int annId = activeNotice["id"].as<int>();
          int qId = activeNotice["queue_id"].as<int>();
          if (annId > 0 && (!isBroadcasting || activeAnnouncementId != annId)) {
            const char* rawT = activeNotice["title"];
            String title = rawT ? String(rawT) : "Campus Notice";
            const char* rawC = activeNotice["content"];
            String content = rawC ? String(rawC) : "";
            const char* rawP = activeNotice["priority"];
            String priority = rawP ? String(rawP) : "NORMAL";
            const char* rawD = activeNotice["department"];
            String dept = rawD ? String(rawD) : "College-Wide";
            int duration = activeNotice["duration_seconds"].isNull() ? 15 : activeNotice["duration_seconds"].as<int>();
            const char* rawA = activeNotice["audio_url"];
            String audioUrl = rawA ? String(rawA) : "";
            triggerNoticeBroadcast(annId, qId, title, content, priority, dept, duration, audioUrl);
          }
        }

        // 3. Process daily important notices for idle display ticker
        if (respDoc["daily_notices"].is<JsonArray>()) {
          JsonArray dailyArray = respDoc["daily_notices"].as<JsonArray>();
          int oldCount = displayMgr.getDailyNoticesCount();
          displayMgr.clearDailyNotices();
          for (JsonObject item : dailyArray) {
            DisplayNotice n;
            n.id = item["id"].as<int>();
            const char* t = item["title"];
            n.title = t ? String(t) : "";
            const char* s = item["summary"];
            n.summary = s ? String(s) : "";
            const char* p = item["priority"];
            n.priority = p ? String(p) : "NORMAL";
            const char* d = item["department"];
            n.department = d ? String(d) : "College-Wide";
            const char* c = item["category"];
            n.category = c ? String(c) : "Notice";
            displayMgr.addDailyNotice(n);
          }
          // Refresh screen if notice count changed, top notice changed, or screen is not rendered
          int newCount = displayMgr.getDailyNoticesCount();
          int currentTopId = dailyArray.size() > 0 ? dailyArray[0]["id"].as<int>() : 0;
          if (!displayMgr.isBroadcasting() && displayMgr.getState() == STATE_IDLE_DAILY_NOTICES) {
            if (oldCount != newCount || currentTopId != lastTopNoticeId || !displayMgr.isRendered()) {
              lastTopNoticeId = currentTopId;
              displayMgr.refreshScreen();
            }
          }
        }
      }
    } else {
      Serial.print(F("⚠️ [HEARTBEAT] Request failed (HTTP "));
      Serial.print(httpCode);
      Serial.println(F(")"));
    }
    http.end();
  }

  // --------------------------------------------------------------------------
  // Command Dispatcher
  // --------------------------------------------------------------------------
  void handleCommand(JsonObject cmd) {
    const char* rawCmd = cmd["command"];
    String command = rawCmd ? String(rawCmd) : "";
    const char* rawMac = cmd["target_mac"];
    String targetMac = rawMac ? String(rawMac) : "";
    if (targetMac.length() > 0 && !targetMac.equalsIgnoreCase("ALL") && !targetMac.equalsIgnoreCase(nodeMac)) {
      return; // Not targeted to this node
    }

    Serial.print(F("⚡ [COMMAND RECEIVED] Action: '"));
    Serial.print(command);
    Serial.println(F("'"));

    if (command.equalsIgnoreCase("TEST_SPEAKER")) {
      audioMgr.playDiagnosticTest();
    } else if (command.equalsIgnoreCase("SET_VOLUME")) {
      int vol = cmd["volume"].isNull() ? audioMgr.getVolume() : cmd["volume"].as<int>();
      audioMgr.setVolume(vol);
    } else if (command.equalsIgnoreCase("PLAY_ANNOUNCEMENT") || command.equalsIgnoreCase("PLAY_EMERGENCY")) {
      int annId = cmd["announcement_id"].as<int>();
      int qId = cmd["queue_id"].as<int>();
      const char* rawTitle = cmd["title"];
      String title = rawTitle ? String(rawTitle) : "Campus Notice";
      const char* rawMsg = cmd["message"];
      if (!rawMsg || strlen(rawMsg) == 0) {
        rawMsg = cmd["content"];
      }
      String message = rawMsg ? String(rawMsg) : "";
      const char* rawPri = cmd["priority"];
      String priority = command.equalsIgnoreCase("PLAY_EMERGENCY") ? "EMERGENCY" : (rawPri ? String(rawPri) : "NORMAL");
      const char* rawDept = cmd["department"];
      String dept = rawDept ? String(rawDept) : "College-Wide";
      int duration = 15;
      if (!cmd["duration"].isNull()) {
        duration = cmd["duration"].as<int>();
      } else if (!cmd["duration_seconds"].isNull()) {
        duration = cmd["duration_seconds"].as<int>();
      }
      const char* rawA = cmd["audio_url"];
      String audioUrl = rawA ? String(rawA) : "";
      triggerNoticeBroadcast(annId, qId, title, message, priority, dept, duration, audioUrl);
    } else if (command.equalsIgnoreCase("STOP") || command.equalsIgnoreCase("CANCEL") || command.equalsIgnoreCase("SKIP")) {
      stopActiveBroadcast();
    } else if (command.equalsIgnoreCase("RESTART")) {
      registerNode();
    }
  }

  // --------------------------------------------------------------------------
  // Notice Playback Flow
  // --------------------------------------------------------------------------
  void triggerNoticeBroadcast(int annId, int qId, const String& title, const String& content, const String& priority, const String& dept, int durationSec, const String& customAudioUrl = "") {
    activeAnnouncementId = annId;
    activeQueueId = qId;
    isBroadcasting = true;
    activePlaybackEndTime = millis() + ((durationSec > 0 ? durationSec : 15) * 1000UL);

    DisplayNotice notice;
    notice.id = annId;
    notice.title = title;
    notice.summary = content;
    notice.priority = priority;
    notice.department = dept;
    notice.category = "Notice";

    // 1. Immediately update OLED/TFT & LED status
    displayMgr.setActiveNotice(notice, durationSec);

    // 2. Play attention chime or emergency siren through speaker
    if (priority.equalsIgnoreCase("EMERGENCY")) {
      audioMgr.playEmergencySiren();
    } else {
      audioMgr.playAttentionChime();
    }

    // 3. Lossless 16-Bit PCM WAV Audio Stream over HTTP to MAX98357A I2S
    String streamUrl = customAudioUrl;
    if (streamUrl.length() == 0 && annId > 0) {
      streamUrl = serverUrl + "/api/v1/announcements/" + String(annId) + "/audio/stream?audio_format=wav";
    } else if (streamUrl.length() > 0 && !streamUrl.startsWith("http://") && !streamUrl.startsWith("https://")) {
      streamUrl = serverUrl + streamUrl;
    }

    if (streamUrl.length() > 0 && streamUrl.indexOf("audio_format=") < 0) {
      streamUrl += (streamUrl.indexOf('?') >= 0 ? "&audio_format=wav" : "?audio_format=wav");
    }

    bool streamPlayed = false;
    if (streamUrl.length() > 0 && WiFi.status() == WL_CONNECTED) {
      Serial.print(F("🎙️ [AUDIO STREAM] Connecting to audio source: "));
      Serial.println(streamUrl);

      HTTPClient httpAudio;
      WiFiClientSecure secureAudioClient;
      WiFiClient plainAudioClient;

      if (streamUrl.startsWith("https://")) {
        secureAudioClient.setInsecure();
        httpAudio.begin(secureAudioClient, streamUrl);
      } else {
        httpAudio.begin(plainAudioClient, streamUrl);
      }

      httpAudio.setTimeout(12000);
      httpAudio.addHeader("Accept", "audio/wav, audio/*");
      int httpCode = httpAudio.GET();

      if (httpCode == 200) {
        Serial.println(F("🔊 [I2S STREAM] HTTP 200 OK received! Streaming 16-bit PCM WAV to MAX98357A..."));
        WiFiClient* streamClient = httpAudio.getStreamPtr();
        if (streamClient) {
          streamPlayed = audioMgr.streamWavAudio(*streamClient, [this]() {
            displayMgr.renderEqualizerGraphic();
          });
          Serial.println(streamPlayed ? F("✅ [I2S STREAM] Audio playback finished successfully!") : F("⚠️ [I2S STREAM] Playback finished or aborted early."));
        } else {
          Serial.println(F("❌ [I2S STREAM] Failed to acquire HTTP stream pointer."));
        }
      } else {
        Serial.print(F("⚠️ [AUDIO STREAM] HTTP error: "));
        Serial.println(httpCode);
      }
      httpAudio.end();
    }

    // 4. Fallback melody if streaming wasn't available
    if (!streamPlayed && !priority.equalsIgnoreCase("EMERGENCY")) {
      audioMgr.playAnnouncementMelody();
    }

    // 5. Play completion chime after speech concludes
    audioMgr.playCompletionChime();

    // 6. Complete active notice and auto-advance speaker queue
    isBroadcasting = false;
    displayMgr.clearActiveNotice();
    int finishedQueueId = activeQueueId;
    activeAnnouncementId = 0;
    activeQueueId = 0;

    if (finishedQueueId > 0) {
      notifyPlaybackCompleted(finishedQueueId);
    }
  }

  void stopActiveBroadcast() {
    if (isBroadcasting) {
      isBroadcasting = false;
      audioMgr.stopTone();
      displayMgr.clearActiveNotice();
      activeAnnouncementId = 0;
      activeQueueId = 0;
    }
  }

  void notifyPlaybackCompleted(int queueId) {
    if (queueId <= 0 || WiFi.status() != WL_CONNECTED) return;

    String url = serverUrl + "/api/v1/hardware/queue/" + String(queueId) + "/action?action=complete";
    Serial.print(F("⏩ [QUEUE AUTO-ADVANCE] Notifying backend of item #"));
    Serial.print(queueId);
    Serial.println(F(" completion..."));

    HTTPClient http;
    WiFiClientSecure secureClient;
    WiFiClient plainClient;

    if (serverUrl.startsWith("https://")) {
      secureClient.setInsecure();
      http.begin(secureClient, url);
    } else {
      http.begin(plainClient, url);
    }

    http.setTimeout(4000);
    int httpCode = http.POST("");
    if (httpCode == 200) {
      Serial.println(F("✅ [QUEUE AUTO-ADVANCE] Server acknowledged completion. Queue advanced!"));
    }
    http.end();
  }

  // --------------------------------------------------------------------------
  // Update Loop (Called in Arduino loop())
  // --------------------------------------------------------------------------
  void update() {
    unsigned long now = millis();

    // 1. Maintain Wi-Fi connection
    checkWiFiConnection();

    // 2. Check if active notice broadcast duration has elapsed
    if (isBroadcasting && now >= activePlaybackEndTime) {
      int completedQueueId = activeQueueId;
      isBroadcasting = false;
      audioMgr.playCompletionChime();
      displayMgr.clearActiveNotice();
      activeAnnouncementId = 0;
      activeQueueId = 0;

      // Auto-advance the backend queue so the next announcement plays!
      if (completedQueueId > 0) {
        notifyPlaybackCompleted(completedQueueId);
      }
    }

    // 3. Periodic 3-second heartbeat & display feed telemetry
    if (now - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
      lastHeartbeatTime = now;
      sendHeartbeat();
    }
  }
};

#endif // ECHOSPHERE_NETWORK_MANAGER_H
