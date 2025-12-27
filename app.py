import os
import ollama
import bcrypt
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.input_widget import Select, Slider, TextInput
import chainlit.data.chainlit_data_layer as cl_data


# --------------------- Global setup --------------------- #

# --- FIX: Chainlit Datetime Bug Workaround ---
# We redefine the ISO_FORMAT to match what your system is actually producing.
# If your error says "unconverted data remains: Z", we use the format with Z.
# If it says "does not match format", we use the one without.
try:
    cl_data.ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f" 
except:
    pass

# A more robust fix: tell Chainlit's data layer to be less picky
original_create_step = cl_data.ChainlitDataLayer.create_step

async def patched_create_step(self, step_dict):
    if "createdAt" in step_dict and isinstance(step_dict["createdAt"], str):
        # Strip the 'Z' if it exists to prevent the "unconverted data" error
        step_dict["createdAt"] = step_dict["createdAt"].replace("Z", "")
    return await original_create_step(self, step_dict)

cl_data.ChainlitDataLayer.create_step = patched_create_step

#       Load the variables from .env
load_dotenv()
SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "templates/system-prompt.txt")
USER_JSON_PATH = os.getenv("USER_JSON_PATH", "public/users")

#       Registered users
if os.path.isdir(USER_JSON_PATH):
    USER_JSON_FILES = os.listdir(USER_JSON_PATH) if os.listdir(USER_JSON_PATH) != [] else ['templates/user.json']

#       Fetch installed Ollama models
available_models = [model['model'] for model in ollama.list()['models']]

if len(available_models) <= 0:
    print("No Ollama models found. Please install some via 'ollama pull'.")
    exit()

DEFAULT_MODEL = "mistral-nemo:latest"
if DEFAULT_MODEL not in available_models:
    DEFAULT_MODEL = available_models[0]

# -------------------------------------------------------- #

# --------------------- Helper functions --------------------- #

async def send_settings_to_chainlit():

    # Tells Chainlit: “Hey, use these settings right now in the chat.”
    # In other words: Apply the chat settings so they take effect.
    settings = await cl.ChatSettings(
        [
            Select(
                id="ollama_model",
                label="Ollama Model",
                values=available_models,
                initial_value=DEFAULT_MODEL
            ),
            Slider(
                id="temperature",
                label="Temperature",
                min=0.0,
                max=1.5,
                step=0.1,
                initial=0.7
            ),
            Slider(
                id="top_p",
                label="Top P",
                min=0.1,
                max=1.0,
                step=0.05,
                initial=0.9
            ),
            TextInput(
                id="num_ctx",
                label="Context Length",
                initial="32768"
            )
        ]
    ).send()

    # Remember these settings for the current user while they’re using the chat.
    cl.user_session.set("settings", settings)

def flatten_json(d, parent_key="", sep="."):

    """
    Flatten nested JSON into dot notation keys.
    Example: {"a": {"b": 1}} => {"a.b": 1}
    """
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_json(v, new_key, sep=sep))
        elif isinstance(v, list):
            # Convert lists to comma-separated strings
            items[new_key] = ", ".join(map(str, v)) if v else ""
        else:
            items[new_key] = v
    return items

def render_system_prompt(template_path: Path, persona_path: Path, user_path: Path) -> str:

    # Load template and JSONs
    template = template_path.read_text(encoding="utf-8")
    persona = json.loads(persona_path.read_text(encoding="utf-8"))
    user = json.loads(user_path.read_text(encoding="utf-8"))

    # Flatten JSONs
    flat_persona = flatten_json(persona)
    flat_user = flatten_json(user)

    # Prepare placeholder dictionary
    placeholders = {}
    for key, val in flat_persona.items():
        placeholders[f"persona.{key}"] = str(val)
    for key, val in flat_user.items():
        placeholders[f"user.{key}"] = str(val)

    # Replace placeholders in template
    system_prompt = template
    for key, val in placeholders.items():
        system_prompt = system_prompt.replace(f"{{{{{key}}}}}", val)

    return system_prompt


# ------------------------------------------------------------ #


@cl.password_auth_callback
def password_auth_callback(username: str, password: str) -> Optional[cl.User]:

    if USER_JSON_FILES == ['templates/user.json']:
        with open(USER_JSON_FILES[0], "r", encoding="utf-8") as f:
            user_data = json.load(f)
    elif f"{username}.json" in USER_JSON_FILES:
        with open(f"{USER_JSON_PATH}/{username}.json", "r", encoding="utf-8") as f:
            user_data = json.load(f)
    else:
        print(f"[ERROR] User '{username}' does not exist.")
        return None

    if username == user_data["username"] and bcrypt.checkpw(password.encode(), user_data["password_hash"].encode()):
        print(f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - INFO - {username} has logged in.")
        return cl.User(identifier=username, metadata={"role": "user", "provider": "credentials"})

    return None

@cl.on_settings_update
async def on_settings_update(settings):
    # Update the session settings
    cl.user_session.set("settings", settings)
    
    # Send a small, formatted notification to the chat
    await cl.Message(
        content=f"✨ `{settings['ollama_model']}`",
        author="System"
    ).send()

@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("chat_history", [])
    await send_settings_to_chainlit()

@cl.on_message
async def on_message(message: cl.Message):
    # 1. Get settings and history
    settings = cl.user_session.get("settings")
    selected_model = settings["ollama_model"]
    history = cl.user_session.get("chat_history")

    # 2. Add the user's new message to the history
    history.append({"role": "user", "content": message.content})
    
    # 3. Build the full message list for Ollama
    # We include the System Prompt at the very beginning
    messages = [
        {
            "role": "system",
            "content": render_system_prompt(
                Path("templates/system-prompt.txt"),
                Path("public/persona.json"),
                Path(f"public/users/{message.author}.json")
            )
        }
    ] + history

    msg = cl.Message(content="")
    
    # 4. Stream the response using the full history
    stream = await cl.make_async(ollama.chat)(
        model=selected_model,
        messages=messages,
        stream=True,
        options={
            "temperature": settings["temperature"],
            "top_p": settings["top_p"],
            "num_ctx": int(settings["num_ctx"]),
            "num_gpu": 999
        }
    )

    full_response = ""
    for chunk in stream:
        token = chunk['message']['content']
        full_response += token
        await msg.stream_token(token)

    # 5. Add the AI's response to history so it's remembered next time
    history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("chat_history", history)

    await msg.send()

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):

    cl.user_session.set("chat_history", [])
    await send_settings_to_chainlit()

    # Loop through all previous messages in the chat thread to rebuild context
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