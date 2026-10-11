#ifndef ECHOSPHERE_DISPLAY_MANAGER_H
#define ECHOSPHERE_DISPLAY_MANAGER_H

#include "config.h"
#include "arduino_compat.h"

// ============================================================================
// 1.8" Color TFT LCD (128x160 SPI ST7735) & Status LED Subsystem
// Landscape Mode: 160 x 128 resolution
// Safe Pin Mapping (< 32): SCLK=18, MOSI=23, CS=5, DC=4, RST=15
// ============================================================================

// 16-Bit RGB565 Color Palette
#define COLOR_BG          0x000F  // Deep Midnight Navy
#define COLOR_PANEL       0x18F0  // Dark Slate
#define COLOR_TEXT_WHITE  0xFFFF  // Pure White
#define COLOR_TEXT_CYAN   0x07FF  // Neon Cyan
#define COLOR_TEXT_GOLD   0xFFE0  // Golden Yellow
#define COLOR_EMERGENCY   0xF800  // Vivid Crimson Red
#define COLOR_URGENT      0xFD20  // Orange
#define COLOR_NORMAL      0x07E0  // Emerald Green
#define COLOR_HEADER_BLUE 0x015A  // Royal Blue

#define MAX_DAILY_NOTICES 10

// Notice Data Structure
struct DisplayNotice {
  int id = 0;
  String title = "";
  String summary = "";
  String priority = "NORMAL";
  String department = "College-Wide";
  String category = "Notice";
};

enum DisplayState {
  STATE_BOOTING,
  STATE_CONNECTING_WIFI,
  STATE_REGISTERING,
  STATE_IDLE_DAILY_NOTICES,
  STATE_PLAYING_ANNOUNCEMENT
};

class DisplayManager {
private:
  Adafruit_ST7735 tft;
  bool isTftReady = false;
  DisplayState currentState = STATE_BOOTING;

  // Active playing notice data
  DisplayNotice activeNotice;
  bool isNoticeActive = false;
  unsigned long playbackStartTime = 0;
  int playbackDurationSeconds = 15;

  // Daily notices list (fixed array for zero heap fragmentation)
  DisplayNotice dailyNotices[MAX_DAILY_NOTICES];
  int dailyNoticesCount = 0;
  int currentDailyNoticeIndex = 0;
  int currentDailyNoticePage = 0;
  unsigned long lastDailyRotateTime = 0;

  // Audio equalizer animation tracking
  int animFrame = 0;
  unsigned long lastAnimTime = 0;
  int prevBarHeights[16] = {0};

  // Heartbeat LED flash tracking (GPIO 22)
  unsigned long heartbeatLedOffTime = 0;
  bool isHeartbeatLedOn = false;

  // Emergency flash tracking (GPIO 21)
  unsigned long lastEmergencyToggleTime = 0;
  bool emergencyLedState = false;

  // Screen redraw optimization flag (prevents repeated redrawing)
  bool isScreenRendered = false;

  // Broadcast auto-paging tracking
  int currentBroadcastPage = 0;
  unsigned long lastBroadcastPageTime = 0;

public:
  // --------------------------------------------------------------------------
  // --------------------------------------------------------------------------
  // Helper: Case-insensitive prefix matcher (zero heap allocations)
  // --------------------------------------------------------------------------
  static bool startsWithIgnoreCase(const String& str, const char* prefix, unsigned int pLen) {
    if (str.length() < pLen) return false;
    for (unsigned int i = 0; i < pLen; i++) {
      char c1 = str.charAt(i);
      char c2 = prefix[i];
      if (c1 >= 'a' && c1 <= 'z') c1 -= 32;
      if (c2 >= 'a' && c2 <= 'z') c2 -= 32;
      if (c1 != c2) return false;
    }
    return true;
  }

  // --------------------------------------------------------------------------
  // Helper: Sanitize title and notice text (removes markdown and redundant prefixes)
  // --------------------------------------------------------------------------
  static String sanitizeTitleText(const String& raw) {
    // 1. Strip markdown formatting symbols (*, _, #, `)
    String clean = "";
    for (unsigned int i = 0; i < raw.length(); i++) {
      char c = raw.charAt(i);
      if (c != '*' && c != '_' && c != '#' && c != '`') {
        clean += c;
      }
    }
    clean.trim();

    // 2. Strip repetitive institutional notice/circular prefixes
    bool stripped = true;
    while (stripped && clean.length() > 0) {
      stripped = false;
      if (startsWithIgnoreCase(clean, "OFFICIAL CIRCULAR:", 18)) { clean = clean.substring(18); stripped = true; }
      else if (startsWithIgnoreCase(clean, "CIRCULAR:", 9)) { clean = clean.substring(9); stripped = true; }
      else if (startsWithIgnoreCase(clean, "OFFICIAL NOTICE:", 16)) { clean = clean.substring(16); stripped = true; }
      else if (startsWithIgnoreCase(clean, "NOTICE:", 7)) { clean = clean.substring(7); stripped = true; }
      else if (startsWithIgnoreCase(clean, "ANNOUNCEMENT:", 13)) { clean = clean.substring(13); stripped = true; }
      else if (startsWithIgnoreCase(clean, "SUMMARY:", 8)) { clean = clean.substring(8); stripped = true; }
      clean.trim();
    }
    return clean.length() > 0 ? clean : raw;
  }

