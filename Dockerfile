FROM python:3.13-slim

WORKDIR /mono-earthquake

RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://bun.sh/install | bash

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /mono-earthquake/ui
RUN ~/.bun/bin/bun i && ~/.bun/bin/bun run build

WORKDIR /mono-earthquake

RUN mkdir -p data && chmod 777 data

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
