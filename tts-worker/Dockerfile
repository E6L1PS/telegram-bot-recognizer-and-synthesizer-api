FROM python:3.11
COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools && pip install -r /app/requirements.txt
COPY ./ /app
WORKDIR /app
CMD ["python", "tts-worker.py"]