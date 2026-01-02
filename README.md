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

## Setup Guide (Windows 11 + NVIDIA GPU)

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
    You should see your RTX GPU VRAM size and CUDA version.

2. **Download and Install CUDA**  
    Download the latest version of CUDA and install it:  
    https://developer.nvidia.com/cuda-toolkit-archive

3. **Install Docker Desktop**  
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

4. **Enable NVIDIA GPU Support in Docker**  
    Open Docker Desktop → Settings → Resources → Advanced
    - GPU support should be enabled automatically with recent drivers.

    Verify GPU passthrough:
    ```cmd
    docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
    ```
    This should show your GPU info inside the container.

5. **Download and Install Ollama**  
    Go to: https://ollama.com/download  
    - Download the Windows installer (.exe).  
    - Run it — installation is quick.  

    Verify Ollama installation:
    ```cmd
    ollama --version
    ```

**Stage 1 complete** - your environment is ready.

### Stage 2️⃣: Pull the LLM models

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

    Type a message and see the response. Exit with `/bye`.  

    Feel free to download and test other uncensored LLM models as well from here: https://ollama.com/search?q=uncensored.  

    The Dolphin LLM that we pulled is actually not that uncensored. So, here are some examples of uncensored LLM models (as of late Dec 2025) so our AI persona has even more freedom.
    - dolphin-phi
    - HammerAI/llama-3-lexi-uncensored
    - slideshow270/llama-3.1-8b-lexi-uncensored-v2  
    
    Feel free to explore and `ollama pull` as many as you like.  
    Users can switch freely between downloaded models in Chainlit UI. 

**Stage 2 complete** when the model responds successfully.

### Stage 3️⃣: Chainlit UI Deployment

