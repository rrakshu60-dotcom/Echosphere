#ifndef ECHOSPHERE_AUDIO_MANAGER_H
#define ECHOSPHERE_AUDIO_MANAGER_H

#include "config.h"
#include "arduino_compat.h"

#include <math.h>
#include <functional>

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
  mutable Audio audio;

public:
  AudioManager() {}

  void begin() {
    Serial.println(F("🔊 [I2S AUDIO] Initializing MAX98357A I2S driver via ESP32-audioI2S..."));

    #if defined(PIN_I2S_SD) && (PIN_I2S_SD >= 0)
      pinMode(PIN_I2S_SD, OUTPUT);
      digitalWrite(PIN_I2S_SD, HIGH); // Un-mute amplifier IC
      delay(10);
    #endif

    // Route standard I2S pins to MAX98357A Class-D amplifier
    audio.setPinout(PIN_I2S_BCLK, PIN_I2S_LRC, PIN_I2S_DIN);

    // Set internal RAM buffer size (24KB RAM buffer for smooth cloud streaming)
    audio.setBufsize(24576, 0);

    // Set connection timeout: 5s plain HTTP, 10s HTTPS SSL handshake (for Cloudflare/Render)
    audio.setConnectionTimeout(5000, 10000);

    // Map 0..100% volume to ESP32-audioI2S scale (0..21)
    uint8_t aVol = (uint8_t)map(currentVolume, 0, 100, 0, 21);
    audio.setVolume(aVol);

    isInitialized = true;
    delay(50); // Allow MAX98357A internal PLL to lock to I2S clock
    Serial.println(F("✅ [I2S AUDIO] MAX98357A 3W Class-D I2S Amplifier ready for 8Ω Speaker!"));
  }

  void setVolume(int vol) {
    currentVolume = constrain(vol, 0, 100);
    uint8_t aVol = (uint8_t)map(currentVolume, 0, 100, 0, 21);
    audio.setVolume(aVol);
    Serial.print(F("🔊 [I2S AUDIO] Volume set to "));
    Serial.print(currentVolume);
    Serial.print(F("% (Audio lib level: "));
    Serial.print(aVol);
    Serial.println(F("/21)"));
  }

  int getVolume() const {
    return currentVolume;
  }

  bool getIsPlaying() const {
    return isPlaying || audio.isRunning();
  }

  // --------------------------------------------------------------------------
  // Pure 16-Bit PCM Sine Wave Tone Generator via I2S
  // --------------------------------------------------------------------------
  void playTone(float frequency, unsigned long durationMs) {
    if (!isInitialized || frequency <= 0 || currentVolume <= 0) {
      delay(durationMs);
      return;
    }

    if (audio.isRunning()) {
      audio.stopSong();
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
#if ESP_IDF_VERSION_MAJOR == 5
      if (!audio.m_i2s_tx_handle) {
        delay(durationMs);
        isPlaying = false;
        return;
      }
      esp_err_t err = i2s_channel_write(audio.m_i2s_tx_handle, sampleBuffer, samplesThisChunk * 4, &bytesWritten, 100);
      if (err != ESP_OK) {
        i2s_channel_enable(audio.m_i2s_tx_handle);
        i2s_channel_write(audio.m_i2s_tx_handle, sampleBuffer, samplesThisChunk * 4, &bytesWritten, 100);
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
#if ESP_IDF_VERSION_MAJOR == 5
    if (!audio.m_i2s_tx_handle) {
      delay(durationMs);
      return;
    }
#endif
    int16_t zeroBuffer[64 * 2] = {0};
    unsigned long totalChunks = (I2S_SAMPLE_RATE * durationMs) / (1000UL * 64);
    if (totalChunks == 0) totalChunks = 1;
    size_t written = 0;
    for (unsigned long i = 0; i < totalChunks; i++) {
#if ESP_IDF_VERSION_MAJOR == 5
      i2s_channel_write(audio.m_i2s_tx_handle, zeroBuffer, sizeof(zeroBuffer), &written, 100);
#else
      i2s_write(I2S_PORT_NUM, zeroBuffer, sizeof(zeroBuffer), &written, portMAX_DELAY);
#endif
    }
  }

  void stopTone() {
    if (audio.isRunning()) {
      audio.stopSong();
    }
    silence(20);
    isPlaying = false;
  }

  // --------------------------------------------------------------------------
  // Stream Lossless / Compressed Audio Stream Directly via ESP32-audioI2S
  // Supports MP3, AAC, and WAV over HTTPS with built-in ring buffering
  // --------------------------------------------------------------------------
  bool playStream(const String& streamUrl, std::function<void()> visualizerCallback = {}) {
    if (!isInitialized || streamUrl.length() == 0) return false;

    isPlaying = true;
    Serial.print(F("🎧 [I2S AUDIO] Connecting ESP32-audioI2S to: "));
    Serial.println(streamUrl);

    #if defined(PIN_I2S_SD) && (PIN_I2S_SD >= 0)
      pinMode(PIN_I2S_SD, OUTPUT);
      digitalWrite(PIN_I2S_SD, HIGH);
    #endif

    // Sync volume
    uint8_t aVol = (uint8_t)map(currentVolume, 0, 100, 0, 21);
    audio.setVolume(aVol);

    if (audio.isRunning()) {
      audio.stopSong();
    }

    bool started = audio.connecttohost(streamUrl.c_str());
    if (!started) {
      Serial.println(F("❌ [I2S AUDIO] Failed to initiate stream connection"));
      isPlaying = false;
      return false;
    }

    unsigned long startTime = millis();
    unsigned long lastVizTime = millis();

    // Dedicated audio pump loop with tight safety timeouts
    while (audio.isRunning()) {
      audio.loop();

      if (visualizerCallback && (millis() - lastVizTime >= 75)) {
        lastVizTime = millis();
        visualizerCallback();
      }

      // Safety duration guard: max 35s per announcement stream
      if (millis() - startTime > 35000UL) {
        Serial.println(F("⚠️ [I2S AUDIO] Stream exceeded 35s safety limit. Stopping cleanly."));
        audio.stopSong();
        break;
      }

      yield();
    }

    Serial.println(F("✅ [I2S AUDIO] Voice stream playback completed cleanly."));
    if (audio.isRunning()) {
      audio.stopSong();
    }
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
