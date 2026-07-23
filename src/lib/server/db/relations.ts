import { relations } from 'drizzle-orm/relations';
import { usersOld, sessions } from './schema';

export const sessionsRelations = relations(sessions, ({ one }) => ({
  usersOld: one(usersOld, {
    fields: [sessions.userId],
    references: [usersOld.id]
  })
}));

export const usersOldRelations = relations(usersOld, ({ many }) => ({
  sessions: many(sessions)
}));
