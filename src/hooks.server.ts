import type { ServerInit, Handle } from '@sveltejs/kit';
import { logger } from '$lib/server/logger';
import { sequence } from '@sveltejs/kit/hooks';
const POLL_INTERVAL: number = parseInt(<any>Bun.env.POLL_INTERVAL) || 60;

const log = logger.child({ scope: 'http' });

const handleLog: Handle = async ({ event, resolve }) => {
  const start = performance.now();
  const response = await resolve(event);
  const ms = Math.round(performance.now() - start);
  // Message reads cleanly on the dev terminal; the fields are kept for the JSON files.
  log.info(
    { method: event.request.method, path: event.url.pathname, status: response.status, ms },
    `${event.request.method} ${event.url.pathname} ${response.status} (${ms}ms)`
  );
  return response;
};

export const handle: Handle = sequence(handleLog);

export const init: ServerInit = async () => {
  const EqWorker = () => {
    Bun.spawn({
      cmd: ['bun', '--bun', './src/lib/eq-worker.ts'],
      stdout: 'inherit',
      stderr: 'inherit'
    });
  };

  EqWorker();

  setInterval(EqWorker, POLL_INTERVAL * 1000);
};
