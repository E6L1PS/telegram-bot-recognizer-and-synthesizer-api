import asyncio
import base64
import logging
import os
import sys

import aio_pika
import aiofiles
import whisper
from aio_pika.patterns import RPC

model = whisper.load_model("small")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


async def process_transcribe(*, filename, data):
    logging.info("Transcribe started...")

    async with aiofiles.open(filename, 'wb') as f:
        await f.write(base64.b64decode(data))
        result = await loop.run_in_executor(None, model.transcribe, filename)

    logging.info(f"Result text: {result['text']}")

    return {
        "text": result['text']
    }


async def main():
    connection = await aio_pika.connect_robust(host=os.environ.get('RABBITMQ_HOST', 'localhost'))
    channel = await connection.channel()
    rpc = await RPC.create(channel)

    await rpc.register('process_transcribe', process_transcribe)

    return connection


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
