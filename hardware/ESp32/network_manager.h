#ifndef ECHOSPHERE_NETWORK_MANAGER_H
#define ECHOSPHERE_NETWORK_MANAGER_H

#include "config.h"
#include "arduino_compat.h"


#include "display_manager.h"
#include "audio_manager.h"
#include <WebSocketsClient.h>

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

  // One persistent TLS session to the backend, reused by heartbeats, the audio stream and the
  // completion callback. A fresh TLS handshake costs ~1s on the ESP32, and heartbeats run every
  // 0.8s, so reusing it removes most of the delay before a notice starts. Only one TLS session
  // ever exists, so heap use is the same as before.
  WiFiClientSecure backendClient;
  bool backendClientConfigured = false;

  WiFiClientSecure& sharedTlsClient() {
    if (!backendClientConfigured) {
      backendClient.setInsecure();
      backendClientConfigured = true;
    }
    return backendClient;
  }

  // Push channel: the backend sends commands down this socket the moment they are queued,
  // so a new notice starts without waiting for the next heartbeat. Heartbeats stay as fallback.
  WebSocketsClient pushSocket;
  bool pushStarted = false;
  bool pushConnected = false;
  // While a notice streams, pushed messages wait here and run when the stream ends
  bool streamInProgress = false;
  static const int MAX_DEFERRED_PUSH = 4;
  String deferredPush[MAX_DEFERRED_PUSH];
  int deferredPushCount = 0;

  String currentStatus = "ONLINE";
  int activeAnnouncementId = 0;
  int activeQueueId = 0;
  unsigned long activePlaybackEndTime = 0;
  bool isBroadcasting = false;

  unsigned long lastHeartbeatTime = 0;
  unsigned long lastQueueCheckTime = 0;

  // Asynchronous broadcast scheduling (allows heartbeat TLS memory to release before audio stream)
  bool pendingBroadcastScheduled = false;
  int pendingTargetAnnId = 0;
  int pendingTargetQId = 0;
  String pendingTargetTitle = "";
  String pendingTargetContent = "";
  String pendingTargetPriority = "NORMAL";
  String pendingTargetDept = "College-Wide";
  int pendingTargetDuration = 15;
  String pendingTargetAudioUrl = "";
  static const int MAX_EXECUTED_CMDS = 16;
  String executedCommandIds[MAX_EXECUTED_CMDS];
  int executedCmdIndex = 0;

  bool isCommandExecuted(const String& cmdId) const {
    if (cmdId.length() == 0) return false;
    for (int i = 0; i < MAX_EXECUTED_CMDS; i++) {
      if (executedCommandIds[i] == cmdId) return true;
    }
    return false;
  }

  void markCommandExecuted(const String& cmdId) {
    if (cmdId.length() == 0) return;
    executedCommandIds[executedCmdIndex] = cmdId;
    executedCmdIndex = (executedCmdIndex + 1) % MAX_EXECUTED_CMDS;
  }

  int pendingTargetRound = 1;
  int activeRepeatRound = 1;

  struct CompletedNoticeRecord {
    int annId = 0;
    int round = 0;
    int queueId = 0;
    unsigned long completedAt = 0;
  };
  static const int MAX_COMPLETED_ANNS = 16;
  CompletedNoticeRecord completedAnnouncements[MAX_COMPLETED_ANNS];
  int completedAnnIndex = 0;

  bool isAnnouncementCompleted(int annId, int round = 0, int queueId = 0) const {
    if (annId <= 0 && queueId <= 0) return false;
    unsigned long now = millis();
    for (int i = 0; i < MAX_COMPLETED_ANNS; i++) {
      bool qMatch = (queueId > 0 && completedAnnouncements[i].queueId == queueId);
      bool aMatch = (annId > 0 && completedAnnouncements[i].annId == annId);
      bool rMatch = (round == 0 || completedAnnouncements[i].round == 0 || completedAnnouncements[i].round == round);
      if ((qMatch || aMatch) && rMatch) {
        // Cooldown of 45 seconds prevents REST heartbeats from re-triggering the same queue item/round
        if (now - completedAnnouncements[i].completedAt < 45000UL) {
          return true;
        }
      }
    }
    return false;
  }

  void markAnnouncementCompleted(int annId, int round = 1, int queueId = 0) {
    if (annId <= 0 && queueId <= 0) return;
    completedAnnouncements[completedAnnIndex].annId = annId;
    completedAnnouncements[completedAnnIndex].round = round;
    completedAnnouncements[completedAnnIndex].queueId = queueId;
    completedAnnouncements[completedAnnIndex].completedAt = millis();
    completedAnnIndex = (completedAnnIndex + 1) % MAX_COMPLETED_ANNS;
    lastCompletedAnnouncementId = annId;
    lastCompletedAnnouncementTime = millis();
  }

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
  int lastCompletedAnnouncementId = 0;
  unsigned long lastCompletedAnnouncementTime = 0;

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
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(true);

    Serial.print(F("📶 [WIFI] Connecting to Primary SSID: "));
    Serial.println(WIFI_SSID);
    displayMgr.setConnectingWiFi(WIFI_SSID);

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