  DisplayManager() : tft(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST) {}

  void begin() {
    // 1. Initialize safe status LED pins (< 32)
    pinMode(PIN_LED_BROADCAST, OUTPUT);
    pinMode(PIN_LED_ONLINE, OUTPUT);
    pinMode(PIN_LED_ONBOARD, OUTPUT);

    #if PIN_TFT_BL >= 0
      pinMode(PIN_TFT_BL, OUTPUT);
      digitalWrite(PIN_TFT_BL, HIGH); // Power backlight if connected to GPIO
    #endif

    // 2. Initialize SPI & 1.8" TFT Display (ST7735)
    SPI.begin(PIN_TFT_SCLK, -1, PIN_TFT_MOSI, PIN_TFT_CS);
    tft.initR(INITR_BLACKTAB); // Standard initialization for 1.8" ST7735 128x160
    tft.setRotation(TFT_ROTATION); // Rotate to 160x128 landscape
    tft.setTextWrap(false);
    tft.fillScreen(COLOR_BG);

    isTftReady = true;
    Serial.println(F("🖥️ [TFT DISPLAY] 1.8\" Color TFT LCD (160x128 ST7735 SPI) initialized in landscape!"));

    // Splash Header
    tft.fillRect(0, 0, 160, 20, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(18, 6);
    tft.print(F("ECHOSPHERE"));

    tft.setTextColor(COLOR_TEXT_CYAN, COLOR_BG);
    tft.setCursor(15, 48);
    tft.print(F("System Initializing..."));
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_BG);
    tft.setCursor(15, 66);
    tft.print(F("Audio: MAX98357A I2S 3W"));
  }

  void setState(DisplayState state) {
    if (state != STATE_PLAYING_ANNOUNCEMENT) {
      isNoticeActive = false;
    }
    if (currentState != state) {
      currentState = state;
      isScreenRendered = false;
      refreshScreen();
    }
  }

  void triggerHeartbeatPulse() {
    // Active heartbeat: Briefly dip Online LED and flash Onboard Blue LED for 100ms
    digitalWrite(PIN_LED_ONLINE, LOW);
    digitalWrite(PIN_LED_ONBOARD, HIGH);
    isHeartbeatLedOn = true;
    heartbeatLedOffTime = millis() + 100;
  }

  void setConnectingWiFi(const String& ssid) {
    if (currentState == STATE_CONNECTING_WIFI && isScreenRendered) return;
    currentState = STATE_CONNECTING_WIFI;
    if (!isTftReady) return;

    tft.fillScreen(COLOR_BG);
    tft.fillRect(0, 0, 160, 20, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(24, 6);
    tft.print(F("CONNECTING WI-FI"));

    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(10, 38);
    tft.print(F("SSID: "));
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_BG);
    tft.println(ssid);

    tft.setTextColor(COLOR_TEXT_CYAN, COLOR_BG);
    tft.setCursor(10, 58);
    tft.println(F("Authenticating..."));
    isScreenRendered = true;
  }

  void setConnectedWiFi(const String& ip) {
    if (currentState == STATE_REGISTERING && isScreenRendered) return;
    currentState = STATE_REGISTERING;
    if (!isTftReady) return;

    tft.fillScreen(COLOR_BG);
    tft.fillRect(0, 0, 160, 20, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(24, 6);
    tft.print(F("WI-FI CONNECTED"));

    tft.setTextColor(COLOR_NORMAL, COLOR_BG);
    tft.setCursor(10, 36);
    tft.print(F("Status: ONLINE"));

    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_BG);
    tft.setCursor(10, 52);
    tft.print(F("IP: "));
    tft.print(ip);

    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(10, 72);
    tft.print(F("Registering with App..."));
    isScreenRendered = true;
  }

  void setActiveNotice(const DisplayNotice& notice, int durationSec = 15) {
    activeNotice = notice;
    activeNotice.title = sanitizeTitleText(notice.title);
    activeNotice.summary = sanitizeTitleText(notice.summary);
    isNoticeActive = true;
    playbackStartTime = millis();
    playbackDurationSeconds = durationSec > 0 ? durationSec : 15;
    currentState = STATE_PLAYING_ANNOUNCEMENT;
    isScreenRendered = false;
    currentBroadcastPage = 0;
    lastBroadcastPageTime = millis();

    // Reset equalizer history
    for (int i = 0; i < 16; i++) {
      prevBarHeights[i] = 0;
    }

    // Broadcasting LED on
    digitalWrite(PIN_LED_BROADCAST, HIGH);
    digitalWrite(PIN_LED_ONBOARD, HIGH);

    printAsciiPlayingBanner(activeNotice);
    refreshScreen();
  }

