/**
 * Reminder worker.
 *
 * Re-sends a 'duyuru' (announcement) message to users who have neither read nor
 * replied to it. Two follow-ups are sent: the first REMINDER_MINUTES[0] minutes
 * after the original message, the second REMINDER_MINUTES[1] minutes after that
 * one (5 and 10 minutes by default). Earthquake ('deprem') notifications are not
 * touched.
 *
 * The original message row is the anchor of the chain and carries reminder_count.
 * Follow-up rows are inserted with reminder_count = MAX_REMINDERS so they are
 * never treated as anchors themselves; they exist so the WhatsApp callbacks can
 * record reads/replies for them (see src/routes/wa-callback/+server.ts). Reading
 * or replying to any message of a chain stops the whole chain.
 */
import { and, eq, isNull, lt, notExists, sql } from 'drizzle-orm';
import { alias } from 'drizzle-orm/sqlite-core';
import { db } from '$lib/server/db';
import { users, waMessages, waMessagesFailed } from '$lib/server/db/schema';

if (Bun.env.BUILD_STEP) {
  process.exit(0);
}

const PHONE_NUMBER_ID = Bun.env.PHONE_NUMBER_ID;
const WHATSAPP_TOKEN = Bun.env.WHATSAPP_TOKEN;
const TEST = Bun.env.TEST === 'true';

const POLL_NAME = 'duyuru';

// Minutes to wait before each follow-up, relative to the previous message.
const REMINDER_MINUTES = (Bun.env.REMINDER_MINUTES || '5,10')
  .split(',')
  .map((value) => Number(value.trim()))
  .filter((value) => Number.isFinite(value) && value > 0);

const MAX_REMINDERS = REMINDER_MINUTES.length;

// Delays measured from the original message: [5, 15] for the default 5,10.
const REMINDER_OFFSETS = REMINDER_MINUTES.reduce<number[]>((acc, minutes, i) => {
  acc.push((acc[i - 1] ?? 0) + minutes);
  return acc;
}, []);

// How long a chain can live: the last follow-up plus some slack.
const CHAIN_WINDOW_SECONDS =
  Number(Bun.env.REMINDER_CHAIN_WINDOW_MINUTES || (REMINDER_OFFSETS.at(-1) ?? 0) + 30) * 60;

// Never chase announcements older than this - after a restart or an outage we do
// not want to flood users with stale reminders.
const MAX_AGE_MINUTES = Number(Bun.env.REMINDER_MAX_AGE_MINUTES || 180);

// "2025-10-06 12:50:45" is stored in UTC.
function ageInMinutes(createdAt: string): number {
  const created = new Date(createdAt.replace(' ', 'T') + 'Z');
  return (Date.now() - created.getTime()) / 1000 / 60;
}

