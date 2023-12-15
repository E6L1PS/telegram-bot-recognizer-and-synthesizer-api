FROM python:3.11
COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt
COPY ./ /app
WORKDIR /app
EXPOSE 8000
CMD ["python", "main.py"]