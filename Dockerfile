FROM python:3.11.3-slim-buster

ADD requirements.txt .
ADD main.py .
RUN apt-get update && apt-get install -y --no-install-recommends python3-dev gcc build-essential && pip3 install -r requirements.txt 

ENV CHANNEL_ACCESS_TOKEN ""
ENV CHANNEL_SECRET ""
ENV CHANNEL_USERID ""
ENV STARTURL ""
ENV CALLBACK_DOMAIN ""

ENTRYPOINT ["/usr/local/bin/python3", "main.py"]