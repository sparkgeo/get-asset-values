FROM python:3.11.0-slim AS builder
LABEL authors="Sparkgeo UK"

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ADD app/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

ADD app/*.py /usr/bin/
RUN chmod +x /usr/bin/*.py

FROM python:3.11.0-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/bin /usr/bin