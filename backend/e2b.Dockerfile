FROM python:3.13.15-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends gzip tar \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir coverage==7.16.0 pytest==9.1.1 tox==4.60.0 \
    && useradd --create-home --shell /usr/sbin/nologin runner \
    && mkdir -p /workspace /tox-work \
    && chown runner:runner /workspace /tox-work

COPY backend/runner/coverage_runner.py /opt/verix/coverage_runner.py
