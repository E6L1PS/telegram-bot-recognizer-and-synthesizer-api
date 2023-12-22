import asyncio
import base64
import json
import logging
import os
import random
import sys

import aio_pika
import aiofiles
import torch
from aio_pika.patterns import RPC
from pyht import Client
from pyht.client import TTSOptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

with open('voices.json') as f:
    data = json.load(f)
voices_id = [entity['id'] for entity in data if entity['id'].startswith("s3:")]
default_voice = "s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json"

client = Client(
    user_id=os.environ.get("PLAY_HT_USER_ID"),
    api_key=os.environ.get("PLAY_HT_API_KEY"),
)

device = torch.device('cpu')
torch.set_num_threads(4)
local_file = 'model.pt'

if not os.path.isfile(local_file):
    torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v3_1_ru.pt',
                                   local_file)

model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
model.to(device)
sample_rate = 48000
speakers = ['aidar', 'kseniya', 'xenia', 'eugene', 'baya']


async def process_tts_pyht(*, is_shuffle_enabled, text):
    logging.info("TTS pyht started...")
    if is_shuffle_enabled:
        random.shuffle(voices_id)
    options = TTSOptions(voice=voices_id[-1])

    audio_bytes = bytearray()
    for chunk in client.tts(text, options):
        audio_bytes += chunk

    return base64.b64encode(audio_bytes).decode('utf-8')


async def process_tts_silero(*, is_shuffle_enabled, text):
    logging.info("TTS silero started...")
    if is_shuffle_enabled:
        random.shuffle(speakers)

    audio_path = model.save_wav(text=text,
                                speaker=speakers[-1],
                                sample_rate=sample_rate)

    async with aiofiles.open(audio_path, 'rb') as file:
        audio_encoded = base64.b64encode(await file.read()).decode('utf-8')

    return audio_encoded


async def main():
    connection = await aio_pika.connect_robust(host=os.environ.get('RABBITMQ_HOST', 'localhost'))
    channel = await connection.channel()
    rpc = await RPC.create(channel)

    await rpc.register('process_tts_pyht', process_tts_pyht)
    await rpc.register('process_tts_silero', process_tts_silero)

    return connection


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
