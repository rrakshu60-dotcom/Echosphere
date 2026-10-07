#ifndef ECHOSPHERE_AUDIO_MANAGER_H
#define ECHOSPHERE_AUDIO_MANAGER_H

#include "config.h"
#include "arduino_compat.h"

#include <math.h>

// ============================================================================
// MAX98357A I2S 3W Class-D Audio Subsystem
// Outputs 16-bit PCM stereo/mono digital audio to 8Ω Speaker
// Standard I2S Pins: BCLK=GPIO 26, LRC=GPIO 25, DIN=GPIO 27 (All < 32 Safe)
// ============================================================================

#define I2S_SAMPLE_RATE     44100
#define I2S_PORT_NUM        I2S_NUM_0
#define BUFFER_SAMPLES_COUNT  256

class AudioManager {
private:
  int currentVolume = NODE_DEFAULT_VOL; // 0 to 100%
  bool isPlaying = false;
  bool isInitialized = false;

public:
  AudioManager() {}

  void begin() {
    Serial.println(F("🔊 [I2S AUDIO] Initializing MAX98357A I2S driver..."));

    #if defined(PIN_I2S_SD) && (PIN_I2S_SD >= 0)
      pinMode(PIN_I2S_SD, OUTPUT);
      digitalWrite(PIN_I2S_SD, HIGH); // Un-mute amplifier IC
      delay(10);
    #endif

    i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
      .sample_rate = I2S_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
      .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 8,
      .dma_buf_len = 128,
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

    esp_err_t err = i2s_driver_install(I2S_PORT_NUM, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
      Serial.print(F("❌ [I2S AUDIO] Driver install error: "));
      Serial.println(err);
      return;
    }

    err = i2s_set_pin(I2S_PORT_NUM, &pin_config);
    if (err != ESP_OK) {
      Serial.print(F("❌ [I2S AUDIO] Pin config error: "));
      Serial.println(err);
      return;
    }

    // Explicitly lock hardware clock PLL dividers for 44.1kHz stereo audio
    i2s_set_clk(I2S_PORT_NUM, I2S_SAMPLE_RATE, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_STEREO);

    #if defined(PIN_I2S_SD) && (PIN_I2S_SD >= 0)
      pinMode(PIN_I2S_SD, OUTPUT);
      digitalWrite(PIN_I2S_SD, HIGH); // Drive SD pin HIGH to wake MAX98357A from shutdown mode
    #endif

    i2s_zero_dma_buffer(I2S_PORT_NUM);
    isInitialized = true;
    Serial.println(F("✅ [I2S AUDIO] MAX98357A 3W Class-D I2S Amplifier ready for 8Ω Speaker!"));
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
      i2s_write(I2S_PORT_NUM, sampleBuffer, samplesThisChunk * 4, &bytesWritten, portMAX_DELAY);
      samplesGenerated += samplesThisChunk;
    }

