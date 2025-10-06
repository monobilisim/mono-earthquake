import sql, { getUser, type User } from '$lib/db';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ cookies }) => {
	type SessionActive = {
		sessionActive: boolean;
	};

	let sessionActive: boolean = false;
	let user: User | null = null;

	try {
		const session = cookies.get('session');

		if (session) {
			user = await getUser(session);

			if (!user.name || user.name === '') {
				cookies.delete('session', { secure: true, sameSite: 'strict', httpOnly: true, path: '/' });

				sessionActive = false;

				return { sessionActive, user };
			}

			sessionActive = true;

			return { sessionActive, user };
		} else {
			sessionActive = false;
			return { sessionActive, user };
		}
	} catch (error) {
		sessionActive = false;
		return { sessionActive, user };
	}
};
