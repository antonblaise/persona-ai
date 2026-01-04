import json
import re
import emoji
import shutil
from datetime import datetime
from pathlib import Path
import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch
from ollama import AsyncClient
from pydub import AudioSegment
from gradio_client import Client


def datetimestamp(no_space=False) -> str:
    return str(datetime.now().strftime("%Y%m%d_%H%M%S_%f")) if no_space else str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def double_each_step(first_number: int, number_of_steps: int) -> list[str]:

    # Return a list of doubling numbers, starting from first_number.
    #       e.g.: 1, 2, 4, 8, 16, 32, 64, ... for number_of_steps
    return [str(first_number * (2 ** i)) for i in range(number_of_steps + 1)]

def flatten_json(d, parent_key="", sep="."):

    # Flatten nested JSON into dot notation keys.
    #       Example: {"a": {"b": 1}} => {"a.b": 1}
    
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

    # Generate the full system prompt using user's JSON file and the template system-prompt.txt.

    #       Load template and JSONs
    template = template_path.read_text(encoding="utf-8")
    persona = json.loads(persona_path.read_text(encoding="utf-8"))
    user = json.loads(user_path.read_text(encoding="utf-8"))

    #       Flatten JSONs
    flat_persona = flatten_json(persona)
    flat_user = flatten_json(user)

    #       Prepare placeholder dictionary
    placeholders = {}
    for key, val in flat_persona.items():
        placeholders[f"persona.{key}"] = str(val)
    for key, val in flat_user.items():
        placeholders[f"user.{key}"] = str(val)

    #       Replace placeholders in template
    system_prompt = template
    for key, val in placeholders.items():
        system_prompt = system_prompt.replace(f"{{{{{key}}}}}", val)

    return system_prompt.replace(r"{{datetime}}", datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S"))

def clean_paragrapher_for_tts(full_response_text: str) -> list:

    # Filter a text filled emojis, new lines, special characters, etc, into one single line of sentences.

    #       Remove emojis
    full_response_text = emoji.replace_emoji(full_response_text, replace="").strip()

    #       Remove code/command snippets - ``` code/command ```
    code_snippets = re.findall(re.compile(r"(\`\`\`[\s\S]*?\n\`\`\`)"), full_response_text)
    for snippet in code_snippets:
        full_response_text = full_response_text.replace(snippet, "")        

    #       Asterisks - *text*
    asterisks = re.findall(re.compile(r"(?:\*.*?\*)"), full_response_text)
    asterisks_content = re.findall(re.compile(r"(?:\*(.*?)\*)"), full_response_text)
    for i in range(len(asterisks)):
        full_response_text = full_response_text.replace(asterisks[i], f"{asterisks_content[i]}")

    #       Exsessive blank spaces - "  " or longer
    excess_blank_spaces = re.findall(re.compile(r" {2,}"), full_response_text)
    for instance in excess_blank_spaces:
        full_response_text = full_response_text.replace(instance, " ")

    #       Excessive new/blank lines - "\n\n" or longer
    excess_new_lines = re.findall(re.compile(r"\n{2,}"), full_response_text)
    for instance in excess_new_lines:
        full_response_text = full_response_text.replace(instance, "\n")

    #       Group the lines in paragraphs of max n lines
    n = 4
    text_lines = [line.strip() for line in full_response_text.splitlines()]

    text_paragraphs = [ " ".join(text_lines[ i : i+n ]) for i in range(0, len(text_lines), n) ]
    
    return text_paragraphs

def join_wav_files(wav_files: list, output_wav_path: str):

    # Combine multiple .wav files into one

    #       If wav_files list is empty
    if not wav_files:
        print("\nINFO - No .wav file given to join.\n")
        return None
    elif len(wav_files) == 1:
        print("\nINFO - Only one .wav file given. No joining is done.\n")
        shutil.move(wav_files[0], output_wav_path)
        print(f"\nINFO - Saved\n\t{wav_files[0]}\nas\n\t{output_wav_path}")
        return None
    else:

        combine_success = False
        max_retries: int = 30
        retry_attempt: int = 0

        while not combine_success and retry_attempt <= max_retries:

            print(f"\nCombining ...\n")

            #       Create an empty .wav
            output_wav = AudioSegment.empty()
            total_wav_length = 0

            #       Combine the given .wav files and calculate their total duration
            for wav_file in wav_files:
                output_wav += AudioSegment.from_wav(wav_file)
                print(f"\t{wav_file}")
                total_wav_length += len(AudioSegment.from_wav(wav_file))
            
            output_wav.export(output_wav_path, format="wav")

            #       Verify that the exported .wav file's duration 
            #       equals to the calculated total from the given .wav files
            if len(AudioSegment.from_wav(output_wav_path)) == total_wav_length:
                combine_success = True
                print(f"\nSuccess! Saved as\n\t{output_wav_path}\n")
            else:
                retry_attempt += 1
                print(f"\nCombination failed.\nRetry attempt: {retry_attempt} of {max_retries}\n")

def text_to_speech(client: Client, input_text: str, voice_sample: dict | None):
    # Generate audio .wav file from given text

    response_audio = client.predict(
        text=input_text,
        reference_id="",
        reference_audio=voice_sample,
        max_new_tokens=0,
        chunk_length=400,
        top_p=0.8,
        repetition_penalty=1.1,
        temperature=0.8,
        seed=0,
        use_memory_cache="on",
        api_name="/partial"
    )

    return response_audio


# ---------------------------------------------------- Async functions ---------------------------------------------------- #


async def send_chainlit_settings(available_models: list, default_model: str, saved_settings: dict | None):

    # Tells Chainlit: “Hey, use these settings right now in the chat.”
    # In other words: Apply the chat settings so they take effect.
    # This enables the settings widget in chat.
    settings = await cl.ChatSettings(
        [
            Select(
                id="ollama_model",
                label="Ollama Model",
                values=available_models,
                initial_value=saved_settings["ollama_model"] if saved_settings is not None else default_model
            ),
            Switch(
                id="stream_response",
                label="Stream Response",
                initial=saved_settings["stream_response"] if saved_settings is not None else True
            ),
            Switch(
                id="disable_thought_process",
                label="Disable Thought Process",
                initial=saved_settings["disable_thought_process"] if saved_settings is not None else False
            ),
            Slider(
                id="temperature",
                label="Temperature",
                min=0.0,
                max=1.5,
                step=0.1,
                initial=saved_settings["temperature"] if saved_settings is not None else 0.7
            ),
            Slider(
                id="top_p",
                label="Top P",
                min=0.1,
                max=1.0,
                step=0.05,
                initial=saved_settings["top_p"] if saved_settings is not None else 0.9
            ),
            Select(
                id="num_ctx",
                label="Context Length (k)",
                values=double_each_step(4, 6),
                initial_value=saved_settings["num_ctx"] if saved_settings is not None else "128",
            )
        ]
    ).send()

    cl.user_session.set("settings", settings)

async def describe_emotions(text: str, llm_model: str) -> str:

    client = AsyncClient()

    llm_input = f"In less than 20 English words, accurately describe the emotions conveyed through this given text:\n\n{text.strip()}"

    response = await client.chat(
        model=llm_model,
        messages=[
            {
                "role": "user",
                "content": llm_input
            }
        ],        
        stream=False,
        think=False,
        options={
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 8 * 1024,
            "num_gpu": 999
        }
    )

    return str(response['message']['content'].strip().lower())
