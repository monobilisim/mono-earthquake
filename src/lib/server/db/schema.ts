import { sqliteTable, index, integer, text, numeric, real } from 'drizzle-orm/sqlite-core';
import { sql } from 'drizzle-orm';

export const webhooks = sqliteTable(
  'webhooks',
  {
    id: integer().primaryKey({ autoIncrement: true }),
    name: text({ length: 255 }).notNull(),
    url: text().notNull(),
    type: text({ length: 255 }).notNull(),
    lastSentAt: numeric('last_sent_at'),
    createdAt: text('created_at').notNull()
  },
  (table) => [index('idx_webhooks_name').on(table.name)]
);

export const sessions = sqliteTable('sessions', {
  id: integer().primaryKey({ autoIncrement: true }),
  userId: integer('user_id')
    .notNull()
    .references(() => usersOld.id, { onDelete: 'cascade' }),
  sessionToken: text('session_token').notNull(),
  expirationDate: numeric('expiration_date')
    .default(sql`(DATETIME('now', '+7 days'))`)
    .notNull()
});

export const groups = sqliteTable('groups', {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text({ length: 255 }).notNull(),
  polls: text({ length: 255 }).default(sql`(NULL)`),
  active: numeric()
    .default(sql`1`)
    .notNull(),
  createdAt: numeric('created_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull(),
  updatedAt: numeric('updated_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull()
});

export const polls = sqliteTable(
  'polls',
  {
    id: integer().primaryKey({ autoIncrement: true }),
    name: text({ length: 255 }).notNull(),
    type: text({ length: 255 }).notNull(),
    threshold: real().default(sql`(NULL)`),
    createdAt: numeric('created_at')
      .default(sql`(CURRENT_TIMESTAMP)`)
      .notNull()
  },
  (table) => [index('idx_polls_name').on(table.name)]
);

export const waMessages = sqliteTable('wa_messages', {
  id: text().primaryKey(),
  userId: integer('user_id').notNull(),
  isRead: numeric('is_read')
    .default(sql`0`)
    .notNull(),
  message: text(),
  pollName: text('poll_name', { length: 255 }).default(sql`(NULL)`),
  earthquakeId: integer('earthquake_id').default(sql`(NULL)`),
  updatedAt: numeric('updated_at').notNull(),
  createdAt: text('created_at').notNull(),
  // Number of follow-up (reminder) messages already sent for this notification.
  // 0 = only the initial message; 1 = 2nd sent; 2 = 3rd sent.
  reminderCount: integer('reminder_count').default(0).notNull(),
  // Set from the WhatsApp callbacks: when the message was read / replied to.
  readAt: integer('read_at', { mode: 'timestamp' }).default(sql`NULL`),
  replyAt: integer('reply_at', { mode: 'timestamp' }).default(sql`NULL`)
});

export const waMessagesFailed = sqliteTable('wa_messages_failed', {
  id: integer().primaryKey({ autoIncrement: true }),
  userId: integer('user_id').notNull(),
  pollName: text('poll_name', { length: 255 }).default(sql`(NULL)`),
  earthquakeId: integer('earthquake_id').default(sql`(NULL)`),
  reason: text(),
  updatedAt: numeric('updated_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull()
});

export const usersOld = sqliteTable('users_old', {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text({ length: 255 }).notNull(),
  phoneNumber: text('phone_number', { length: 20 }).default(sql`(NULL)`),
  groups: text().default(sql`(NULL)`),
  roles: text().default(sql`(NULL)`),
  activationToken: text('activation_token', { length: 255 }).default(sql`(NULL)`),
  active: numeric()
    .default(sql`1`)
    .notNull(),
  createdAt: numeric('created_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull(),
  updatedAt: numeric('updated_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull(),
  userGroup: text('user_group').default(sql`(NULL)`),
  province: text({ length: 255 }).default(sql`(NULL)`)
});

export const waUsers = sqliteTable(
  'wa_users',
  {
    id: integer().primaryKey({ autoIncrement: true }),
    name: text({ length: 255 }).notNull(),
    phoneNumber: text('phone_number', { length: 20 }).notNull(),
    pollName: text('poll_name', { length: 255 }).default(sql`(NULL)`),
    lastSentAt: numeric('last_sent_at'),
    createdAt: text('created_at').notNull()
  },
  (table) => [index('idx_wa_users_phone').on(table.phoneNumber)]
);

export const userGroups = sqliteTable('user_groups', {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text().notNull(),
  tenant: text().notNull(),
  createdAt: numeric('created_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull(),
  updatedAt: numeric('updated_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull()
});

export const earthquakes = sqliteTable('earthquakes', {
  id: integer().primaryKey({ autoIncrement: true }),
  timestamp: text().notNull(),
  date: text().notNull(),
  time: text().notNull(),
  latitude: real().notNull(),
  longitude: real().notNull(),
  depth: real().notNull(),
  md: real(),
  ml: real(),
  mw: real(),
  magnitude: real(),
  location: text().notNull(),
  quality: text().notNull(),
  year: integer().notNull(),
  month: integer().notNull(),
  day: integer().notNull(),
  week: integer().notNull(),
  createdAt: numeric('created_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull()
});

export const users = sqliteTable('users', {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text({ length: 255 }).notNull(),
  phoneNumber: text('phone_number', { length: 20 }).default(sql`(NULL)`),
  groups: text().default(sql`(NULL)`),
  userGroup: text('user_group').default(sql`(NULL)`),
  roles: text().default(sql`(NULL)`),
  activationToken: text('activation_token', { length: 255 }).default(sql`(NULL)`),
  active: numeric()
    .default(sql`1`)
    .notNull(),
  province: text({ length: 255 }).default(sql`(NULL)`),
  createdAt: numeric('created_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull(),
  updatedAt: numeric('updated_at')
    .default(sql`(CURRENT_TIMESTAMP)`)
    .notNull()
});
