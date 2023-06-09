FROM mcr.microsoft.com/devcontainers/python:0-3.11

WORKDIR /app
ADD requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends python3-dev gcc build-essential ffmpeg && pip3 install -r requirements.txt 
RUN playwright install-deps && playwright install

WORKDIR /app/apps/static/
ADD ./apps/static/* .

WORKDIR /app/apps/movie/
WORKDIR /app/apps/audio/

WORKDIR /app/apps/
ADD ./apps/*.py .

WORKDIR /app
ADD main.py .
ENTRYPOINT ["/usr/local/bin/python3", "main.py"]