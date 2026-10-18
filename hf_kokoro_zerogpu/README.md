---
title: EchoSphere Kokoro TTS & Campus Gemma Brain
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.16.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: ZeroGPU Campus Brain and Speech Worker
---

# 🎙️ EchoSphere Unified ZeroGPU AI & Voice Worker

This Hugging Face Space is a dedicated, **100% free** multi-modal neural microservice for **EchoSphere** (Smart Campus Announcement & PA Broadcast System).

## 🚀 Key Capabilities
- **ZeroGPU Acceleration**: Dynamically acquires NVIDIA A10G/A100 GPU computing power via Hugging Face `@spaces.GPU`.
- **Fine-Tuned Campus Brain**: Runs `RakshiRoxy/echosphere-campus-gemma-2b` in 4-bit NF4 quantization for institutional drafting, circular expanding, tutoring, and reasoning.
- **Kokoro-82M Voice Synthesis**: Generates crystal-clear 24kHz audio in 17 distinct institutional voices (`af_heart`, `am_adam`, `bf_emma`, etc.).
- **OpenAI-Compatible Speech API**: Exposes `POST /v1/audio/speech` for backend and ESP32 IoT audio streaming.
- **Campus AI Endpoint**: Exposes `POST /generate` for instant text generation from the fine-tuned model.
- **Zero Credit Card / Zero Local Server**: Runs 24/7 serverlessly in the cloud.

## 📡 API Endpoints
- `GET /health` - Health check & model readiness
- `POST /generate` - Notice drafting, circular expanding, and academic Q&A
  - Body: `{"prompt": "Draft an announcement...", "max_new_tokens": 256}`
- `POST /v1/audio/speech` - Speech audio synthesis
  - Body: `{"input": "Text to read", "voice": "af_heart", "response_format": "wav"}`
- `GET /` - Interactive Gradio Web Demo