  void clearActiveNotice() {
    isNoticeActive = false;
    currentBroadcastPage = 0;
    currentState = STATE_IDLE_DAILY_NOTICES;
    isScreenRendered = false;
    resetEqualizerGraphic();

    // Turn off Broadcasting LED
    digitalWrite(PIN_LED_BROADCAST, LOW);
    digitalWrite(PIN_LED_ONBOARD, LOW);

    // CRITICAL: Clean wipe screen to erase broadcasting headers, badges, and card
    if (isTftReady) {
      tft.fillScreen(COLOR_BG);
    }

    Serial.println(F("\n══════════════════════════════════════════════════════════════════════"));
    Serial.println(F("⏹️  [BROADCAST COMPLETE] 1.8\" TFT Returning to Daily Campus Notice Screen"));
    Serial.println(F("══════════════════════════════════════════════════════════════════════\n"));

    refreshScreen();
  }

  void clearDailyNotices() {
    dailyNoticesCount = 0;
    currentDailyNoticeIndex = 0;
    currentDailyNoticePage = 0;
    lastDailyRotateTime = millis();
  }

  void finalizeDailyNotices() {
    if (dailyNoticesCount == 0) {
      currentDailyNoticeIndex = 0;
      currentDailyNoticePage = 0;
    } else {
      if (currentDailyNoticeIndex >= dailyNoticesCount) {
        currentDailyNoticeIndex = 0;
      }
      currentDailyNoticePage = 0;
    }
  }

  void addDailyNotice(const DisplayNotice& notice) {
    if (dailyNoticesCount < MAX_DAILY_NOTICES) {
      DisplayNotice cleanN = notice;
      cleanN.title = sanitizeTitleText(notice.title);
      cleanN.summary = sanitizeTitleText(notice.summary);
      dailyNotices[dailyNoticesCount++] = cleanN;
    }
  }

  int getDailyNoticesCount() const { return dailyNoticesCount; }
  bool isBroadcasting() const { return isNoticeActive; }
  bool isRendered() const { return isScreenRendered; }
  DisplayState getState() const { return currentState; }

  // --------------------------------------------------------------------------
  // Subtitle Synchronization: Advances notice text page smoothly in real-time
  // matching audio stream speech progression!
  // --------------------------------------------------------------------------
  void updateSubtitleProgress(float progressRatio) {
    if (!isNoticeActive || !isTftReady) return;
    String msg = activeNotice.summary.length() > 0 ? activeNotice.summary : activeNotice.title;
    msg = sanitizeTitleText(msg);
    String cleanTitle = sanitizeTitleText(activeNotice.title);
    int titleLines = countWrappedLines(cleanTitle, 24);
    int linesPerPage = (titleLines > 1) ? 4 : 5;
    int totalLines = countWrappedLines(msg, 24);
    int totalPages = (totalLines + linesPerPage - 1) / linesPerPage;
    if (totalPages <= 1) return;

    if (progressRatio < 0.0f) progressRatio = 0.0f;
    if (progressRatio > 1.0f) progressRatio = 1.0f;

    // Calculate exact target page based on speech progress ratio
    int targetPage = (int)(progressRatio * totalPages);
    if (targetPage >= totalPages) targetPage = totalPages - 1;

    if (targetPage != currentBroadcastPage) {
      currentBroadcastPage = targetPage;
      renderPlayingContentCard();
      Serial.print(F("📄 [SUBTITLE SYNC] Speech audio page: "));
      Serial.print(currentBroadcastPage + 1);
      Serial.print(F("/"));
      Serial.print(totalPages);
      Serial.print(F(" (Progress: "));
      Serial.print((int)(progressRatio * 100));
      Serial.println(F("%)"));
    }
  }

  // --------------------------------------------------------------------------
  // Auto-Paging Carousel for Live Broadcast (Used during post-speech dwell)
  // --------------------------------------------------------------------------
  void tickBroadcastCarousel(unsigned long now = 0) {
    if (!isNoticeActive || !isTftReady) return;
    if (now == 0) now = millis();
    if (now - lastBroadcastPageTime >= 3500) {
      lastBroadcastPageTime = now;
      String msg = activeNotice.summary.length() > 0 ? activeNotice.summary : activeNotice.title;
      msg = sanitizeTitleText(msg);
      String cleanTitle = sanitizeTitleText(activeNotice.title);
      int titleLines = countWrappedLines(cleanTitle, 24);
      int linesPerPage = (titleLines > 1) ? 4 : 5;
      int totalLines = countWrappedLines(msg, 24);
      int totalPages = (totalLines + linesPerPage - 1) / linesPerPage;
      if (totalPages > 1) {
        currentBroadcastPage = (currentBroadcastPage + 1) % totalPages;
        renderPlayingContentCard();
        Serial.print(F("📄 [LCD LIVE CAROUSEL] Rotated notice page: "));
        Serial.print(currentBroadcastPage + 1);
        Serial.print(F("/"));
        Serial.println(totalPages);
      }
    }
  }


