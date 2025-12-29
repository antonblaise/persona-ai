# ==================== System & Environment ====================
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ==================== Core AI & Inference ====================
import ollama
from ollama import AsyncClient

# ==================== Utilities ====================
import json
import bcrypt

# ==================== Typing ====================
from typing import Optional

# ==================== Chainlit Framework ====================
import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.input_widget import Select, Slider, TextInput, Switch

# ==================== Chainlit Data Layer (optional/custom) ====================
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

#       Load the variables from .env. Fallback to the 2nd parameter if failed.
load_dotenv()
SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "templates/system-prompt.txt")
USER_JSON_PATH = os.getenv("USER_JSON_PATH", "public/users")

#       Registered users
USER_JSON_FILES = ['templates/user.json']
if os.path.isdir(USER_JSON_PATH):
    if os.listdir(USER_JSON_PATH) != []:
        USER_JSON_FILES = os.listdir(USER_JSON_PATH)

#       Fetch installed Ollama and set a default model
available_models = [model['model'] for model in ollama.list()['models']]

if len(available_models) <= 0:
    print("[ERROR] No Ollama models found. Please install some via 'ollama pull'.")
    exit()

DEFAULT_MODEL = "deepseek-r1:8b"
if DEFAULT_MODEL not in available_models:
    DEFAULT_MODEL = available_models[0]

# -------------------------------------------------------- #

# --------------------- Helper functions --------------------- #

def datetimestamp():
    return str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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
            Switch(
                id="disable_thought_process",
                label="Disable Thought Process",
                initial=False
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
                label="Context Length (k)",
                initial="32"
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
        print(f"{datetimestamp()} - INFO - {username} has logged in.")
        return cl.User(identifier=username, metadata={"role": "user", "provider": "credentials"})

    return None

@cl.on_settings_update
async def on_settings_update(settings):

    # Update the session settings
    cl.user_session.set("settings", settings)
    
    # Indicate the switched model name the chat
    await cl.Message(
        content=f"✨ `{settings['ollama_model']}`",
        author="System"
    ).send()

@cl.on_chat_start
async def on_chat_start():

    # 1. Initialize an empty chat history
    cl.user_session.set("chat_history", [])

    # 2. Build the system prompt ONCE per chat session
    system_prompt = render_system_prompt(
        Path("templates/system-prompt.txt"),
        Path("public/persona.json"),
        Path(f"public/users/{cl.user_session.get("user").identifier}.json")
    )

    # Store system prompt so it is reused on every turn
    cl.user_session.set("system_prompt", system_prompt)

    # Send UI settings (model, temp, etc.)
    await send_settings_to_chainlit()

@cl.on_message
async def on_message(message: cl.Message):

    # Get settings, history, and system prompt
    settings = cl.user_session.get("settings")
    selected_model = settings["ollama_model"]
    history = cl.user_session.get("chat_history", [])
    system_prompt = cl.user_session.get("system_prompt", "")

    # Build input: system prompt + full history + current user message
    history.append({"role": "user", "content": message.content})
    llm_input = [{"role": "system", "content": system_prompt}] + history

    # Stream using AsyncClient
    client = AsyncClient()
    disable_thought_process = settings.get("disable_thought_process", False)

    try:
        if disable_thought_process:
            stream = await client.chat(
                model=selected_model,
                messages=llm_input,
                stream=True,
                think=False,
                options={
                    "temperature": settings["temperature"],
                    "top_p": settings["top_p"],
                    "num_ctx": int(settings["num_ctx"]) * 1024,
                    "num_gpu": -1
                }
            )
        else:
            stream = await client.chat(
                model=selected_model,
                messages=llm_input,
                stream=True,
                options={
                    "temperature": settings["temperature"],
                    "top_p": settings["top_p"],
                    "num_ctx": int(settings["num_ctx"]) * 1024,
                    "num_gpu": -1
                }
            )

        # Initialize variables
        response_content = ""
        thinking_content = ""  # Track thinking separately
        msg = cl.Message(content="💭")
        await msg.send()

        thinking_step = None

        async for chunk in stream:

            # Use default empty strings to avoid 'NoneType' errors
            thinking_token = chunk['message'].get('thinking', "")
            content_token = chunk['message'].get('content', "")

            # Handle thinking tokens
            if thinking_token and not disable_thought_process:
                thinking_content += thinking_token
                
                # Create the thinking Step if not created yet
                if thinking_step is None:
                    thinking_step = cl.Step(name="Thought Process")
                    thinking_step.content = ""
                    await thinking_step.send()
                
                await thinking_step.stream_token(thinking_token)

            # Handle actual response content
            if content_token:
                response_content += content_token

        # ======================== Finalize all content ======================== #
        
        # 1. Update the main message with FULL response content
        msg.content = response_content
        await msg.update()
        
        # 2. Update thinking step with FULL thinking content
        if thinking_step is not None:
            thinking_step.output = thinking_content
            await thinking_step.update()

        # 3. Save to session history
        history.append(
            {
                "role": "assistant",
                "content": f"{thinking_content}\n\n{response_content}" if thinking_content else response_content
            }
        )
        cl.user_session.set("chat_history", history)

    except Exception as e:
        await cl.Message(
            content=f"⚠️ `{str(e)}`",
            author="System"
        ).send()
        print(f"{datetimestamp()} - ERROR - {str(e)}")

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):

    # Send UI settings (model, temp, etc.)
    await send_settings_to_chainlit()

    # Indicate the switched model name the chat
    await cl.Message(
        content=f"✨ `{cl.user_session.get('settings')['ollama_model']}`",
        author="System"
    ).send()

    # Reset chat history
    cl.user_session.set("chat_history", [])

    # Rebuild history from previous thread steps
    history = []
    steps = thread.get("steps", [])
    
    # First, map thinking steps to their parent messages
    thinking_by_parent = {}
    
    for step in steps:
        if step.get("type") == "step" and step.get("name") == "Thought Process":
            parent_id = step.get("parentId")
            if parent_id:
                thinking_by_parent[parent_id] = step.get("output", step.get("content", ""))
    
    # Now reconstruct the conversation
    for step in steps:
        step_type = step.get("type")
        
        if step_type == "user_message":
            history.append({"role": "user", "content": step.get("output", "")})
            
        elif step_type == "assistant_message":
            step_id = step.get("id")
            thinking_content = thinking_by_parent.get(step_id, "")
            response_content = step.get("output", "")
            
            if thinking_content and response_content:
                full_content = f"{thinking_content}\n\n{response_content}"
            elif response_content:
                full_content = response_content
            else:
                continue  # Skip empty messages
                
            history.append({"role": "assistant", "content": full_content})

    cl.user_session.set("chat_history", history)

@cl.on_chat_end
async def on_chat_end():

    try:
        await cl.context.emitter.emit("clear", {})
    except Exception as e:
        print(f"{datetimestamp()} - INFO - cl.on_chat_end hit Exception: {e}")
        pass