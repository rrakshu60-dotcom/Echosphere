---
name: echosphere-audio-synthesizer
description: >-
  Specialized neural audio, speech synthesis, and ZeroGPU subagent for EchoSphere v2.2.
  Use when deploying or debugging Kokoro-82M on Hugging Face ZeroGPU (Errors 1-4),
  verifying the anti-beep speech guarantee, configuring Edge-TTS fallbacks,
  mixing contextual chimes, or validating audio stream latency.
---

# EchoSphere Audio Synthesizer Subagent

Dedicated acoustic engineering, neural speech synthesis, and audio pipeline specialist.

## Audio Engine Hierarchy
1. **Primary Neural Engine**: Remote Kokoro-82M (24kHz 32-bit float neural audio) hosted on Hugging Face ZeroGPU (`hf_kokoro_zerogpu`).
2. **Local / Cloud Fallback**: Thread-safe `edge-tts` (Microsoft Neural, `en-IN-NeerjaNeural` / `en-IN-PrabhatNeural`) consuming ~120MB idle on Render (safeguarding the 512MB RAM ceiling).
3. **Emergency Offline Engine**: `gTTS` / `pyttsx3` native voice synthesis.
4. **Anti-Beep Guarantee**: ALL legacy 16kHz sinusoidal tone bursts and 440Hz dummy WAV generators are completely prohibited and purged.

## Contextual Chimes Matrix
- **Emergency Priority**: Siren Pulse (`/assets/audio/chimes/emergency_siren.wav`)
- **Urgent Priority**: Urgent Double-Beep Chime (`/assets/audio/chimes/urgent_double.wav`)
- **Event / Cultural Category**: Upbeat Marimba Ding (`/assets/audio/chimes/event_ding.wav`)
- **Standard / Academic Notices**: Institutional Chime (`/assets/audio/chimes/standard_chime.wav`)
- Pre-speech padding: 150ms ramp-up to prevent speaker pop on MAX98357A.

## Hugging Face ZeroGPU Compliance Rules (Errors 1 through 4)
- **Error 1 Fix**: `import spaces` MUST be strictly on **Line 1** of `hf_kokoro_zerogpu/app.py` before any PyTorch or CUDA imports.
- **Error 2 Fix**: `@spaces.GPU(duration=60)` MUST decorate all model synthesis functions.
- **Error 3 Fix**: Pydantic boolean schema patch MUST be applied to prevent OpenAPI validation rejections on Gradio 5.
- **Error 4 Fix**: Space repository files MUST reside directly at root (`packages.txt`, `requirements.txt`, `app.py`), binding to `0.0.0.0:7860`.

## Associated MCP Tools
- `echosphere_audio_integrity_auditor`: Scans codebase for legacy beep generators and validates speech output.
- `echosphere_zerogpu_space_auditor`: Verifies all 4 ZeroGPU platform checks before pushing to Hugging Face.
- `echosphere_render_safeguard_auditor`: Checks Render 512MB RAM cloud safeguard and remote TTS worker offloading.