  // --------------------------------------------------------------------------
  // Helper: Count total lines needed to word-wrap a given text string
  // --------------------------------------------------------------------------
  int countWrappedLines(const String& str, int maxCharsPerLine) const {
    const char* text = str.c_str();
    int len = 0;
    while (text[len] != '\0') len++;
    if (len == 0) return 0;

    int totalLines = 0;
    int currentPos = 0;

    while (currentPos < len) {
      int endPos = currentPos + maxCharsPerLine;
      if (endPos >= len) {
        endPos = len;
      } else {
        int lastSpace = -1;
        for (int i = endPos; i > currentPos; i--) {
          if (text[i] == ' ') {
            lastSpace = i;
            break;
          }
        }
        if (lastSpace > currentPos) {
          endPos = lastSpace;
        }
      }

      while (currentPos < endPos && text[currentPos] == ' ') {
        currentPos++;
      }

      totalLines++;
      currentPos = endPos;
      while (currentPos < len && text[currentPos] == ' ') {
        currentPos++;
      }
    }
    return totalLines;
  }

  // --------------------------------------------------------------------------
  // Helper: Draw word-wrapped text with crisp glyphs and ZERO screen flutter
  // Supports lineOffset to smoothly paginate through long circular/notice text!
  // Uses tft.setTextColor(color, bgColor) to draw glyph and clear background
  // in a single operation without calling fillRect!
  // --------------------------------------------------------------------------
  void drawWrappedText(const String& str, int startX, int startY, int maxCharsPerLine, int maxLines, uint16_t color, uint16_t bgColor, int lineOffset = 0, int linePitch = 10) {
    tft.setTextColor(color, bgColor);
    tft.setTextSize(1);
    tft.setTextWrap(false);

    const char* text = str.c_str();
    int len = 0;
    while (text[len] != '\0') len++;

    int totalLineIdx = 0;
    int visibleLine = 0;
    int currentPos = 0;

    while (currentPos < len && visibleLine < maxLines) {
      // Skip leading spaces or newlines before starting a line
      while (currentPos < len && (text[currentPos] == ' ' || text[currentPos] == '\r' || text[currentPos] == '\n')) {
        currentPos++;
      }
      if (currentPos >= len) break;

      int endPos = currentPos + maxCharsPerLine;
      if (endPos >= len) {
        endPos = len;
      }

      // Check if an explicit newline exists within the current line buffer
      int newlinePos = -1;
      for (int i = currentPos; i < endPos; i++) {
        if (text[i] == '\n' || text[i] == '\r') {
          newlinePos = i;
          break;
        }
      }

      if (newlinePos != -1) {
        endPos = newlinePos;
      } else if (endPos < len) {
        // Find last space before endPos to avoid cutting words
        int lastSpace = -1;
        for (int i = endPos; i > currentPos; i--) {
          if (text[i] == ' ') {
            lastSpace = i;
            break;
          }
        }
        if (lastSpace > currentPos) {
          endPos = lastSpace;
        }
      }

      // If this line is within the current requested page, render it!
      if (totalLineIdx >= lineOffset) {
        int printedChars = 0;
        tft.setCursor(startX, startY + (visibleLine * linePitch));
        for (int i = currentPos; i < endPos; i++) {
          if (text[i] != '\r' && text[i] != '\n') {
            tft.print(text[i]);
            printedChars++;
          }
        }

        // Pad remaining space on line with blanks to cleanly overwrite old content
        for (int s = printedChars; s < maxCharsPerLine; s++) {
          tft.print(' ');
        }
        visibleLine++;
      }

      totalLineIdx++;
      currentPos = endPos;
      // Skip spaces or newline characters after word break
      while (currentPos < len && (text[currentPos] == ' ' || text[currentPos] == '\r' || text[currentPos] == '\n')) {
        currentPos++;
      }
    }

    // Clear any unused remaining lines
    while (visibleLine < maxLines) {
      tft.setCursor(startX, startY + (visibleLine * linePitch));
      for (int s = 0; s < maxCharsPerLine; s++) {
        tft.print(' ');
      }
      visibleLine++;
    }
  }

