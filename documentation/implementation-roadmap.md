# Personal AI Companion – Implementation Roadmap

**Project Goal**  
Build a 100% local, fully personalized, uncensored virtual companion hosted on a Windows 11 PC (RTX 4070 12GB VRAM + Intel i7-13700KF), accessible only via home LAN/OpenVPN.

**Current Status**  
Design phase complete – Architecture finalized.

**Implementation Pace**  
Slow and deliberate – one stage at a time, with full testing and confirmation before proceeding.

## Stages

| Stage | Objective | Key Deliverables | Estimated Time | Status |
|-------|-----------|------------------|----------------|--------|
| **1** | Environment Setup | • Docker Desktop installed & running<br>• NVIDIA drivers + CUDA verified<br>• Ollama installed and GPU working | 1–2 hours | Not started |
| **2** | Core LLM | • Pull Dolphin 3.0 Llama-3.1 8B (uncensored)<br>• Full GPU offload confirmed<br>• Test basic inference via Ollama CLI | 2–4 hours (download time) | Not started |
| **3** | Open WebUI Deployment | • Deploy Open WebUI via Docker (CUDA-enabled)<br>• Bind to LAN IP (192.168.x.x:8080)<br>• Basic chat working with Dolphin 8B | 2–3 hours | Not started |
| **4** | Persona & Customization | • Create `persona.json`<br>• Custom system prompt<br>• Set persona avatar & replace Open WebUI logo<br>• Enable Piper TTS voice | 1–2 hours | Not started |
| **5** | Image Generation | • Install ComfyUI<br>• Load FLUX.1 Dev/Schnell<br>• Integrate with Open WebUI → inline image generation & editing | 4–6 hours | Not started |
| **6** | Memory, Multimodal & Web Search | • Activate persistent ChromaDB memory across chats<br>• Add Qwen2.5-VL 7B for image/video/doc analysis<br>• Enable real-time web search (RAG tools) | 3–5 hours | Not started |
| **7** | Advanced Features | • Video generation & editing (Wan 2.1 / Mochi-1 via ComfyUI)<br>• Custom Python tools (folder browsing, file reading, screenshot capture)<br>• Optional: Automatic screen monitoring / phone mirroring | 4–8 hours | Not started |

## Rules for Progress
- Complete one stage fully before moving to the next.
- Test thoroughly after each stage.
- Only proceed when I confirm “Stage X complete – ready for next”.

**Total estimated time**: 2–4 weeks (part-time, relaxed pace)