FROM python:3.10.6

RUN apt update && \
    apt install -y git gcc golang-go libffi-dev make && \
    git clone https://github.com/go-enry/go-enry

SHELL ["/bin/bash", "-c"]

RUN cd go-enry/python && \
    pushd .. && make static && popd && \
    pip install -r requirements.txt && \
    python build_enry.py && \
    python setup.py bdist_wheel && \
    pip install ./dist/*.whl

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY simdev simdev

ENV PYTHONPATH "/app"

ENTRYPOINT ["python3", "-m", "simdev"]