  // --------------------------------------------------------------------------
  // Standby Screen (Drawn once when 0 notices exist today)
  // --------------------------------------------------------------------------
  void renderStandbyScreen() {
    if (!isTftReady) return;

    // 1. Top Header Banner with Online Status Indicator
    tft.fillRect(0, 0, 160, 18, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(14, 5);
    tft.print(F("ECHOSPHERE SMART PA"));
    drawStatusDot(148, 8, 3, COLOR_NORMAL);

    // 2. Standby Content Area (Expanded to fill entire screen)
    tft.fillRect(0, 18, 160, 110, COLOR_BG);
    tft.drawRoundRect(10, 24, 140, 96, 4, COLOR_PANEL);

    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(24, 42);
    tft.print(F("No Active Notices"));

    tft.setTextColor(COLOR_TEXT_CYAN, COLOR_BG);
    tft.setCursor(22, 62);
    tft.print(F("System on Standby"));

    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_BG);
    tft.setCursor(18, 82);
    tft.print(F("Ready for Broadcast"));

    // Online Status Indicator inside the Standby Card
    drawStatusDot(50, 103, 3, COLOR_NORMAL);
    tft.setTextColor(COLOR_NORMAL, COLOR_BG);
    tft.setCursor(58, 100);
    tft.print(F("ONLINE"));

    isScreenRendered = true;
  }

  // --------------------------------------------------------------------------
  // Main Update Loop (Called frequently from loop())
  // --------------------------------------------------------------------------
  void update() {
    unsigned long now = millis();

    // 1. Manage Heartbeat LED dip duration on GPIO 22 & 2
    if (isHeartbeatLedOn && now >= heartbeatLedOffTime) {
      digitalWrite(PIN_LED_ONLINE, HIGH);
      digitalWrite(PIN_LED_ONBOARD, LOW);
      isHeartbeatLedOn = false;
    }

    // 2. Manage Emergency LED strobe on GPIO 21
    if (isNoticeActive && activeNotice.priority.equalsIgnoreCase("EMERGENCY")) {
      if (now - lastEmergencyToggleTime >= 100) {
        lastEmergencyToggleTime = now;
        emergencyLedState = !emergencyLedState;
        digitalWrite(PIN_LED_BROADCAST, emergencyLedState ? HIGH : LOW);
      }
    }

    // 2c. Autonomous Safety Timeout for Live Broadcast Screen:
    // If notice broadcast has been active for longer than declared duration + 4s buffer,
    // automatically exit the broadcast screen and restore the idle daily notices screen!
    if (isNoticeActive && (now - playbackStartTime >= (playbackDurationSeconds + 4) * 1000UL)) {
      Serial.println(F("⏱️ [DISPLAY TIMEOUT] Notice playback duration exceeded. Restoring Idle Screen."));
      clearActiveNotice();
    }

    // 3. Smooth Audio Equalizer Animation (During Playing State Only)
    // Differential drawing: updates ONLY the 16 small bars, zero text flutter!
    if (isNoticeActive && (now - lastAnimTime >= 80)) {
      lastAnimTime = now;
      animFrame = (animFrame + 1) % 16;
      if (isTftReady) {
        renderEqualizerGraphic();
      }
    }

    // 3b. Synchronized Auto-Paging Carousel for Live Broadcast (Every 3.5s while active)
    tickBroadcastCarousel(now);

    // 4. Smooth Rotation of Daily Notices (Paginated & Multi-Notice Rotation)
    // When idle and notices exist, smoothly displays notice pages every 4s, and rotates notices!
    if (!isNoticeActive && currentState == STATE_IDLE_DAILY_NOTICES) {
      if (!isScreenRendered) {
        if (dailyNoticesCount > 0) {
          renderDailyNoticesScreen();
        } else {
          renderStandbyScreen();
        }
      } else if (dailyNoticesCount > 0) {
        if (now - lastDailyRotateTime >= 4000) {
          lastDailyRotateTime = now;
          const DisplayNotice& curNotice = dailyNotices[currentDailyNoticeIndex];
          String summaryText = curNotice.summary.length() > 0 ? curNotice.summary : curNotice.title;
          int summaryLines = countWrappedLines(summaryText, 25);
          int totalPages = (summaryLines + 5) / 6;
          if (totalPages < 1) totalPages = 1;

          if (currentDailyNoticePage + 1 < totalPages) {
            // Next page of current notice
            currentDailyNoticePage++;
            renderDailyNoticeCard();
          } else {
            // Current notice is done, reset page and advance to next notice if multiple exist
            currentDailyNoticePage = 0;
            if (dailyNoticesCount > 1) {
              currentDailyNoticeIndex = (currentDailyNoticeIndex + 1) % dailyNoticesCount;
              printAsciiDailyNotice(dailyNotices[currentDailyNoticeIndex], currentDailyNoticeIndex + 1, dailyNoticesCount);
              renderDailyNoticeCard();
            } else if (totalPages > 1) {
              // Only 1 notice, but has multiple pages: loop back to page 0
              renderDailyNoticeCard();
            }
          }
        }
      }
    }
  }

