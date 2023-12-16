import json
import os
import uuid
import wave
import pika
import base64
import aiofiles
import aiohttp
import uvicorn
# from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pyht import Client
from pyht.client import TTSOptions

from scemas import Update

# load_dotenv()
TG_API = os.getenv("BOT_API_KEY")

app = FastAPI()
options = TTSOptions(voice="s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")

host = os.getenv("RABBIT_MQ_HOST", "localhost")
connection = pika.BlockingConnection(pika.ConnectionParameters(host))
channel = connection.channel()
channel.queue_declare(queue='to_worker')
channel.queue_declare(queue='from_worker')


def mq_reply_callback(ch, method, properties, body):
    message = json.loads(body)

    reply_message(int(message['chat_id']), int(message['reply_to_message_id']), message.text)


# test button
@app.get("/hey")
async def test(request: Request):
    print("hey")
    return {"hey": "HEY!"}


@app.post("/")
async def reed_root(request: Request):
    print("Request in /")
    json = await request.json()
    print(json)

    obj = Update.model_validate(json)
    chat_id = obj.message.chat.id
    reply_to_message_id = obj.message.message_id

    # test button
    await set_chat_menu_button(chat_id)

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

    with open(f'./audio_files/{filename}.{ext}', 'rb') as file:
        audio_encoded = base64.b64encode(file.read())

    message = {
        "chat_id": chat_id,
        "reply_to_message_id": reply_to_message_id,
        "filename": f'{filename}.{ext}',
        "data": str(audio_encoded)
    }

    json_message = json.dumps(message)

    channel.basic_publish(exchange='',
                          routing_key='to_worker',
                          body=json_message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,
                          ))

    # path_to_synth_file = text_to_speach(result['text'])
    # await send_audio(chat_id, path_to_synth_file)
    await send_message(chat_id, "Processing...")

    # Эту часть нужно будет перенести куда-то в другое место (вместе с колбеком)

    channel.basic_consume(queue='from_worker',
                          auto_ack=True,
                          on_message_callback=mq_reply_callback)

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


async def reply_message(chat_id: int, reply_to_message_id: int, message: str):
    uri = f'https://api.telegram.org/bot{TG_API}/sendMessage'
    async with aiohttp.ClientSession() as session:
        async with session.post(uri,
                                data={
                                    'chat_id': chat_id,
                                    'text': message,
                                    'reply_to_message_id': reply_to_message_id
                                }) as response:
            res = await response.json()
            print(res)


async def send_audio(chat_id: int, path: str):
    uri = f'https://api.telegram.org/bot{TG_API}/sendAudio'
    async with aiohttp.ClientSession() as session:
        async with aiofiles.open(path, 'rb') as f:
            audio_file = await f.read()

        form_data = aiohttp.FormData()
        form_data.add_field('chat_id', str(chat_id))
        form_data.add_field('audio', audio_file, filename='audio_file.mp3', content_type='audio/mpeg')

        async with session.post(uri, data=form_data) as response:
            res = await response.json()
            print(res)


async def reply_audio(chat_id: int, reply_to_message_id: int, path: str):
    uri = f'https://api.telegram.org/bot{TG_API}/sendAudio'
    async with aiohttp.ClientSession() as session:
        async with aiofiles.open(path, 'rb') as f:
            audio_file = await f.read()

        form_data = aiohttp.FormData()
        form_data.add_field('chat_id', str(chat_id))
        form_data.add_field('reply_to_message_id', str(reply_to_message_id))
        form_data.add_field('audio', audio_file, filename='audio_file.mp3', content_type='audio/mpeg')

        async with session.post(uri, data=form_data) as response:
            res = await response.json()
            print(res)


def text_to_speach(text: str):
    client = Client(
        user_id=os.getenv("PLAY_HT_USER_ID"),
        api_key=os.getenv("PLAY_HT_API_KEY"),
    )
    generated_file_name = uuid.uuid4().hex
    path = f"./synth_files/{generated_file_name}"
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)  # 1 channel for mono, 2 channels for stereo
        wf.setsampwidth(2)  # 2 bytes per sample
        wf.setframerate(22050)  # Adjust the frame rate according to your needs

        for chunk in client.tts(text, options):
            wf.writeframes(chunk)
        client.close()
        return path


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


async def set_chat_menu_button(chat_id):
    uri = f'https://api.telegram.org/bot{TG_API}/setChatMenuButton'
    menu_button_data = {
        "type": "web_app",
        "text": "button",
        "web_app": {
            "url": "https://6caf-194-54-176-118.ngrok.io/hey"
        }
    }
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field('chat_id', str(chat_id))
        form_data.add_field('menu_button', json.dumps(menu_button_data))

        async with session.post(uri, data=form_data) as response:
            res = await response.json()
            print(res)


if __name__ == '__main__':
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
    connection.close()
