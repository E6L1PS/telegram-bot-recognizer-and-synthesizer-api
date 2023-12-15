import base64
import logging
import os
import sys
import uuid

import aio_pika
import aiofiles
from aio_pika.patterns import RPC
from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold

router = Router()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hi {hbold(message.from_user.full_name)}, im a RecognizerSynthesizerBot.\n"
                         "I can convert your voice message to text.\n"
                         "I'm waiting for your voice messages...")


@router.message(F.audio | F.voice)
async def get_audio(message: types.Message, bot: Bot) -> None:
    try:
        logging.info("Download file...")
        file = await bot.get_file(message.voice.file_id)
        filename = uuid.uuid4().hex
        filename_path = f'./audio_files/{filename}'
        await bot.download_file(file.file_path, destination=filename_path)

        async with aiofiles.open(filename_path, 'rb') as file:
            audio_encoded = base64.b64encode(await file.read()).decode('utf-8')

        connection = await aio_pika.connect_robust(host=os.environ.get('RABBITMQ_HOST', 'localhost'))

        async with connection:
            async with connection.channel() as channel:
                logging.info("Processing...")
                rpc = await RPC.create(channel)
                dict_data = await rpc.call('process_transcribe',
                                           kwargs={
                                               "filename": filename,
                                               "data": str(audio_encoded)
                                           })
                print(dict_data["text"])

        await message.answer(dict_data["text"])
    except TypeError:
        await message.answer("Nice try!")


@router.message(F.text)
async def any_text(message: types.Message) -> None:
    try:
        await message.answer("Sorry, I can only work with the audio file and the voice message.")
    except TypeError:
        await message.answer("Nice try!")
