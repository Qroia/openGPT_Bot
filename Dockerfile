FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    chmod +x ~/.cargo/bin/uv && \
    ln -s ~/.cargo/bin/uv /usr/local/bin/uv && \
    rm -rf /var/lib/apt/lists/*

RUN uv pip install -r requirements.txt --system

COPY . .

CMD ["python", "main.py"]