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
    
    Users can switch freely between downloaded models in Open WebUI. 

**Stage 2 complete** when the model responds successfully.

### Stage 3️⃣: Chainlit UI Deployment

In this stage, we will make use of the open-source customizable [Chainlit UI](https://docs.chainlit.io/get-started/overview) to run the AI persona.

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
    Those features can actually be enabled, so no worries.
    Besides, as Chainlit allows extensive rebranding (as of late December 2025), we can greatly customize this Chainlit UI to fit our AI persona's themes.  

4. Chainlit Configuration  
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
        ```
        npx prisma migrate deploy
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

5. Chainlit setup for `app.py`  
    Now, we must create a folder named `public` under the root directory.  
    In that folder, create two files: `users.txt` and `system-prompt.txt` (optional).  
    - `users.txt`
        A file to store user credentials in the form of `username,password`.  
        Fill in the file with the allowed credentials.  
        Example:
        ```
        admin,admin_Password
        janedoe,jane123doe456
        ```
        This file must be present, or the app won't start.  
        Of course, you can also omit the authentication altogether, but please note that chat histories and side bar **cannot** be enabled without authentication and data layer both implemented.  

    - `system-prompt.txt`  
        A system prompt is a prompt fed into the AI to define its details.  
        This file is optional, as no system prompt simply means to use the AI model as is.
        Example of system prompt:
        ```
        You are {{name}}, a {{age}}-year-old {{gender}} virtual companion.
        Appearance: {{appearance}}
        Personality: {{personality}}
        Birthday: {{birthday}}

        {{other details and backgrounds}}

        Rules:
        {{rules joined by newlines}}

        Use full conversation history and retrieved memories to stay consistent.
        You live in {{country}} — always use local cultural accuracy when relevant.
        ```  

        Feel free to modify `app.py` and `system-prompt.txt` as you need.
    
    ```
    persona-ai/
    ├── public/
    |   ├── users.txt
    |   └── system-prompt.txt (optional)
    └── app.py
    ```

    
6. Chainlit UI Customization  
    Chainlit offers deep customization of it UI. Here, we will go through some of the basics:  

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
    |   ├── system-prompt.txt
    |   └── users.txt
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
        Then, go to `en-US.json` and edit this part to change the browser tab name:
        ```
        "auth": {
            "login": {
                "title": "<browser tab name>",
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
     
    


**Stage 3 complete** - you now have a full-featured, ChatGPT-style browser interface connected to your local LLM!

### Stage 4️⃣: ...
