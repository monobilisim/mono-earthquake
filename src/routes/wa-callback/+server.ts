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

		const date = new Date();
		const now = new Date(date.getTime() + 3 * 60 * 60 * 1000); // GMT+3

		const year = now.getFullYear();
		const month = String(now.getMonth() + 1).padStart(2, '0');
		const day = String(now.getDate()).padStart(2, '0');
		const hours = String(now.getHours()).padStart(2, '0');
		const minutes = String(now.getMinutes()).padStart(2, '0');
		const seconds = String(now.getSeconds()).padStart(2, '0');

		const formatted = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;

		if (is_read === true && message === null) {
			try {
				await sql`UPDATE wa_messages SET is_read = true, updated_at = ${formatted} WHERE id = ${id}`;
			} catch (error) {
				console.error('Error updating WhatsApp message status in database:', error);
			}
		}

		if (message !== null) {
			try {
				await sql`UPDATE wa_messages SET is_read = true, message = ${message}, updated_at = ${formatted} WHERE id = ${id}`;
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
