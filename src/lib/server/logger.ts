import pino, { type Logger } from 'pino';

/**
 * Server logger.
 *
 * Built on **pino**:
 *
 *   - **Always** persists **JSON** to rolling files under `./logs`
 *     (`app.<date>.<n>.log`, rotated daily) via `pino-roll`.
 *   - In `NODE_ENV=development`, **additionally** mirrors a clean one-line
 *     `HH:MM:ss LEVEL message` to the terminal (the structured object is hidden
 *     there and only kept in the files).
 *
 * File retention targets **~2 weeks** of history capped near **512 MiB** on disk.
 * pino-roll retains by file count (not a single total-bytes number), so we keep
 * 14 daily files and cap each near 512 MiB / 14 ≈ 36 MiB, bounding the total.
 */

/** Directory holding rotated log files (relative to the process cwd). */
export const LOG_DIR = './logs';

/** Rotated files to retain in addition to the active file (~2 weeks of daily logs). */
const RETAINED_FILES = 14;

/** Total on-disk budget for the log directory. */
const MAX_TOTAL_MIB = 512;

/** Per-file roll threshold so RETAINED_FILES stay within MAX_TOTAL_MIB. */
const PER_FILE_MIB = Math.floor(MAX_TOTAL_MIB / RETAINED_FILES);

/** pino-roll options — exported so retention can be asserted without spawning a transport. */
export const fileRotationOptions = {
  file: `${LOG_DIR}/app`,
  frequency: 'daily',
  size: `${PER_FILE_MIB}m`,
  limit: { count: RETAINED_FILES },
  dateFormat: 'yyyy-MM-dd',
  extension: '.log',
  mkdir: true
} as const;

const isDevelopment = Bun.env.NODE_ENV === 'development';

const level = Bun.env.LOG_LEVEL ?? (Bun.env.NODE_ENV === 'production' ? 'info' : 'debug');

// JSON to the rolling files under ./logs — ALWAYS, every environment.
const fileTarget = { target: 'pino-roll', level, options: fileRotationOptions };

// In development, ALSO mirror a clean one-liner to the terminal: just
// `HH:MM:ss LEVEL message` — the structured object stays out of the terminal
// (`hideObject`) and lives in the JSON files instead.
const terminalTarget = {
  target: 'pino-pretty',
  level,
  options: {
    colorize: true,
    translateTime: 'HH:MM:ss',
    ignore: 'pid,hostname',
    hideObject: true
  }
};

export const logger: Logger = pino({
  level,
  // Never let secrets reach the terminal or disk.
  redact: {
    paths: [
      'password',
      '*.password',
      'clientSecret',
      '*.clientSecret',
      'token',
      '*.token',
      '*.headers.cookie',
      '*.headers.authorization'
    ],
    censor: '[redacted]'
  },
  transport: {
    targets: isDevelopment ? [terminalTarget, fileTarget] : [fileTarget]
  }
});
