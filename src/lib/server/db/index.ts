import { drizzle } from 'drizzle-orm/bun-sqlite';
import { Database } from 'bun:sqlite';
import * as schema from './schema';
import * as relations from './relations';

if (!Bun.env.DATABASE_URL) throw new Error('DATABASE_URL is not set');

// drizzle-kit needs a URL ("file:./data/earthquakes.db"), bun:sqlite needs a path.
const sqlite = new Database(Bun.env.DATABASE_URL.replace(/^file:/, ''));

// The server and the workers hit the same file from separate processes.
sqlite.exec('PRAGMA journal_mode = WAL');
sqlite.exec('PRAGMA busy_timeout = 5000');

export const db = drizzle(sqlite, { schema: { ...schema, ...relations } });
