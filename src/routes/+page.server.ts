import { error, fail } from '@sveltejs/kit';
import type { Poll } from '$lib/types';
import type { Actions, PageServerLoad } from './$types';
import sql, { getUser } from '$lib/db';
import { generateRandomToken } from '$lib/utils';

const PHONE_NUMBER_ID = Bun.env.PHONE_NUMBER_ID;
const WHATSAPP_TOKEN = Bun.env.WHATSAPP_TOKEN;

type User = {
  name: string;
  roles: string[];
  groups: string[];
};

type Earthquake = {
  id: number;
  latitude: number;
  longitude: number;
  depth: number;
  md: number;
  ml: number;
  mw: number;
  magnitude: number;
  location: string;
  timestamp: string;
  date: string;
  time: string;
  quality: string;
  year: number;
  month: number;
  day: number;
  week: number;
};

type Last30DaysStats = {
  messages: {
    successful: number;
    failed: number;
    total: number;
  };
  earthquakes: {
    total: number;
    days: Record<string, string>[];
  };
};

type EarthquakeFilters = {
  min_magnitude?: number;
  max_magnitude?: number;
  start_date?: string;
  end_date?: string;
};

export const load: PageServerLoad = async ({ cookies, url }) => {
  const sessionToken = cookies.get('session') || null;

  let user: User = {
    name: '',
    roles: [],
    groups: []
  };

  let last30DaysStats: Last30DaysStats = {
    messages: {
      successful: 0,
      failed: 0,
      total: 0
    },
    earthquakes: {
      total: 0,
      days: []
    }
  };

  const polls: Poll[] = await sql`SELECT id, name, type, threshold FROM polls`;
  const earthquakePoll = <Poll>polls.find((poll) => poll.name === 'deprem');
  const earthquakeThreshold = earthquakePoll.threshold;

  let earthquakeFilters: EarthquakeFilters = {
    min_magnitude: url.searchParams.get('min_magnitude') as never,
    max_magnitude: url.searchParams.get('max_magnitude') as never,
    start_date: url.searchParams.get('start_date') as never,
    end_date: url.searchParams.get('end_date') as never
  };

  let earthquakes: Earthquake[] = [];

  let earthquakesResult: Earthquake[] = [];

  if (
    earthquakeFilters.min_magnitude ||
    earthquakeFilters.max_magnitude ||
    earthquakeFilters.start_date ||
    earthquakeFilters.end_date
  ) {
    earthquakesResult = await sql`
		SELECT id, latitude, longitude, depth, md, ml, mw,
	  magnitude, location, timestamp, date, time, quality,
		year, month, day, week FROM earthquakes
		WHERE magnitude >= ${earthquakeFilters.min_magnitude} AND magnitude <= ${earthquakeFilters.max_magnitude}
	  AND date >= ${earthquakeFilters.start_date} AND date <= ${earthquakeFilters.end_date} ORDER BY id DESC LIMIT 1000;`;
  } else {
    // no filter
    earthquakesResult = await sql`SELECT id, latitude, longitude, depth,
			md, ml, mw, magnitude, location, timestamp, date,
			time, quality, year, month, day, week FROM earthquakes ORDER BY id DESC LIMIT 1000;`;
  }

  if (earthquakesResult.length > 0) {
    let earthquakesWithFeedbacks: Earthquake[] = [];

    // @ts-ignore it is Promise<Earthquake[] | undefined>[]
    earthquakesWithFeedbacks = earthquakesResult.map(async (eq) => {
      const feedbacks = await sql`SELECT id FROM wa_messages WHERE earthquake_id = ${eq.id}`;

      if (feedbacks.length > 0) {
        return eq;
      }

      return undefined;
    });

    // first convert Promise<Earthquake[] | undefined> to Earthquake[] | undefined then filter out undefined
    earthquakes = (await Promise.all(earthquakesWithFeedbacks)).filter((i) => i !== undefined);
  }

  try {
    const successful =
      await sql`SELECT count(*) as count from wa_messages WHERE created_at >= date('now', '-30 days')`;
    const failed =
      await sql`SELECT count(*) as count from wa_messages_failed WHERE updated_at >= date('now', '-30 days')`;
    const total = successful[0].count + failed[0].count;
    const earthquakesCount =
      await sql`SELECT count(*) as count from earthquakes WHERE timestamp >= date('now', '-30 days')`;

    const today = new Date();

    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const daysValueArray = [];

    const years = [today.getFullYear(), today.getFullYear() - 1];

    for (const year of years) {
      if (daysValueArray.length >= 30) {
        break;
      }

      for (const month of Array.from({ length: 12 }, (_, i) => 12 - i)) {
        if (daysValueArray.length >= 30) {
          break;
        }

        const daysInMonth = new Date(year, month, 0).getDate();

        for (const day of Array.from({ length: daysInMonth }, (_, i) => daysInMonth - i)) {
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const dateToCheck = new Date(year, month - 1, day);
          dateToCheck.setHours(0, 0, 0, 0);

          if (dateToCheck >= thirtyDaysAgo && dateToCheck <= today) {
          } else {
            continue;
          }

          if (daysValueArray.length >= 30) {
            break;
          }

          const formattedMonth = month.toString().padStart(2, '0');
          const formattedDay = day.toString().padStart(2, '0');

          const countByDate =
            await sql`SELECT COUNT(*) as count FROM earthquakes WHERE year = ${year} AND month = ${month} AND day = ${day} AND magnitude >= ${earthquakeThreshold}`;

          console.log(`${year}-${formattedMonth}-${formattedDay}: ${countByDate[0].count}`);

          if (countByDate.length > 0) {
            daysValueArray.push({
              date: `${year}-${formattedMonth}-${formattedDay}`,
              count: countByDate[0].count
            });
          }
        }
      }
    }

    last30DaysStats = {
      messages: {
        successful: successful[0].count,
        failed: failed[0].count,
        total: total
      },
      earthquakes: {
        total: earthquakesCount[0].count,
        days: daysValueArray.reverse()
      }
    };
  } catch (e) {
    console.error(e);
  }

  if (typeof PHONE_NUMBER_ID !== 'string') {
    error(500, 'PHONE_NUMBER_ID is not set');
  }

  if (typeof WHATSAPP_TOKEN !== 'string') {
    error(500, 'WHATSAPP_TOKEN is not set');
  }

  if (!sessionToken) {
    return { user, earthquakes, last30DaysStats };
  }

  let userResult;

  try {
    userResult =
      await sql`SELECT user_id FROM sessions WHERE session_token = ${sessionToken} ORDER BY id DESC LIMIT 1;`;
  } catch (e) {
    console.error(e);
  }

  if (userResult.length === 0) {
    return { user, earthquakes, last30DaysStats };
  }

  const userId = <number>userResult[0].user_id;

  const userInfo = await sql`SELECT name, groups, roles FROM users WHERE id = ${userId} LIMIT 1;`;

  if (userInfo.length === 0) {
    return { user, earthquakes, last30DaysStats };
  }

  // if user does exists
  if (userInfo.length > 0) {
    const name = userInfo[0].name;
    const roles = userInfo[0].roles.split(',').map((item: string) => item.trim());
    const groups = userInfo[0].groups.split(',').map((item: string) => item.trim());

    const user = {
      name,
      roles,
      groups
    };

    return { user, earthquakes, last30DaysStats };
  }

  return { user, earthquakes, last30DaysStats };
};