In this stage, we will implement the open-source customizable [Chainlit UI](https://docs.chainlit.io/get-started/overview) to run the AI persona.

1. First, we need to make sure Ollama is running in the background:  
    Open a new Command Prompt or PowerShell and run:
    ```cmd
    ollama list
    ```

    You should see cognitivecomputations/dolphin-llama3.1:8b listed.  
    If Ollama isn't running, start it with `ollama run dolphin-llama3.1:8b` in a separate window (you can close the chat prompt with `/bye`, but leave the window open to keep the server alive). Ollama runs as a service on port 11434.  
    If everything looks good → no further action.

2. Download and Install PostgreSQL  
    PostgreSQL acts as the database to store the memories of the AI persona. When implemented, we enable data persistence on Chainlit.  
    Download and install it from here: https://www.postgresql.org/download/  
    For chat history and side bar to be enabled, Chainlit requires authentication and data persistence to be enabled beforehand.  

3. Install `chainlit` using `pip` and make sure it works.
    Open a new Command Prompt or PowerShell and run:
    ```cmd
    pip install chainlit
    ```
    And then, run this command to test it:
    ```cmd
    chainlit hello
    ```
    This will run Chainlit and open the UI on your browser. It's on the address http://localhost:8000.  

    Notice that it starts up as very basic - just a plain chat, no login page, no side bar with chat histories, and using Chainlit logo everywhere.  

    Those features will be enabled in the next stage, so no worries!
    Besides, as Chainlit allows extensive rebranding (as of late December 2025), we will also customize the Chainlit UI to fit our AI persona's themes!  

**Stage 3 complete** - you now have a full-featured, ChatGPT-style browser interface connected to your local LLM!

### Stage 4️⃣: Persona & Customization

In this stage, we will enable useful features in Chainlit UI, and also customize the UI to suit our persona's themes.  

1. Chainlit Database and Chat Histories  
    First of all, for chat history and sidebar to be enabled, we need to integrate PostgreSQL to Chainlit.  

    - **Create database for the AI**  
        Open `pgAdmin` on your computer.  
        On `Object Explorer` panel, right-click on `Servers > PostgreSQL > Databases`.  
        Then click on `Create > Database`.  
        Give it a name, and then click `Save`.  
        The newly created database now shows under `Databases`.  

    - **Imprint the Prisma schema of Chainlit datalayer to the database**  
        In a folder **outside** of this project folder, clone the [chainlit-datalayer](https://github.com/Chainlit/chainlit-datalayer) repository:
        ```cmd
        git clone https://github.com/Chainlit/chainlit-datalayer
        ```
        Navigate into the `chainlit-datalayer` folder, create a file named `.env` in its root directory.
        Edit this line and paste it into `.env`:
        ```
        DATABASE_URL=postgresql://<database owner name>:<password>@localhost:5432/<database name>
        ```
        For example:
        ```
        DATABASE_URL=postgresql://postgres:postgres_Password@localhost:5432/persona-ai
        ```
        Now, still in the root directory, run:
        ```cmd
        npx prisma migrate deploy
        ```
        (Optional) The database can be viewed and edited in a browser by running this command in the `chainlit-datalayer` root directory:
        ```cmd
        npx prisma studio
        ```
    
    - **Setup Chainlit environment in our project**  
        Copy the `.env` file created in `chainlit-datalayer` folder just now into this project's root directory.  
        Run this command in this project's root directory:
        ```
        chainlit create-secret
        ```
        This will create the Chainlit JWT secret needed to run the Python script that powers Chainlit ─ `app.py`.
        Copy the whole line into the `.env` file.
        Now, the `.env` file should look like this:
        ```
        DATABASE_URL=postgresql://<database owner name>:<password>@localhost:5432/<database name>
        CHAINLIT_AUTH_SECRET="*abcdefghijklmnopqrstuvwxyz!@#$%^&><:?0123456789"
        ```

2. Chainlit Environment Configuration for `app.py`  
    First of all, paste this into your `.env` file:
    ```
    # Network & Server Settings
    CHAINLIT_HOST=0.0.0.0
    CHAINLIT_PORT=8080

    # Ollama Parallelism Settings
    OLLAMA_NUM_PARALLEL=5
    OLLAMA_MAX_LOADED_MODELS=5

    # Hardware Optimization
    # Setting this to 1 helps reduce VRAM usage on your RTX 4070
    OLLAMA_FLASH_ATTENTION=1 

    # Application Paths
    SYSTEM_PROMPT_PATH=templates/system-prompt.txt
    USER_JSON_PATH=public/users
    ```

    `CHAINLIT_HOST`: Host on the LAN IP address.
    `CHAINLIT_PORT`: The LAN IP port to use.
    `OLLAMA_NUM_PARALLEL`: How many concurrent users can be processed at once.  
    `OLLAMA_MAX_LOADED_MODELS`: The number of LLM models Ollama keeps loaded in memory (VRAM/RAM) simultaneously.  
    `OLLAMA_FLASH_ATTENTION`: Enables Flash Attention, an optimized attention mechanism for transformers that reduces memory usage and improves inference speed on NVIDIA GPUs. Helpful for larger models (e.g., 7-13B) by minimizing VRAM overhead during attention computations.  
    `system-prompt.txt`: A system prompt is a prompt fed into the AI to define its details. This file is a template file that `app.py` edits and feeds into the AI model.  
    `public/users`: Folder where each user's system prompt JSON file resides. `app.py` will fall back to just using the Guest profile if this folder doesn't exist.   

    Now, create the `public` folder in the root directory of this project. We'll be using this folder extensively in the upcoming steps.  

    In the `public` folder, create a folder named `users`.  

    Copy `templates/users.json` into `public/users`, open and fill in the fields accordingly and rename it to the username of the allowed user. `app.py` generates a unique system prompt of each user based on their JSON file here.   

    **Important note on filling up the users' system prompt JSONs:**  
    Use 3rd person (he/him/she/her/they/them/this user/...) pronouns to address the user.  
    Use 2nd person (you/your/...) pronouns to address the persona.

    Use `bcrypt-hash.py` generate the password hash (using `bcrypt`) for the account, and copy paste into the `password_hash` field of the user's JSON.
    ```cmd
    python bcrypt-hash.py <password in plain text>
    ```

    There can be more than one of this JSON files. Each JSON file means each allowed user.  
    FYI, chat histories are **not** shared among users.  

    Next, copy `templates/persona.json` into `public` folder. Open and fill in the fields accordingly. This JSON file defines the global settings, configurations and personalities of your persona.  
    Feel free to modify `app.py` and `templates/system-prompt.txt` as you need.
    ```
    persona-ai/
    ├── public/
    |   ├── users/
    |   |   └── <username>.json
    |   └── persona.json
    ├── app.py
    └── bcrypt-hash.py
    ```

3. Chainlit UI Customization  
    Chainlit offers deep customization of its UI. Here, we will go through some of the basics:  

    ```
    persona-ai/
    ├── .chainlit/
    |   ├── translations/
    |   |   └── en-US.json              <----- Login page wordings
    |   └── config.toml                 <----- Assistant name, session timeouts, default theme, login page image and filters
    ├── public/
    |   ├── avatars/
    |   |   └── <assistant name>.png    <----- Assistant's chat avatar
    |   ├── login.png                   <----- (can be any name) Login page background
    |   ├── logo_dark.png               <----- Logo used in dark theme
    |   ├── logo_light.png              <----- Logo used in light theme
    |   ├── favicon.png                 <----- Browser tab icon
    |   ├── users/
    |   |   └── <username>.json
    |   └── persona.json
    ├── .env
    └── chainlit.md                     <----- Readme button content
    ```

    *Note: You can also use .jpg and .gif instead of .png files, but we'll use .png as the example.*

    - Persona browser tab name and icon
        Browser tab name ─ edit `config.toml`:
        ```
        [UI]
        # Name of the assistant.
        name = <assistant name>
        ```
        As for tab icon, name your picture as `favicon.png` and place it in `public` folder.
    
    - Login page ─ background image and wordings
        Put the picture (of any name) in `public` folder.   
        Then, edit this line in `config.toml`:  
        ```
        [UI]
        ...
        login_page_image = "./public/<login background image file>"
        ```
        Then, go to `en-US.json` and edit this part to change the login page wordings:
        ```
        "auth": {
            "login": {
                "title": "<welcome message>",
                "form": {
                ...
        ```
    
    - Persona avatar
        Put the picture `public/avatars` and name it as `<assistant name>.png`.
    
    - Remove `Readme` button in chat space 
        Make `chainlit.md` blank, and the `Readme` button in the chat space will be gone.
    
    - Disable session timeouts
        Comment out (#) these two options in `config.toml`:
        ```
        [project]
        # Duration (in seconds) during which the session is saved when the connection is lost
        # session_timeout = 3600

        # Duration (in seconds) of the user session expiry
        # user_session_timeout = 1296000  # 15 days
        ```
    
    Feel free to explore and experiment around for more customizations!

4. Enable XTTS Voice for Responses  
    Create a folder named `voice` in `public` folder. Put the voice sample for your persona into the folder as `persona.wav`.  

    ```
    persona-ai/
    └── public/
        └── voice/
            └── persona.wav
    ```

**Stage 4 complete** - you now have a fully customizable AI chat frontend UI with multiple LLM models, with a fully configurable AI persona with voice support, who can switch its personalities depending on who it's interacting with!

### Stage 5️⃣: Image generation

1. Install ComfyUI  
    Go to this link, download and install ComfyUI: https://www.comfy.org/download  
    After installed, launch it for further setups.
    


## Quick Start

Run these commands in the root directory of this project ─ `persona-ai/`

```cmd
conda create -n persona-ai python=3.11 -y
conda activate persona-
conda install -c conda-forge ffmpeg
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/<cu***>
pip install -r requirements.txt
hf download fishaudio/openaudio-s1-mini --local-dir public/fishaudio/models/openaudio-s1-mini
docker run -d --name fish-speech -p 8081:7860 --gpus all -v "%CD%\public\fishaudio\models":/app/checkpoints -e BACKEND=cuda -e COMPILE=1 fishaudio/fish-speech:latest
launcher.bat
```
`<cu***>`: Find out the correct version for your GPU. For example, RTX 4070 uses 'cu121'.


