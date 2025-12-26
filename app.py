import os
import requests
import ollama
import json
import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.input_widget import Select
from typing import Optional

# --------------------- Global setup --------------------- #

if os.path.isfile("public/users.txt"):
    with open("public/users.txt", "r") as f:
        USERS = f.read()
else:
    print("[ERROR] Please create a 'user.txt' file under 'public' folder and store user credentials there as 'username,password'.\nExample: admin,adminpassword")
    exit()

if os.path.isfile("public/system-prompt.txt"):
    # Load system prompt from txt file
    with open("public/system-prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
else:
    print("[WARNING] No system prompt provided.")
    SYSTEM_PROMPT = ""

# Fetch installed Ollama models
available_models = [model['model'] for model in ollama.list()['models']]

if len(available_models) <= 0:
    print("No Ollama models found. Please install some via 'ollama pull'.")
    exit()

# -------------------------------------------------------- #

@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    if f"{username},{password}" in USERS:
        return cl.User(identifier=username, metadata={"role": "admin", "provider": "credentials"})
    return None

@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("chat_history", [])
    
    # Create and send the settings panel
    settings = await cl.ChatSettings(
        [
            Select(
                id="ollama_model",
                label="Select Ollama Model",
                values=available_models,
                initial_index=0
            )
        ]
    ).send()

    # Store in session
    cl.user_session.set("settings", settings)

@cl.on_message
async def on_message(message: cl.Message):

    settings = cl.user_session.get("settings")
    selected_model = settings["ollama_model"]

    # 1. Initialize an empty message to stream into
    msg = cl.Message(content="")
    await msg.send()

    # 2. Call Ollama with stream=True
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": selected_model,
            "prompt": message.content,
            "system": SYSTEM_PROMPT,
            "stream": True
        },
        stream=True
    )

    for chunk in response.iter_lines():
        if chunk:
            data = chunk.decode("utf-8")
            if "response" in data:
                await msg.stream_token(json.loads(data)["response"])

    await msg.update()

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):

    cl.user_session.set("chat_history", [])

    for message in thread["steps"]:
        if message["type"] == "user_message":
            cl.user_session.get("chat_history").append(
                {"role": "user", "content": message["output"]}
            )
        elif message["type"] == "assistant_message":
            cl.user_session.get("chat_history").append(
                {"role": "assistant", "content": message["output"]}
            )

@cl.on_chat_end
async def on_chat_end():
    try:
        await cl.context.emitter.emit("clear", {})
    except Exception:
        pass
