FROM python:3.13.15-slim

RUN pip install --no-cache-dir pytest==9.1.1 tox==4.60.0 \
    && useradd --create-home --shell /usr/sbin/nologin runner

WORKDIR /workspace
USER runner

ENTRYPOINT ["pytest"]
