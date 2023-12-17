import asyncio
import base64
import logging
import os
import sys

import aio_pika
from aio_pika.patterns import RPC
from pyht import Client
from pyht.client import TTSOptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

options = TTSOptions(voice="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")
client = Client(
    user_id=os.environ.get("PLAY_HT_USER_ID"),
    api_key=os.environ.get("PLAY_HT_API_KEY"),
)


async def process_tts_transcribe(*, text):
    logging.info("TTS transcribe started...")

    audio_bytes = bytearray()
    for chunk in client.tts(text, options):
        audio_bytes += chunk

    return base64.b64encode(audio_bytes).decode('utf-8')


async def main():
    connection = await aio_pika.connect_robust(host=os.environ.get('RABBITMQ_HOST', 'localhost'))
    channel = await connection.channel()
    rpc = await RPC.create(channel)

    await rpc.register('process_tts_transcribe', process_tts_transcribe)

    return connection


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
