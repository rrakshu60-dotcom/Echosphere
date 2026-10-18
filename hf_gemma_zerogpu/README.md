---
title: EchoSphere Campus Gemma 2B AI Brain
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: 100% Free ZeroGPU AI Brain for EchoSphere
---

# 🧠 EchoSphere Campus Gemma 2B AI Brain (ZeroGPU)

Dedicated, **100% free** neural text generation microservice for **EchoSphere** (Campus Announcement & Broadcast Platform).

## 🚀 Key Capabilities
- **ZeroGPU Acceleration**: Dynamically acquires NVIDIA A10G/A100 GPU computing power via Hugging Face `@spaces.GPU` for sub-second inference.
- **Fine-Tuned Campus Weights**: Powered by `RakshiRoxy/echosphere-campus-gemma-2b` fine-tuned on 50,000+ institutional samples.
- **Zero Local Hardware**: Runs 100% serverlessly on Hugging Face Spaces.
- **API Endpoints**:
  - `POST /generate` - Notice drafting, circular expanding, tutoring, and conversational answering
  - `GET /health` - Health check and GPU readiness status
  - `GET /` - Interactive Gradio Web Demo
