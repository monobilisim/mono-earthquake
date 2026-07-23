import sql, { getUser, getAllGroups, type User } from '$lib/db';
import { fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';

const PHONE_NUMBER_ID = Bun.env.PHONE_NUMBER_ID;
const WHATSAPP_TOKEN = Bun.env.WHATSAPP_TOKEN;
const TEST = Bun.env.TEST === 'true';

const MAX_MESSAGE_LENGTH = 4096; // WhatsApp text message body limit

type Recipient = {
  id: number;
  name: string;
  phone_number: string;
};

// An organization manager is a non-admin whose role matches one of the groups (tenants).
// Their own organization is their first group.
function isOrgManager(user: User, allgroups: string[]): boolean {
  return !user.roles.includes('admin') && user.roles.some((role) => allgroups.includes(role));
}

export const load: PageServerLoad = async ({ cookies }) => {
  const session = cookies.get('session') || null;

  if (!session) {
    throw redirect(303, '/');
  }

  const user = await getUser(session);

  if (!user || !user.name) {
    throw redirect(303, '/');
  }

  const allgroups = await getAllGroups('groups');
  const isAdmin = user.roles.includes('admin');
  const manager = isOrgManager(user, allgroups);

  if (!isAdmin && !manager) {
    return { authorized: false, isAdmin: false, organization: null, groups: [], recipientCount: 0 };
  }

  if (isAdmin) {
    // Admins can pick any organization.
    return { authorized: true, isAdmin: true, organization: null, groups: allgroups, recipientCount: 0 };
  }

  // Organization manager: locked to their own organization.
  const organization = user.groups[0] ?? null;
  let recipientCount = 0;

  if (organization) {
    try {
      const rows =
        await sql`SELECT COUNT(*) AS count FROM users WHERE active = 1 AND phone_number IS NOT NULL AND phone_number != '' AND groups LIKE ${'%' + organization + '%'}`;
      recipientCount = rows[0]?.count ?? 0;
    } catch (e) {
      console.error(e);
    }
  }

  return { authorized: true, isAdmin: false, organization, groups: [], recipientCount };
};

export const actions: Actions = {
  sendMessage: async ({ cookies, request }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, { message: 'Oturum bulunamadı' });
    }

    const user = await getUser(session);

    if (!user || !user.name) {
      return fail(403, { message: 'Yetkisiz' });
    }

    const allgroups = await getAllGroups('groups');
    const isAdmin = user.roles.includes('admin');
    const manager = isOrgManager(user, allgroups);

    if (!isAdmin && !manager) {
      return fail(403, { message: 'Bu işlem için yetkiniz yok' });
    }

    const formData = await request.formData();
    const message = ((formData.get('message') as string) || '').trim();

    if (!message) {
      return fail(400, { message: 'Mesaj boş olamaz' });
    }

    if (message.length > MAX_MESSAGE_LENGTH) {
      return fail(400, { message: `Mesaj çok uzun (en fazla ${MAX_MESSAGE_LENGTH} karakter)` });
    }

    // Determine the target organization.
    // Admins may choose; managers are always locked to their own organization
    // (any submitted value is ignored) so they cannot message other organizations.
    let organization: string;

    if (isAdmin) {
      const submitted = ((formData.get('organization') as string) || '').trim();
      if (!submitted) {
        return fail(400, { message: 'Organizasyon seçilmedi' });
      }
      if (!allgroups.includes(submitted)) {
        return fail(400, { message: 'Geçersiz organizasyon' });
      }
      organization = submitted;
    } else {
      organization = user.groups[0];
      if (!organization) {
        return fail(400, { message: 'Organizasyonunuz bulunamadı' });
      }
    }

    let recipients: Recipient[] = [];

    try {
      recipients =
        await sql`SELECT id, name, phone_number FROM users WHERE active = 1 AND phone_number IS NOT NULL AND phone_number != '' AND groups LIKE ${'%' + organization + '%'}`;
    } catch (e) {
      console.error(e);
      return fail(500, { message: 'Alıcılar getirilirken bir hata oluştu' });
    }

    if (recipients.length === 0) {
      return fail(400, { message: 'Bu organizasyonda mesaj gönderilecek aktif kullanıcı yok' });
    }

    if (!TEST && (typeof PHONE_NUMBER_ID !== 'string' || typeof WHATSAPP_TOKEN !== 'string')) {
      return fail(500, { message: 'WhatsApp yapılandırması eksik' });
    }

    let sent = 0;
    let failed = 0;

    for (const recipient of recipients) {
      try {
        let response: Response;

        if (TEST) {
          response = new Response(
            JSON.stringify({ messages: [{ id: `test_message_${recipient.id}_${Date.now()}` }] }),
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
              to: recipient.phone_number,
              type: 'text',
              text: { body: message }
            })
          });
        }

        if (!response.ok) {
          failed++;
          const body = await response.text();
          try {
            await sql`INSERT INTO wa_messages_failed (user_id, poll_name, earthquake_id, reason)
              VALUES (${recipient.id}, 'duyuru', NULL, ${body})`;
          } catch (e) {
            console.error('Failed to log failed message:', e);
          }
          continue;
        }

        try {
          const data = await response.json();
          const messageId = data.messages[0].id;

          await sql`INSERT INTO wa_messages (id, user_id, is_read, message, poll_name, earthquake_id, updated_at, created_at)
            VALUES (${messageId}, ${recipient.id}, 0, ${message}, 'duyuru', NULL, datetime('now', '+3 hours'), CURRENT_TIMESTAMP)`;
          sent++;
        } catch (e) {
          failed++;
          console.error(e);
          try {
            await sql`INSERT INTO wa_messages_failed (user_id, poll_name, earthquake_id, reason)
              VALUES (${recipient.id}, 'duyuru', NULL, ${e instanceof Error ? e.message : 'Unknown error'})`;
          } catch (err) {
            console.error('Failed to log failed message:', err);
          }
        }
      } catch (e) {
        failed++;
        console.error(`Failed to send message to user ${recipient.name} (${recipient.id}):`, e);
      }

      // be gentle with the WhatsApp API, mirrors the earthquake worker
      await new Promise((resolve) => setTimeout(resolve, 120));
    }

    return { success: true, sent, failed, total: recipients.length, organization };
  }
};
