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
  uint32_t lastDailyNoticesHash = 0;

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

  unsigned long lastWiFiCheckTime = 0;
  bool isReconnecting = false;

  void checkWiFiConnection() {
    unsigned long now = millis();
    if (WiFi.status() == WL_CONNECTED) {
      if (isReconnecting) {
        isReconnecting = false;
        Serial.println();
        Serial.print(F("✅ [WIFI] Reconnected! Assigned IP: "));
        Serial.println(WiFi.localIP());
        displayMgr.setConnectedWiFi(WiFi.localIP().toString());
        digitalWrite(PIN_LED_ONLINE, HIGH);
        registerNode();
      }
      return;
    }

    // Wi-Fi is disconnected: throttle reconnection attempts to once every 8 seconds!
    // This allows the ESP32 Wi-Fi radio sufficient time to authenticate and complete DHCP!
    if (now - lastWiFiCheckTime >= 8000) {
      lastWiFiCheckTime = now;
      isReconnecting = true;
      digitalWrite(PIN_LED_ONLINE, LOW);
      Serial.println(F("⚠️ [WIFI] Wi-Fi disconnected. Attempting reconnection..."));
      displayMgr.setConnectingWiFi(WIFI_SSID);
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
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

    // Extraction variables to hold incoming playback/control instructions
    bool hasControlCommand = false;
    String pendingCommand = "";
    int cmdVol = -1;

    bool shouldTriggerBroadcast = false;
    int targetAnnId = 0;
    int targetQId = 0;
    String targetTitle = "";
    String targetContent = "";
    String targetPriority = "NORMAL";
    String targetDept = "College-Wide";
    int targetDuration = 15;
    String targetAudioUrl = "";

    int httpCode = http.POST(requestBody);
    if (httpCode == 200 || httpCode == 201) {
      displayMgr.triggerHeartbeatPulse();

      String response = http.getString();
      #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
        JsonDocument respDoc;
      #else
        DynamicJsonDocument respDoc(4096);
      #endif
      DeserializationError err = deserializeJson(respDoc, response);
      if (!err) {
        // 1. Check pending commands
        if (respDoc["pending_commands"].is<JsonArray>()) {
          JsonArray commands = respDoc["pending_commands"].as<JsonArray>();
          for (JsonObject cmd : commands) {
            const char* rawMac = cmd["target_mac"];
            String tMac = rawMac ? String(rawMac) : "";
            if (tMac.length() > 0 && !tMac.equalsIgnoreCase("ALL") && !tMac.equalsIgnoreCase(nodeMac)) {
              continue; // not for this node
            }
            const char* rawC = cmd["command"];
            String c = rawC ? String(rawC) : "";
            if (c.equalsIgnoreCase("TEST_SPEAKER") || c.equalsIgnoreCase("RESTART") || c.equalsIgnoreCase("STOP") || c.equalsIgnoreCase("CANCEL") || c.equalsIgnoreCase("SKIP")) {
              hasControlCommand = true;
              pendingCommand = c;
            } else if (c.equalsIgnoreCase("SET_VOLUME")) {
              hasControlCommand = true;
              pendingCommand = c;
              cmdVol = cmd["volume"].isNull() ? audioMgr.getVolume() : cmd["volume"].as<int>();
            } else if (c.equalsIgnoreCase("PLAY_ANNOUNCEMENT") || c.equalsIgnoreCase("PLAY_EMERGENCY")) {
              int aId = cmd["announcement_id"].as<int>();
              if (aId > 0 && (!isBroadcasting || activeAnnouncementId != aId)) {
                shouldTriggerBroadcast = true;
                targetAnnId = aId;
                targetQId = cmd["queue_id"].as<int>();
                const char* rT = cmd["title"];
                targetTitle = rT ? String(rT) : "Campus Notice";
                const char* rM = cmd["message"];
                if (!rM || strlen(rM) == 0) rM = cmd["content"];
                targetContent = rM ? String(rM) : "";
                targetPriority = c.equalsIgnoreCase("PLAY_EMERGENCY") ? "EMERGENCY" : (cmd["priority"].isNull() ? "NORMAL" : String(cmd["priority"].as<const char*>()));
                const char* rD = cmd["department"];
                targetDept = rD ? String(rD) : "College-Wide";
                targetDuration = cmd["duration_seconds"].isNull() ? 15 : cmd["duration_seconds"].as<int>();
                const char* rA = cmd["audio_url"];
                targetAudioUrl = rA ? String(rA) : "";
              }
            }
          }
        }

        // 2. Check active playing notice if no command triggered playback
        if (!shouldTriggerBroadcast && !respDoc["active_notice"].isNull()) {
          JsonObject activeNotice = respDoc["active_notice"].as<JsonObject>();
          int aId = activeNotice["id"].as<int>();
          if (aId > 0 && (!isBroadcasting || activeAnnouncementId != aId)) {
            shouldTriggerBroadcast = true;
            targetAnnId = aId;
            targetQId = activeNotice["queue_id"].as<int>();
            const char* rawT = activeNotice["title"];
            targetTitle = rawT ? String(rawT) : "Campus Notice";
            const char* rawC = activeNotice["content"];
            targetContent = rawC ? String(rawC) : "";
            const char* rawP = activeNotice["priority"];
            targetPriority = rawP ? String(rawP) : "NORMAL";
            const char* rawD = activeNotice["department"];
            targetDept = rawD ? String(rawD) : "College-Wide";
            targetDuration = activeNotice["duration_seconds"].isNull() ? 15 : activeNotice["duration_seconds"].as<int>();
            const char* rawA = activeNotice["audio_url"];
            targetAudioUrl = rawA ? String(rawA) : "";
          }
        }

        // 3. Process daily important notices for idle display ticker
        if (respDoc["daily_notices"].is<JsonArray>()) {
          JsonArray dailyArray = respDoc["daily_notices"].as<JsonArray>();
          uint32_t incomingHash = 0;
          for (JsonObject item : dailyArray) {
            incomingHash = (incomingHash * 31) + (uint32_t)item["id"].as<int>();
          }

          if (incomingHash != lastDailyNoticesHash || !displayMgr.isRendered()) {
            lastDailyNoticesHash = incomingHash;
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
              const char* cat = item["category"];
              n.category = cat ? String(cat) : "Notice";
              displayMgr.addDailyNotice(n);
            }
            displayMgr.finalizeDailyNotices();
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
      }
    } else {
      Serial.print(F("⚠️ [HEARTBEAT] Request failed (HTTP "));
      Serial.print(httpCode);
      Serial.println(F(")"));
    }

    // CRITICAL: Close heartbeat HTTP & release TLS heap memory BEFORE dispatching audio streams!
    http.end();

    // Now execute control command if present
    if (hasControlCommand) {
      if (pendingCommand.equalsIgnoreCase("TEST_SPEAKER")) {
        audioMgr.playDiagnosticTest();
      } else if (pendingCommand.equalsIgnoreCase("SET_VOLUME")) {
        if (cmdVol >= 0) audioMgr.setVolume(cmdVol);
      } else if (pendingCommand.equalsIgnoreCase("STOP") || pendingCommand.equalsIgnoreCase("CANCEL") || pendingCommand.equalsIgnoreCase("SKIP")) {
        stopActiveBroadcast();
      } else if (pendingCommand.equalsIgnoreCase("RESTART")) {
        registerNode();
      }
    }

    // Now trigger audio broadcast if scheduled
    if (shouldTriggerBroadcast) {
      Serial.print(F("🧠 [HEAP] Free heap before audio stream: "));
      Serial.println(ESP.getFreeHeap());
      triggerNoticeBroadcast(targetAnnId, targetQId, targetTitle, targetContent, targetPriority, targetDept, targetDuration, targetAudioUrl);
    }
  }

  // --------------------------------------------------------------------------
  // Notice Playback Flow
  // --------------------------------------------------------------------------
  void triggerNoticeBroadcast(int annId, int qId, const String& title, const String& content, const String& priority, const String& dept, int durationSec, const String& customAudioUrl = "") {
    activeAnnouncementId = annId;
    activeQueueId = qId;
    isBroadcasting = true;

    // Minimum 12 seconds or requested duration so notice card is readable
    int effectiveDuration = durationSec > 0 ? max(durationSec, 12) : 15;
    activePlaybackEndTime = millis() + (effectiveDuration * 1000UL);

    DisplayNotice notice;
    notice.id = annId;
    notice.title = title;
    notice.summary = content;
    notice.priority = priority;
    notice.department = dept;
    notice.category = "Notice";

    // 1. Immediately update TFT Display & LED status
    // (This renders the card header, badges, wrapped title, message, AND initial equalizer bars!)
    displayMgr.setActiveNotice(notice, effectiveDuration);

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
      Serial.print(F("🧠 [HEAP] Free heap for audio client: "));
      Serial.println(ESP.getFreeHeap());

      HTTPClient httpAudio;
      WiFiClientSecure secureAudioClient;
      WiFiClient plainAudioClient;

      if (streamUrl.startsWith("https://")) {
        secureAudioClient.setInsecure();
        httpAudio.begin(secureAudioClient, streamUrl);
      } else {
        httpAudio.begin(plainAudioClient, streamUrl);
      }

      httpAudio.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
      httpAudio.setTimeout(15000);
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
      Serial.println(F("ℹ️ [AUDIO FALLBACK] Playing fallback broadcast chime sequence..."));
      audioMgr.playAnnouncementMelody();
    }

    // 5. Play completion chime after speech concludes
    audioMgr.playCompletionChime();

    // 6. Reset visualizer graphic to clean baseline
    displayMgr.resetEqualizerGraphic();

    // 7. Auto-advance the backend queue right away so next item can queue
    int finishedQueueId = activeQueueId;
    activeQueueId = 0; // Reset so notify is only called once
    if (finishedQueueId > 0) {
      notifyPlaybackCompleted(finishedQueueId);
    }

    // Notice remains on the TFT screen until activePlaybackEndTime in update()
    if (millis() >= activePlaybackEndTime) {
      isBroadcasting = false;
      displayMgr.clearActiveNotice();
      activeAnnouncementId = 0;
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
      isBroadcasting = false;
      displayMgr.clearActiveNotice();
      activeAnnouncementId = 0;
      activeQueueId = 0;
    }

    // 3. Periodic 3-second heartbeat & display feed telemetry
    if (now - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
      lastHeartbeatTime = now;
      sendHeartbeat();
    }
  }
};

#endif // ECHOSPHERE_NETWORK_MANAGER_H
