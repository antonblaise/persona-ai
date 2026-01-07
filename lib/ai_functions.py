from ollama import AsyncClient
from gradio_client import Client



def fishaudio_tts(client: Client, input_text: str, voice_sample: dict | None):
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


async def describe_emotions(input_text: str):

    async_client = AsyncClient()

    llm_input = [{"role": "user", "content": f"In English ONLY, less than 20 words, use as many English adjectives as possible to explicitly and accurately describe the emotions carried and conveyed in the given text below. Just answer in English, don't prefix, don't explain.\n\n{input_text}"}]

    response = await async_client.chat(
        model="deepseek-v3.1:671b-cloud",
        messages=llm_input,
        stream=False,
        think=False
    )

    return response['message'].get('content', "")