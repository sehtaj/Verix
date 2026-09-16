FROM python:3.13.15-slim

RUN pip install --no-cache-dir coverage==7.16.0 pytest==9.1.1 tox==4.60.0 \
    && useradd --create-home --shell /usr/sbin/nologin runner

COPY runner/coverage_runner.py /opt/verix/coverage_runner.py

WORKDIR /workspace
USER runner

ENTRYPOINT ["pytest"]