  void refreshScreen() {
    if (!isTftReady) return;

    if (currentState == STATE_PLAYING_ANNOUNCEMENT && isNoticeActive) {
      renderPlayingScreen();
    } else if (currentState == STATE_IDLE_DAILY_NOTICES) {
      if (dailyNoticesCount > 0) {
        renderDailyNoticesScreen();
      } else {
        renderStandbyScreen();
      }
    }
  }

  // --------------------------------------------------------------------------
  // Differential Equalizer Graphic (Flicker-Free Bar-by-Bar Animation)
  // Only updates the vertical difference of each 5px column, zero text flicker!
  // --------------------------------------------------------------------------
  void renderEqualizerGraphic() {
    if (!isTftReady) return;

    int eqBottom = 110;
    int eqMaxHeight = 16;
    int waveHeights[16] = {3, 8, 14, 16, 11, 5, 13, 15, 9, 12, 6, 14, 10, 4, 16, 7};

    for (int i = 0; i < 16; i++) {
      int newH = waveHeights[(i + animFrame) % 16];
      int oldH = prevBarHeights[i];
      int barX = 8 + (i * 9);
      int barW = 5;

      if (newH != oldH) {
        uint16_t barColor = newH > 13 ? COLOR_EMERGENCY : (newH > 8 ? COLOR_URGENT : COLOR_NORMAL);

        if (newH > oldH) {
          // Grow bar upward
          tft.fillRect(barX, eqBottom - newH, barW, newH - oldH, barColor);
        } else {
          // Shrink bar downward (erase top part with background)
          tft.fillRect(barX, eqBottom - oldH, barW, oldH - newH, COLOR_BG);
        }
        prevBarHeights[i] = newH;
      }
    }
  }

  void resetEqualizerGraphic() {
    if (!isTftReady) return;
    int eqBottom = 110;
    for (int i = 0; i < 16; i++) {
      int oldH = prevBarHeights[i];
      int barX = 8 + (i * 9);
      int barW = 5;
      if (oldH > 0) {
        tft.fillRect(barX, eqBottom - oldH, barW, oldH, COLOR_BG);
        prevBarHeights[i] = 0;
      }
    }
  }

private:
  void drawStatusDot(int16_t cx, int16_t cy, int16_t r, uint16_t color) {
    tft.fillRoundRect(cx - r, cy - r, (r * 2) + 1, (r * 2) + 1, r, color);
  }

  uint16_t getPriorityColor(const String& priority) {
    if (priority.equalsIgnoreCase("EMERGENCY")) return COLOR_EMERGENCY;
    if (priority.equalsIgnoreCase("HIGH") || priority.equalsIgnoreCase("URGENT")) return COLOR_URGENT;
    return COLOR_NORMAL;
  }

  // --------------------------------------------------------------------------
  // Playing Notice Screen (Broadcast Mode)
  // --------------------------------------------------------------------------
  void renderPlayingScreen() {
    bool isEmergency = activeNotice.priority.equalsIgnoreCase("EMERGENCY");
    uint16_t headerColor = isEmergency ? COLOR_EMERGENCY : COLOR_HEADER_BLUE;

    // 1. Top Header Banner (Y: 0 to 16)
    tft.fillRect(0, 0, 160, 16, headerColor);
    tft.setTextColor(COLOR_TEXT_WHITE, headerColor);
    tft.setTextSize(1);
    tft.setCursor(isEmergency ? 12 : 20, 4);
    tft.print(isEmergency ? F("! EMERGENCY BROADCAST !") : F("> NOW BROADCASTING"));

    // 2. Clear content body cleanly down to footer (Y: 16 to 112)
    tft.fillRect(0, 16, 160, 96, COLOR_BG);

    // 3. Department & Priority Badges (Y: 17 to 26)
    uint16_t pColor = getPriorityColor(activeNotice.priority);
    tft.fillRoundRect(8, 17, 44, 10, 2, pColor);
    tft.setTextColor(COLOR_BG, pColor);
    tft.setTextSize(1);
    tft.setCursor(11, 18);
    tft.print(activeNotice.priority);

    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(56, 18);
    String deptStr = activeNotice.department;
    if (deptStr.length() > 16) deptStr = deptStr.substring(0, 16);
    tft.print(deptStr);

    tft.drawFastHLine(8, 28, 144, COLOR_PANEL);

    // 4. Compact Clean Sanitized Notice Title (1 or 2 lines depending on length)
    String cleanTitle = sanitizeTitleText(activeNotice.title);
    int titleLines = countWrappedLines(cleanTitle, 24);
    if (titleLines > 1) {
      drawWrappedText(cleanTitle, 8, 30, 24, 2, COLOR_TEXT_WHITE, COLOR_BG, 0, 9);
      tft.drawFastHLine(8, 48, 144, COLOR_PANEL);
    } else {
      drawWrappedText(cleanTitle, 8, 30, 24, 1, COLOR_TEXT_WHITE, COLOR_BG, 0, 9);
      tft.drawFastHLine(8, 39, 144, COLOR_PANEL);
    }

    // 5. Divider above equalizer
    tft.drawFastHLine(8, 88, 144, COLOR_PANEL);

    // 6. Base line for Equalizer (Y: 111)
    tft.drawFastHLine(8, 111, 144, COLOR_PANEL);

    // 7. Render Notice Content Page (4 or 5 lines) & Footer
    currentBroadcastPage = 0;
    renderPlayingContentCard();

    isScreenRendered = true;

    // 8. Immediately render initial equalizer frame
    renderEqualizerGraphic();
  }

