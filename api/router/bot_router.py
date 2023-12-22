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

tts_mode_enabled = False
should_translate = True
is_shuffle_enabled = True


@router.message(filters.CommandStart())
async def command_start_handler(message: Message) -> None:
    kb = [
        [
            types.KeyboardButton(text="Speech synthesis mode"),
            types.KeyboardButton(text="Auto translate"),
            types.KeyboardButton(text="Random voice"),
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Choice mode"
    )

    await message.answer(f"Hi {message.from_user.full_name}, im a RecognizerSynthesizerBot.\n"
                         "I can convert your voice message to text and synthesize your voice.\n"
                         "I'm waiting for your voice messages...", reply_markup=keyboard)


@router.message(filters.Command("sts"))
@router.message(F.text == "Speech synthesis mode")
async def command_synthesis_handler(message: Message) -> None:
    global tts_mode_enabled
    tts_mode_enabled = not tts_mode_enabled
    await message.answer("Speech synthesis mode is enabled."
                         if tts_mode_enabled else "Speech synthesis is disabled. Only text convert.")


@router.message(filters.Command("en"))
@router.message(F.text == "Auto translate")
async def command_translate_handler(message: Message) -> None:
    global should_translate
    should_translate = not should_translate
    await message.answer("Auto translate to en is enabled."
                         if should_translate else "Auto translate to en is disabled.")


@router.message(filters.Command("rand"))
@router.message(F.text == "Random voice")
async def command_rand_handler(message: Message) -> None:
    global is_shuffle_enabled
    is_shuffle_enabled = not is_shuffle_enabled
    await message.answer("Random voice is enabled."
                         if is_shuffle_enabled else "Random voice is disabled.")


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
                                                "should_translate": should_translate,
                                                "filename": filename,
                                                "data": audio_encoded
                                            })
                logging.info(stt_result)

            if tts_mode_enabled:
                async with connection.channel() as channel:
                    logging.info("TTS processing...")
                    rpc = await RPC.create(channel)
                    tts_data_result = await rpc.call(
                        'process_tts_pyht' if should_translate else 'process_tts_silero',
                        kwargs={
                            "is_shuffle_enabled": is_shuffle_enabled,
                            "text": stt_result
                        })

                tts_filepath = f"./{filename}.mp3"
                async with aiofiles.open(tts_filepath, 'wb') as f:
                    await f.write(base64.b64decode(tts_data_result))

                audio = FSInputFile(tts_filepath)
                await message.answer_voice(audio)
            else:
                await message.answer(stt_result)
    except TypeError:
        await message.answer("Nice try!")


@router.message(F.text)
async def any_text(message: types.Message) -> None:
    try:
        await message.answer("Sorry, I can only work with the audio file and the voice message.")
    except TypeError:
        await message.answer("Nice try!")
