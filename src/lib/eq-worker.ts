import { AfadParser, type EarthquakeData } from './afad';
import { KoeriParser } from './koeri';
import sql from '$lib/db';

type Poll = {
  id: number;
  name: string;
  type: string;
  threshold: number;
};

if (Bun.env.BUILD_STEP) {
  process.exit(0);
}

const PHONE_NUMBER_ID = Bun.env.PHONE_NUMBER_ID;
const WHATSAPP_TOKEN = Bun.env.WHATSAPP_TOKEN;
const EARTHQUAKE_SOURCE = Bun.env.EARTHQUAKE_SOURCE;
try {
  const polls: Poll[] = await sql`SELECT id, name, type, threshold FROM polls`;

  if (polls.length === 0) {
    console.log('No polls found in the database.');
    process.exit(0);
  }

  let newRecords: EarthquakeData[] = [];
  let afadNewRecords: EarthquakeData[] = [];
  let koeriNewRecords: EarthquakeData[] = [];

  if (EARTHQUAKE_SOURCE === 'afad' || EARTHQUAKE_SOURCE === 'all') {
    const afadParser = new AfadParser();
    afadNewRecords = await afadParser.saveToDatabase();
    newRecords = newRecords.concat(afadNewRecords);
  }

  if (EARTHQUAKE_SOURCE === 'koeri' || EARTHQUAKE_SOURCE === 'all') {
    const koeriParser = new KoeriParser();
    koeriNewRecords = await koeriParser.saveToDatabase();
    newRecords = newRecords.concat(koeriNewRecords);
  }

  console.log('afad earthquakes: ', afadNewRecords);

  console.log('koeri earthquakes: ', koeriNewRecords);

  const earthquakePoll = <Poll>polls.find((poll) => poll.name === 'deprem');
  const pollType = earthquakePoll.type;
  const earthquakeThreshold = earthquakePoll.threshold;

  if (newRecords.length > 0) {
    for (const record of newRecords) {
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
                const response = await fetch(
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

                if (!response.ok) {
                  console.log(
                    `Failed to send message to user ${user.name} with ID ${user.id}:`,
                    await response.text()
                  );
                  continue;
                }

                try {
                  const data = await response.json();

                  const messageId = data.messages[0].id;

                  await sql`INSERT INTO wa_messages
								 (id, user_id, is_read, message, poll_name, earthquake_id, updated_at, created_at)
                  VALUES
                  (${messageId}, ${user.id}, 0, NULL, 'deprem', ${record.id}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`;
                } catch (error) {
                  console.error(error);
                  await sql`INSERT INTO wa_messages_failed
								 (user_id, poll_name, earthquake_id, reason)
                  VALUES
                  (${user.id}, 'deprem', ${record.id}, 'Failed to parse response')`;
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
