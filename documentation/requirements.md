All Requirements (Adjusted for RTX 4070 12GB + i7-13700KF):

Functional Requirements:
- Persona customization: Name, gender, age, birthday, physical appearance, personality, voice, etc.
- Abilities:
  - Companion/chat (uncensored text generation).
  - Web search/consolidation.
  - Image/video generation/editing (short videos feasible).
  - Coding, homework/tests, self-learning help.
  - Continuous user learning (memory DB + interaction logging).
  - World updates via internet tools.
  - Analyze/summarize images/videos/documents (multimodal).

Non-Functional Requirements:
- 100% personalized, uncensored, user-rule only.
- Modular for updates.
- Hosted locally via Open WebUI on PC.
- Accessible only via home LAN/VPN (trusted users, primarily you).
- Full privacy: Local data/storage.
- Performance: GPU-accelerated (quantized models for optimal speed/VRAM).
- Use models fitting 12GB VRAM (7-13B full, up to ~30B quantized).

Persona Requirements:
- Fully user-defined virtual persona attributes.

Other:
- Personal/home use only.
- Leverage RTX 4070 for inference/training/image gen; i7-13700KF for CPU tasks.