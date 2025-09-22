import sql, { getUser, type User } from '$lib/db';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ cookies }) => {
	type SessionActive = {
		sessionActive: boolean;
	};

	let user: User | null = null;

	try {
		const session = cookies.get('session');

		if (session) {
			user = await getUser(session);

			if (!user.name || user.name === '') {
				cookies.delete('session', { secure: true, sameSite: 'strict', httpOnly: true, path: '/' });

				return { sessionActive: false, user } as SessionActive;
			}

			return { sessionActive: true, user } as SessionActive;
		} else {
			return { sessionActive: false, user } as SessionActive;
		}
	} catch (error) {
		return { sessionActive: false, user } as SessionActive;
	}
};
