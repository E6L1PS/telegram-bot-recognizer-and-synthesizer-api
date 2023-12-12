FROM python:3.11

ADD main.py .

RUN pip install --upgrade openai-whisper pika

CMD ["python", "./main.py"]