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

public:
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
  }

  void setConnectedWiFi(const String& ip) {
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
  }

  void setActiveNotice(const DisplayNotice& notice, int durationSec = 15) {
    activeNotice = notice;
    isNoticeActive = true;
    playbackStartTime = millis();
    playbackDurationSeconds = durationSec > 0 ? durationSec : 15;
    currentState = STATE_PLAYING_ANNOUNCEMENT;
    isScreenRendered = false;

    // Reset equalizer history
    for (int i = 0; i < 16; i++) {
      prevBarHeights[i] = 0;
    }

    // Broadcasting LED on
    digitalWrite(PIN_LED_BROADCAST, HIGH);
    digitalWrite(PIN_LED_ONBOARD, HIGH);

    printAsciiPlayingBanner(notice);
    refreshScreen();
  }

  void clearActiveNotice() {
    isNoticeActive = false;
    currentState = STATE_IDLE_DAILY_NOTICES;
    isScreenRendered = false;

    // Turn off Broadcasting LED
    digitalWrite(PIN_LED_BROADCAST, LOW);
    digitalWrite(PIN_LED_ONBOARD, LOW);

    Serial.println(F("\n══════════════════════════════════════════════════════════════════════"));
    Serial.println(F("⏹️  [BROADCAST COMPLETE] 1.8\" TFT Returning to Daily Campus Notice Screen"));
    Serial.println(F("══════════════════════════════════════════════════════════════════════\n"));

    refreshScreen();
  }

  void clearDailyNotices() {
    dailyNoticesCount = 0;
    currentDailyNoticeIndex = 0;
  }

  void addDailyNotice(const DisplayNotice& notice) {
    if (dailyNoticesCount < MAX_DAILY_NOTICES) {
      dailyNotices[dailyNoticesCount++] = notice;
    }
  }

  int getDailyNoticesCount() const { return dailyNoticesCount; }
  bool isBroadcasting() const { return isNoticeActive; }
  bool isRendered() const { return isScreenRendered; }
  DisplayState getState() const { return currentState; }

  // --------------------------------------------------------------------------
  // Helper: Draw word-wrapped text with crisp glyphs and ZERO screen flutter
  // Uses tft.setTextColor(color, bgColor) to draw glyph and clear background
  // in a single operation without calling fillRect!
  // --------------------------------------------------------------------------
  void drawWrappedText(const String& str, int startX, int startY, int maxCharsPerLine, int maxLines, uint16_t color, uint16_t bgColor) {
    tft.setTextColor(color, bgColor);
    tft.setTextSize(1);
    tft.setTextWrap(false);

    const char* text = str.c_str();
    int len = 0;
    while (text[len] != '\0') len++;

    int line = 0;
    int currentPos = 0;

    while (currentPos < len && line < maxLines) {
      int endPos = currentPos + maxCharsPerLine;
      if (endPos >= len) {
        endPos = len;
      } else {
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

      // Skip leading spaces for the line
      while (currentPos < endPos && text[currentPos] == ' ') {
        currentPos++;
      }

      // Measure printed characters
      int printedChars = 0;
      tft.setCursor(startX, startY + (line * 10));
      for (int i = currentPos; i < endPos; i++) {
        tft.print(text[i]);
        printedChars++;
      }

      // Pad remaining space on line with blanks to cleanly overwrite old content
      for (int s = printedChars; s < maxCharsPerLine; s++) {
        tft.print(' ');
      }

      currentPos = endPos;
      // Skip spaces after word break
      while (currentPos < len && text[currentPos] == ' ') {
        currentPos++;
      }
      line++;
    }

    // Clear any unused remaining lines
    while (line < maxLines) {
      tft.setCursor(startX, startY + (line * 10));
      for (int s = 0; s < maxCharsPerLine; s++) {
        tft.print(' ');
      }
      line++;
    }
  }

  // --------------------------------------------------------------------------
  // Standby Screen (Drawn once when 0 notices exist today)
  // --------------------------------------------------------------------------
  void renderStandbyScreen() {
    if (!isTftReady) return;

    // 1. Top Header Banner
    tft.fillRect(0, 0, 160, 20, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(18, 6);
    tft.print(F("ECHOSPHERE SMART PA"));

    // 2. Standby Content Area
    tft.fillRect(0, 20, 160, 92, COLOR_BG);
    tft.drawRoundRect(10, 26, 140, 80, 4, COLOR_PANEL);

    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(24, 40);
    tft.print(F("No Active Notices"));

    tft.setTextColor(COLOR_TEXT_CYAN, COLOR_BG);
    tft.setCursor(22, 58);
    tft.print(F("System on Standby"));

    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_BG);
    tft.setCursor(18, 78);
    tft.print(F("Ready for Broadcast"));

    // 3. Status Footer Bar
    tft.fillRect(0, 112, 160, 16, COLOR_PANEL);
    tft.setTextColor(COLOR_NORMAL, COLOR_PANEL);
    tft.setCursor(8, 116);
    tft.print(F("ONLINE"));
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_PANEL);
    tft.print(F(" | "));
    tft.print(NODE_ZONE);

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

    // 3. Smooth Audio Equalizer Animation (During Playing State Only)
    // Differential drawing: updates ONLY the 16 small bars, zero text flutter!
    if (isNoticeActive && (now - lastAnimTime >= 80)) {
      lastAnimTime = now;
      animFrame = (animFrame + 1) % 8;
      if (isTftReady) {
        renderEqualizerGraphic();
      }
    }

    // 4. Smooth Rotation of Daily Notices (Every 6 seconds)
    // When idle and multiple notices exist, transitions cleanly once every 6s.
    if (!isNoticeActive && currentState == STATE_IDLE_DAILY_NOTICES) {
      if (!isScreenRendered) {
        if (dailyNoticesCount > 0) {
          renderDailyNoticesScreen();
        } else {
          renderStandbyScreen();
        }
      } else if (dailyNoticesCount > 1) {
        if (now - lastDailyRotateTime >= DAILY_NOTICE_ROTATE_INTERVAL_MS) {
          lastDailyRotateTime = now;
          currentDailyNoticeIndex = (currentDailyNoticeIndex + 1) % dailyNoticesCount;
          printAsciiDailyNotice(dailyNotices[currentDailyNoticeIndex], currentDailyNoticeIndex + 1, dailyNoticesCount);
          renderDailyNoticeCard();
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

private:
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

    // 1. Top Header Banner
    tft.fillRect(0, 0, 160, 20, headerColor);
    tft.setTextColor(COLOR_TEXT_WHITE, headerColor);
    tft.setTextSize(1);
    tft.setCursor(isEmergency ? 12 : 20, 6);
    tft.print(isEmergency ? F("! EMERGENCY BROADCAST !") : F("> NOW BROADCASTING"));

    // 2. Clear content body once
    tft.fillRect(0, 20, 160, 72, COLOR_BG);

    // 3. Department & Priority Badges
    uint16_t pColor = getPriorityColor(activeNotice.priority);
    tft.fillRoundRect(8, 23, 44, 11, 2, pColor);
    tft.setTextColor(COLOR_BG, pColor);
    tft.setTextSize(1);
    tft.setCursor(11, 25);
    tft.print(activeNotice.priority);

    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(56, 25);
    tft.print(activeNotice.department);

    tft.drawFastHLine(8, 36, 144, COLOR_PANEL);

    // 4. Compact Wrapped Notice Title (Max 2 lines, 24 chars/line)
    drawWrappedText(activeNotice.title, 8, 40, 24, 2, COLOR_TEXT_WHITE, COLOR_BG);

    // 5. Compact Wrapped Message / Summary (Max 2 lines)
    String msg = activeNotice.summary.length() > 0 ? activeNotice.summary : activeNotice.title;
    drawWrappedText(msg, 8, 62, 24, 2, COLOR_TEXT_CYAN, COLOR_BG);

    // 6. Base line for Equalizer
    tft.drawFastHLine(8, 92, 144, COLOR_PANEL);

    isScreenRendered = true;
  }

  // --------------------------------------------------------------------------
  // Daily Notice Screen (Full static layout, refreshed cleanly)
  // --------------------------------------------------------------------------
  void renderDailyNoticesScreen() {
    if (dailyNoticesCount == 0) {
      renderStandbyScreen();
      return;
    }

    // Draw full template (Header + Footer)
    const DisplayNotice& notice = dailyNotices[currentDailyNoticeIndex];

    // 1. Top Header Banner
    tft.fillRect(0, 0, 160, 20, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(8, 6);
    tft.print(F("* TODAY'S NOTICE ["));
    tft.print(currentDailyNoticeIndex + 1);
    tft.print(F("/"));
    tft.print(dailyNoticesCount);
    tft.print(F("]"));

    // 2. Status Footer Bar
    tft.fillRect(0, 112, 160, 16, COLOR_PANEL);
    tft.setTextColor(COLOR_NORMAL, COLOR_PANEL);
    tft.setCursor(8, 116);
    tft.print(F("ONLINE"));
    tft.setTextColor(COLOR_TEXT_WHITE, COLOR_PANEL);
    tft.print(F(" | "));
    tft.print(NODE_ZONE);

    // 3. Render the card body
    renderDailyNoticeCard();
  }

  // --------------------------------------------------------------------------
  // Daily Notice Card Body (Smoothly updated when rotating notices)
  // --------------------------------------------------------------------------
  void renderDailyNoticeCard() {
    if (dailyNoticesCount == 0) return;
    const DisplayNotice& notice = dailyNotices[currentDailyNoticeIndex];

    // Update Header Counter smoothly
    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_HEADER_BLUE);
    tft.setTextSize(1);
    tft.setCursor(8, 6);
    tft.print(F("* TODAY'S NOTICE ["));
    tft.print(currentDailyNoticeIndex + 1);
    tft.print(F("/"));
    tft.print(dailyNoticesCount);
    tft.print(F("] "));

    // Clear card content area once (Y: 21 to 111 = 90px)
    tft.fillRect(0, 21, 160, 90, COLOR_BG);

    // Priority badge
    uint16_t pColor = getPriorityColor(notice.priority);
    tft.fillRoundRect(8, 23, 44, 11, 2, pColor);
    tft.setTextColor(COLOR_BG, pColor);
    tft.setCursor(11, 25);
    tft.print(notice.priority);

    // Category & Department
    tft.setTextColor(COLOR_TEXT_GOLD, COLOR_BG);
    tft.setCursor(56, 25);
    String meta = notice.category;
    if (meta.length() > 0 && notice.department.length() > 0) {
      meta += " * " + notice.department;
    }
    if (meta.length() > 16) {
      meta = meta.substring(0, 15);
    }
    tft.print(meta);

    tft.drawFastHLine(8, 36, 144, COLOR_PANEL);

    // Notice Title (Compact font size 1, up to 2 lines word-wrapped)
    drawWrappedText(notice.title, 8, 40, 24, 2, COLOR_TEXT_WHITE, COLOR_BG);

    tft.drawFastHLine(8, 62, 144, COLOR_PANEL);

    // Notice Summary (Compact font size 1, up to 4 lines word-wrapped)
    String summaryText = notice.summary.length() > 0 ? notice.summary : notice.title;
    drawWrappedText(summaryText, 8, 66, 24, 4, COLOR_TEXT_CYAN, COLOR_BG);

    isScreenRendered = true;
  }

  // --------------------------------------------------------------------------
  // Differential Equalizer Graphic (Flicker-Free Bar-by-Bar Animation)
  // Only updates the vertical difference of each 5px column, zero text flicker!
  // --------------------------------------------------------------------------
  void renderEqualizerGraphic() {
    if (!isTftReady) return;

    int eqBottom = 111;
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
    animFrame = (animFrame + 1) % 16;
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
