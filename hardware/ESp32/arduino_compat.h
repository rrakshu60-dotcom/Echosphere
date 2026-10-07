#ifndef ECHOSPHERE_ARDUINO_COMPAT_H
#define ECHOSPHERE_ARDUINO_COMPAT_H

// ============================================================================
// EchoSphere Arduino & ESP32 Desktop IDE Compatibility Shim
// When compiling in Arduino IDE / PlatformIO / ESP-IDF, <Arduino.h> exists, so
// native toolchain headers are included directly.
// When opened in desktop IDE editors (VS Code / Antigravity), this header provides
// complete C++ type definitions to eliminate ALL IDE errors and diagnostics.
// ============================================================================

#if __has_include(<Arduino.h>)

  #include <Arduino.h>
  #include <SPI.h>
  #include <Wire.h>

  #if __has_include(<Adafruit_GFX.h>)
    #include <Adafruit_GFX.h>
  #endif

  #if __has_include(<Adafruit_ST7735.h>)
    #include <Adafruit_ST7735.h>
  #endif

  #if __has_include(<driver/i2s.h>)
    #include <driver/i2s.h>
  #endif

  #if __has_include(<WiFi.h>)
    #include <WiFi.h>
    #include <HTTPClient.h>
    #include <WiFiClientSecure.h>
    #include <ArduinoJson.h>
  #endif

