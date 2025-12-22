# 🎁 Local Persona AI Starter Template

A fully local, modular template for building your own personalized, uncensored AI companion on Windows 11 (RTX 40-series GPU recommended).

This repo is intentionally a **blank slate** — no pre-defined name, personality, or memory.  
You clone it, run the setup, and mold your companion from scratch: give it a name, a voice, a story, train it on your data, and make it truly yours.

**Features (when complete)**  
- Chat with a powerful local LLM (Dolphin 3.0 Llama-3.1 8B uncensored)  
- Inline image generation & editing (FLUX.1 via ComfyUI)  
- Short video generation (Wan 2.1 / Mochi-1)  
- Multimodal analysis (Qwen2.5-VL for images/videos/docs)  
- Persistent long-term memory across chats (ChromaDB)  
- Real-time web search  
- Custom tools (folder browsing, screenshots, etc.)  
- Secure access via your home LAN/OpenVPN  
- 100% private — nothing leaves your PC

**Tech Stack Summary**  
See `documentation/tech-stack.csv` for the full finalized stack.

## Quick Start (Windows 11 + NVIDIA GPU)

### 📋 Prerequisites
- Windows 11
- NVIDIA RTX GPU (4070 or better recommended) with **at least** 12 GB VRAM
- At least 16 GB system RAM

### Stage 1️⃣: Environment Setup

1. **Update NVIDIA Drivers**  
    Download and install the latest Game Ready or Studio Driver:  
    https://www.nvidia.com/Download/index.aspx

    Verify with:
    ```cmd
    nvidia-smi
    ```
    You should see your RTX 4070 with ~12 GB VRAM and CUDA 12+.

2. **Install Docker Desktop**  
    Download from:  
    https://www.docker.com/products/docker-desktop/  
    - Use the default WSL 2 backend.
    - Allow it to enable WSL 2 features if prompted.  
    
    After installation and reboot, test:
    ```cmd
    docker --version
    docker run hello-world
    ```
    You should see "Hello from Docker!".

3. **Enable NVIDIA GPU Support in Docker**  
    Open Docker Desktop → Settings → Resources → Advanced
    - GPU support should be enabled automatically with recent drivers.

    Verify GPU passthrough:
    ```cmd
    docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
    ```
    This should show your GPU info inside the container.

4. **Download and Install Ollama**  
    Go to: https://ollama.com/download  
    - Download the Windows installer (.exe).  
    - Run it — installation is quick.  

    Verify Ollama installation:
    ```cmd
    ollama --version
    ```

**Stage 1 complete** - your environment is ready.

### Stage 2️⃣: Pull the Core LLM

1. Pull the Core LLM Model
    Recommended starting model: cognitivecomputations/dolphin-llama3.1:8b (uncensored, ~4.7 GB Q4 quantized - fast and capable on 12 GB VRAM).  
    Run:
    ```cmd
    ollama pull cognitivecomputations/dolphin-llama3.1:8b
    ```

2. Test the Model
    ```cmd
    ollama run cognitivecomputations/dolphin-llama3.1:8b
    ```

    Type a message and see the response. Exit with /bye.  

**Stage 2 complete** when the model responds successfully.

### Stage 3️⃣: Open WebUI Deployment

1. Make sure Ollama is running in the background:  
    Open a new Command Prompt or PowerShell and run:
    ```cmd
    ollama list
    ```

    You should see cognitivecomputations/dolphin-llama3.1:8b listed.  
    If Ollama isn't running, start it with `ollama run dolphin-llama3.1:8b` in a separate window (you can close the chat prompt with /bye, but leave the window open to keep the server alive). Ollama runs as a service on port 11434.  
    If everything looks good → no further action.

2. **Pull, Run and Verify the Open WebUI Docker Container**  
    In PowerShell or Command Prompt (run as normal user, no admin needed), execute this single command:  
    ```powershell
    docker run -d -p 0.0.0.0:8080:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda
    ```
    This command pulls the official CUDA-optimized image and connects it to your host Ollama instance.  
    Explanation of the flags:  
    - `-d`: Run in detached (background) mode  
    - `-p 8080:8080`: Map container port 8080 to your host port 8080 (we'll access via http://localhost:8080)  
    - `--add-host=host.docker.internal:host-gateway`: Allows the container to reach your host's Ollama at http://host.docker.internal:11434  
    - `-v open-webui:/app/backend/data`: Persistent volume for chats, settings, etc.  
    - `--name open-webui`: Easy name to manage later  
    - `--restart always`: Auto-start on boot  
    - `ghcr.io/open-webui/open-webui:cuda`: The official GPU-enabled image (uses your RTX GPU)  

    The first run will download the image (~2-3 GB) — it may take 5–15 minutes depending on your internet.  
    Expected output: A long container ID (e.g., `ac3482bffbf1...`) will be printed — this means the container started successfully.  
    Verify in Docker Desktop:
    - Open Docker Desktop
    - Go to the **Containers** tab
    - You should see a container named **open-webui** with status **Running**
    - If it's not running, check **Logs** for errors.


3. **Access Open WebUI in Your Browser**

    - Open your web browser and go to:  
        **http://localhost:8080**

    - On first launch, you will be prompted to create an admin account:
        - Choose a username (e.g., your name or "admin")
        - Set a strong password
        - Click **Create Account** or **Sign Up**

    - After signing in, you’ll land on the main chat dashboard.

    - In the top-left corner, click the model selector dropdown.
        - Select **cognitivecomputations/dolphin-llama3.1:8b**

    - Click **New Chat** (or the + button) and send a test message:
        ```
        Hello, can you hear me?
        ```

    You should see a fast, streaming response powered by your RTX GPU.

**Stage 3 complete** - you now have a full-featured, ChatGPT-style browser interface connected to your local LLM!