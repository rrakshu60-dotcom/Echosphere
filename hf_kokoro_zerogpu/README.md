---
title: EchoSphere Kokoro TTS
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: Kokoro-82M High-Fidelity Speech Worker for EchoSphere
---

# 🎙️ EchoSphere Kokoro-82M AI Worker (ZeroGPU)

This Hugging Face Space is a dedicated, **100% free** neural audio microservice for **EchoSphere** (Smart Campus PA & IoT Speaker System).

## 🚀 Key Capabilities
- **ZeroGPU Acceleration**: Dynamically acquires NVIDIA A100 GPU computing power via Hugging Face `@spaces.GPU` for lightning-fast speech generation.
- **OpenAI-Compatible Speech API**: Exposes `POST /v1/audio/speech` so Render backend communicates seamlessly with zero memory overhead.
- **Dual Audio Format Pipeline**:
  - **16-bit PCM WAV (24,000 Hz)**: Perfect for direct, lossless I2S streaming on ESP32 (`MAX98357A`).
  - **MP3 (128 kbps)**: Compact streaming for Web and Mobile Flutter clients.
- **Zero Credit Card Required**: Runs entirely on Hugging Face Spaces' free Gradio + ZeroGPU / CPU Basic tier.

## 📡 API Endpoints
- `GET /health` - Health check & GPU status
- `GET /v1/models` - Model listing
- `POST /v1/audio/speech` - Speech synthesis
  - Body: `{"input": "Text to read", "voice": "af_heart", "response_format": "wav"}`
- `GET /` - Interactive Gradio Web Demo
