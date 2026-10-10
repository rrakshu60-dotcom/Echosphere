#ifndef ECHOSPHERE_ARDUINO_COMPAT_H
#define ECHOSPHERE_ARDUINO_COMPAT_H

// ============================================================================
// EchoSphere Arduino & ESP32 Desktop IDE Compatibility Shim
// When compiling in Arduino IDE / PlatformIO / ESP-IDF, <Arduino.h> exists, so
// native toolchain headers are included directly.
// When opened in desktop IDE editors (VS Code / Antigravity), this header provides
// complete C++ type definitions to eliminate ALL IDE errors and diagnostics.
// ============================================================================

#include <functional>

#if __has_include(<Arduino.h>) && !defined(__clang__)

  #include <Arduino.h>
  #include <SPI.h>
  #include <Wire.h>

  #if __has_include(<Adafruit_GFX.h>)
    #include <Adafruit_GFX.h>
  #endif

  #if __has_include(<Adafruit_ST7735.h>)
    #include <Adafruit_ST7735.h>
  #endif

  #if __has_include(<driver/i2s_std.h>)
    #include <driver/i2s_std.h>
  #elif __has_include(<driver/i2s.h>)
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

  typedef int clockid_t;
  #ifndef M_PI
    #define M_PI 3.14159265358979323846
  #endif

  // --- Arduino Core Constants ---
  #ifndef OUTPUT
    #define OUTPUT 0x01
    #define INPUT  0x00
    #define LOW    0x00
    #define HIGH   0x01
  #endif

  class __FlashStringHelper;
  #ifndef FPSTR
    #define FPSTR(p) (reinterpret_cast<const __FlashStringHelper *>(p))
  #endif
  #ifndef F
    #define F(str) (reinterpret_cast<const __FlashStringHelper *>(str))
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

    int indexOf(char ch, unsigned int fromIndex = 0) const {
      size_t found = find(ch, fromIndex);
      return (found == std::string::npos) ? -1 : (int)found;
    }

    int indexOf(const String& val, unsigned int fromIndex = 0) const {
      size_t found = find(val, fromIndex);
      return (found == std::string::npos) ? -1 : (int)found;
    }

    int indexOf(const char* val, unsigned int fromIndex = 0) const {
      if (!val) return -1;
      size_t found = find(val, fromIndex);
      return (found == std::string::npos) ? -1 : (int)found;
    }

    int lastIndexOf(char ch, int fromIndex = -1) const {
      if (empty()) return -1;
      size_t pos = (fromIndex < 0 || fromIndex >= (int)length()) ? length() - 1 : fromIndex;
      size_t found = rfind(ch, pos);
      return (found == std::string::npos) ? -1 : (int)found;
    }

    char charAt(unsigned int index) const {
      if (index >= length()) return 0;
      return (*this)[index];
    }

    void trim() {
      while (!empty() && isspace((unsigned char)front())) erase(begin());
      while (!empty() && isspace((unsigned char)back())) pop_back();
    }

    void replace(const char* findStr, const char* replaceStr) {
      if (!findStr || !replaceStr) return;
      size_t pos = 0;
      size_t findLen = strlen(findStr);
      size_t replaceLen = strlen(replaceStr);
      if (findLen == 0) return;
      while ((pos = std::string::find(findStr, pos)) != std::string::npos) {
        std::string::replace(pos, findLen, replaceStr);
        pos += replaceLen;
      }
    }
    void replace(const String& findStr, const String& replaceStr) {
      this->replace(findStr.c_str(), replaceStr.c_str());
    }

    String& operator+=(const String& o) { append(o); return *this; }
    String& operator+=(const char* s) { if (s) append(s); return *this; }
    String& operator+=(char c) { push_back(c); return *this; }
    String& operator+=(int i) { append(std::to_string(i)); return *this; }
  };

  inline String operator+(const String& lhs, const String& rhs) { String r = lhs; r += rhs; return r; }
  inline String operator+(const String& lhs, const char* rhs) { String r = lhs; r += rhs; return r; }
  inline String operator+(const char* lhs, const String& rhs) { String r(lhs); r += rhs; return r; }
  inline String operator+(const String& lhs, char rhs) { String r = lhs; r += rhs; return r; }
  inline String operator+(const String& lhs, int rhs) { String r = lhs; r += rhs; return r; }

  // --- Wi-Fi IP Address Shim ---
  class IPAddress {
  public:
    String toString() const { return String("192.168.1.100"); }
    operator String() const { return toString(); }
  };

  // --- Standard Arduino Print Base Class ---
  class Print {
  public:
    virtual size_t write(uint8_t) { return 1; }
    virtual size_t write(const uint8_t*, size_t size) { return size; }

    size_t print(const __FlashStringHelper*) { return 0; }
    size_t print(const String&) { return 0; }
    size_t print(const char*) { return 0; }
    size_t print(char) { return 0; }
    size_t print(unsigned char, int = 10) { return 0; }
    size_t print(int, int = 10) { return 0; }
    size_t print(unsigned int, int = 10) { return 0; }
    size_t print(long, int = 10) { return 0; }
    size_t print(unsigned long, int = 10) { return 0; }
    size_t print(double, int = 2) { return 0; }
    size_t print(const IPAddress&) { return 0; }
    template <typename T>
    size_t print(const T&) { return 0; }

    size_t println(const __FlashStringHelper*) { return 0; }
    size_t println(const String&) { return 0; }
    size_t println(const char*) { return 0; }
    size_t println(char) { return 0; }
    size_t println(unsigned char, int = 10) { return 0; }
    size_t println(int, int = 10) { return 0; }
    size_t println(unsigned int, int = 10) { return 0; }
    size_t println(long, int = 10) { return 0; }
    size_t println(unsigned long, int = 10) { return 0; }
    size_t println(double, int = 2) { return 0; }
    size_t println(const IPAddress&) { return 0; }
    size_t println(void) { return 0; }
    template <typename T>
    size_t println(const T&) { return 0; }
  };

  // --- Standard Arduino Stream Base Class ---
  class Stream : public Print {
  public:
    virtual int available() { return 0; }
    virtual int read() { return -1; }
    virtual int peek() { return -1; }
    virtual void flush() {}
  };

  // --- HardwareSerial Stream Shim ---
  class HardwareSerial : public Stream {
  public:
    void begin(unsigned long, uint32_t = 0, int8_t = -1, int8_t = -1, bool = false, unsigned long = 20000UL) {}
    void end() {}
  };
  static HardwareSerial Serial;

  class SPIClass {
  public:
    void begin(int, int, int, int) {}
  };
  static SPIClass SPI;

  // --- Display Graphics Shim (Adafruit GFX / ST7735) ---
  class Adafruit_GFX : public Print {
  public:
    void setTextSize(uint8_t) {}
    void setTextWrap(bool) {}
    void setTextColor(uint16_t) {}
    void setTextColor(uint16_t, uint16_t) {}
    void setCursor(int16_t, int16_t) {}
    void drawFastHLine(int16_t, int16_t, int16_t, uint16_t) {}
    void drawFastVLine(int16_t, int16_t, int16_t, uint16_t) {}
    void drawLine(int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void drawRect(int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void fillRect(int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void drawRoundRect(int16_t, int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void fillRoundRect(int16_t, int16_t, int16_t, int16_t, int16_t, uint16_t) {}
    void fillScreen(uint16_t) {}
    void startWrite() {}
    void endWrite() {}
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
  inline long map(long x, long in_min, long in_max, long out_min, long out_max) {
    return (in_max == in_min) ? out_min : (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
  }

  #ifndef min
    #define min(a, b) (((a) < (b)) ? (a) : (b))
  #endif
  #ifndef max
    #define max(a, b) (((a) > (b)) ? (a) : (b))
  #endif

  // --- ESP32 I2S Audio Driver Types & Functions ---
  typedef int esp_err_t;
  typedef int i2s_bits_per_sample_t;
  typedef int i2s_channel_t;
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

  typedef void* i2s_chan_handle_t;
  typedef int gpio_num_t;
  #define I2S_ROLE_MASTER 0
  #define I2S_DATA_BIT_WIDTH_16BIT 16
  #define I2S_SLOT_MODE_STEREO 2
  #define I2S_SLOT_MODE_MONO 1

  struct i2s_chan_config_t {
    int id;
    int role;
  };
  #define I2S_CHANNEL_DEFAULT_CONFIG(port, role) { port, role }

  struct i2s_std_clk_config_t {
    uint32_t sample_rate_hz;
  };
  #define I2S_STD_CLK_DEFAULT_CONFIG(rate) { (uint32_t)(rate) }

  struct i2s_std_slot_config_t {
    int data_bit_width;
    int slot_mode;
  };
  #define I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(width, mode) { width, mode }

  struct i2s_std_gpio_config_t {
    int mclk;
    gpio_num_t bclk;
    gpio_num_t ws;
    gpio_num_t dout;
    int din;
    struct {
      bool mclk_inv;
      bool bclk_inv;
      bool ws_inv;
    } invert_flags;
  };

  struct i2s_std_config_t {
    i2s_std_clk_config_t clk_cfg;
    i2s_std_slot_config_t slot_cfg;
    i2s_std_gpio_config_t gpio_cfg;
  };

  inline esp_err_t i2s_new_channel(const i2s_chan_config_t*, i2s_chan_handle_t*, void*) { return ESP_OK; }
  inline esp_err_t i2s_channel_init_std_mode(i2s_chan_handle_t, const i2s_std_config_t*) { return ESP_OK; }
  inline esp_err_t i2s_channel_enable(i2s_chan_handle_t) { return ESP_OK; }
  inline esp_err_t i2s_channel_disable(i2s_chan_handle_t) { return ESP_OK; }
  inline esp_err_t i2s_channel_reconfig_std_clock(i2s_chan_handle_t, const i2s_std_clk_config_t*) { return ESP_OK; }
  inline esp_err_t i2s_channel_write(i2s_chan_handle_t, const void*, size_t, size_t* bytes_written, uint32_t) {
    if (bytes_written) *bytes_written = 0;
    return ESP_OK;
  }
  inline esp_err_t i2s_driver_install(i2s_port_t, const i2s_config_t*, int, void*) { return ESP_OK; }
  inline esp_err_t i2s_set_pin(i2s_port_t, const i2s_pin_config_t*) { return ESP_OK; }
  inline esp_err_t i2s_set_clk(i2s_port_t, uint32_t, i2s_bits_per_sample_t, i2s_channel_t) { return ESP_OK; }
  inline void i2s_zero_dma_buffer(i2s_port_t) {}
  inline esp_err_t i2s_write(i2s_port_t, const void*, size_t, size_t* bytes_written, uint32_t) {
    if (bytes_written) *bytes_written = 0;
    return ESP_OK;
  }
  inline void yield() {}

  // --- Wi-Fi & HTTP Client Types ---
  #define WL_CONNECTED 3
  #define WIFI_STA     1
  #define WIFI_AP_STA  3

  class WiFiClass {
  public:
    void mode(int) {}
    void begin(const char*, const char*) {}
    bool disconnect(bool = false, bool = false) { return true; }
    bool softAP(const char*, const char* = nullptr) { return true; }
    IPAddress softAPIP() { return IPAddress(); }
    int status() { return WL_CONNECTED; }
    IPAddress localIP() { return IPAddress(); }
    String macAddress() { return String("D4:F3:2D:22:2A:CB"); }
    void reconnect() {}
  };
  static WiFiClass WiFi;

  class WiFiClient {
  public:
    WiFiClient() {}
    int available() { return 0; }
    int read() { return -1; }
    size_t read(uint8_t*, size_t) { return 0; }
    bool connected() { return false; }
    void stop() {}
  };
  class WiFiClientSecure : public WiFiClient { public: void setInsecure() {} };

  #define HTTPC_STRICT_FOLLOW_REDIRECTS 1
  #define HTTPC_FORCE_FOLLOW_REDIRECTS 2

  class EspClass {
  public:
    uint32_t getFreeHeap() { return 110000; }
  };
  static EspClass ESP;

  class HTTPClient {
  public:
    bool begin(WiFiClient&, const String&) { return true; }
    void addHeader(const String&, const String&) {}
    void setTimeout(uint16_t) {}
    void setFollowRedirects(int) {}
    int POST(const String&) { return 200; }
    int GET() { return 200; }
    String getString() { return String("{}"); }
    WiFiClient* getStreamPtr() { static WiFiClient c; return &c; }
    WiFiClient& getStream() { static WiFiClient c; return c; }
    int getSize() { return 0; }
    void end() {}
  };

  // --- ESP32-audioI2S Shim for Desktop IntelliSense ---
  class Audio {
  public:
    Audio(bool = false, uint8_t = 3, uint8_t = 0) {}
    void setBufsize(int = 0, int = 0) {}
    bool setPinout(uint8_t, uint8_t, uint8_t, int8_t = -1) { return true; }
    void setVolume(uint8_t, uint8_t = 0) {}
    void setConnectionTimeout(uint16_t = 0, uint16_t = 0) {}
    bool connecttohost(const char*, const char* = "", const char* = "") { return true; }
    bool isRunning() const { return false; }
    void loop() {}
    uint32_t stopSong() { return 0; }
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
    const char* c_str() const { return "Ok"; }
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
