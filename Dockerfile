FROM oven/bun:1.4.4-slim AS builder

WORKDIR /mono-earthquake

COPY . .

ENV DATABASE_URL=/tmp/build.db

RUN bun i && bun --bun run build

RUN bun build src/lib/eq-worker.ts src/lib/reminder-worker.ts --target bun --outdir workers --entry-naming '[name].ts'

FROM oven/bun:1.4.4-slim AS runner

WORKDIR /mono-earthquake

COPY package.json bun.lock ./
RUN bun i --production --frozen-lockfile --ignore-scripts

COPY --from=builder /mono-earthquake/build ./build
COPY --from=builder /mono-earthquake/workers ./src/lib

RUN mkdir -p data && chmod 777 data

EXPOSE ${PORT}

CMD ["bun", "./build/index.js"]
