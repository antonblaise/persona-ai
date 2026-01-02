import json
import re
import emoji
from datetime import datetime
from pathlib import Path
import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch
from ollama import AsyncClient


def datetimestamp(no_space=False) -> str:
    return str(datetime.now().strftime("%Y%m%d_%H%M%S_%f")) if no_space else str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def double_each_step(first_number: int, number_of_steps: int) -> list[str]:

    # Return a list of doubling numbers, starting from first_number.
    # e.g.: 1, 2, 4, 8, 16, 32, 64, ... for number_of_steps
    return [str(first_number * (2 ** i)) for i in range(number_of_steps + 1)]

def flatten_json(d, parent_key="", sep="."):

    # Flatten nested JSON into dot notation keys.
    # Example: {"a": {"b": 1}} => {"a.b": 1}
    
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

    return system_prompt.replace(r"{{datetime}}", datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S"))

def purify_string(input_string: str) -> str:

    # Filter a text filled emojis, new lines, special characters, etc, into one single line of sentences.

    output_string = input_string

    # Remove emojis
    output_string = emoji.replace_emoji(output_string, replace="").strip()

    # Parentheses - English and Chinese - ( )（ ）
    # Asterisks - *
    # ... no white spaces after the first and before the second. e.g.: *text*, (text)
    descriptions = re.findall(re.compile(r"(?:\(|（|\*)\S(?:.*?\S)?(?:\)|）|\*)"), output_string)
    wrapped_text = re.findall(re.compile(r"(?:\(|（|\*)(\S.*?\S)?(?:\)|）|\*)"), output_string)
    for i in range(len(descriptions)):
        output_string = output_string.replace(descriptions[i], f"{wrapped_text[i]}.")

    # Missing periods/full stops
    missing_periods = re.findall(re.compile(r"[a-z]+ {2,}", re.IGNORECASE), output_string)
    for instance in missing_periods:
        output_string = output_string.replace(instance, f"{instance.strip()}. ")

    # Exsessive blank spaces like "\n" and "  "
    excess_blank_spaces = re.findall(re.compile(r" {2,}|\n"), output_string)
    for instance in excess_blank_spaces:
        output_string = output_string.replace(instance, "" if "\n" in instance else " ")

    return output_string.strip()


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
