print("Importing libraries ...")

# ==================== System & Environment ====================
import os
from pathlib import Path
from dotenv import load_dotenv

# ==================== Core AI & Inference ====================
import ollama
from ollama import AsyncClient

# ==================== TTS ====================
from gradio_client import Client, handle_file

# ==================== Utilities ====================
import json
import bcrypt
import shutil

# ==================== Typing ====================
from typing import Optional

# ==================== Chainlit Framework ====================
import chainlit as cl
from chainlit.types import ThreadDict

# ==================== Chainlit Data Layer (optional/custom) ====================
import chainlit.data.chainlit_data_layer as cl_data
import boto3
from botocore.exceptions import ClientError

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
DATABASE_URL = os.getenv("DATABASE_URL", "")
SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "templates/system-prompt.txt")
USER_JSON_FOLDER = os.getenv("USER_JSON_FOLDER", "public/users")
VOICE_SAMPLE_PATH = os.getenv("VOICE_SAMPLE_PATH", None)
RESPONSE_AUDIO_FOLDER = os.getenv("RESPONSE_AUDIO_FOLDER", "storage/audio")
BUCKET_NAME = os.getenv("BUCKET_NAME", "my-bucket")

#       Registered users
USER_JSON_FILES = ['templates/user.json']
if os.path.isdir(USER_JSON_FOLDER):
    if os.listdir(USER_JSON_FOLDER) != []:
        USER_JSON_FILES = os.listdir(USER_JSON_FOLDER)

#       Fetch installed Ollama and set a default model
AVAILABLE_MODELS = [model['model'] for model in ollama.list()['models']]

if len(AVAILABLE_MODELS) <= 0:
    print("[ERROR] No Ollama models found. Please install some via 'ollama pull'.")
    exit()

DEFAULT_MODEL = "deepseek-r1:8b-0528-qwen3-q8_0"
if DEFAULT_MODEL not in AVAILABLE_MODELS:
    DEFAULT_MODEL = AVAILABLE_MODELS[0]

#       S3 client setup
DEV_AWS_ENDPOINT = os.getenv("DEV_AWS_ENDPOINT", "http://localhost:4566")
APP_AWS_ACCESS_KEY = os.getenv("APP_AWS_ACCESS_KEY", "random-key")
APP_AWS_SECRET_KEY = os.getenv("APP_AWS_SECRET_KEY", "random-key")
APP_AWS_REGION = os.getenv("APP_AWS_REGION", "eu-central-1")

s3_client = boto3.client(
    's3',
    endpoint_url=DEV_AWS_ENDPOINT,
    aws_access_key_id=APP_AWS_ACCESS_KEY,
    aws_secret_access_key=APP_AWS_SECRET_KEY,
    region_name=APP_AWS_REGION
)

# -------------------------------------------------------- #


@cl.password_auth_callback
def password_auth_callback(username: str, password: str) -> Optional[cl.User]:

    if USER_JSON_FILES == ['templates/user.json']:
        with open(USER_JSON_FILES[0], "r", encoding="utf-8") as f:
            user_data = json.load(f)
    elif f"{username}.json" in USER_JSON_FILES:
        with open(f"{USER_JSON_FOLDER}/{username}.json", "r", encoding="utf-8") as f:
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
    print(f"\non_settings_update\n{json.dumps(cl.user_session.get('settings'), indent=4)}\n")


@cl.on_chat_start
async def on_chat_start():

    # Initialize an empty chat space
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
    print(f"\non_chat_start\n{json.dumps(cl.user_session.get('settings'), indent=4)}\n")

