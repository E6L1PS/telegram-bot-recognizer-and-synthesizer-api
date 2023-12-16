FROM python:3.11

RUN pip install --upgrade openai-whisper pika

ADD main.py .

CMD ["python", "./main.py"]