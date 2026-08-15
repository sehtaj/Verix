FROM python:3.13-slim

RUN pip install --no-cache-dir pytest tox \
    && useradd --create-home --shell /usr/sbin/nologin runner

WORKDIR /workspace
USER runner

ENTRYPOINT ["pytest"]
