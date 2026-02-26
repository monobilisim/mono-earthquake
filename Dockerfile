FROM oven/bun:1.3.10-slim

WORKDIR /mono-earthquake

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN bun i && bun --bun run build

RUN mkdir -p data && chmod 777 data

EXPOSE ${PORT}

CMD ["bun", "./build/index.js"]
