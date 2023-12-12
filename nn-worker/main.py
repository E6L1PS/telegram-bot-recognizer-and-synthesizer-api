import whisper
import json
import pika
import base64

model = whisper.load_model("small")

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()


def mq_reply_callback(ch, method, properties, body):
    message = json.loads(body)

    with open(message["filename"], 'wb') as file:
        file.write(base64.b64decode(message["data"]))

    result = model.transcribe(message["filename"])

    reply = {
        "chat_id": message["chat_id"],
        "reply_to_message_id": message["reply_to_message_id"],
        "text": result['text']
    }

    json_message = json.dumps(reply)

    channel.basic_publish(exchange='',
                          routing_key='from_worker',
                          body=json_message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,
                          ))


while True:
    channel.basic_consume(queue='to_worker',
                          auto_ack=True,
                          on_message_callback=mq_reply_callback)
