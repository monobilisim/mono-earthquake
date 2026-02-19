import { AfadParser, type EarthquakeData } from './afad';
import { KoeriParser } from './koeri';
import sql from '$lib/db';
import type { Poll } from '$lib/types';

if (Bun.env.BUILD_STEP) {
  process.exit(0);
}

const PHONE_NUMBER_ID = Bun.env.PHONE_NUMBER_ID;
const WHATSAPP_TOKEN = Bun.env.WHATSAPP_TOKEN;
const EARTHQUAKE_SOURCE_PRIORITY = Bun.env.EARTHQUAKE_SOURCE_PRIORITY || 'afad';
const HOW_MANY_MINUTES_BETWEEN_MESSAGES = Number(Bun.env.HOW_MANY_MINUTES_BETWEEN_MESSAGES) || 30;
const TEST = Bun.env.TEST === 'true';

try {
  const polls: Poll[] = await sql`SELECT id, name, type, threshold FROM polls`;

  if (polls.length === 0) {
    console.log('No polls found in the database.');
    process.exit(0);
  }

  let newRecords: EarthquakeData[] = [];
  let afadNewRecords: EarthquakeData[] = [];
  let koeriNewRecords: EarthquakeData[] = [];

  // this will be a failover instead of both if not all selected
  // EARTHQUAKE_SOURCE_PRIORITY can be koeri, afad or all
  if (EARTHQUAKE_SOURCE_PRIORITY === 'afad') {
    try {
      console.log('Fetching data from AFAD as primary source.');
      const afadParser = new AfadParser();
      afadNewRecords = await afadParser.saveToDatabase();
      newRecords = newRecords.concat(afadNewRecords);

      // if afad successfully fetch data, also fetch data from koeri to know they are old
      try {
        console.info('Fetching old data from KOERI for saving to database.');
        const koeriParser = new KoeriParser();
        await koeriParser.saveToDatabase();
      } catch {
        console.error('KOERI parser failed while fetching old data');
      }
    } catch {
      console.info('AFAD parser failed, trying KOERI as failover');
      try {
        const koeriParser = new KoeriParser();
        koeriNewRecords = await koeriParser.saveToDatabase();
        newRecords = newRecords.concat(koeriNewRecords);
      } catch {
        console.error('KOERI parser also failed');
      }
    }
  }

  if (EARTHQUAKE_SOURCE_PRIORITY === 'koeri') {
    try {
      console.log('Fetching data from KOERI as primary source.');
      const koeriParser = new KoeriParser();
      koeriNewRecords = await koeriParser.saveToDatabase();
      newRecords = newRecords.concat(koeriNewRecords);

      // if koeri successfully fetch data, also fetch data from afad to know they are old
      try {
        console.info('Fetching old data from AFAD for saving to database.');
        const afadParser = new AfadParser();
        await afadParser.saveToDatabase();
      } catch {
        console.error('AFAD parser failed while fetching old data');
      }
    } catch {
      console.info('KOERI parser failed, trying AFAD as failover');
      try {
        const afadParser = new AfadParser();
        afadNewRecords = await afadParser.saveToDatabase();
        newRecords = newRecords.concat(afadNewRecords);
      } catch {
        console.error('AFAD parser also failed');
      }
    }
  }

  if (EARTHQUAKE_SOURCE_PRIORITY === 'all') {
    const afadParser = new AfadParser();
    afadNewRecords = await afadParser.saveToDatabase();
    newRecords = newRecords.concat(afadNewRecords);
  }

  if (EARTHQUAKE_SOURCE_PRIORITY === 'all') {
    const koeriParser = new KoeriParser();
    koeriNewRecords = await koeriParser.saveToDatabase();
    newRecords = newRecords.concat(koeriNewRecords);
  }

  if (newRecords.length > 0) {
    if (afadNewRecords.length > 0) {
      console.log('afad earthquakes: ', afadNewRecords);
    }

    if (koeriNewRecords.length > 0) {
      console.log('koeri earthquakes: ', koeriNewRecords);
    }
  }

  const earthquakePoll = <Poll>polls.find((poll) => poll.name === 'deprem');
  const pollType = earthquakePoll.type;
  const earthquakeThreshold = earthquakePoll.threshold;

  // if enough time has not passed since last message, exit
  const lastMessageSentToUsers: { earthquake_id: number }[] =
    await sql`SELECT earthquake_id FROM wa_messages ORDER BY created_at DESC LIMIT 1`;

  const lastEarthquakeMessagedToUsers =
    await sql`SELECT created_at FROM earthquakes WHERE id = ${lastMessageSentToUsers[0]?.earthquake_id} LIMIT 1`;

  if (lastEarthquakeMessagedToUsers.length > 0) {
    // "2025-10-06 12:50:45" etc. its UTC
    const dateFromDB = lastEarthquakeMessagedToUsers[0].created_at;
    const dbDate = new Date(dateFromDB.replace(' ', 'T') + 'Z');

    // also in UTC
    const now = new Date();

    const diffMs = Math.abs(now.getTime() - dbDate.getTime());
    const diffMinutes = Math.floor(diffMs / 1000 / 60);

    if (diffMinutes < HOW_MANY_MINUTES_BETWEEN_MESSAGES) {
      // toTimeString() gives time in local timezone
      console.log(
        `Last message sent at ${dbDate.toTimeString()} (${diffMinutes} minutes ago)
Enough time has not passed yet. (${HOW_MANY_MINUTES_BETWEEN_MESSAGES} minutes)`
      );

      process.exit(0);
    }
  }

  if (newRecords.length > 0) {
    // @ts-ignore
    const highestRecord = [...newRecords].sort((a, b) => b.magnitude - a.magnitude)[0];

    console.log('Whatsapp messages sent for the record: ', highestRecord);

    for (const record of [highestRecord]) {
      if (<number>record.magnitude >= earthquakeThreshold) {
        console.log(
          `New earthquake record above threshold: ${record.magnitude} at ${record.location}`
        );

        const activeGroups =
          await sql`SELECT name FROM groups WHERE active = 1 AND polls LIKE '%deprem%'`;

        console.log(`Active Groups: ${activeGroups.length}`);

        for (const group of activeGroups) {
          console.log(`Group: ${group.name}`);

          const groupName = group.name;
          const groupUsers =
            await sql`SELECT id, name, phone_number, active FROM users WHERE active = 1 AND groups LIKE ${groupName}`;

          if (groupUsers.length === 0) {
            console.log('No users found in this group.');
            continue;
          }

          let earthqaukeSource = '';
          if (record.quality === 'AFAD') {
            earthqaukeSource = 'AFAD';
          } else {
            earthqaukeSource = 'KOERI';
          }

          for (const user of groupUsers) {
            if (pollType === 'whatsapp') {
              console.log(`Sending whatsapp template to user ${user.name} with ID ${user.id}`);

              try {
                let response: Response;
                if (TEST) {
                  response = await fetch("https://google.com");
                } else {
                  response = await fetch(
                    `https://graph.facebook.com/v23.0/${PHONE_NUMBER_ID}/messages`,
                    {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${WHATSAPP_TOKEN}`
                      },
                      body: JSON.stringify({
                        messaging_product: 'whatsapp',
                        to: user.phone_number,
                        type: 'template',
                        template: {
                          name: 'deprem',
                          language: { code: 'tr' },
                          components: [
                            {
                              type: 'body',
                              parameters: [
                                { type: 'text', parameter_name: 'adsoyad', text: user.name },
                                {
                                  type: 'text',
                                  parameter_name: 'detay',
                                  text: `Biraz önce (${record.time}) ${record.location} merkezli, ${record.magnitude} büyüklüğünde (${earthqaukeSource})`
                                }
                              ]
                            }
                          ]
                        }
                      })
                    }
                  );
                }

                if (!response.ok) {
                  const body = await response.text();
                  console.log(`Failed to send message to user ${user.name} with ID ${user.id}:`);

                  try {
                    await sql`INSERT INTO wa_messages_failed
								 (user_id, poll_name, earthquake_id, reason)
                    VALUES
                    (${user.id}, 'deprem', ${record.id}, ${body})`;
                  } catch (error) {
                    console.error('Failed to log failed message to database:', error);
                  }
                  continue;
                }

                try {
                  const data = await response.json();

                  const messageId = data.messages[0].id;

                  await sql`INSERT INTO wa_messages
								 (id, user_id, is_read, message, poll_name, earthquake_id, updated_at, created_at)
                  VALUES
                  (${messageId}, ${user.id}, 0, NULL, 'deprem', ${record.id}, datetime('now', '+3 hours'), CURRENT_TIMESTAMP)`;
                } catch (error) {
                  console.error(error);
                  await sql`INSERT INTO wa_messages_failed
								 (user_id, poll_name, earthquake_id, reason)
                  VALUES
                  (${user.id}, 'deprem', ${record.id}, ${error instanceof Error ? error.message : error ?? 'Unknown error'})`;
                }
              } catch (error) {
                console.error(
                  `Failed to send message to user ${user.name} with ID ${user.id}:`,
                  error
                );
              }
            } else {
              continue;
            }

            await new Promise((resolve) => setTimeout(resolve, 200));
          }
        }

        await new Promise((resolve) => setTimeout(resolve, 200));
      } else {
        console.log('Record is not above the threshold.');
      }
    }
  } else {
    console.log('No new records found.');
  }
} catch (error) {
  console.error(error);
}