  // --------------------------------------------------------------------------
  // Broadcast Notice Content Card (Auto-paged every 3.5s during live speech)
  // --------------------------------------------------------------------------
  void renderPlayingContentCard() {
    bool isEmergency = activeNotice.priority.equalsIgnoreCase("EMERGENCY");
    String msg = activeNotice.summary.length() > 0 ? activeNotice.summary : activeNotice.title;
    msg = sanitizeTitleText(msg);

    String cleanTitle = sanitizeTitleText(activeNotice.title);
    int titleLines = countWrappedLines(cleanTitle, 24);
    int linesPerPage = (titleLines > 1) ? 4 : 5;
    int startY = (titleLines > 1) ? 50 : 41;

    int totalLines = countWrappedLines(msg, 24);
    int totalPages = (totalLines + linesPerPage - 1) / linesPerPage;
    if (totalPages < 1) totalPages = 1;
    if (currentBroadcastPage >= totalPages) currentBroadcastPage = 0;

    // Word-wrapped text with linePitch 9, zero flicker, auto-padded with blanks
    drawWrappedText(msg, 8, startY, 24, linesPerPage, COLOR_TEXT_CYAN, COLOR_BG, currentBroadcastPage * linesPerPage, 9);

    // Footer Status Bar with Live Page Indicator (Y: 113 to 127)
    uint16_t footerColor = isEmergency ? COLOR_EMERGENCY : COLOR_PANEL;
    tft.fillRect(0, 113, 160, 15, footerColor);
    tft.setTextColor(COLOR_TEXT_WHITE, footerColor);
    tft.setTextSize(1);
    tft.setCursor(8, 116);

    if (totalPages > 1) {
      tft.print(isEmergency ? F("! STREAM [P ") : F(">> LIVE AUDIO [P "));
      tft.print(currentBroadcastPage + 1);
      tft.print(F("/"));
      tft.print(totalPages);
      tft.print(F("]"));
    } else {
      tft.print(isEmergency ? F("! EMERGENCY AUDIO STREAM !") : F(">> LIVE AUDIO BROADCAST"));
    }
  }