@cl.on_message
async def on_message(message: cl.Message):

    # Get settings, history, and system prompt
    settings = cl.user_session.get("settings")
    selected_model = settings["ollama_model"]
    history = cl.user_session.get("chat_history", [])
    system_prompt = cl.user_session.get("system_prompt", "")

    # Enable settings UI (model, temp, etc.) and inherit the old 
    await send_chainlit_settings(available_models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL, saved_settings=settings)
    print(f"\non_message\n{json.dumps(cl.user_session.get('settings'), indent=4)}\n")

    # Build input: system prompt + full history + current user message
    history.append({"role": "user", "content": message.content})
    llm_input = [{"role": "system", "content": system_prompt}] + history

    # Stream using AsyncClient
    async_client = AsyncClient()
    disable_thought_process = settings.get("disable_thought_process", False)

    try:
        ollama_options = {
            "temperature": settings["temperature"],
            "top_p": settings["top_p"],
            "num_ctx": int(settings["num_ctx"]) * 1024,
            "repeat_penalty": 1.1,      # <--- Sets the penalty strength (1.1 is default)
            "repeat_last_n": -1,        # <--- Look back window tokens, -1 means the entire context window
            "num_gpu": 999
        }
        if disable_thought_process:
            stream = await async_client.chat(
                model=selected_model,
                messages=llm_input,
                stream=True,
                think=False,
                options=ollama_options
            )
        else:
            stream = await async_client.chat(
                model=selected_model,
                messages=llm_input,
                stream=True,
                options=ollama_options
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
                    if "</think>" in response_content:
                        print(f"\n{datetimestamp()} - INFO - '</think>' tag found in the response.\n")
                        response_content = response_content.split("</think>")[1]
                    msg.content = response_content
        
        # Update thinking step with FULL thinking content
        if thinking_step is not None:
            thinking_step.output = thinking_content
            await thinking_step.update()

        # Add audio button to response
        msg.actions = [
            cl.Action(
                name="tts_button",
                icon="volume-2",
                payload={
                    "message_content": msg.content,
                    "message_id": msg.id,
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

    print(f"\non_chat_resume\n- Thread ID: {thread['id']}\n{json.dumps(cl.user_session.get('settings'), indent=4)}\n")

    # Enable settings UI (model, temp, etc.) and inherit the old settings
    await send_chainlit_settings(available_models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL, saved_settings=cl.user_session.get('settings'))

    # Reconstruct action buttons
    for step in thread['steps'] or []:

        step_actions = []
        # Audio (TTS) button
        step_actions.append(
            cl.Action(
                name="tts_button",
                icon="volume-2",
                payload={
                    "message_content": step['output'],
                    "message_id": step['id'],
                },
            )
        )

        # Edit directly on the assistant message
        if step['type'] == "assistant_message":
            await cl.Message(
                id=step['id'],
                author=step['name'],
                content=step['output'],
                actions=step_actions
            ).update()
  

@cl.on_chat_end
async def on_chat_end():

    try:
        username = cl.user_session.get("user").identifier

        # Delete generated media files of the user
        user_audio_files_path = f"{RESPONSE_AUDIO_FOLDER}/{username}"
        if os.path.isdir(user_audio_files_path):
            shutil.rmtree(user_audio_files_path)

        await cl.context.emitter.emit("clear", {})
    except Exception as e:
        print(f"{datetimestamp()} - INFO - cl.on_chat_end hit Exception: {e}")
        pass

@cl.action_callback("tts_button")
async def generate_audio_for_step(action: cl.Action):

    # Get voice sample
    if os.path.isfile(VOICE_SAMPLE_PATH):
        print(f"\n\n{'-'*50}\n\nFish Audio will use '{VOICE_SAMPLE_PATH}' as the sample audio.\n\n")
        voice_sample = handle_file(fr"{VOICE_SAMPLE_PATH}")
    else:
        warning_message = f"\n\n{'-'*50}\n\nNo voice sample given. Fish Audio will use a random voice.\n\n"
        print(warning_message)
        await cl.Message(
            content=f"⚠️ `{warning_message}`",
            author="System",
            type="system_message"
        ).send()
        voice_sample = None

    # Initialize variables
    full_response = action.payload.get("message_content")
    message_id = action.payload.get("message_id")
    username = cl.user_session.get('user').identifier

    # Filter response - real text only (remove emojis and wrapped texts, like (text) and *text*)
    response_paragraphs = clean_paragrapher_for_tts(full_response_text=full_response)

    # If there's no words, just skip audio generation
    if response_paragraphs == []:
        await cl.Message(
            content=f"⚠️ `The response has no words.`",
            author="System",
            type="system_message"
        ).send()
        print(f"{datetimestamp()} - The response has no words.")

        return None

    # Create user's folder in storage/audio if not exist yet
    audio_folder_of_user = f"{RESPONSE_AUDIO_FOLDER}/{username}"
    os.mkdir(audio_folder_of_user) if not os.path.isdir(audio_folder_of_user) else None

    audio_filename = f"{username}_{message_id}.wav"
    audio_output_file = f"{audio_folder_of_user}/{audio_filename}"

    # ------- Enable TTS voice button with Voice Cloning - fishaudio/fish-speech -------
    if not os.path.isfile(audio_output_file):
        tts_client = Client("http://localhost:8081")
        response_paragraphs_audio: list = []

        for i, paragraph in enumerate(response_paragraphs):

            print(f"\nParagraph {i+1}/{len(response_paragraphs)}:\n{paragraph}\n")

            try:
                # Generate audio .wav file
                response_audio = text_to_speech(client=tts_client, input_text=paragraph, voice_sample=voice_sample)
            except Exception as e:
                await cl.Message(
                    content=f"⚠️ `{str(e)}`",
                    author="System",
                    type="system_message"
                ).send()
                print(f"{datetimestamp()} - ERROR - TTS generation failed: {e}")
                return None

            # Collect all the .wav files into a list of their paths
            response_paragraphs_audio.append(response_audio[0])

        # Combine into one final .wav file, save as audio_output_file and ... upload to S3
        join_wav_files(response_paragraphs_audio, audio_output_file)

    # ... upload to S3
    s3_client.upload_file(audio_output_file, BUCKET_NAME, audio_filename)

    url_of_the_wav_file = f"{DEV_AWS_ENDPOINT}/{BUCKET_NAME}/{audio_filename}"

    print(f"\nAudio file '{audio_filename}' uploaded to S3 at:\n\t{url_of_the_wav_file}\n")

    # Create Chainlit audio element
    audio_element = cl.Audio(
        url=url_of_the_wav_file,
        mime="audio/wav",
        display="inline",
    )

    # Point to the message and append the audio element into it.
    message = cl.Message(
        id=message_id,
        content=full_response,
        elements=[audio_element],
        metadata={
            "audio_url": url_of_the_wav_file
        }
    )

    await message.update()

    

