import base64
import logging
import os
import sys
import uuid

import aio_pika
import aiofiles
from aio_pika.patterns import RPC
from aiogram import Router, types, Bot, F, filters
from aiogram.types import Message, FSInputFile

router = Router()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

TTS_transcribe = False


@router.message(filters.CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hi {message.from_user.full_name}, im a RecognizerSynthesizerBot.\n"
                         "I can convert your voice message to text.\n"
                         "I'm waiting for your voice messages...")


@router.message(filters.Command("stt"))
async def command_stt_handler(message: Message) -> None:
    global TTS_transcribe
    TTS_transcribe = False
    await message.answer("STT mode is on.")


@router.message(filters.Command("sts"))
async def command_stt_handler(message: Message) -> None:
    global TTS_transcribe
    TTS_transcribe = True
    await message.answer("STS mode is on. Only English language is supported.")


@router.message(F.audio | F.voice)
async def get_audio(message: types.Message, bot: Bot) -> None:
    try:
        logging.info("Download file...")
        file = await bot.get_file(message.voice.file_id)
        filename = uuid.uuid4().hex
        stt_filepath = f'./{filename}'
        await bot.download_file(file.file_path, destination=stt_filepath)

        async with aiofiles.open(stt_filepath, 'rb') as file:
            audio_encoded = base64.b64encode(await file.read()).decode('utf-8')

        connection = await aio_pika.connect_robust(host=os.environ.get('RABBITMQ_HOST', 'localhost'))

        async with connection:
            async with connection.channel() as channel:
                logging.info("STT processing...")
                rpc = await RPC.create(channel)
                stt_result = await rpc.call('process_stt_transcribe',
                                            kwargs={
                                                "filename": filename,
                                                "data": audio_encoded
                                            })
                logging.info(stt_result['text'])

            if TTS_transcribe:
                async with connection.channel() as channel:
                    logging.info("TTS processing...")
                    rpc = await RPC.create(channel)
                    tts_data_result = await rpc.call('process_tts_transcribe',
                                                     kwargs={
                                                         "text": stt_result['text']
                                                     })

                    tts_filepath = f"./{filename}.mp3"
                async with aiofiles.open(tts_filepath, 'wb') as f:
                    await f.write(base64.b64decode(tts_data_result['data']))

                audio = FSInputFile(f"./{filename}.mp3")
                await message.answer_voice(audio)
            else:
                await message.answer(stt_result['text'])
    except TypeError:
        await message.answer("Nice try!")


@router.message(F.text)
async def any_text(message: types.Message) -> None:
    try:
        await message.answer("Sorry, I can only work with the audio file and the voice message.")
    except TypeError:
        await message.answer("Nice try!")