    // Flush zeros at end of note
    silence(10);
    isPlaying = false;
  }

  void silence(unsigned long durationMs) {
    if (!isInitialized) return;
    int16_t zeroBuffer[64 * 2] = {0};
    unsigned long totalChunks = (I2S_SAMPLE_RATE * durationMs) / (1000UL * 64);
    if (totalChunks == 0) totalChunks = 1;
    size_t written = 0;
    for (unsigned long i = 0; i < totalChunks; i++) {
      i2s_write(I2S_PORT_NUM, zeroBuffer, sizeof(zeroBuffer), &written, portMAX_DELAY);
    }
  }

  void stopTone() {
    silence(20);
    isPlaying = false;
  }

  // --------------------------------------------------------------------------
  // Stream Lossless 16-Bit PCM WAV Audio Directly to MAX98357A I2S
  // --------------------------------------------------------------------------
  bool streamWavAudio(WiFiClient& client, void (*visualizerCallback)() = nullptr) {
    if (!isInitialized) return false;

    isPlaying = true;
    Serial.println(F("🎧 [I2S AUDIO] Starting 16-bit PCM WAV stream playback..."));

    // 1. Read RIFF/WAVE header (first 12 bytes)
    uint8_t riffHeader[12];
    size_t headerBytesRead = 0;
    unsigned long startWait = millis();

    while (headerBytesRead < 12 && client.connected() && (millis() - startWait < 6000)) {
      if (client.available()) {
        riffHeader[headerBytesRead++] = (uint8_t)client.read();
      } else {
        delay(2);
      }
    }

    if (headerBytesRead < 12) {
      Serial.println(F("❌ [I2S AUDIO] Timeout reading WAV RIFF header"));
      isPlaying = false;
      return false;
    }

    // Verify RIFF & WAVE signature
    if (riffHeader[0] != 'R' || riffHeader[1] != 'I' || riffHeader[2] != 'F' || riffHeader[3] != 'F' ||
        riffHeader[8] != 'W' || riffHeader[9] != 'A' || riffHeader[10] != 'V' || riffHeader[11] != 'E') {
      Serial.println(F("❌ [I2S AUDIO] Invalid WAV file signature"));
      isPlaying = false;
      return false;
    }

    // 2. Scan chunks to extract "fmt " parameters and locate "data" chunk
    uint32_t sampleRate = 24000;
    uint16_t channels = 1;
    uint16_t bitsPerSample = 16;
    bool foundData = false;

    startWait = millis();
    while (client.connected() && !foundData && (millis() - startWait < 8000)) {
      uint8_t chunkHeader[8];
      size_t chRead = 0;
      while (chRead < 8 && client.connected()) {
        if (client.available()) {
          chunkHeader[chRead++] = (uint8_t)client.read();
        } else {
          delay(1);
        }
      }
      if (chRead < 8) break;

      uint32_t chunkSize = (uint32_t)chunkHeader[4] |
                           ((uint32_t)chunkHeader[5] << 8) |
                           ((uint32_t)chunkHeader[6] << 16) |
                           ((uint32_t)chunkHeader[7] << 24);

      // Check for "fmt " chunk
      if (chunkHeader[0] == 'f' && chunkHeader[1] == 'm' && chunkHeader[2] == 't' && chunkHeader[3] == ' ') {
        uint8_t fmtData[16];
        size_t fmtRead = 0;
        while (fmtRead < 16 && client.connected()) {
          if (client.available()) {
            fmtData[fmtRead++] = (uint8_t)client.read();
          } else {
            delay(1);
          }
        }
        channels = (uint16_t)fmtData[2] | ((uint16_t)fmtData[3] << 8);
        sampleRate = (uint32_t)fmtData[4] | ((uint32_t)fmtData[5] << 8) |
                     ((uint32_t)fmtData[6] << 16) | ((uint32_t)fmtData[7] << 24);
        bitsPerSample = (uint16_t)fmtData[14] | ((uint16_t)fmtData[15] << 8);

        // Skip extra header bytes if chunk > 16
        if (chunkSize > 16) {
          for (uint32_t k = 0; k < chunkSize - 16; k++) {
            while (!client.available() && client.connected()) delay(1);
            if (client.available()) client.read();
          }
        }
      }
      // Check for "data" chunk
      else if (chunkHeader[0] == 'd' && chunkHeader[1] == 'a' && chunkHeader[2] == 't' && chunkHeader[3] == 'a') {
        foundData = true;
        break;
      }
      else {
        // Skip unknown chunk
        for (uint32_t k = 0; k < chunkSize; k++) {
          while (!client.available() && client.connected()) delay(1);
          if (client.available()) client.read();
        }
      }
    }

    if (!foundData) {
      Serial.println(F("❌ [I2S AUDIO] Could not locate 'data' chunk in WAV stream"));
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

    // Dynamically lock hardware clock PLL dividers to match audio sample rate
    i2s_set_clk(I2S_PORT_NUM, sampleRate, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_STEREO);

    // 3. Audio Streaming Loop
    const int CHUNK_SAMPLES = 128;
    int16_t rawChunk[CHUNK_SAMPLES * 2];
    int16_t stereoChunk[CHUNK_SAMPLES * 2];

    unsigned long lastIdleTime = millis();
    unsigned long lastVizTime = millis();
    unsigned long totalBytesStreamed = 0;

    while (client.connected() || client.available()) {
      int avail = client.available();
      if (avail <= 0) {
        if (millis() - lastIdleTime > 3000) {
          break; // Stream completed
        }
        delay(2);
        yield();
        continue;
      }

      lastIdleTime = millis();

      int bytesToRead = (channels == 1) ? (CHUNK_SAMPLES * 2) : (CHUNK_SAMPLES * 4);
      if (avail < bytesToRead) bytesToRead = avail;
      if (bytesToRead % 2 != 0) bytesToRead--;

      if (bytesToRead <= 0) {
        delay(1);
        continue;
      }

      size_t bytesRead = client.read((uint8_t*)rawChunk, bytesToRead);
      if (bytesRead == 0) continue;

      totalBytesStreamed += bytesRead;
      int samplesRead = bytesRead / 2;

      // Scale volume and duplicate mono into stereo channels
      if (channels == 1) {
        for (int i = 0; i < samplesRead; i++) {
          int16_t s = (int16_t)(((int32_t)rawChunk[i] * currentVolume) / 100);
          stereoChunk[i * 2]     = s;
          stereoChunk[i * 2 + 1] = s;
        }
        size_t written = 0;
        i2s_write(I2S_PORT_NUM, stereoChunk, samplesRead * 4, &written, portMAX_DELAY);
      } else {
        for (int i = 0; i < samplesRead; i++) {
          stereoChunk[i] = (int16_t)(((int32_t)rawChunk[i] * currentVolume) / 100);
        }
        size_t written = 0;
        i2s_write(I2S_PORT_NUM, stereoChunk, samplesRead * 2, &written, portMAX_DELAY);
      }

      // Animate visualizer periodically
      if (visualizerCallback && (millis() - lastVizTime >= 65)) {
        lastVizTime = millis();
        visualizerCallback();
      }

      yield();
    }

    Serial.print(F("✅ [I2S AUDIO] Voice stream playback completed ("));
    Serial.print(totalBytesStreamed);
    Serial.println(F(" bytes delivered to 8Ω speaker)"));

    silence(25);
    // Restore default 44.1kHz rate for standard chimes
    i2s_set_clk(I2S_PORT_NUM, I2S_SAMPLE_RATE, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_STEREO);
    isPlaying = false;
    return true;
  }


  // --------------------------------------------------------------------------
  // Attention Chime (Matches speaker_node_client.py: 587Hz -> 880Hz)
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
  // Notice Playback Sound Cue (Played when announcement stream begins)
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
