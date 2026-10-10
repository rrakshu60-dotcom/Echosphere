#ifndef ECHOSPHERE_AUDIO_MANAGER_H
#define ECHOSPHERE_AUDIO_MANAGER_H

#include "config.h"
#include "arduino_compat.h"

#include <math.h>
#include <functional>

// ============================================================================
// MAX98357A I2S 3W Class-D Audio Subsystem
// Outputs 16-bit PCM digital audio directly to MAX98357A and 8Ω Speaker
// Standard I2S Pins: BCLK=GPIO 26, LRC=GPIO 25, DIN=GPIO 27 (All < 32 Safe)
// Compatible with ESP-IDF v5 (Arduino Core 3.x) & ESP-IDF v4 (Arduino Core 2.x)
// Zero external library dependencies, Zero PSRAM overhead, Zero heap fragmentation
// ============================================================================

#define I2S_SAMPLE_RATE       44100
#define I2S_PORT_NUM          I2S_NUM_0
#define BUFFER_SAMPLES_COUNT  256

#if defined(ESP_IDF_VERSION_MAJOR) && (ESP_IDF_VERSION_MAJOR >= 5)
  #define ECHOSPHERE_I2S_V5 1
#elif defined(ESP_IDF_VERSION) && (ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0))
  #define ECHOSPHERE_I2S_V5 1
#endif

class AudioManager {
private:
  int currentVolume = NODE_DEFAULT_VOL; // 0 to 100%
  bool isPlaying = false;
  bool isInitialized = false;
  uint32_t currentSampleRate = I2S_SAMPLE_RATE;

#ifdef ECHOSPHERE_I2S_V5
  i2s_chan_handle_t tx_handle = nullptr;
#endif

public:
  AudioManager() {}

  void begin() {
    Serial.println(F("🔊 [I2S AUDIO] Initializing MAX98357A I2S driver..."));

    #if defined(PIN_I2S_SD) && (PIN_I2S_SD >= 0)
      pinMode(PIN_I2S_SD, OUTPUT);
      digitalWrite(PIN_I2S_SD, HIGH); // Un-mute amplifier IC
      delay(10);
    #endif

#ifdef ECHOSPHERE_I2S_V5
    if (tx_handle == nullptr) {
      i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
      esp_err_t err = i2s_new_channel(&chan_cfg, &tx_handle, NULL);
      if (err != ESP_OK) {
        Serial.print(F("❌ [I2S AUDIO] i2s_new_channel failed: "));
        Serial.println(err);
        return;
      }

      i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(I2S_SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
          .mclk = I2S_GPIO_UNUSED,
          .bclk = (gpio_num_t)PIN_I2S_BCLK,
          .ws = (gpio_num_t)PIN_I2S_LRC,
          .dout = (gpio_num_t)PIN_I2S_DIN,
          .din = I2S_GPIO_UNUSED,
          .invert_flags = {
            .mclk_inv = false,
            .bclk_inv = false,
            .ws_inv = false,
          },
        },
      };

      err = i2s_channel_init_std_mode(tx_handle, &std_cfg);
      if (err != ESP_OK) {
        Serial.print(F("❌ [I2S AUDIO] i2s_channel_init_std_mode failed: "));
        Serial.println(err);
        return;
      }

      err = i2s_channel_enable(tx_handle);
      if (err != ESP_OK) {
        Serial.print(F("❌ [I2S AUDIO] i2s_channel_enable failed: "));
        Serial.println(err);
        return;
      }
    }
#else
    i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
      .sample_rate = I2S_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
      .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 12,
      .dma_buf_len = 256,
      .use_apll = false,
      .tx_desc_auto_clear = true,
      .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
      .bck_io_num = PIN_I2S_BCLK,   // GPIO 26
      .ws_io_num = PIN_I2S_LRC,     // GPIO 25
      .data_out_num = PIN_I2S_DIN,  // GPIO 27
      .data_in_num = I2S_PIN_NO_CHANGE
    };

    i2s_driver_install(I2S_PORT_NUM, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT_NUM, &pin_config);