export const actions: Actions = {
  sendToken: async ({ cookies, request }) => {
    const formData = await request.formData();

    let phone_number = formData.get('phone_number') || undefined;

    if (!phone_number) {
      return fail(400, 'Phone number does not exists');
    }

    if (phone_number.slice(0, 2) !== '90') {
      phone_number = '90' + phone_number;
    }

    const user =
      await sql`SELECT id, roles FROM users WHERE phone_number = ${phone_number} LIMIT 1`;

    if (user.length === 0) {
      return fail(400, 'User does not exists');
    }

    const user_roles = user[0].roles;

    if (user_roles === null || user_roles === '' || user_roles.length === 0) {
      return fail(403, 'User has no roles assigned');
    }

    const activation_token = generateRandomToken(6);

    const success =
      await sql`UPDATE users SET activation_token = ${activation_token} WHERE phone_number = ${phone_number}`;

    if (success.count === 0) {
      return fail(400, 'Phone number does not exists');
    }

    const whatsappResponse = await fetch(
      `https://graph.facebook.com/v23.0/${PHONE_NUMBER_ID}/messages`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${WHATSAPP_TOKEN}`
        },
        body: JSON.stringify({
          messaging_product: 'whatsapp',
          to: phone_number,
          type: 'template',
          template: {
            name: 'giris_kodu',
            language: { code: 'tr' },
            components: [
              {
                type: 'body',
                parameters: [
                  {
                    type: 'text',
                    text: activation_token
                  }
                ]
              },
              {
                type: 'button',
                sub_type: 'url',
                index: '0',
                parameters: [{ type: 'text', text: activation_token }]
              }
            ]
          }
        })
      }
    );

    if (!whatsappResponse.ok) {
      console.log(await whatsappResponse.json());
      await sql`UPDATE users SET activation_token = NULL WHERE phone_number = ${phone_number}`;
      return fail(500, 'Could not send WhatsApp message');
    }

    return { success: true };
  },

  verifyToken: async ({ cookies, request }) => {
    const formData = await request.formData();

    const activation_token = formData.get('activation_token') || undefined;
    let phone_number = formData.get('phone_number') || undefined;

    if (!activation_token) {
      return fail(400, 'Token does not exists');
    }

    if (!phone_number) {
      return fail(400, 'Phone number does not exists');
    }

    if (phone_number.slice(0, 2) !== '90') {
      phone_number = '90' + phone_number;
    }

    const user =
      await sql`SELECT id, roles FROM users WHERE activation_token = ${activation_token} AND phone_number = ${phone_number} LIMIT 1`;

    if (user.length === 0) {
      return fail(400, 'User does not exists');
    }

    const user_id = user[0].id;
    const user_roles = user[0].roles;

    if (user_roles === null || user_roles === '' || user_roles.length === 0) {
      return fail(403, 'User has no roles assigned');
    }

    const success =
      await sql`UPDATE users SET activation_token = NULL WHERE activation_token = ${activation_token}`;

    if (success.count === 0) {
      return fail(400, 'activation_token does not exists');
    }

    const sessionToken = generateRandomToken(32, true);

    const createSession =
      await sql`INSERT INTO sessions (user_id, session_token) VALUES (${user_id}, ${sessionToken})`;

    if (createSession.count === 0) {
      return fail(500, 'Could not create session');
    }

    cookies.set('session', sessionToken, {
      path: '/',
      httpOnly: true,
      sameSite: 'strict',
      secure: true,
      maxAge: 60 * 60 * 24 * 7 // 1 week
    });

    return { success: true };
  },

  getFeedbackStatsByEarthquakeID: async ({ request, cookies }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(403, 'Not authenticated');
    }

    const user = await getUser(session);

    const formData = await request.formData();
    const id = formData.get('id') || undefined;

    type Feedbacks = {
      id: number;
      user_id: number;
      message: string;
      is_read: boolean;
      updated_at: string;
      created_at: string;
    };

    let feedbacks: Feedbacks[] = [];

    if (!id) {
      return fail(400, 'ID does not exists');
    }

    try {
      const allGroups = await sql`SELECT name FROM groups`;
      let possibleRoles: string[] = ['admin', 'masked'];
      allGroups.forEach((group: { name: string }) => {
        possibleRoles.push(group.name);
        possibleRoles.push(`${group.name}-masked`);
      });

      const hasValidRole = user.roles.some((role: string) => possibleRoles.includes(role));

      if (!hasValidRole) {
        return feedbacks;
      }

      function censorString(str: string): string {
        if (str.length <= 2) {
          return '*'.repeat(str.length);
        }

        const firstTwo = str.slice(0, 2);
        const lastTwo = str.slice(-2);
        const middle = '*'.repeat(str.length - 4);

        return firstTwo + middle + lastTwo;
      }

      if (user.roles.includes('admin')) {
        let feedbacksResult: Feedbacks[] =
          await sql`SELECT id, user_id, is_read, message, updated_at FROM wa_messages WHERE earthquake_id = ${id} ORDER BY id DESC`;

        if (feedbacksResult.length === 0) {
          return [];
        }

        const resultsWithNames = feedbacksResult.map(async (feedback) => {
          const result =
            await sql`SELECT name, phone_number FROM users WHERE id = ${feedback.user_id} LIMIT 1`;
          const name = result.length > 0 ? result[0].name : 'Unknown';
          const phone_number = result.length > 0 ? result[0].phone_number : 'Unknown';
          return { ...feedback, name, phone_number };
        });

        feedbacks = await Promise.all(resultsWithNames);

        return feedbacks;
      }

      if (user.roles.includes('masked')) {
        let feedbacksResult: Feedbacks[] =
          await sql`SELECT id, user_id, is_read, message, updated_at FROM wa_messages WHERE earthquake_id = ${id} ORDER BY id DESC`;

        if (feedbacksResult.length === 0) {
          return [];
        }

        const resultsWithNames = feedbacksResult.map(async (feedback) => {
          const result =
            await sql`SELECT name, phone_number FROM users WHERE id = ${feedback.user_id} LIMIT 1`;
          const name = result.length > 0 ? result[0].name : 'Unknown';
          const phone_number = result.length > 0 ? censorString(result[0].phone_number) : 'Unknown';
          return { ...feedback, name, phone_number };
        });

        feedbacks = await Promise.all(resultsWithNames);

        return feedbacks;
      }

      for (const role of user.roles) {
        if (possibleRoles.includes(role)) {
          // full see role
          if (!role.includes('-masked')) {
            const pattern = `%${role}%`;
            let usersFromGroup: { id: number; name: string }[] =
              await sql`SELECT id, name FROM users WHERE groups LIKE ${pattern}`;

            let feedbacksResult: Feedbacks[] = [];
            for (const u of usersFromGroup) {
              const fResult =
                await sql`SELECT id, user_id, is_read, message, updated_at FROM wa_messages WHERE earthquake_id = ${id} AND user_id = ${u.id} ORDER BY id DESC`;
              if (fResult.length > 0) {
                feedbacksResult = feedbacksResult.concat(fResult);
              }
            }

            if (feedbacksResult.length === 0) {
              return [];
            }

            const resultsWithNames = feedbacksResult.map(async (feedback) => {
              const result =
                await sql`SELECT name, phone_number FROM users WHERE id = ${feedback.user_id} LIMIT 1`;
              const name = result.length > 0 ? result[0].name : 'Unknown';
              const phone_number = result.length > 0 ? result[0].phone_number : 'Unknown';
              return { ...feedback, name, phone_number };
            });

            feedbacks = await Promise.all(resultsWithNames);

            return feedbacks;
          }

          // masked see role
          if (role.includes('-masked')) {
            const pattern = `%${role.replace('-masked', '')}%`;
            let usersFromGroup: { id: number; name: string }[] =
              await sql`SELECT id, name FROM users WHERE groups LIKE ${pattern}`;

            let feedbacksResult: Feedbacks[] = [];
            for (const u of usersFromGroup) {
              const fResult =
                await sql`SELECT id, user_id, is_read, message, updated_at FROM wa_messages WHERE earthquake_id = ${id} AND user_id = ${u.id} ORDER BY id DESC`;
              if (fResult.length > 0) {
                feedbacksResult = feedbacksResult.concat(fResult);
              }
            }

            if (feedbacksResult.length === 0) {
              return [];
            }

            const resultsWithNames = feedbacksResult.map(async (feedback) => {
              const result =
                await sql`SELECT name, phone_number FROM users WHERE id = ${feedback.user_id} LIMIT 1`;
              const name = result.length > 0 ? result[0].name : 'Unknown';
              const phone_number =
                result.length > 0 ? censorString(result[0].phone_number) : 'Unknown';
              return { ...feedback, name, phone_number };
            });

            feedbacks = await Promise.all(resultsWithNames);

            return feedbacks;
          }
        }
      }
    } catch (error) {
      console.error(error);
      return fail(500, 'Could not fetch feedbacks');
    }

    return feedbacks;
  }
};
