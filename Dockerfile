FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

WORKDIR /work

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    apt-get update && apt-get install -y --no-install-recommends \
        coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "--version"]