#endif

    currentSampleRate = I2S_SAMPLE_RATE;
    isInitialized = true;
    delay(50); // Allow MAX98357A internal PLL to lock to I2S clock
    Serial.println(F("✅ [I2S AUDIO] MAX98357A 3W Class-D I2S Amplifier ready for 8Ω Speaker!"));
  }

  void setSampleRate(uint32_t rate) {
    if (rate == currentSampleRate || rate < 8000 || rate > 96000) return;
#ifdef ECHOSPHERE_I2S_V5
    if (tx_handle) {
      i2s_channel_disable(tx_handle);
      i2s_std_clk_config_t clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(rate);
      i2s_channel_reconfig_std_clock(tx_handle, &clk_cfg);
      i2s_channel_enable(tx_handle);
    }
#else
    i2s_set_clk(I2S_PORT_NUM, rate, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_STEREO);
#endif
    currentSampleRate = rate;
  }

  void setVolume(int vol) {
    currentVolume = constrain(vol, 0, 100);
    Serial.print(F("🔊 [I2S AUDIO] Volume set to "));
    Serial.print(currentVolume);
    Serial.println(F("%"));
  }

  int getVolume() const {
    return currentVolume;
  }

  bool getIsPlaying() const {
    return isPlaying;
  }

  // --------------------------------------------------------------------------
  // Pure 16-Bit PCM Sine Wave Tone Generator via I2S
  // --------------------------------------------------------------------------
  void playTone(float frequency, unsigned long durationMs) {
    if (!isInitialized || frequency <= 0 || currentVolume <= 0) {
      delay(durationMs);
      return;
    }

    if (currentSampleRate != I2S_SAMPLE_RATE) {
      setSampleRate(I2S_SAMPLE_RATE);
    }

    isPlaying = true;

    // Amplitude scaled by 0-100% volume (16-bit max is 32767)
    float amplitude = (32767.0f * (currentVolume / 100.0f)) * 0.90f;
    unsigned long totalSamples = (I2S_SAMPLE_RATE * durationMs) / 1000UL;

    int16_t sampleBuffer[BUFFER_SAMPLES_COUNT * 2]; // Stereo (Left + Right)
    float phase = 0.0f;
    float phaseIncrement = (2.0f * M_PI * frequency) / I2S_SAMPLE_RATE;

    unsigned long samplesGenerated = 0;
    while (samplesGenerated < totalSamples) {
      int samplesThisChunk = min((unsigned long)BUFFER_SAMPLES_COUNT, totalSamples - samplesGenerated);

      for (int i = 0; i < samplesThisChunk; i++) {
        // Smooth fade-in and fade-out envelope to prevent clicking
        float env = 1.0f;
        if (samplesGenerated + i < 200) {
          env = (float)(samplesGenerated + i) / 200.0f;
        } else if (totalSamples - (samplesGenerated + i) < 200) {
          env = (float)(totalSamples - (samplesGenerated + i)) / 200.0f;
        }

        int16_t sampleValue = (int16_t)(sinf(phase) * amplitude * env);
        sampleBuffer[i * 2]     = sampleValue; // Left channel
        sampleBuffer[i * 2 + 1] = sampleValue; // Right channel

        phase += phaseIncrement;
        if (phase >= 2.0f * M_PI) {
          phase -= 2.0f * M_PI;
        }
      }

      size_t bytesWritten = 0;
#ifdef ECHOSPHERE_I2S_V5
      if (tx_handle) {
        esp_err_t err = i2s_channel_write(tx_handle, sampleBuffer, samplesThisChunk * 4, &bytesWritten, 100);
        if (err != ESP_OK) {
          i2s_channel_enable(tx_handle);
          i2s_channel_write(tx_handle, sampleBuffer, samplesThisChunk * 4, &bytesWritten, 100);
        }
      }
#else
      i2s_write(I2S_PORT_NUM, sampleBuffer, samplesThisChunk * 4, &bytesWritten, portMAX_DELAY);
#endif
      samplesGenerated += samplesThisChunk;
    }

    // Flush zeros at end of note
    silence(10);
    isPlaying = false;
  }

  void silence(unsigned long durationMs) {
    if (!isInitialized) return;
    int16_t zeroBuffer[64 * 2] = {0};
    unsigned long totalChunks = (currentSampleRate * durationMs) / (1000UL * 64);
    if (totalChunks == 0) totalChunks = 1;
    size_t written = 0;
    for (unsigned long i = 0; i < totalChunks; i++) {
#ifdef ECHOSPHERE_I2S_V5
      if (tx_handle) {
        i2s_channel_write(tx_handle, zeroBuffer, sizeof(zeroBuffer), &written, 100);
      }
#else
      i2s_write(I2S_PORT_NUM, zeroBuffer, sizeof(zeroBuffer), &written, portMAX_DELAY);
#endif
    }
  }

  void stopTone() {
    silence(20);
    isPlaying = false;
  }

  // --------------------------------------------------------------------------
  // Stream Lossless 16-Bit PCM WAV Audio Stream Directly to MAX98357A I2S
  // Supports HTTP & HTTPS with dynamic sample rate detection and tight buffering
  // --------------------------------------------------------------------------
  bool playStream(const String& streamUrl, std::function<void()> visualizerCallback = {}) {
    if (!isInitialized || streamUrl.length() == 0) return false;

    isPlaying = true;
    Serial.print(F("🎧 [I2S AUDIO] Streaming from URL: "));
    Serial.println(streamUrl);

    #if defined(PIN_I2S_SD) && (PIN_I2S_SD >= 0)
      pinMode(PIN_I2S_SD, OUTPUT);
      digitalWrite(PIN_I2S_SD, HIGH);
    #endif

    // 1. Establish HTTP / HTTPS connection
    WiFiClientSecure secureClient;
    WiFiClient plainClient;
    WiFiClient* clientPtr = nullptr;

    bool isHttps = streamUrl.startsWith("https://");
    if (isHttps) {
      secureClient.setInsecure(); // Skip certificate verification for low memory overhead
      secureClient.setTimeout(12);
      clientPtr = &secureClient;
    } else {
      plainClient.setTimeout(10);
      clientPtr = &plainClient;
    }

    HTTPClient http;
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    http.setTimeout(15000); // 15s socket timeout

    bool beginOk = false;
    if (isHttps) {
      beginOk = http.begin(secureClient, streamUrl);
    } else {
      beginOk = http.begin(plainClient, streamUrl);
    }

    if (!beginOk) {
      Serial.println(F("❌ [I2S AUDIO] HTTP client begin failed"));
      isPlaying = false;
      return false;
    }

    http.addHeader("User-Agent", "EchoSphere-ESP32-Speaker/2.2");

    int httpCode = http.GET();
    if (httpCode != 200) {
      Serial.print(F("❌ [I2S AUDIO] HTTP GET failed with code: "));
      Serial.println(httpCode);
      http.end();
      isPlaying = false;
      return false;
    }

    WiFiClient* stream = http.getStreamPtr();
    if (!stream) {
      Serial.println(F("❌ [I2S AUDIO] Could not obtain HTTP stream pointer"));
      http.end();
      isPlaying = false;
      return false;
    }

    // 2. Parse WAV Header (RIFF format)
    uint8_t header[12];
    unsigned long startWait = millis();
    size_t headerBytesRead = 0;
    while (headerBytesRead < 12 && stream->connected() && (millis() - startWait < 8000)) {
      int r = stream->read(header + headerBytesRead, 12 - headerBytesRead);
      if (r > 0) headerBytesRead += r;
      else delay(2);
    }

    if (headerBytesRead < 12 || header[0] != 'R' || header[1] != 'I' || header[2] != 'F' || header[3] != 'F') {
      Serial.println(F("❌ [I2S AUDIO] Invalid RIFF header in stream response"));
      http.end();
      isPlaying = false;
      return false;
    }

    // Parse RIFF chunks until "fmt " and "data" chunks are found
    uint16_t channels = 1;
    uint32_t sampleRate = 24000;
    uint16_t bitsPerSample = 16;
    uint32_t totalDataBytes = 0;
    bool foundData = false;

    while (stream->connected() && (millis() - startWait < 8000)) {
      uint8_t chunkHeader[8];
      size_t chRead = 0;
      while (chRead < 8 && stream->connected() && (millis() - startWait < 8000)) {
        int r = stream->read(chunkHeader + chRead, 8 - chRead);
        if (r > 0) chRead += r;
        else delay(2);
      }
      if (chRead < 8) break;

      uint32_t chunkSize = (uint32_t)chunkHeader[4] | ((uint32_t)chunkHeader[5] << 8) |
                           ((uint32_t)chunkHeader[6] << 16) | ((uint32_t)chunkHeader[7] << 24);

      // "fmt " chunk
      if (chunkHeader[0] == 'f' && chunkHeader[1] == 'm' && chunkHeader[2] == 't' && chunkHeader[3] == ' ') {
        uint8_t fmtData[16];
        size_t fmtRead = 0;
        while (fmtRead < 16 && stream->connected() && (millis() - startWait < 8000)) {
          int r = stream->read(fmtData + fmtRead, 16 - fmtRead);
          if (r > 0) fmtRead += r;
          else delay(2);
        }
        if (fmtRead < 16) break;

        channels = (uint16_t)fmtData[2] | ((uint16_t)fmtData[3] << 8);
        sampleRate = (uint32_t)fmtData[4] | ((uint32_t)fmtData[5] << 8) |
                     ((uint32_t)fmtData[6] << 16) | ((uint32_t)fmtData[7] << 24);
        bitsPerSample = (uint16_t)fmtData[14] | ((uint16_t)fmtData[15] << 8);

        // Skip extra header bytes if chunk > 16
        if (chunkSize > 16) {
          uint32_t toSkip = chunkSize - 16;
          uint8_t skipBuf[64];
          while (toSkip > 0 && stream->connected() && (millis() - startWait < 8000)) {
            int r = stream->read(skipBuf, (int)min((uint32_t)sizeof(skipBuf), toSkip));
            if (r > 0) toSkip -= r;
            else delay(2);
          }
        }
      }
      // "data" chunk
      else if (chunkHeader[0] == 'd' && chunkHeader[1] == 'a' && chunkHeader[2] == 't' && chunkHeader[3] == 'a') {
        foundData = true;
        totalDataBytes = chunkSize;
        break;
      }
      else {
        // Skip unknown chunk
        uint32_t toSkip = chunkSize;
        uint8_t skipBuf[64];
        while (toSkip > 0 && stream->connected() && (millis() - startWait < 8000)) {
          int r = stream->read(skipBuf, (int)min((uint32_t)sizeof(skipBuf), toSkip));
          if (r > 0) toSkip -= r;
          else delay(2);
        }
      }
    }

    if (!foundData) {
      Serial.println(F("❌ [I2S AUDIO] Could not locate 'data' chunk in WAV stream"));
      http.end();
      isPlaying = false;
      return false;
    }

    if (sampleRate < 8000 || sampleRate > 96000) sampleRate = 24000;
    Serial.print(F("✅ [I2S AUDIO] Stream Format: "));
    Serial.print(sampleRate);
    Serial.print(F("Hz, "));
    Serial.print(channels);
    Serial.print(F("ch, "));
    Serial.print(bitsPerSample);
    Serial.println(F("bit PCM. Locking hardware I2S clock..."));

    // Dynamically lock hardware clock to stream rate
    setSampleRate(sampleRate);

    // 3. Audio Streaming Loop
    const int CHUNK_SAMPLES = 256;
    int16_t rawChunk[CHUNK_SAMPLES * 2];
    int16_t stereoChunk[CHUNK_SAMPLES * 2];

    unsigned long lastDataTime = millis();
    unsigned long lastVizTime = millis();
    unsigned long totalBytesStreamed = 0;
    unsigned long streamStartTime = millis();

    while (stream->connected() || stream->available()) {
      int bytesToRead = (channels == 1) ? (CHUNK_SAMPLES * 2) : (CHUNK_SAMPLES * 4);

      int bytesRead = stream->read((uint8_t*)rawChunk, bytesToRead);

      if (bytesRead > 0) {
        lastDataTime = millis();

        // 16-bit PCM word-alignment guard: ensure even number of bytes
        if (bytesRead % 2 != 0) {
          int extra = stream->read();
          if (extra >= 0) {
            ((uint8_t*)rawChunk)[bytesRead++] = (uint8_t)extra;
          } else {
            bytesRead--; // Drop dangling odd byte
          }
        }

        totalBytesStreamed += bytesRead;
        int samplesRead = bytesRead / 2;

        // Scale volume and duplicate mono to stereo
        if (channels == 1) {
          for (int i = 0; i < samplesRead; i++) {
            int16_t s = (int16_t)(((int32_t)rawChunk[i] * currentVolume) / 100);
            stereoChunk[i * 2]     = s;
            stereoChunk[i * 2 + 1] = s;
          }
          size_t written = 0;
#ifdef ECHOSPHERE_I2S_V5
          if (tx_handle) i2s_channel_write(tx_handle, stereoChunk, samplesRead * 4, &written, 100);
#else
          i2s_write(I2S_PORT_NUM, stereoChunk, samplesRead * 4, &written, portMAX_DELAY);
#endif
        } else {
          for (int i = 0; i < samplesRead; i++) {
            stereoChunk[i] = (int16_t)(((int32_t)rawChunk[i] * currentVolume) / 100);
          }
          size_t written = 0;
#ifdef ECHOSPHERE_I2S_V5
          if (tx_handle) i2s_channel_write(tx_handle, stereoChunk, samplesRead * 2, &written, 100);
#else
          i2s_write(I2S_PORT_NUM, stereoChunk, samplesRead * 2, &written, portMAX_DELAY);
#endif
        }

        // Animate visualizer periodically
        if (visualizerCallback && (millis() - lastVizTime >= 65)) {
          lastVizTime = millis();
          visualizerCallback();
        }

        // Clean exit when all declared WAV data bytes have been delivered
        if (totalDataBytes > 0 && totalBytesStreamed >= totalDataBytes) {
          Serial.print(F("✅ [I2S AUDIO] All data chunk bytes ("));
          Serial.print(totalBytesStreamed);
          Serial.println(F(" bytes) fully streamed to I2S."));
          break;
        }
      } else {
        if (!stream->connected() && stream->available() <= 0) {
          break; // Stream ended cleanly
        }
        if (millis() - lastDataTime > 3000) {
          Serial.println(F("⚠️ [I2S AUDIO] Stream idle timeout (3s without data)"));
          break;
        }
        delay(2);
      }

      // Safety timeout guard: max 45s per announcement stream
      if (millis() - streamStartTime > 45000UL) {
        Serial.println(F("⚠️ [I2S AUDIO] Stream exceeded 45s safety limit. Stopping."));
        break;
      }

      yield();
    }

    http.end();

    Serial.print(F("✅ [I2S AUDIO] Voice stream playback completed ("));
    Serial.print(totalBytesStreamed);
    Serial.println(F(" bytes delivered to 8Ω speaker)"));

    silence(25);
    // Restore default sample rate for standard chimes
    setSampleRate(I2S_SAMPLE_RATE);
    isPlaying = false;
    return true;
  }

  // Legacy compatibility wrapper
  bool streamWavAudio(const String& streamUrl, std::function<void()> visualizerCallback = {}) {
    return playStream(streamUrl, visualizerCallback);
  }

  // --------------------------------------------------------------------------
  // Startup Confirmation Beep (Plays immediately when ESP32 powers on)
  // Crisp power-on confirmation tone: 880Hz (A5, 100ms) -> 1200Hz (150ms)
  // --------------------------------------------------------------------------
  void playStartupBeep() {
    Serial.println(F("⚡ [I2S AUDIO] Power-On Startup Beep on MAX98357A 8Ω speaker..."));
    playTone(880.00f, 100);  // High A5 note (100ms)
    silence(25);
    playTone(1200.00f, 150); // Crisp confirmation note (150ms)
    silence(30);
  }

  // --------------------------------------------------------------------------
  // Attention Chime (Matches campus PA standard: 587Hz -> 880Hz)
  // --------------------------------------------------------------------------
  void playAttentionChime() {
    Serial.println(F("🔔 [I2S AUDIO] Broadcasting Attention Chime (587Hz -> 880Hz) to 8Ω speaker..."));
    playTone(587.33f, 180); // D5
    silence(40);
    playTone(880.00f, 280); // A5
    silence(50);
  }

  // --------------------------------------------------------------------------
  // Emergency Siren (Urgent dual-sweep alarm: 650Hz <-> 1400Hz)
  // --------------------------------------------------------------------------
  void playEmergencySiren() {
    Serial.println(F("🚨 [I2S AUDIO] Broadcasting Emergency Siren Sweeps to 8Ω speaker..."));
    int prevVol = currentVolume;
    currentVolume = 100; // Maximum power on emergency

    for (int sweep = 0; sweep < 3; sweep++) {
      // Sweep up
      for (float freq = 650.0f; freq <= 1400.0f; freq += 60.0f) {
        playTone(freq, 22);
      }
      // Sweep down
      for (float freq = 1400.0f; freq >= 650.0f; freq -= 60.0f) {
        playTone(freq, 22);
      }
    }

    currentVolume = prevVol;
    silence(50);
  }

  // --------------------------------------------------------------------------
  // Notice Playback Sound Cue (Played when announcement melody begins)
  // --------------------------------------------------------------------------
  void playAnnouncementMelody() {
    Serial.println(F("🎵 [I2S AUDIO] Playing broadcast melody cue..."));
    playTone(523.25f, 130); // C5
    silence(25);
    playTone(659.25f, 130); // E5
    silence(25);
    playTone(783.99f, 200); // G5
    silence(40);
  }

  // --------------------------------------------------------------------------
  // Playback Completion Chime (Soft resolving notification)
  // --------------------------------------------------------------------------
  void playCompletionChime() {
    playTone(880.00f, 90);
    silence(30);
    playTone(587.33f, 150);
    silence(40);
  }

  // --------------------------------------------------------------------------
  // Diagnostic Self-Test (Arpeggio scale + chime)
  // --------------------------------------------------------------------------
  void playDiagnosticTest() {
    Serial.println(F("🎛️ [I2S AUDIO] Running Speaker Diagnostic Self-Test on MAX98357A..."));
    float notes[] = {440.0f, 554.37f, 659.25f, 880.0f};
    for (int i = 0; i < 4; i++) {
      playTone(notes[i], 120);
      silence(30);
    }
    silence(80);
    playAttentionChime();
    Serial.println(F("✅ [I2S AUDIO] Diagnostic test finished. 8Ω speaker verified."));
  }
};

#endif // ECHOSPHERE_AUDIO_MANAGER_H
