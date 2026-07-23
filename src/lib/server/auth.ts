import { db } from './db';
import { sessions, users, groups } from './db/schema';
import { eq, desc } from 'drizzle-orm';

export type SessionUser = {
  id: number;
  name: string;
  roles: string[];
  groups: string[];
};

function splitList(value: string | null): string[] {
  return (value ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * Resolve the current user from a session token using Drizzle.
 * Expired sessions are deleted and treated as unauthenticated.
 * This replaces the raw-SQL getUser for the centralized auth in hooks.server.ts.
 */
export async function getUserFromSession(token: string): Promise<SessionUser | null> {
  try {
    const sessionRows = await db
      .select({ userId: sessions.userId, expirationDate: sessions.expirationDate })
      .from(sessions)
      .where(eq(sessions.sessionToken, token))
      .orderBy(desc(sessions.id))
      .limit(1);

    if (sessionRows.length === 0) {
      return null;
    }

    const expirationDate = new Date(String(sessionRows[0].expirationDate));

    if (expirationDate < new Date()) {
      await db.delete(sessions).where(eq(sessions.sessionToken, token));
      return null;
    }

    const userRows = await db
      .select({ id: users.id, name: users.name, roles: users.roles, groups: users.groups })
      .from(users)
      .where(eq(users.id, sessionRows[0].userId))
      .limit(1);

    if (userRows.length === 0) {
      return null;
    }

    const row = userRows[0];

    return {
      id: row.id,
      name: row.name,
      roles: splitList(row.roles),
      groups: splitList(row.groups)
    };
  } catch (error) {
    console.error('Error resolving user from session:', error);
    return null;
  }
}

/** All group (tenant) names, via Drizzle. */
export async function getGroupNames(): Promise<string[]> {
  try {
    const rows = await db.select({ name: groups.name }).from(groups);
    return rows.map((row) => row.name);
  } catch (error) {
    console.error('Error fetching group names:', error);
    return [];
  }
}
