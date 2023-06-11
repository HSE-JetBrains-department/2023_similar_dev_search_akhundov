FROM python:3.8-slim-buster
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY simdev simdev
ENV PYTHONPATH "/app"
CMD ["python3", "simdev/main.py"]