import sql from '$lib/db';

export const POST = async ({ request }): Promise<Response> => {
	try {
		const data = await request.json();

		const value = data.entry[0].changes[0].value;

		let is_read = false;
		let message = null;
		let id = null;

		if (value['statuses']) {
			id = value.statuses[0]?.id;
			is_read = value.statuses[0]?.status === 'read';
		}

		if (value['messages']) {
			id = value.messages[0]?.context?.id;
			message = value.messages[0]?.button?.text;
		}

		if (is_read === true && message === null) {
			try {
				await sql`UPDATE wa_messages SET is_read = true WHERE id = ${id}`;
			} catch (error) {
				console.error('Error updating WhatsApp message status in database:', error);
			}
		}

		if (message !== null) {
			try {
				await sql`UPDATE wa_messages SET is_read = true, message = ${message} WHERE id = ${id}`;
			} catch (error) {
				console.error('Error updating WhatsApp message status and message in database:', error);
			}
		}

		return new Response('', { status: 200 });
	} catch (error) {
		console.error('Error parsing JSON:', error);
		return new Response('Invalid JSON', { status: 400 });
	}
};