#ifdef WIFI_FALLBACK_SSID
    // If primary SSID timed out, try secondary / fallback SSID
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println();
      Serial.print(F("📶 [WIFI] Primary timed out. Trying Fallback SSID: "));
      Serial.println(WIFI_FALLBACK_SSID);
      displayMgr.setConnectingWiFi(WIFI_FALLBACK_SSID);
      WiFi.disconnect();
      WiFi.begin(WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD);

      startAttempt = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < WIFI_TIMEOUT_MS) {
        delay(300);
        Serial.print(F("."));
        ledToggle = !ledToggle;
        digitalWrite(PIN_LED_ONLINE, ledToggle ? HIGH : LOW);
        digitalWrite(PIN_LED_ONBOARD, ledToggle ? HIGH : LOW);
      }
    }
#endif
#ifdef WIFI_ALT_SSID
    // If fallback SSID timed out, try alternative SSID
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println();
      Serial.print(F("📶 [WIFI] Fallback timed out. Trying Alt SSID: "));
      Serial.println(WIFI_ALT_SSID);
      displayMgr.setConnectingWiFi(WIFI_ALT_SSID);
      WiFi.disconnect();
      WiFi.begin(WIFI_ALT_SSID, WIFI_ALT_PASSWORD);

      startAttempt = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < WIFI_TIMEOUT_MS) {
        delay(300);
        Serial.print(F("."));
        ledToggle = !ledToggle;
        digitalWrite(PIN_LED_ONLINE, ledToggle ? HIGH : LOW);
        digitalWrite(PIN_LED_ONBOARD, ledToggle ? HIGH : LOW);
      }
    }
