FROM python:3.11
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY ./ /app
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
CMD ["python", "stt-worker.py"]