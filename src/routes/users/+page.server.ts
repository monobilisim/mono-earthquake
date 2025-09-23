import sql, { getUser } from '$lib/db';
import { fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';

type AppUser = {
	id: number;
	name: string;
	phone_number: string;
	groups: string[];
	roles: string[];
	active: boolean;
};

export const load: PageServerLoad = async ({ cookies }) => {
	const session = cookies.get('session') || null;

	if (!session) {
		return {
			users: []
		};
	}

	const user = await getUser(session);

	if (!user) {
		return { users: [] };
	}

	if (user.roles.includes('admin')) {
		const usersResult = await sql`SELECT id, name, phone_number, groups, roles, active FROM users`;

		if (usersResult.length === 0) {
			return { users: [] };
		}

		const users: AppUser[] = usersResult.map((row: Record<string, string>) => ({
			id: row.id,
			name: row.name,
			phone_number: row.phone_number,
			groups: row.groups ? row.groups.split(',') : [],
			roles: row.roles ? row.roles.split(',') : [],
			active: row.active
		}));

		const groupResult = await sql`SELECT name FROM groups`;
		const groups: string[] = groupResult.map((row: Record<string, string>) => row.name);

		return {
			users,
			groups
		};
	}
};

export const actions: Actions = {
	addUser: async ({ request, cookies }) => {
		const session = cookies.get('session') || null;

		if (!session) {
			return fail(401, 'Unauthorized');
		}

		const user = await getUser(session);

		if (!user || !user.roles.includes('admin')) {
			return fail(403, 'Forbidden');
		}

		const formData = await request.formData();
		const name = formData.get('name') as string;
		const phone_number = formData.get('phone_number').replace(/[^0-9]/g, '') as string;
		const groups = (formData.get('groups').replace(/[^a-zA-Z0-9,]/g, '') as string) || '';
		const roles = (formData.get('roles').replace(/[^a-zA-Z0-9,-]/g, '') as string) || '';

		if (!name || !phone_number) {
			return fail(400, 'Name and phone number are required');
		}

		try {
			await sql`INSERT INTO users (name, phone_number, groups, roles) VALUES (${name},${phone_number},${groups},${roles})`;
			return { success: true, message: 'User added successfully' };
		} catch {
			return fail(500, 'Error adding user');
		}
	},
	deleteUser: async ({ request, cookies }) => {
		const session = cookies.get('session') || null;

		if (!session) {
			return fail(401, 'Unauthorized');
		}

		const user = await getUser(session);
		if (!user || !user.roles.includes('admin')) {
			return fail(403, 'Forbidden');
		}

		const formData = await request.formData();
		const id = formData.get('id').replace(/[^0-9]/g, '') as string;

		if (!id) {
			return fail(400, 'User ID is required');
		}

		try {
			await sql`DELETE FROM users WHERE id = ${id}`;
			return { success: true, message: 'User deleted successfully' };
		} catch (e) {
			console.error(e);
			return fail(500, 'Error deleting user');
		}
	},
	editUser: async ({ request, cookies }) => {},
	toggleUser: async ({ request, cookies }) => {
		const session = cookies.get('session') || null;

		if (!session) {
			return fail(401, 'Unauthorized');
		}

		const user = await getUser(session);

		if (!user || !user.roles.includes('admin')) {
			return fail(403, 'Forbidden');
		}

		const formData = await request.formData();
		const id = formData.get('id').replace(/[^0-9]/g, '');
		const state = formData.get('state'); // "on" or null

		let active = false;

		if (state === 'on') {
			active = true;
		}

		if (!id) {
			return fail(400, 'User ID is required');
		}

		try {
			await sql`UPDATE users SET active = ${active} WHERE id = ${id}`;
			return { success: true, message: 'User state updated successfully' };
		} catch (e) {
			console.error(e);
			return fail(500, 'Error updating user state');
		}
	}
};
