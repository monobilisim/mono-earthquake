import { SQL } from 'bun';

const sql = new SQL('sqlite://./data/earthquakes.db');

export default sql;

export type User = {
	name: string;
	roles: string[];
	groups: string[];
};

export async function getUser(session: string): Promise<User> {
	let user: User = {
		name: '',
		roles: [],
		groups: []
	};

	try {
		const sessionResult =
			await sql`SELECT user_id, expiration_date FROM sessions WHERE session_token = ${session} ORDER BY id DESC LIMIT 1;`;

		if (sessionResult.length > 0) {
			const expirationDate = new Date(sessionResult[0].expiration_date);
			const currentDate = new Date();

			if (expirationDate < currentDate) {
				await sql`DELETE FROM sessions WHERE session_token = ${session};`;

				return user;
			}

			const userId = sessionResult[0].user_id;

			const userInfo =
				await sql`SELECT name, roles, groups FROM users WHERE id = ${userId} LIMIT 1;`;

			if (userInfo.length > 0) {
				const name = userInfo[0].name;
				const roles = userInfo[0].roles.split(',').map((item: string) => item.trim());
				const groups = userInfo[0].groups.split(',').map((item: string) => item.trim());

				const user = {
					name,
					roles,
					groups
				};

				return user;
			}
		}
	} catch (error) {
		console.error('Error fetching user:', error);
	}

	return user;
}
