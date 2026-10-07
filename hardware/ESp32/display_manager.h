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

  // Horizontal ticker scrolling variables
  int scrollOffset = 0;
  unsigned long lastScrollTime = 0;
  int animFrame = 0;
  unsigned long lastAnimTime = 0;

  // Heartbeat LED flash tracking (GPIO 22)
  unsigned long heartbeatLedOffTime = 0;
  bool isHeartbeatLedOn = false;

  // Emergency flash tracking (GPIO 21)
  unsigned long lastEmergencyToggleTime = 0;
  bool emergencyLedState = false;

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
    tft.fillScreen(COLOR_BG);

    isTftReady = true;
    Serial.println(F("🖥️ [TFT DISPLAY] 1.8\" Color TFT LCD (160x128 ST7735 SPI) initialized in landscape!"));

    // Splash Header
    tft.fillRect(0, 0, 160, 22, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setTextSize(1);
    tft.setCursor(18, 7);
    tft.print(F("ECHOSPHERE SMART NODE"));

    tft.setTextColor(COLOR_TEXT_CYAN);
    tft.setCursor(15, 50);
    tft.print(F("System Initializing..."));
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setCursor(15, 68);
    tft.print(F("Audio: MAX98357A I2S 3W"));
  }

  void setState(DisplayState state) {
    if (currentState != state) {
      currentState = state;
      scrollOffset = 0;
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
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setCursor(15, 6);
    tft.print(F("CONNECTING WI-FI"));

    tft.setTextColor(COLOR_TEXT_GOLD);
    tft.setCursor(10, 40);
    tft.print(F("SSID: "));
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.println(ssid);

    tft.setTextColor(COLOR_TEXT_CYAN);
    tft.setCursor(10, 60);
    tft.println(F("Authenticating..."));
  }

  void setConnectedWiFi(const String& ip) {
    currentState = STATE_REGISTERING;
    if (!isTftReady) return;

    tft.fillScreen(COLOR_BG);
    tft.fillRect(0, 0, 160, 20, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setCursor(20, 6);
    tft.print(F("WI-FI CONNECTED"));

    tft.setTextColor(COLOR_NORMAL);
    tft.setCursor(10, 36);
    tft.print(F("Status: ONLINE"));

    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setCursor(10, 52);
    tft.print(F("IP: "));
    tft.print(ip);

    tft.setTextColor(COLOR_TEXT_GOLD);
    tft.setCursor(10, 72);
    tft.print(F("Registering with App..."));
  }

  void setActiveNotice(const DisplayNotice& notice, int durationSec = 15) {
    activeNotice = notice;
    isNoticeActive = true;
    playbackStartTime = millis();
    playbackDurationSeconds = durationSec > 0 ? durationSec : 15;
    currentState = STATE_PLAYING_ANNOUNCEMENT;
    scrollOffset = 0;

    // Broadcasting LED on (solid for normal, flashing handled in update loop for emergency)
    digitalWrite(PIN_LED_BROADCAST, HIGH);
    digitalWrite(PIN_LED_ONBOARD, HIGH);

    printAsciiPlayingBanner(notice);
    refreshScreen();
  }

  void clearActiveNotice() {
    isNoticeActive = false;
    currentState = STATE_IDLE_DAILY_NOTICES;
    scrollOffset = 0;

    // Turn off Broadcasting LED
    digitalWrite(PIN_LED_BROADCAST, LOW);
    digitalWrite(PIN_LED_ONBOARD, LOW);

    Serial.println(F("\n══════════════════════════════════════════════════════════════════════"));
    Serial.println(F("⏹️  [BROADCAST COMPLETE] 1.8\" TFT Returning to Daily Campus Ticker"));
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
  DisplayState getState() const { return currentState; }

  void renderStandbyScreen() {
    if (!isTftReady) return;

    // 1. Top Header Banner
    tft.fillRect(0, 0, 160, 22, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setTextSize(1);
    tft.setCursor(18, 7);
    tft.print(F("ECHOSPHERE SMART PA"));

    // 2. Standby Status Box
    tft.drawRect(8, 30, 144, 74, COLOR_PANEL);

    tft.setTextColor(COLOR_TEXT_GOLD);
    tft.setCursor(26, 42);
    tft.print(F("No Active Notices"));

    tft.setTextColor(COLOR_TEXT_CYAN);
    tft.setCursor(24, 60);
    tft.print(F("System on Standby"));

    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setCursor(20, 78);
    tft.print(F("Ready for Broadcast"));

    // 3. Status Footer Bar
    tft.fillRect(0, 112, 160, 16, COLOR_PANEL);
    tft.setTextColor(COLOR_NORMAL);
    tft.setCursor(8, 116);
    tft.print(F("ONLINE"));
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.print(F(" | "));
    tft.print(NODE_ZONE);
  }

  void update() {
    unsigned long now = millis();

    // 1. Manage Heartbeat LED dip duration on GPIO 22 & 2
    if (isHeartbeatLedOn && now >= heartbeatLedOffTime) {
      digitalWrite(PIN_LED_ONLINE, HIGH); // Back to solid ON
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

    // 3. Audio Equalizer Animation Frame (every 90ms)
    if (now - lastAnimTime >= 90) {
      lastAnimTime = now;
      animFrame = (animFrame + 1) % 8;
      if (isNoticeActive && isTftReady) {
        renderEqualizerGraphic();
      }
    }

    // 4. Horizontal Ticker Text Scrolling (every TICKER_SCROLL_SPEED_MS)
    if (now - lastScrollTime >= TICKER_SCROLL_SPEED_MS) {
      lastScrollTime = now;
      scrollOffset += 2;
      if (scrollOffset > 360) {
        scrollOffset = 0;
      }
      if (currentState == STATE_PLAYING_ANNOUNCEMENT || (currentState == STATE_IDLE_DAILY_NOTICES && dailyNoticesCount > 0)) {
        renderScrollingTickerRegion();
      }
    }

    // 5. Rotate Daily Notices during idle state (every DAILY_NOTICE_ROTATE_INTERVAL_MS)
    if (!isNoticeActive && currentState == STATE_IDLE_DAILY_NOTICES) {
      if (now - lastDailyRotateTime >= DAILY_NOTICE_ROTATE_INTERVAL_MS) {
        lastDailyRotateTime = now;
        if (dailyNoticesCount > 0) {
          currentDailyNoticeIndex = (currentDailyNoticeIndex + 1) % dailyNoticesCount;
          scrollOffset = 0;
          printAsciiDailyNotice(dailyNotices[currentDailyNoticeIndex], currentDailyNoticeIndex + 1, dailyNoticesCount);
          refreshScreen();
        }
      }
    }
  }

  void refreshScreen() {
    if (!isTftReady) return;

    tft.fillScreen(COLOR_BG);

    if (currentState == STATE_PLAYING_ANNOUNCEMENT && isNoticeActive) {
      renderPlayingScreen();
    } else if (currentState == STATE_IDLE_DAILY_NOTICES) {
      renderDailyNoticesScreen();
    }
  }

private:
  uint16_t getPriorityColor(const String& priority) {
    if (priority.equalsIgnoreCase("EMERGENCY")) return COLOR_EMERGENCY;
    if (priority.equalsIgnoreCase("HIGH") || priority.equalsIgnoreCase("URGENT")) return COLOR_URGENT;
    return COLOR_NORMAL;
  }

  void renderPlayingScreen() {
    bool isEmergency = activeNotice.priority.equalsIgnoreCase("EMERGENCY");
    uint16_t headerColor = isEmergency ? COLOR_EMERGENCY : COLOR_HEADER_BLUE;

    // 1. Top Header Banner
    tft.fillRect(0, 0, 160, 22, headerColor);
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.setTextSize(1);
    tft.setCursor(isEmergency ? 12 : 22, 7);
    tft.print(isEmergency ? F("! EMERGENCY BROADCAST !") : F("> NOW BROADCASTING"));

    // 2. Department & Priority Badges
    uint16_t pColor = getPriorityColor(activeNotice.priority);
    tft.fillRoundRect(6, 28, 48, 14, 3, pColor);
    tft.setTextColor(COLOR_BG);
    tft.setCursor(10, 31);
    tft.print(activeNotice.priority);

    tft.setTextColor(COLOR_TEXT_GOLD);
    tft.setCursor(60, 31);
    tft.print(activeNotice.department);

    // 3. Notice Title Static Base
    tft.drawFastHLine(6, 46, 148, COLOR_PANEL);

    // 4. Initial ticker region render
    renderScrollingTickerRegion();

    // 5. Initial Equalizer bars render
    renderEqualizerGraphic();
  }

  void renderScrollingTickerRegion() {
    if (!isTftReady) return;

    if (currentState == STATE_PLAYING_ANNOUNCEMENT && isNoticeActive) {
      // Clear ticker area
      tft.fillRect(6, 50, 148, 38, COLOR_BG);

      // Title line
      tft.setTextColor(COLOR_TEXT_WHITE);
      tft.setTextSize(1);
      int titlePixelWidth = (int)activeNotice.title.length() * 6;
      if (titlePixelWidth > 140) {
        int x = 6 - (scrollOffset % (titlePixelWidth + 40));
        tft.setCursor(x, 52);
        tft.print(activeNotice.title);
        if (x + titlePixelWidth < 140) {
          tft.setCursor(x + titlePixelWidth + 30, 52);
          tft.print(activeNotice.title);
        }
      } else {
        tft.setCursor(6, 52);
        tft.print(activeNotice.title);
      }

      // Summary snippet line
      String msg = activeNotice.summary.length() > 0 ? activeNotice.summary : activeNotice.title;
      tft.setTextColor(COLOR_TEXT_CYAN);
      int msgPixelWidth = (int)msg.length() * 6;
      int mX = 6 - ((scrollOffset / 2) % (msgPixelWidth + 40));
      tft.setCursor(mX, 68);
      tft.print(msg);
      if (mX + msgPixelWidth < 140) {
        tft.setCursor(mX + msgPixelWidth + 30, 68);
        tft.print(msg);
      }

    } else if (currentState == STATE_IDLE_DAILY_NOTICES && dailyNoticesCount > 0) {
      const DisplayNotice& notice = dailyNotices[currentDailyNoticeIndex];

      // Clear title and summary ticker area
      tft.fillRect(6, 48, 148, 48, COLOR_BG);

      // Notice Title with horizontal scroll
      tft.setTextColor(COLOR_TEXT_WHITE);
      tft.setTextSize(1);
      int titlePixelWidth = (int)notice.title.length() * 6;
      if (titlePixelWidth > 140) {
        int x = 6 - (scrollOffset % (titlePixelWidth + 40));
        tft.setCursor(x, 50);
        tft.print(notice.title);
        if (x + titlePixelWidth < 140) {
          tft.setCursor(x + titlePixelWidth + 30, 50);
          tft.print(notice.title);
        }
      } else {
        tft.setCursor(6, 50);
        tft.print(notice.title);
      }

      // Summary Ticker
      tft.drawFastHLine(6, 64, 148, COLOR_PANEL);
      String summaryText = notice.summary.length() > 0 ? notice.summary : notice.title;
      tft.setTextColor(COLOR_TEXT_CYAN);
      int sWidth = (int)summaryText.length() * 6;
      int sX = 6 - ((scrollOffset / 2) % (sWidth + 40));
      tft.setCursor(sX, 72);
      tft.print(summaryText);
      if (sX + sWidth < 140) {
        tft.setCursor(sX + sWidth + 30, 72);
        tft.print(summaryText);
      }
    }
  }

  void renderEqualizerGraphic() {
    if (!isTftReady) return;

    // Equalizer bounding box at bottom (Y: 96 to 124)
    int eqY = 96;
    int eqHeight = 28;
    tft.fillRect(6, eqY, 148, eqHeight, COLOR_BG);
    tft.drawFastHLine(6, eqY, 148, COLOR_PANEL);

    // Multi-color dynamic dancing bars
    int waveHeights[16] = {6, 12, 18, 24, 15, 8, 20, 26, 14, 19, 10, 22, 16, 7, 25, 11};
    for (int i = 0; i < 16; i++) {
      int h = waveHeights[(i + animFrame) % 16];
      int barX = 8 + (i * 9);
      uint16_t barColor = h > 20 ? COLOR_EMERGENCY : (h > 12 ? COLOR_URGENT : COLOR_NORMAL);
      tft.fillRect(barX, (eqY + eqHeight) - h, 6, h, barColor);
    }
  }

  void renderDailyNoticesScreen() {
    if (dailyNoticesCount == 0) {
      renderStandbyScreen();
      return;
    }

    const DisplayNotice& notice = dailyNotices[currentDailyNoticeIndex];

    // 1. Top Header Banner
    tft.fillRect(0, 0, 160, 22, COLOR_HEADER_BLUE);
    tft.setTextColor(COLOR_TEXT_GOLD);
    tft.setTextSize(1);
    tft.setCursor(8, 7);
    tft.print(F("* TODAY'S NOTICE ["));
    tft.print(currentDailyNoticeIndex + 1);
    tft.print(F("/"));
    tft.print(dailyNoticesCount);
    tft.print(F("]"));

    // 2. Department & Priority Badges
    uint16_t pColor = getPriorityColor(notice.priority);
    tft.fillRoundRect(6, 28, 48, 14, 3, pColor);
    tft.setTextColor(COLOR_BG);
    tft.setCursor(10, 31);
    tft.print(notice.priority);

    tft.setTextColor(COLOR_TEXT_GOLD);
    tft.setCursor(60, 31);
    tft.print(notice.category);
    tft.print(F(" * "));
    tft.print(notice.department);

    tft.drawFastHLine(6, 45, 148, COLOR_PANEL);

    // 3. Render Title & Scrolling summary
    renderScrollingTickerRegion();

    // 4. Status Footer Bar
    tft.fillRect(0, 112, 160, 16, COLOR_PANEL);
    tft.setTextColor(COLOR_NORMAL);
    tft.setCursor(8, 116);
    tft.print(F("ONLINE"));
    tft.setTextColor(COLOR_TEXT_WHITE);
    tft.print(F(" | "));
    tft.print(NODE_ZONE);
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
