FROM python:3.8-slim-buster

WORKDIR /app

RUN apt update && apt install git -y

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

SHELL ["/bin/bash", "-c"]

COPY simdev simdev

ENV PYTHONPATH "/app"

CMD ["bash"]