  // --------------------------------------------------------------------------
  // Daily Notice Screen (Full static layout, refreshed cleanly)
  // --------------------------------------------------------------------------
  void renderDailyNoticesScreen() {
    if (dailyNoticesCount == 0) {
      renderStandbyScreen();
      return;
    }

    // Always reset to Notice 1, Page 1 upon entering the daily notice screen
    currentDailyNoticeIndex = 0;
    currentDailyNoticePage = 0;
    lastDailyRotateTime = millis();

    // 1. Top Header Banner with sleek Online Indicator
    tft.fillRect(0, 0, 160, 18, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(6, 5);
    tft.print(F("* NOTICE [1/"));
    tft.print(dailyNoticesCount);
    tft.print(F("]"));

    // Small Online Indicator: Green Dot + 'ON' in top-right of header
    tft.setTextColor(COLOR_NORMAL, COLOR_HEADER_BLUE);
    tft.setCursor(128, 5);
    tft.print(F("ON"));
    drawStatusDot(148, 8, 3, COLOR_NORMAL);

    // 2. Clear entire notice content body (Y: 18 to 127 = 110px) cleanly
    tft.fillRect(0, 18, 160, 110, COLOR_BG);

    // 3. Render the card body for Notice 1, Page 1
    renderDailyNoticeCard();

    // Mark rendered to prevent 100Hz loop re-render flickering!
    isScreenRendered = true;
  }

  // --------------------------------------------------------------------------
  // Daily Notice Card Body (Smoothly updated when rotating notices)
  // Maximize space: 6 full lines of summary text (was 4), zero wasted footer!
  // --------------------------------------------------------------------------
  void renderDailyNoticeCard() {
    if (dailyNoticesCount == 0) return;
    const DisplayNotice& notice = dailyNotices[currentDailyNoticeIndex];

    String summaryText = notice.summary.length() > 0 ? notice.summary : notice.title;
    int summaryLines = countWrappedLines(summaryText, 25);
    int totalPages = (summaryLines + 5) / 6;
    if (totalPages < 1) totalPages = 1;
    if (currentDailyNoticePage >= totalPages) currentDailyNoticePage = 0;

    // Update Header Counter smoothly in-place with background color (zero flash)
    tft.setCursor(6, 5);
    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    char headerBuf[24];
    if (totalPages > 1) {
      snprintf(headerBuf, sizeof(headerBuf), "* NOTICE [%d/%d] P%d/%d",
               currentDailyNoticeIndex + 1, dailyNoticesCount,
               currentDailyNoticePage + 1, totalPages);
    } else {
      snprintf(headerBuf, sizeof(headerBuf), "* NOTICE [%d/%d]",
               currentDailyNoticeIndex + 1, dailyNoticesCount);
    }
    tft.print(headerBuf);
    int hLen = strlen(headerBuf);
    for (int s = hLen; s < 20; s++) {
      tft.print(' ');
    }

    // Ensure Online Indicator remains intact
    tft.setTextColor(COLOR_NORMAL, COLOR_HEADER_BLUE);
    tft.setCursor(128, 5);
    tft.print(F("ON"));
    drawStatusDot(148, 8, 3, COLOR_NORMAL);

    // Badge area (Y: 20 to 32): clear only the 13px badge row
    tft.fillRect(6, 20, 148, 13, COLOR_BG);

    // Priority badge
    uint16_t pColor = getPriorityColor(notice.priority);
    tft.fillRoundRect(6, 20, 44, 11, 2, pColor);
    tft.setTextColor(COLOR_BG, pColor);
    tft.setCursor(9, 22);
    tft.print(notice.priority);

    // Category & Department
    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(54, 22);
    String meta = notice.category;
    if (meta.length() > 0 && notice.department.length() > 0) {
      meta += " * " + notice.department;
    }
    if (meta.length() > 17) {
      meta = meta.substring(0, 17);
    }
    tft.print(meta);

    tft.drawFastHLine(6, 33, 148, COLOR_PANEL);

    // Notice Title (Compact font size 1, up to 2 lines word-wrapped)
    String cleanTitle = sanitizeTitleText(notice.title);
    drawWrappedText(cleanTitle, 6, 36, 25, 2, COLOR_TEXT_WHITE, COLOR_BG, 0, 10);

    tft.drawFastHLine(6, 57, 148, COLOR_PANEL);

    // Notice Summary: Now 6 full lines of text (was 4)!
    summaryText = sanitizeTitleText(summaryText);
    drawWrappedText(summaryText, 6, 60, 25, 6, COLOR_TEXT_CYAN, COLOR_BG, currentDailyNoticePage * 6, 10);

    // Mark rendered
    isScreenRendered = true;
  }

  void printAsciiPlayingBanner(const DisplayNotice& n) {
    Serial.println(F("\n╔══════════════════════════════════════════════════════════════════════╗"));
    if (n.priority.equalsIgnoreCase("EMERGENCY")) {
      Serial.println(F("║ 🚨 EMERGENCY CAMPUS BROADCAST ACTIVE                                ║"));
    } else {
      Serial.println(F("║ 📢 NOW BROADCASTING NOTICE THROUGH 8Ω SPEAKER & 1.8\" TFT LCD        ║"));
    }
    Serial.println(F("╠══════════════════════════════════════════════════════════════════════╣"));
    Serial.print(F("║ Title:      ")); Serial.println(n.title);
    Serial.print(F("║ Priority:   ")); Serial.print(n.priority);
    Serial.print(F("  | Department: ")); Serial.println(n.department);
    if (n.summary.length() > 0) {
      Serial.print(F("║ Message:    ")); Serial.println(n.summary);
    }
    Serial.println(F("║ Audio Out:  MAX98357A I2S (BCLK:26, LRC:25, DIN:27) -> 8Ω Speaker  ║"));
    Serial.println(F("║ Display:    1.8\" TFT ST7735 SPI (SCLK:18, MOSI:23, CS:5, DC:4)     ║"));
    Serial.println(F("║ LED:        GPIO 21 ACTIVE (Notice Broadcasting Indicator)          ║"));
    Serial.println(F("╚══════════════════════════════════════════════════════════════════════╝\n"));
  }

  void printAsciiDailyNotice(const DisplayNotice& n, int index, int total) {
    Serial.print(F("📰 [DAILY NOTICE ")); Serial.print(index); Serial.print(F("/")); Serial.print(total);
    Serial.print(F("] ")); Serial.print(n.title);
    Serial.print(F(" (")); Serial.print(n.department); Serial.print(F(" - ")); Serial.print(n.priority); Serial.println(F(")"));
  }
};

#endif // ECHOSPHERE_DISPLAY_MANAGER_H
