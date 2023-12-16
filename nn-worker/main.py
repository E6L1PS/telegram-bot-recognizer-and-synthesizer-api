import whisper
import json
import pika
import base64
import os

print("Loading ML model")
model = whisper.load_model("small")
print("Model loaded")
host = os.getenv("RABBIT_MQ_HOST", "localhost")
print("Trying to access rabbit at ", host)
connection = pika.BlockingConnection(pika.ConnectionParameters(host))
channel = connection.channel()
channel.queue_declare(queue='to_worker')
channel.queue_declare(queue='from_worker')

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


print("Worker started.")

while True:
    channel.basic_consume(queue='to_worker',
                          auto_ack=True,
                          on_message_callback=mq_reply_callback)
