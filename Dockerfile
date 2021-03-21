FROM python:3.9.1-slim-buster

RUN apt update && \
    apt install -y \
    gcc \
    g++

COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

WORKDIR /app

COPY server.py /app/api.py

CMD python -m api