#endif

    if (WiFi.status() == WL_CONNECTED) {
      WiFi.setSleep(false); // Disable Wi-Fi modem sleep to guarantee lowest latency and zero packet jitter for audio streaming!
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
  int wifiRetryCount = 0;

  void checkWiFiConnection() {
    unsigned long now = millis();
    if (WiFi.status() == WL_CONNECTED) {
      if (isReconnecting) {
        isReconnecting = false;
        wifiRetryCount = 0;
        Serial.println();
        Serial.print(F("✅ [WIFI] Reconnected! Assigned IP: "));
        Serial.println(WiFi.localIP());
        displayMgr.setConnectedWiFi(WiFi.localIP().toString());
        digitalWrite(PIN_LED_ONLINE, HIGH);
        registerNode();
      }
      return;
    }

    // Wi-Fi is disconnected: throttle reconnection attempts to once every 12 seconds
    if (now - lastWiFiCheckTime >= 12000) {
      lastWiFiCheckTime = now;
      isReconnecting = true;
      wifiRetryCount++;
      digitalWrite(PIN_LED_ONLINE, LOW);
      Serial.println(F("⚠️ [WIFI] Wi-Fi disconnected. Attempting reconnection..."));

      int cycle = wifiRetryCount % 3;
      if (cycle == 1) {
        displayMgr.setConnectingWiFi(WIFI_FALLBACK_SSID);
        WiFi.disconnect();
        WiFi.begin(WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD);
      } else if (cycle == 2) {
#ifdef WIFI_ALT_SSID
        displayMgr.setConnectingWiFi(WIFI_ALT_SSID);
        WiFi.disconnect();
        WiFi.begin(WIFI_ALT_SSID, WIFI_ALT_PASSWORD);
#else
        displayMgr.setConnectingWiFi(WIFI_SSID);
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
#endif
      } else {
        displayMgr.setConnectingWiFi(WIFI_SSID);
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      }
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
  // Command handling shared by heartbeat responses and the push channel
  // --------------------------------------------------------------------------
  struct BroadcastTarget {
    int annId = 0;
    int qId = 0;
    int round = 1;
    String title = "";
    String content = "";
    String priority = "NORMAL";
    String dept = "College-Wide";
    int duration = 15;
    String audioUrl = "";
  };

  // Reads a pending_commands array. Returns true if a notice should play (filled into target);
  // the last control command lands in controlCmd/cmdVol. Each command_id runs only once.
  bool parsePendingCommands(JsonArray commands, BroadcastTarget& target, String& controlCmd, int& cmdVol) {
    bool shouldTriggerBroadcast = false;
    for (JsonObject cmd : commands) {
      const char* rawMac = cmd["target_mac"];
      String tMac = rawMac ? String(rawMac) : "";
      if (tMac.length() > 0 && !tMac.equalsIgnoreCase("ALL") && !tMac.equalsIgnoreCase(nodeMac)) {
        continue; // not for this node
      }

      // Deduplicate commands by unique ID to prevent repeated replay loops
      String cmdId = "";
      if (!cmd["command_id"].isNull()) {
        cmdId = String(cmd["command_id"].as<const char*>());
      } else if (!cmd["id"].isNull()) {
        cmdId = String(cmd["id"].as<int>());
      }
      if (cmdId.length() > 0 && isCommandExecuted(cmdId)) {
        continue; // already executed this command
      }

      const char* rawC = cmd["command"];
      String c = rawC ? String(rawC) : "";
      if (c.equalsIgnoreCase("TEST_SPEAKER") || c.equalsIgnoreCase("RESTART") || c.equalsIgnoreCase("STOP") || c.equalsIgnoreCase("CANCEL") || c.equalsIgnoreCase("SKIP") || c.equalsIgnoreCase("PAUSE")) {
        controlCmd = c;
        if (cmdId.length() > 0) markCommandExecuted(cmdId);
      } else if (c.equalsIgnoreCase("SET_VOLUME")) {
        controlCmd = c;
        cmdVol = cmd["volume"].isNull() ? audioMgr.getVolume() : cmd["volume"].as<int>();
        if (cmdId.length() > 0) markCommandExecuted(cmdId);
      } else if (c.equalsIgnoreCase("PLAY_ANNOUNCEMENT") || c.equalsIgnoreCase("PLAY_EMERGENCY")) {
        int aId = cmd["announcement_id"].as<int>();
        bool isIncomingEmerg = c.equalsIgnoreCase("PLAY_EMERGENCY") || (!cmd["is_emergency"].isNull() && cmd["is_emergency"].as<bool>());
        const char* rT = cmd["title"];
        if (rT && (strstr(rT, "EMERGENCY") != NULL || strstr(rT, "Emergency") != NULL)) {
          isIncomingEmerg = true;
        }

        // A routine non-emergency notice CANNOT interrupt an ongoing broadcast!
        if (isBroadcasting && !isIncomingEmerg) {
          continue;
        }

        // Pending command deduplication is already guaranteed by isCommandExecuted(cmdId).
        // Never block repeat rounds of the same announcement ID!
        if (aId > 0 && (!isBroadcasting || isIncomingEmerg)) {
          shouldTriggerBroadcast = true;
          target.annId = aId;
          target.qId = cmd["queue_id"].isNull() ? 0 : cmd["queue_id"].as<int>();
          target.round = cmd["repeat_round"].isNull() ? 1 : cmd["repeat_round"].as<int>();
          target.title = rT ? String(rT) : "Campus Notice";
          const char* rM = cmd["message"];
          if (!rM || strlen(rM) == 0) rM = cmd["content"];
          target.content = rM ? String(rM) : "";
          target.priority = (c.equalsIgnoreCase("PLAY_EMERGENCY") || (!cmd["is_emergency"].isNull() && cmd["is_emergency"].as<bool>())) ? "EMERGENCY" : (cmd["priority"].isNull() ? "NORMAL" : String(cmd["priority"].as<const char*>()));
          if (target.title.indexOf("EMERGENCY") >= 0 || target.title.indexOf("Emergency") >= 0 || target.priority.indexOf("EMERG") >= 0 || target.priority.indexOf("emerg") >= 0) {
            target.priority = "EMERGENCY";
          }
          const char* rD = cmd["department"];
          target.dept = rD ? String(rD) : "College-Wide";
          target.duration = cmd["duration_seconds"].isNull() ? 15 : cmd["duration_seconds"].as<int>();
          const char* rA = cmd["audio_url"];
          target.audioUrl = rA ? String(rA) : "";
          if (cmdId.length() > 0) markCommandExecuted(cmdId);
        }
      }
    }
    return shouldTriggerBroadcast;
  }

  // Switches the TFT and status LED to the notice right away, before audio streaming begins
  void showBroadcastCard(const BroadcastTarget& t) {
    int effectiveDuration = t.duration > 0 ? max(t.duration, 4) : 4;
    DisplayNotice notice;
    notice.id = t.annId;
    notice.title = t.title;
    notice.summary = t.content;
    notice.priority = t.priority;
    notice.department = t.dept;
    notice.category = "Notice";

    displayMgr.setActiveNotice(notice, effectiveDuration);
    isBroadcasting = true;
    activeAnnouncementId = t.annId;
    activeQueueId = t.qId;
    activePlaybackEndTime = millis() + (effectiveDuration * 1000UL);
  }

  void runControlCommand(const String& pendingCommand, int cmdVol) {
    if (pendingCommand.equalsIgnoreCase("TEST_SPEAKER")) {
      audioMgr.playDiagnosticTest();
    } else if (pendingCommand.equalsIgnoreCase("SET_VOLUME")) {
      if (cmdVol >= 0) audioMgr.setVolume(cmdVol);
    } else if (pendingCommand.equalsIgnoreCase("STOP") || pendingCommand.equalsIgnoreCase("CANCEL") || pendingCommand.equalsIgnoreCase("SKIP") || pendingCommand.equalsIgnoreCase("PAUSE")) {
      stopActiveBroadcast();
    } else if (pendingCommand.equalsIgnoreCase("RESTART")) {
      registerNode();
    }
  }

  // The audio stream starts on the next update() pass, outside the HTTP / socket callback
  void queuePendingBroadcast(const BroadcastTarget& t) {
    pendingBroadcastScheduled = true;
    pendingTargetAnnId = t.annId;
    pendingTargetQId = t.qId;
    pendingTargetRound = t.round;
    pendingTargetTitle = t.title;
    pendingTargetContent = t.content;
    pendingTargetPriority = t.priority;
    pendingTargetDept = t.dept;
    pendingTargetDuration = t.duration;
    pendingTargetAudioUrl = t.audioUrl;
  }

  // --------------------------------------------------------------------------
  // Push channel (WebSocket /api/v1/ws/speaker/{mac})
  // --------------------------------------------------------------------------
  void startPushChannel() {
    bool secure = serverUrl.startsWith("https://");
    String host = serverUrl.substring(serverUrl.indexOf("://") + 3);
    uint16_t port = secure ? 443 : 80;
    int colon = host.indexOf(':');
    if (colon >= 0) {
      port = (uint16_t)host.substring(colon + 1).toInt();
      host = host.substring(0, colon);
    }
    String path = "/api/v1/ws/speaker/" + nodeMac;
    if (secure) {
      pushSocket.beginSSL(host.c_str(), port, path.c_str());
    } else {
      pushSocket.begin(host.c_str(), port, path.c_str());
    }
    pushSocket.onEvent([this](WStype_t type, uint8_t* payload, size_t length) {
      if (type == WStype_CONNECTED) {
        pushConnected = true;
        Serial.println(F("⚡ [PUSH] Connected: notices now arrive the moment they are published."));
      } else if (type == WStype_DISCONNECTED) {
        if (pushConnected) Serial.println(F("⚡ [PUSH] Disconnected; heartbeats deliver commands until it reconnects."));
        pushConnected = false;
      } else if (type == WStype_TEXT) {
        handlePushMessage(payload, length);
      } else if (type == WStype_ERROR) {
        Serial.println(F("⚡ [PUSH] Socket error."));
      }
    });
    pushSocket.setReconnectInterval(5000);
    // After a server restart Render's proxy can leave this side of the socket open with nothing
    // behind it, and no close ever arrives. Ping every 15s; two missed pongs drop and reconnect.
    pushSocket.enableHeartbeat(15000, 3000, 2);
    pushStarted = true;
  }

  // The library reads only one handshake header line per loop() call, and a heartbeat blocks the
  // main loop for ~1s, so a single call per pass let the handshake time out. Drain several per pass.
  void servicePushChannel() {
    for (int i = 0; i < 16; i++) pushSocket.loop();
  }

  void runDeferredPushMessages() {
    for (int i = 0; i < deferredPushCount; i++) {
      handlePushMessage((uint8_t*)deferredPush[i].c_str(), deferredPush[i].length());
      deferredPush[i] = "";
    }
    deferredPushCount = 0;
  }

  void handlePushMessage(uint8_t* payload, size_t length) {
    if (streamInProgress) {
      // A pause/stop silences the speaker at once; everything else waits until the stream ends
      String msg((const char*)payload, length);
      if (msg.indexOf("\"PAUSE\"") >= 0 || msg.indexOf("\"STOP\"") >= 0 || msg.indexOf("\"CANCEL\"") >= 0 || msg.indexOf("\"SKIP\"") >= 0) {
        Serial.println(F("⚡ [PUSH] Stop received during playback: ending the stream now."));
        audioMgr.requestStreamStop();
      }
      if (deferredPushCount < MAX_DEFERRED_PUSH) {
        deferredPush[deferredPushCount++] = msg;
      }
      return;
    }
    #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
      JsonDocument doc;
    #else
      DynamicJsonDocument doc(4096);
    #endif
    DeserializationError err = deserializeJson(doc, payload, length);
    if (err || !doc["pending_commands"].is<JsonArray>()) {
      Serial.print(F("⚡ [PUSH] Ignored message ("));
      Serial.print(length);
      Serial.print(F(" bytes): "));
      Serial.println(err ? err.c_str() : "no pending_commands");
      return;
    }

    BroadcastTarget target;
    String controlCmd = "";
    int cmdVol = -1;
    bool shouldTriggerBroadcast = parsePendingCommands(doc["pending_commands"].as<JsonArray>(), target, controlCmd, cmdVol);
    if (!shouldTriggerBroadcast && controlCmd.length() == 0) {
      Serial.println(F("⚡ [PUSH] Command received; already handled or not for this speaker."));
    }
    if (shouldTriggerBroadcast) {
      Serial.print(F("⚡ [PUSH] Play command received for notice #"));
      Serial.println(target.annId);
      showBroadcastCard(target);
    }
    if (controlCmd.length() > 0) {
      Serial.print(F("⚡ [PUSH] Control command received: "));
      Serial.println(controlCmd);
      runControlCommand(controlCmd, cmdVol);
    }
    if (shouldTriggerBroadcast) queuePendingBroadcast(target);
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
    WiFiClient plainClient;
    http.setReuse(true);  // keep the TLS session open between heartbeats

    if (serverUrl.startsWith("https://")) {
      http.begin(sharedTlsClient(), url);
    } else {
      http.begin(plainClient, url);
    }

    http.addHeader("Content-Type", "application/json");
    http.setTimeout(4000);

    // Extraction variables to hold incoming playback/control instructions
    String pendingCommand = "";
    int cmdVol = -1;
    bool shouldTriggerBroadcast = false;
    BroadcastTarget target;

    int httpCode = http.POST(requestBody);
    if (httpCode == 200 || httpCode == 201) {
      displayMgr.triggerHeartbeatPulse();

      String response = http.getString();
      #if defined(ARDUINOJSON_VERSION_MAJOR) && (ARDUINOJSON_VERSION_MAJOR >= 7)
        JsonDocument respDoc;
      #else
        DynamicJsonDocument respDoc(8192);
      #endif
      DeserializationError err = deserializeJson(respDoc, response);
      if (!err) {
        // 1. Check pending commands
        if (respDoc["pending_commands"].is<JsonArray>()) {
          shouldTriggerBroadcast = parsePendingCommands(respDoc["pending_commands"].as<JsonArray>(), target, pendingCommand, cmdVol);
        }

        // 2. Check active playing notice if no command triggered playback
        if (!shouldTriggerBroadcast && !respDoc["active_notice"].isNull()) {
          JsonObject activeNotice = respDoc["active_notice"].as<JsonObject>();
          int aId = activeNotice["id"].as<int>();
          int qId = activeNotice["queue_id"].isNull() ? 0 : activeNotice["queue_id"].as<int>();
          int repRound = activeNotice["repeat_round"].isNull() ? 1 : activeNotice["repeat_round"].as<int>();
          bool isJustCompleted = isAnnouncementCompleted(aId, repRound, qId);
          if (aId > 0 && !isJustCompleted && (!isBroadcasting || activeAnnouncementId != aId)) {
            shouldTriggerBroadcast = true;
            target.annId = aId;
            target.qId = qId;
            target.round = repRound;
            const char* rawT = activeNotice["title"];
            target.title = rawT ? String(rawT) : "Campus Notice";
            const char* rawC = activeNotice["content"];
            target.content = rawC ? String(rawC) : "";
            const char* rawP = activeNotice["priority"];
            target.priority = rawP ? String(rawP) : "NORMAL";
            if (!activeNotice["is_emergency"].isNull() && activeNotice["is_emergency"].as<bool>()) {
              target.priority = "EMERGENCY";
            }
            if (target.title.indexOf("EMERGENCY") >= 0 || target.title.indexOf("Emergency") >= 0 || target.priority.indexOf("EMERG") >= 0 || target.priority.indexOf("emerg") >= 0) {
              target.priority = "EMERGENCY";
            }
            const char* rawD = activeNotice["department"];
            target.dept = rawD ? String(rawD) : "College-Wide";
            target.duration = activeNotice["duration_seconds"].isNull() ? 15 : activeNotice["duration_seconds"].as<int>();
            const char* rawA = activeNotice["audio_url"];
            target.audioUrl = rawA ? String(rawA) : "";
          } else if (isJustCompleted && (isBroadcasting || displayMgr.isBroadcasting() || displayMgr.getState() == STATE_PLAYING_ANNOUNCEMENT)) {
            // Already finished playing this announcement; clean up active notice and return to idle ticker
            isBroadcasting = false;
            activeAnnouncementId = 0;
            activeQueueId = 0;
            displayMgr.clearActiveNotice();
          }
        } else if (!shouldTriggerBroadcast && respDoc["active_notice"].isNull() && !pendingBroadcastScheduled) {
          // Backend has no active notice: ensure node is never stuck on "NOW BROADCASTING"
          if (isBroadcasting || displayMgr.isBroadcasting() || displayMgr.getState() == STATE_PLAYING_ANNOUNCEMENT) {
            Serial.println(F("⏹️ [HEARTBEAT SYNC] Backend has no active notice. Exiting broadcast mode."));
            isBroadcasting = false;
            activeAnnouncementId = 0;
            activeQueueId = 0;
            displayMgr.clearActiveNotice();
          }
        }

        // 2b. If broadcast was triggered (by pending command or active notice),
        // IMMEDIATELY switch TFT display and status LED to STATE_PLAYING_ANNOUNCEMENT!
        // This guarantees the display leaves idle mode instantly upon push,
        // and renders the active notice before audio streaming begins.
        if (shouldTriggerBroadcast) {
          showBroadcastCard(target);
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
            // Only switch or refresh to idle screen if NOT currently broadcasting or about to broadcast
            if (!displayMgr.isBroadcasting() && !shouldTriggerBroadcast && !pendingBroadcastScheduled) {
              if (displayMgr.getState() != STATE_IDLE_DAILY_NOTICES) {
                displayMgr.setState(STATE_IDLE_DAILY_NOTICES);
              } else if (oldCount != newCount || currentTopId != lastTopNoticeId || !displayMgr.isRendered()) {
                lastTopNoticeId = currentTopId;
                displayMgr.refreshScreen();
              }
            }
          }
        }
      } else {
        Serial.print(F("⚠️ [HEARTBEAT] JSON parse error: "));
        Serial.println(err.c_str());
      }
    } else {
      Serial.print(F("⚠️ [HEARTBEAT] Request failed (HTTP "));
      Serial.print(httpCode);
      Serial.println(F(")"));
      backendClient.stop();  // stale/broken session: reconnect on the next heartbeat
    }

    // Ends this request but keeps the shared TLS session open (setReuse); the audio stream reuses
    // the same session, so there is still only one TLS session in memory.
    http.end();

    // Now execute control command if present
    if (pendingCommand.length() > 0) {
      runControlCommand(pendingCommand, cmdVol);
    }

    // Asynchronously schedule audio broadcast so sendHeartbeat() exits completely
    if (shouldTriggerBroadcast) {
      queuePendingBroadcast(target);
    }
  }

  // --------------------------------------------------------------------------
  // Notice Playback Flow
  // --------------------------------------------------------------------------
  void triggerNoticeBroadcast(int annId, int qId, const String& title, const String& content, const String& priority, const String& dept, int durationSec, const String& customAudioUrl = "", int repeatRound = 1) {
    activeAnnouncementId = annId;
    activeQueueId = qId;
    activeRepeatRound = repeatRound;
    isBroadcasting = true;

    // Minimum 4 seconds or requested duration so notice card is readable
    int effectiveDuration = durationSec > 0 ? max(durationSec, 4) : 4;
    if (millis() + (effectiveDuration * 1000UL) > activePlaybackEndTime) {
      activePlaybackEndTime = millis() + (effectiveDuration * 1000UL);
    }

    String effPriority = priority;
    if (title.indexOf("EMERGENCY") >= 0 || title.indexOf("Emergency") >= 0 ||
        effPriority.indexOf("EMERG") >= 0 || effPriority.indexOf("emerg") >= 0) {
      effPriority = "EMERGENCY";
    }

    DisplayNotice notice;
    notice.id = annId;
    notice.title = title;
    notice.summary = content;
    notice.priority = effPriority;
    notice.department = dept;
    notice.category = "Notice";

    // 1. Immediately update TFT Display & LED status (always render the active notice card)
    displayMgr.setActiveNotice(notice, effectiveDuration);

    // 2. High-Fidelity Speech Audio Stream over HTTPS via Native I2S
    // Note: Chime/Siren is triggered seamlessly via preChimeCallback the moment
    // the stream is connected and verified, guaranteeing 0.0s dead silence between chime and speech!
    String streamUrl = customAudioUrl;
    if (streamUrl.length() == 0 && annId > 0) {
      streamUrl = serverUrl + "/api/v1/announcements/" + String(annId) + "/audio/stream?audio_format=wav&include_chime=false";
    } else if (streamUrl.length() > 0 && !streamUrl.startsWith("http://") && !streamUrl.startsWith("https://")) {
      streamUrl = serverUrl + streamUrl;
    }

    // Always enforce 16-bit PCM WAV for native hardware I2S streaming
    int mp3FormatPos = streamUrl.indexOf("audio_format=mp3");
    if (mp3FormatPos >= 0) {
      streamUrl = streamUrl.substring(0, mp3FormatPos) + "audio_format=wav" + streamUrl.substring(mp3FormatPos + 16);
    } else if (streamUrl.indexOf("audio_format=") < 0) {
      streamUrl += (streamUrl.indexOf('?') >= 0 ? "&audio_format=wav" : "?audio_format=wav");
    }

    // Always enforce include_chime=false because ESP32 plays local attention chime directly
    if (streamUrl.indexOf("include_chime=") < 0) {
      streamUrl += (streamUrl.indexOf('?') >= 0 ? "&include_chime=false" : "?include_chime=false");
    }

    bool streamPlayed = false;
    if (streamUrl.length() > 0 && WiFi.status() == WL_CONNECTED) {
      Serial.print(F("🎙️ [AUDIO STREAM] Streaming 16-bit PCM WAV notice speech via Native I2S: "));
      Serial.println(streamUrl);
      Serial.print(F("🧠 [HEAP] Free heap before stream: "));
      Serial.println(ESP.getFreeHeap());

      streamInProgress = true;
      streamPlayed = audioMgr.playStream(
        streamUrl,
        [this](float progress) {
          displayMgr.renderEqualizerGraphic();
          displayMgr.updateSubtitleProgress(progress);
          if (pushStarted) servicePushChannel();  // answer server pings so the socket survives long notices
        },
        [this, effPriority]() {
          if (effPriority.equalsIgnoreCase("EMERGENCY")) {
            audioMgr.playEmergencySiren();
          } else {
            audioMgr.playAttentionChime();
          }
        },
        streamUrl.startsWith("https://") ? &sharedTlsClient() : nullptr
      );
      streamInProgress = false;

      if (streamPlayed) {
        Serial.println(F("✅ [I2S STREAM] Notice speech playback completed successfully!"));
      } else if (!audioMgr.wasLastStreamPreempted()) {
        Serial.println(F("⚠️ [I2S STREAM] Cloud speech stream unavailable."));
      }
    }

    // 2b. The server stopped the stream (pause/stop/remove/skip or an emergency taking over):
    // skip the completion chime, dwell and 'complete' callback, and ask the backend what to do next.
    if (audioMgr.wasLastStreamPreempted()) {
      Serial.println(F("⏹️ [STREAM STOPPED] Server ended this notice early. Skipping completion chime and notify; checking backend for what plays next."));
      displayMgr.resetEqualizerGraphic();
      isBroadcasting = false;
      activeAnnouncementId = 0;
      activeQueueId = 0;
      // Immediately call sendHeartbeat to fetch and execute emergency broadcast
      sendHeartbeat();
      return;
    }

    // 3. Fallback melody if cloud speech streaming wasn't available
    if (!streamPlayed && !effPriority.equalsIgnoreCase("EMERGENCY")) {
      Serial.println(F("ℹ️ [AUDIO FALLBACK] Playing campus broadcast melody..."));
      audioMgr.playAttentionChime();
      audioMgr.playAnnouncementMelody();
    }


    // 5. Play completion chime after speech concludes (with 350ms natural breathing space)
    delay(350);
    audioMgr.playCompletionChime();

    // 6. Reset visualizer graphic to clean baseline
    displayMgr.resetEqualizerGraphic();

    // Give ESP32 CPU and heap a short breather to clean up buffers
    yield();
    delay(50);

    // 7. Auto-advance the backend queue right away so next item can queue
    int finishedQueueId = activeQueueId;
    int finishedRound = activeRepeatRound;
    activeQueueId = 0; // Reset so notify is only called once
    if (finishedQueueId > 0) {
      notifyPlaybackCompleted(finishedQueueId);
    } else if (annId > 0) {
      notifyPlaybackCompleted(annId);
    }

    // Record as completed to prevent duplicate replay loops
    markAnnouncementCompleted(annId, finishedRound, finishedQueueId);

    // After speech concludes, keep the notice card on screen for 1.5 seconds
    // so viewers have brief time to read, while eliminating delay between close schedule broadcasts
    unsigned long dwellStart = millis();
    while (millis() - dwellStart < 1500UL) {
      displayMgr.tickBroadcastCarousel();
      delay(50);
      yield();
    }

    // GUARANTEED: Explicitly clear active notice and return to idle daily ticker!
    isBroadcasting = false;
    lastCompletedAnnouncementId = annId;
    lastCompletedAnnouncementTime = millis();
    activeAnnouncementId = 0;
    displayMgr.clearActiveNotice();
    Serial.println(F("📺 [DISPLAY] Broadcast completed. Cleanly restored Today's Notices ticker."));

    // ZERO LATENCY NEXT TRACK TRIGGER:
    // Reset lastHeartbeatTime so the very next loop() iteration sends a heartbeat instantly (<10ms)!
    lastHeartbeatTime = 0;
  }

  void stopActiveBroadcast() {
    if (isBroadcasting || pendingBroadcastScheduled) {
      pendingBroadcastScheduled = false;
      isBroadcasting = false;
      audioMgr.stopTone();
      displayMgr.clearActiveNotice();
      lastCompletedAnnouncementId = activeAnnouncementId;
      lastCompletedAnnouncementTime = millis();
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
    WiFiClient plainClient;
    http.setReuse(true);

    if (serverUrl.startsWith("https://")) {
      http.begin(sharedTlsClient(), url);
    } else {
      http.begin(plainClient, url);
    }

    http.setTimeout(8000);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST("{}");
    Serial.print(F("⏩ [QUEUE AUTO-ADVANCE] Server HTTP code: "));
    Serial.println(httpCode);
    if (httpCode == 200) {
      Serial.println(F("✅ [QUEUE AUTO-ADVANCE] Server acknowledged completion. Queue advanced!"));
    }
    http.end();
    if (httpCode <= 0) {
      backendClient.stop();
    }
  }

  // --------------------------------------------------------------------------
  // Update Loop (Called in Arduino loop())
  // --------------------------------------------------------------------------
  void update() {
    unsigned long now = millis();

    // 1. Maintain Wi-Fi connection
    checkWiFiConnection();

    // 2. Check if active notice broadcast duration has elapsed
    if ((isBroadcasting || displayMgr.isBroadcasting() || displayMgr.getState() == STATE_PLAYING_ANNOUNCEMENT) && now >= activePlaybackEndTime) {
      isBroadcasting = false;
      lastCompletedAnnouncementId = activeAnnouncementId;
      lastCompletedAnnouncementTime = millis();
      displayMgr.clearActiveNotice();
      activeAnnouncementId = 0;
      activeQueueId = 0;
    }

    // 2b. Execute pending broadcast outside of sendHeartbeat() call stack
    // (This guarantees the heartbeat WiFiClientSecure is destroyed and its ~45KB TLS buffer freed before audio streaming starts!)
    if (pendingBroadcastScheduled) {
      pendingBroadcastScheduled = false;
      Serial.print(F("🧠 [HEAP] Free heap before audio stream: "));
      Serial.println(ESP.getFreeHeap());
      triggerNoticeBroadcast(pendingTargetAnnId, pendingTargetQId, pendingTargetTitle, pendingTargetContent, pendingTargetPriority, pendingTargetDept, pendingTargetDuration, pendingTargetAudioUrl, pendingTargetRound);
    }

    // 3. Periodic heartbeat & display feed telemetry (a fallback for commands while push is connected)
    unsigned long heartbeatInterval = pushConnected ? PUSH_HEARTBEAT_INTERVAL_MS : HEARTBEAT_INTERVAL_MS;
    if (now - lastHeartbeatTime >= heartbeatInterval) {
      lastHeartbeatTime = now;
      sendHeartbeat();
    }

    // 4. Push channel: delivers commands instantly; runs after playback so a reconnect never delays audio
    if (WiFi.status() == WL_CONNECTED) {
      if (!pushStarted) startPushChannel();
      servicePushChannel();
      if (deferredPushCount > 0 && !streamInProgress) runDeferredPushMessages();
    }
  }
};

#endif // ECHOSPHERE_NETWORK_MANAGER_H
