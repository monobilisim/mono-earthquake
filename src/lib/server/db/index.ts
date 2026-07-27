import { drizzle } from 'drizzle-orm/libsql';
import { createClient } from '@libsql/client';
import * as schema from './schema';
import * as relations from './relations';

// Bun.env instead of `$env/dynamic/private` so that standalone workers spawned
// outside of SvelteKit (eq-worker, reminder-worker) can import this module too.
if (!Bun.env.DATABASE_URL) throw new Error('DATABASE_URL is not set');

const client = createClient({ url: Bun.env.DATABASE_URL });

export const db = drizzle(client, { schema: { ...schema, ...relations } });
