import os
import uuid

import aiofiles
import aiohttp
import uvicorn
import whisper
from dotenv import load_dotenv
from fastapi import FastAPI, Request

from scemas import Update

load_dotenv()
TG_API = os.getenv("BOT_API_KEY")

app = FastAPI()
model = whisper.load_model("small")


@app.post("/")
async def reed_root(request: Request):
    json = await request.json()
    print(json)


    obj = Update.model_validate(json)
    chat_id = obj.message.chat.id

    if obj.message.text == '/start':
        return await send_message(chat_id,
                                  "Hi, im a RecognizerSynthesizerBot.\n"
                                  "I can convert your voice message to text.\n"
                                  "I'm waiting for your voice messages...")

    if obj.message.voice:
        file_id = obj.message.voice.file_id
    elif obj.message.audio:
        file_id = obj.message.audio.file_id
    else:
        return await send_message(chat_id,
                                  "Sorry, I can only work with the audio file and the voice message.")

    filename = uuid.uuid4().hex

    ext = await get_file_and_write(file_id, filename)
    result = model.transcribe(f"./audio_files/{filename}.{ext}")
    print(result['text'])
    await send_message(chat_id, result['text'])

    return 200


async def send_message(chat_id: int, message: str):
    uri = f'https://api.telegram.org/bot{TG_API}/sendMessage'
    async with aiohttp.ClientSession() as session:
        async with session.post(uri,
                                data={
                                    'chat_id': chat_id,
                                    'text': message
                                }) as response:
            res = await response.json()
            print(res)


async def send_audio(chat_id: int, path: str):
    uri = f'https://api.telegram.org/bot{TG_API}/sendAudio'
    with open(path, 'rb') as f:
        async with aiohttp.ClientSession() as session:
            async with session.post(uri,
                                    data={
                                        'chat_id': chat_id,
                                        'audio': f
                                    }) as response:
                res = await response.json()
                print(res)


async def get_file_and_write(file_id: str, filename: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"https://api.telegram.org/bot{TG_API}/getFile", data={'file_id': file_id}) as response:
            rest_file_info = await response.json()
            if rest_file_info.get("ok"):
                path = rest_file_info['result']['file_path']
                ext = path.split('.')[-1]
                async with session.get(f"https://api.telegram.org/file/bot{TG_API}/{path}") as dwfile:
                    async with aiofiles.open(f'./audio_files/{filename}.{ext}', mode='wb') as f:
                        content = await dwfile.read()
                        await f.write(content)
    return ext


if __name__ == '__main__':
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