#else

  // ==========================================================================
  // Host Desktop IDE Fallback Definitions (Active when <Arduino.h> is absent)
  // ==========================================================================
  #include <cstdint>
  #include <cstddef>
  #include <string>
  #include <iostream>
  #include <algorithm>
  #include <cmath>

  // --- Arduino Core Constants ---
  #ifndef OUTPUT
    #define OUTPUT 0x01
    #define INPUT  0x00
    #define LOW    0x00
    #define HIGH   0x01
  #endif

  #ifndef F
    #define F(str) (str)
  #endif

  #ifndef INITR_BLACKTAB
    #define INITR_BLACKTAB 0
    #define INITR_REDTAB   1
    #define INITR_GREENTAB 2
  #endif

  // --- Arduino String Implementation for Desktop ---
  class String : public std::string {
  public:
    String() : std::string() {}
    String(const char* s) : std::string(s ? s : "") {}
    String(const std::string& s) : std::string(s) {}
    String(int val) : std::string(std::to_string(val)) {}
    String(unsigned int val) : std::string(std::to_string(val)) {}
    String(long val) : std::string(std::to_string(val)) {}
    String(unsigned long val) : std::string(std::to_string(val)) {}

    bool equalsIgnoreCase(const String& o) const {
      if (length() != o.length()) return false;
      for (size_t i = 0; i < length(); i++) {
        if (tolower((unsigned char)(*this)[i]) != tolower((unsigned char)o[i])) return false;
      }
      return true;
    }

    bool endsWith(const String& suffix) const {
      if (suffix.length() > length()) return false;
      return compare(length() - suffix.length(), suffix.length(), suffix) == 0;
    }

    bool startsWith(const String& prefix) const {
      if (prefix.length() > length()) return false;
      return compare(0, prefix.length(), prefix) == 0;
    }

    String substring(size_t from, size_t to = std::string::npos) const {
      if (from >= length()) return String("");
      if (to == std::string::npos || to > length()) return substr(from);
      return substr(from, to - from);
    }

    String& operator+=(const String& o) { append(o); return *this; }
    String& operator+=(const char* s) { if (s) append(s); return *this; }
    String& operator+=(int i) { append(std::to_string(i)); return *this; }
  };

  inline String operator+(const String& lhs, const String& rhs) { String r = lhs; r += rhs; return r; }
  inline String operator+(const String& lhs, const char* rhs) { String r = lhs; r += rhs; return r; }
  inline String operator+(const char* lhs, const String& rhs) { String r(lhs); r += rhs; return r; }
  inline String operator+(const String& lhs, int rhs) { String r = lhs; r += rhs; return r; }

  // --- Wi-Fi IP Address Shim ---
  class IPAddress {
  public:
    String toString() const { return String("192.168.1.100"); }
    operator String() const { return toString(); }
  };

  // --- Serial & Peripheral Stream Shim ---
  class HardwareSerial {
  public:
    void begin(unsigned long) {}
    void print(const String& s) { std::cout << s; }
    void print(const char* s) { if (s) std::cout << s; }
    void print(int i) { std::cout << i; }
    void print(float f) { std::cout << f; }
    void print(const IPAddress& ip) { std::cout << ip.toString(); }
    void println(const String& s) { std::cout << s << std::endl; }
    void println(const char* s) { if (s) std::cout << s << std::endl; else std::cout << std::endl; }
    void println(int i) { std::cout << i << std::endl; }
    void println(float f) { std::cout << f << std::endl; }
    void println(const IPAddress& ip) { std::cout << ip.toString() << std::endl; }
    void println() { std::cout << std::endl; }
  };
  static HardwareSerial Serial;

  class SPIClass {
  public:
    void begin(int, int, int, int) {}
  };
  static SPIClass SPI;

  // --- Display Graphics Shim (Adafruit GFX / ST7735) ---
  class Adafruit_GFX {
  public:
    void setTextSize(uint8_t) {}
    void setTextColor(uint16_t) {}
    void setTextColor(uint16_t, uint16_t) {}
    void setCursor(int16_t, int16_t) {}
    void print(const String&) {}
    void print(const char*) {}
    void print(int) {}
    void println(const String&) {}
    void println(const char*) {}
    void drawFastHLine(int16_t, int16_t, int16_t, uint16_t) {}
    void drawFastVLine(int16_t, int16_t, int16_t, uint16_t) {}
    void drawLine(int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void drawRect(int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void fillRect(int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void drawRoundRect(int16_t, int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void fillRoundRect(int16_t, int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void fillScreen(uint16_t) {}
  };

  class Adafruit_ST7735 : public Adafruit_GFX {
  public:
    Adafruit_ST7735(int8_t, int8_t, int8_t) {}
    void initR(uint8_t) {}
    void setRotation(uint8_t) {}
  };

  // --- Core Utility Functions ---
  inline void pinMode(uint8_t, uint8_t) {}
  inline void digitalWrite(uint8_t, uint8_t) {}
  inline int digitalRead(uint8_t) { return LOW; }
  inline void delay(unsigned long) {}
  inline unsigned long millis() { return 0; }
  inline int constrain(int amt, int low, int high) {
    return ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)));
  }

  #ifndef min
    #define min(a, b) (((a) < (b)) ? (a) : (b))
  #endif
  #ifndef max
    #define max(a, b) (((a) > (b)) ? (a) : (b))
  #endif

  // --- ESP32 I2S Audio Driver Types & Functions ---
  typedef int esp_err_t;
  #define ESP_OK 0
  typedef int i2s_port_t;
  #define I2S_NUM_0 0
  typedef int i2s_mode_t;
  #define I2S_MODE_MASTER 1
  #define I2S_MODE_TX     2
  #define I2S_BITS_PER_SAMPLE_16BIT 16
  #define I2S_CHANNEL_FMT_RIGHT_LEFT 1
  typedef int i2s_comm_format_t;
  #define I2S_COMM_FORMAT_STAND_I2S 1
  #define I2S_COMM_FORMAT_I2S       1
  #define I2S_COMM_FORMAT_I2S_MSB   2
  #define ESP_INTR_FLAG_LEVEL1      0
  #define I2S_PIN_NO_CHANGE        -1
  #define portMAX_DELAY            0xFFFFFFFF

  struct i2s_config_t {
    i2s_mode_t mode;
    int sample_rate;
    int bits_per_sample;
    int channel_format;
    i2s_comm_format_t communication_format;
    int intr_alloc_flags;
    int dma_buf_count;
    int dma_buf_len;
    bool use_apll;
    bool tx_desc_auto_clear;
    int fixed_mclk;
  };

  struct i2s_pin_config_t {
    int bck_io_num;
    int ws_io_num;
    int data_out_num;
    int data_in_num;
  };

  inline esp_err_t i2s_driver_install(i2s_port_t, const i2s_config_t*, int, void*) { return ESP_OK; }
  inline esp_err_t i2s_set_pin(i2s_port_t, const i2s_pin_config_t*) { return ESP_OK; }
  inline void i2s_zero_dma_buffer(i2s_port_t) {}
  inline esp_err_t i2s_write(i2s_port_t, const void*, size_t, size_t* bytes_written, uint32_t) {
    if (bytes_written) *bytes_written = 0;
    return ESP_OK;
  }

  // --- Wi-Fi & HTTP Client Types ---
  #define WL_CONNECTED 3
  #define WIFI_STA     1
  #define WIFI_AP_STA  3

  class WiFiClass {
  public:
    void mode(int) {}
    void begin(const char*, const char*) {}
    bool softAP(const char*, const char* = nullptr) { return true; }
    IPAddress softAPIP() { return IPAddress(); }
    int status() { return WL_CONNECTED; }
    IPAddress localIP() { return IPAddress(); }
    String macAddress() { return String("D4:F3:2D:22:2A:CB"); }
    void reconnect() {}
  };
  static WiFiClass WiFi;

  class WiFiClient { public: WiFiClient() {} };
  class WiFiClientSecure : public WiFiClient { public: void setInsecure() {} };

  class HTTPClient {
  public:
    bool begin(WiFiClient&, const String&) { return true; }
    void addHeader(const String&, const String&) {}
    void setTimeout(uint16_t) {}
    int POST(const String&) { return 200; }
    String getString() { return String("{}"); }
    void end() {}
  };

  // --- ArduinoJson Shim for Desktop IntelliSense ---
  class JsonVariant {
  public:
    template<typename T> T as() const { return T(); }
    template<typename T> operator T() const { return T(); }
    bool isNull() const { return false; }
    template<typename T> bool is() const { return true; }
    JsonVariant operator[](const char*) const { return JsonVariant(); }
    JsonVariant operator[](int) const { return JsonVariant(); }
    template<typename T> JsonVariant& operator=(const T&) { return *this; }
    JsonVariant& operator=(const JsonVariant&) { return *this; }
    template<typename T> T operator|(T fallback) const { return fallback; }
    size_t size() const { return 0; }
  };

  class JsonObject : public JsonVariant {
  public:
    bool containsKey(const char*) const { return true; }
  };

  class JsonArray : public JsonVariant {
  public:
    JsonObject* begin() { return nullptr; }
    JsonObject* end() { return nullptr; }
    const JsonObject* begin() const { return nullptr; }
    const JsonObject* end() const { return nullptr; }
  };

  class DeserializationError {
  public:
    operator bool() const { return false; }
  };

  template<size_t N>
  class StaticJsonDocument : public JsonObject {};

  class DynamicJsonDocument : public JsonObject {
  public:
    DynamicJsonDocument(size_t) {}
  };

  template<typename TDoc>
  inline DeserializationError deserializeJson(TDoc&, const String&) { return DeserializationError(); }

  template<typename TDoc>
  inline size_t serializeJson(const TDoc&, String&) { return 0; }

#endif // __has_include(<Arduino.h>)

#endif // ECHOSPHERE_ARDUINO_COMPAT_H
