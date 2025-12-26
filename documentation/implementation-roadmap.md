# Personal AI Companion – Implementation Roadmap

**Project Goal**  
Build a 100% local, fully personalized, uncensored virtual companion hosted on a Windows 11 PC (RTX 4070 12GB VRAM + Intel i7-13700KF), accessible only via home LAN/OpenVPN.

**Implementation Pace**  
Slow and deliberate – one stage at a time, with full testing and confirmation before proceeding.

## Stages

| Stage | Objective | Key Deliverables | Estimated Time |
|-------|-----------|------------------|----------------|
| **1** | Environment Setup | • Docker Desktop installed & running<br>• NVIDIA drivers + CUDA verified<br>• Ollama installed and GPU working | 1–2 hours |
| **2** | Core LLM | • Pull Dolphin 3.0 Llama-3.1 8B (uncensored)<br>• Full GPU offload confirmed<br>• Test basic inference via Ollama CLI | 2–4 hours (download time) |
| **3** | Chainlit UI Deployment | • Install Chainlit<br>• Create basic app script<br>• Test chat with local LLM in browser UI | 1–2 hours |
| **4** | Persona & Customization | • Create `persona.json`<br>• Custom system prompt<br>• Set persona avatar & replace Chainlit UI logo<br>• Enable Piper TTS voice | 1–2 hours |
| **5** | Image Generation | • Install ComfyUI<br>• Load FLUX.1 Dev/Schnell<br>• Integrate with Chainlit UI → inline image generation & editing | 4–6 hours |
| **6** | Memory, Multimodal & Web Search | • Activate persistent ChromaDB memory across chats<br>• Add Qwen2.5-VL 7B for image/video/doc analysis<br>• Enable real-time web search (RAG tools) | 3–5 hours |
| **7** | Advanced Features | • Video generation & editing (Wan 2.1 / Mochi-1 via ComfyUI)<br>• Custom Python tools (folder browsing, file reading, screenshot capture)<br>• Optional: Automatic screen monitoring / phone mirroring | 4–8 hours |

**Total estimated time**: 2–4 weeks (part-time, relaxed pace)