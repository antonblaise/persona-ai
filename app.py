print("Importing libraries ...")

# ==================== System & Environment ====================
import os
from pathlib import Path
from dotenv import load_dotenv

# ==================== Core AI & Inference ====================
import ollama
from ollama import AsyncClient
import torch
from TTS.api import TTS

# ==================== Utilities ====================
import json
import bcrypt
import emoji
import re
from langdetect import detect

# ==================== Typing ====================
from typing import Optional

# ==================== Chainlit Framework ====================
import chainlit as cl
from chainlit.types import ThreadDict

# ==================== Chainlit Data Layer (optional/custom) ====================
import chainlit.data.chainlit_data_layer as cl_data

# ==================== Custom functions ====================
from lib.helper_functions import *

# --------------------- Global Setup --------------------- #

print("Doing global setup ...")

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
VOICE_SAMPLE_PATH = os.getenv("VOICE_SAMPLE_PATH", "")
RESPONSE_AUDIO_PATH = os.getenv("RESPONSE_AUDIO_PATH", "storage/audio")

#       Registered users
USER_JSON_FILES = ['templates/user.json']
if os.path.isdir(USER_JSON_PATH):
    if os.listdir(USER_JSON_PATH) != []:
        USER_JSON_FILES = os.listdir(USER_JSON_PATH)

#       Fetch installed Ollama and set a default model
AVAILABLE_MODELS = [model['model'] for model in ollama.list()['models']]

if len(AVAILABLE_MODELS) <= 0:
    print("[ERROR] No Ollama models found. Please install some via 'ollama pull'.")
    exit()

DEFAULT_MODEL = "deepseek-r1:8b"
if DEFAULT_MODEL not in AVAILABLE_MODELS:
    DEFAULT_MODEL = AVAILABLE_MODELS[0]

#       Global XTTS instance (loaded once)
XTTS_MODEL = None

if os.path.isfile(VOICE_SAMPLE_PATH):

    try:
        XTTS_MODEL = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        if torch.cuda.is_available():
            XTTS_MODEL.to(device="cuda")
            print("INFO - TTS model loaded successfully with GPU.")
        else:
            XTTS_MODEL.to(device="cpu")
            print("INFO - TTS model loaded with CPU.")

    except Exception as e:
        print(f"ERROR - TTS model failed to load: {e}. Falling back to text-only.")

else:
    print(f"WARNING - Voice sample '{VOICE_SAMPLE_PATH}' not found. Voice disabled.")

# -------------------------------------------------------- #



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
    print(f"on_settings_update - {cl.user_session.get('settings')}")


@cl.on_chat_start
async def on_chat_start():

    # Set the XTTS model
    cl.user_session.set("XTTS_MODEL", XTTS_MODEL)

    # Initialize an empty chat history
    cl.user_session.set("chat_history", [])

    # Build the system prompt ONCE per chat session
    system_prompt = render_system_prompt(
        Path("templates/system-prompt.txt"),
        Path("public/persona.json"),
        Path(f"public/users/{cl.user_session.get('user').identifier}.json")
    )

    # Store system prompt so it is reused on every turn
    cl.user_session.set("system_prompt", system_prompt)

    # Enable settings UI (model, temp, etc.) with the initial settings
    await send_chainlit_settings(available_models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL, saved_settings=None)
    print(f"on_chat_start - {cl.user_session.get('settings')}")


