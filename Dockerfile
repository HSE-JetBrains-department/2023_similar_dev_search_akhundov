FROM python:3.8-slim-buster
COPY entrypoint.sh entrypoint.sh
WORKDIR /app
COPY requirements.txt requirements.txt
RUN apt update && apt install git -y
RUN pip3 install -r requirements.txt
COPY simdev simdev
ENV PYTHONPATH "/app"
ENTRYPOINT ["/entrypoint.sh"]