---
title: EchoSphere Kokoro TTS
emoji: 🎙️
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 8880
---

# EchoSphere Kokoro-82M Neural TTS Worker

High-performance Text-to-Speech microservice for EchoSphere Campus PA & Smart Speakers.
Powered by `remsky/Kokoro-FastAPI` and the open-weights `hexgrad/Kokoro-82M` neural model.

### Features
- Native OpenAI-compatible `/v1/audio/speech` endpoint.
- 16 GB RAM allocation on Hugging Face Spaces (zero OOM risk).
- High-fidelity neural voice synthesis (`af_heart`, `am_adam`, `af_bella`, `bf_emma`, etc.).
- Direct MP3 and WAV streaming for ESP32 hardware and web dashboards.