try {
  if (MAX_REMINDERS === 0) {
    console.log('No reminder intervals configured, nothing to do.');
    process.exit(0);
  }

  if (!TEST && (typeof PHONE_NUMBER_ID !== 'string' || typeof WHATSAPP_TOKEN !== 'string')) {
    console.error('WhatsApp configuration is missing, skipping reminders.');
    process.exit(0);
  }

  // A message of the same chain that was read or replied to stops the chain.
  // Announcements have no earthquake_id, so a chain is: same user, same body,
  // sent within the reminder window. A reply overwrites `message` with the button
  // text, which is why a replied row inside the window counts as well.
  const sibling = alias(waMessages, 'sibling');
  const chainAnswered = notExists(
    db
      .select({ one: sql`1` })
      .from(sibling)
      .where(
        and(
          eq(sibling.userId, waMessages.userId),
          eq(sibling.pollName, POLL_NAME),
          // IS is NULL-safe equality in SQLite
          sql`(${sibling.message} IS ${waMessages.message} OR ${sibling.replyAt} IS NOT NULL)`,
          sql`unixepoch(${sibling.createdAt}) >= unixepoch(${waMessages.createdAt})`,
          sql`unixepoch(${sibling.createdAt}) <= unixepoch(${waMessages.createdAt}) + ${CHAIN_WINDOW_SECONDS}`,
          sql`(${sibling.readAt} IS NOT NULL OR ${sibling.replyAt} IS NOT NULL OR ${sibling.isRead} = 1)`
        )
      )
  );

  const anchors = await db
    .select({
      id: waMessages.id,
      userId: waMessages.userId,
      message: waMessages.message,
      createdAt: waMessages.createdAt,
      reminderCount: waMessages.reminderCount
    })
    .from(waMessages)
    .where(
      and(
        eq(waMessages.pollName, POLL_NAME),
        lt(waMessages.reminderCount, MAX_REMINDERS),
        isNull(waMessages.readAt),
        isNull(waMessages.replyAt),
        sql`${waMessages.isRead} = 0`,
        sql`unixepoch(${waMessages.createdAt}) >= unixepoch() - ${MAX_AGE_MINUTES * 60}`,
        chainAnswered
      )
    );

  if (anchors.length === 0) {
    console.log('No announcements waiting for a reminder.');
    process.exit(0);
  }

  const due = anchors.filter(
    (anchor) => ageInMinutes(anchor.createdAt) >= REMINDER_OFFSETS[anchor.reminderCount]
  );

  console.log(
    `${due.length} of ${anchors.length} unanswered announcement(s) are due for a reminder.`
  );

  // Stops re-checking a row that can never produce a reminder.
  const exhaust = (id: string) =>
    db
      .update(waMessages)
      .set({ reminderCount: MAX_REMINDERS, updatedAt: sql`datetime('now', '+3 hours')` })
      .where(eq(waMessages.id, id));

  for (const anchor of due) {
    const reminderNo = anchor.reminderCount + 1;

    if (!anchor.message) {
      console.log(`Announcement ${anchor.id} has no body, skipping.`);
      await exhaust(anchor.id);
      continue;
    }

    const [user] = await db
      .select({ id: users.id, name: users.name, phoneNumber: users.phoneNumber })
      .from(users)
      .where(and(eq(users.id, anchor.userId), sql`${users.active} = 1`))
      .limit(1);

    if (!user || !user.phoneNumber) {
      console.log(`User ${anchor.userId} is inactive or has no phone number, skipping.`);
      await exhaust(anchor.id);
      continue;
    }

    const text = `[Hatırlatma ${reminderNo}] ${anchor.message}`;

    console.log(`Sending reminder ${reminderNo} to user ${user.name} with ID ${user.id}`);

    try {
      let response: Response;

      if (TEST) {
        response = new Response(
          JSON.stringify({ messages: [{ id: `test_reminder_${user.id}_${Date.now()}` }] }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      } else {
        response = await fetch(`https://graph.facebook.com/v23.0/${PHONE_NUMBER_ID}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${WHATSAPP_TOKEN}`
          },
          body: JSON.stringify({
            messaging_product: 'whatsapp',
            to: user.phoneNumber,
            type: 'template',
            template: {
              name: 'deprem',
              language: { code: 'tr' },
              components: [
                {
                  type: 'body',
                  parameters: [
                    { type: 'text', parameter_name: 'adsoyad', text: user.name },
                    { type: 'text', parameter_name: 'detay', text }
                  ]
                }
              ]
            }
          })
        });
      }

      if (!response.ok) {
        const body = await response.text();
        console.log(`Failed to send reminder ${reminderNo} to user ${user.name} (${user.id})`);

        try {
          await db
            .insert(waMessagesFailed)
            .values({ userId: user.id, pollName: POLL_NAME, earthquakeId: null, reason: body });
        } catch (error) {
          console.error('Failed to log failed reminder to database:', error);
        }
        continue;
      }

      const data = await response.json();
      const messageId = data.messages[0].id;

      await db.insert(waMessages).values({
        id: messageId,
        userId: user.id,
        isRead: sql`0`,
        // same body as the anchor, that is what keeps the chain together
        message: anchor.message,
        pollName: POLL_NAME,
        earthquakeId: null,
        // a follow-up is never the anchor of a new chain
        reminderCount: MAX_REMINDERS,
        updatedAt: sql`datetime('now', '+3 hours')`,
        createdAt: sql`CURRENT_TIMESTAMP`
      });

      await db
        .update(waMessages)
        .set({ reminderCount: reminderNo, updatedAt: sql`datetime('now', '+3 hours')` })
        .where(eq(waMessages.id, anchor.id));
    } catch (error) {
      console.error(`Failed to send reminder to user ${user.name} with ID ${user.id}:`, error);

      try {
        await db.insert(waMessagesFailed).values({
          userId: user.id,
          pollName: POLL_NAME,
          earthquakeId: null,
          reason: error instanceof Error ? error.message : 'Unknown error'
        });
      } catch (err) {
        console.error('Failed to log failed reminder to database:', err);
      }
    }

    // be gentle with the WhatsApp API, mirrors the earthquake worker
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
} catch (error) {
  console.error(error);
}

process.exit(0);