@cl.on_message
async def on_message(message: cl.Message):

    # Get settings, history, and system prompt
    settings = cl.user_session.get("settings")
    selected_model = settings["ollama_model"]
    history = cl.user_session.get("chat_history", [])
    system_prompt = cl.user_session.get("system_prompt", "")

    # Enable settings UI (model, temp, etc.) and inherit the old 
    await send_chainlit_settings(available_models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL, saved_settings=settings)
    print(f"on_message - {cl.user_session.get('settings')}")

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
                    "num_gpu": 999
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
                    "num_gpu": 999
                }
            )

        # Initialize variables
        response_content = ""
        thinking_content = ""  # Track thinking separately
        msg = cl.Message(content="💭")
        await msg.send()

        thinking_step = None
        first_content = True

        async for chunk in stream:

            # Use default empty strings to avoid 'NoneType' errors
            thinking_token = chunk['message'].get('thinking', "")
            content_token = chunk['message'].get('content', "")

            # Handle thinking tokens
            if thinking_token and not disable_thought_process:
                thinking_content += thinking_token
                
                # Create the thinking Step if not created yet
                if thinking_step is None:
                    thinking_step = cl.Step(name="Thought Process", type="llm")
                    thinking_step.content = ""
                    await thinking_step.send()
                
                await thinking_step.stream_token(thinking_token)

            # Handle actual response content
            if content_token:
                response_content += content_token
                
                #  Stream it as it comes if streaming is enabled
                if settings["stream_response"]:
                    if first_content:
                        msg.content = content_token
                        await msg.update()
                        first_content = False
                    else:
                        await msg.stream_token(content_token)
                # Otherwise, update the main message with FULL response content
                else:
                    msg.content = response_content
        
        # Update thinking step with FULL thinking content
        if thinking_step is not None:
            thinking_step.output = thinking_content
            await thinking_step.update()

        # Add audio button to response
        msg.actions = [
            cl.Action(
                name="tts_button",
                icon="speaker",
                payload={
                    "message_content": msg.content,
                    "message_id": msg.id,
                    "llm_model": selected_model,
                },
            )
        ]
        print(f"\nResponse message ID - {msg.id}\n")

        # Update the message with the final content
        await msg.update()

        # Save to session history
        history.append(
            {
                "role": "assistant",
                "content": f"{thinking_content}\n\n{response_content}" if thinking_content else response_content,
                "actions": msg.actions 
            }
        )
        cl.user_session.set("chat_history", history)

    except Exception as e:
        await cl.Message(
            content=f"⚠️ `{str(e)}`",
            author="System",
            type="system_message"
        ).send()
        print(f"{datetimestamp()} - ERROR - {str(e)}")

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):

    # Enable settings UI (model, temp, etc.) and inherit the old settings
    await send_chainlit_settings(available_models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL, saved_settings=cl.user_session.get('settings'))
    settings = cl.user_session.get('settings')
    selected_model = settings["ollama_model"]

    # Set the XTTS model
    cl.user_session.set("XTTS_MODEL", XTTS_MODEL)

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
            
            if not response_content:
                continue  # Skip empty messages
                
            full_content = f"{thinking_content}\n\n{response_content}" if thinking_content else response_content
            
            history.append(
                {
                    "role": "assistant",
                    "content": full_content,
                }
            )

            # === FIX: Re-add the TTS speaker button to the persisted message ===
            await cl.Message(
                id=step_id,
                content=response_content,  # Use the original output (without thinking prefix)
                actions=[
                    cl.Action(
                        name="tts_button",
                        icon="speaker",
                        payload={
                            "message_content": response_content,
                            "message_id": step_id,
                            "llm_model": selected_model
                        },
                    )
                ]
            ).send()

        else:
            pass

    cl.user_session.set("chat_history", history)

@cl.on_chat_end
async def on_chat_end():

    try:
        await cl.context.emitter.emit("clear", {})
    except Exception as e:
        print(f"{datetimestamp()} - INFO - cl.on_chat_end hit Exception: {e}")
        pass

@cl.action_callback("tts_button")
async def generate_audio_for_step(action: cl.Action):

    # Initialize variables
    full_response = action.payload.get("message_content")
    message_id = action.payload.get("message_id")
    username = cl.user_session.get('user').identifier
    llm_model = action.payload.get("llm_model")

    # Filter response - real text only (remove emojis and wrapped texts, like (text) and *text*)
    response_text = full_response
    descriptions = re.compile(r"(?:\(|（|\*)\S(?:.*?\S)?(?:\)|）|\*)")
    missing_periods = re.compile(r"[a-z]+ {2,}", re.IGNORECASE)
    excess_blank_spaces = re.compile(r" {2,}|\n")

    response_text = emoji.replace_emoji(response_text, replace="").strip()
    for instance in re.findall(descriptions, response_text):
        response_text = response_text.replace(instance, instance.replace("*", ""))
    for instance in re.findall(missing_periods, response_text):
        response_text = response_text.replace(instance, instance.replace("  ", ". "))
    for instance in re.findall(excess_blank_spaces, response_text):
        response_text = response_text.replace(instance, "" if "\n" in instance else " ")

    # Ask the selected LLM model to describe the flow of emotions in the full response using 3 English adjectives.
    emotions = await describe_emotions(text=full_response, llm_model=llm_model)
    print(f"\nEmotions of LLM response: {emotions}\n")

    # Detect the response's language
    supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']
    language_detected = detect(response_text)
    language_used = language_detected if language_detected in supported_languages else "en"
    print(f"\nMost probable language of LLM response: {language_detected}. Language to be used by TTS: {language_used}\n")

    # Create user's folder in storage/audio if not exist yet
    audio_folder_of_user = f"{RESPONSE_AUDIO_PATH}/{username}"
    os.mkdir(audio_folder_of_user) if not os.path.isdir(audio_folder_of_user) else None  

    # Enable TTS voice button with XTTS Voice Cloning
    if XTTS_MODEL and response_text:
        try:
            response_audio = f"{audio_folder_of_user}/{username}_{datetimestamp(no_space=True)}.wav"
            XTTS_MODEL.tts_to_file(
                text=emoji.replace_emoji(response_text.strip(), replace="").strip(),
                speaker_wav=VOICE_SAMPLE_PATH,
                language=language_used,
                file_path=response_audio,
                emotion=emotions
            )
            audio_element = cl.Audio(
                path=response_audio,
                name="", 
                mime="audio/wav",
                display="inline",
            )
            
            message = cl.Message(id=message_id, content=full_response)
            message.elements.append(audio_element)
            await message.update()
        except Exception as e:
            await cl.Message(
                content=f"⚠️ `{str(e)}`",
                author="System",
                type="system_message"
            ).send()
            print(f"{datetimestamp()} - ERROR - TTS generation failed: {e}")
