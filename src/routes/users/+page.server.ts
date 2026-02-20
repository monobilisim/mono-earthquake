import sql, { getUser, getAllGroups } from '$lib/db';
import { fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';

type AppUser = {
  id: number;
  name: string;
  phone_number: string;
  groups: string[];
  user_group: string;
  roles: string[];
  active: boolean;
  province: string;
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

  let usersResult = [];

  if (user.roles.includes('admin')) {
    usersResult =
      await sql`SELECT id, name, phone_number, groups, user_group, roles, province, active FROM users`;
  }

  const allgroups = await getAllGroups("groups");

  // Non admin tenant owners can see users in their own tenant
  if (!user.roles.includes('admin') && user.roles.some(role => allgroups.includes(role))) {
    usersResult =
      await sql`SELECT id, name, phone_number, groups, user_group, roles, province, active FROM users WHERE groups LIKE ${'%' + user.groups[0] + '%'}`;
  }

  if (usersResult.length === 0) {
    return { users: [] };
  }

  const users: AppUser[] = usersResult.map((row: Record<string, string>) => ({
    id: row.id,
    name: row.name,
    phone_number: row.phone_number,
    groups: row.groups ? row.groups.split(',') : [],
    user_group: row.user_group,
    roles: row.roles ? row.roles.split(',') : [],
    active: row.active,
    province: row.province || ""
  }));

  const groupResult = await sql`SELECT name FROM groups`;
  const groups: string[] = groupResult.map((row: Record<string, string>) => row.name);

  type userGroup = {
    tenant: string;
    userGroups: string[];
  };

  let userGroups: userGroup[] = [];

  for (const group of groups) {
    const userGroupsResult = await sql`SELECT name FROM user_groups WHERE tenant = ${group}`;

    if (userGroupsResult.length > 0) {
      const _userGroups: string[] = userGroupsResult.map(
        (row: Record<string, string>) => row.name
      );
      userGroups.push({ tenant: group, userGroups: _userGroups });
    }
  }

  return {
    users,
    groups,
    userGroups
  };

};

export const actions: Actions = {
  addUser: async ({ request, cookies }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);

    if (!user) {
      return fail(403, 'Forbidden');
    }

    const allgroups = await getAllGroups("groups");

    if (!user.roles.includes('admin') && user.roles.some(role => allgroups.some(group => group === role))) {
      const formData = await request.formData();
      const name = formData.get('name') as string;
      let phone_number = (formData.get('phone_number') as string).replace(/[^0-9]/g, '');
      const groups = user.groups[0]; // Non admin users can only add users to their own group
      const roles = `${user.groups[0]}-masked`;
      const userGroup = formData.get('userGroup') as string;
      const province = formData.get('province') as string;

      if (!name || !phone_number) {
        return fail(400, 'Name and phone number are required');
      }

      if (phone_number.slice(0, 2) !== '90') {
        phone_number = '90' + phone_number;
      }

      try {
        const existingUser = await sql`SELECT id, name, groups FROM users WHERE phone_number = ${phone_number}`;
        if (existingUser.length > 0) {
          if (existingUser[0].groups?.includes(groups)) {
            return fail(400, 'A user with this phone number already exists in the selected group');
          }
        }
      } catch (e) {
        return fail(500, 'Error checking existing users');
      }

      try {
        await sql`INSERT INTO users (name, phone_number, groups, roles, user_group, province) VALUES (${name},${phone_number},${groups},${roles},${userGroup},${province})`;
        return { success: true, message: 'User added successfully' };
      } catch (e) {
        return fail(500, 'Error adding user');
      }
    }

    if (user.roles.includes('admin')) {
      const formData = await request.formData();
      const name = formData.get('name') as string;
      let phone_number = (formData.get('phone_number') as string).replace(/[^0-9]/g, '');
      const groups = (formData.get('groups') as string).replace(/[^a-zA-Z0-9,]/g, '') || '';
      const roles = (formData.get('roles') as string).replace(/[^a-zA-Z0-9,-]/g, '') || '';
      const userGroup = formData.get('userGroup') as string;
      const province = formData.get('province') as string;

      if (!name || !phone_number) {
        return fail(400, 'Name and phone number are required');
      }

      if (phone_number.slice(0, 2) !== '90') {
        phone_number = '90' + phone_number;
      }

      try {
        const existingUser = await sql`SELECT id, name, groups FROM users WHERE phone_number = ${phone_number}`;
        if (existingUser.length > 0) {
          if (existingUser[0].groups?.includes(groups)) {
            return fail(400, 'A user with this phone number already exists in the selected group');
          }
        }
      } catch (e) {
        return fail(500, 'Error checking existing users');
      }

      try {
        await sql`INSERT INTO users (name, phone_number, groups, roles, user_group, province) VALUES (${name},${phone_number},${groups},${roles},${userGroup},${province})`;
        return { success: true, message: 'User added successfully' };
      } catch (e) {
        return fail(500, 'Error adding user');
      }
    }
  },
  deleteUser: async ({ request, cookies }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);
    if (!user) {
      return fail(403, 'Forbidden');
    }

    const allgroups = await getAllGroups("groups");

    if (!user.roles.includes('admin') && user.roles.some(role => allgroups.some(group => group === role))) {
      const formData = await request.formData();
      const id = (formData.get('id') as string).replace(/[^0-9]/g, '');

      if (!id) {
        return fail(400, 'User ID is required');
      }

      try {
        const userFromSameGroup = await sql`SELECT id FROM users WHERE id = ${id} AND groups LIKE ${'%' + user.groups[0] + '%'}`;
        if (userFromSameGroup.length === 0) {
          return fail(403, 'Forbidden');
        }

        await sql`DELETE FROM users WHERE id = ${id}`;
        return { success: true, message: 'User deleted successfully' };
      } catch (e) {
        console.error(e);
        return fail(500, 'Error deleting user');
      }
    }

    if (user.roles.includes('admin')) {
      const formData = await request.formData();
      const id = (formData.get('id') as string).replace(/[^0-9]/g, '');

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
    }
  },
  editUser: async ({ request, cookies }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);

    if (!user) {
      return fail(403, 'Forbidden');
    }

    const allgroups = await getAllGroups("groups");

    if (!user.roles.includes('admin') && user.roles.some(role => allgroups.some(group => group === role))) {
      const formData = await request.formData();
      const id = (formData.get('id') as string).replace(/[^0-9]/g, '');
      const name = formData.get('name') as string;
      let phone_number = (formData.get('phone_number') as string).replace(/[^0-9+]/g, '');
      const groups = user.groups[0];
      const roles = `${user.groups[0]}-masked`;
      const userGroup = formData.get('userGroup') as string;
      const province = formData.get('province') as string;

      if (!id || !name || !phone_number) {
        return fail(400, 'User ID, name and phone number are required');
      }

      if (phone_number[0] !== '+') {
        if (phone_number.slice(0, 2) !== '90') {
          phone_number = '90' + phone_number;
        }
      } else {
        phone_number = phone_number.replace('+', '');
      }

      try {
        const userFromSameGroup = await sql`SELECT id FROM users WHERE id = ${id} AND groups LIKE ${'%' + user.groups[0] + '%'}`;
        if (userFromSameGroup.length === 0) {
          return fail(403, 'Forbidden');
        }

        await sql`UPDATE users SET name = ${name}, phone_number = ${phone_number}, groups = ${groups}, roles = ${roles}, user_group = ${userGroup}, province = ${province} WHERE id = ${id}`;
        return { success: true, message: 'User updated successfully' };
      } catch (e) {
        console.error(e);
        return fail(500, 'Error updating user');
      }
    }

    if (user.roles.includes('admin')) {
      const formData = await request.formData();
      const id = (formData.get('id') as string).replace(/[^0-9]/g, '');
      const name = formData.get('name') as string;
      let phone_number = (formData.get('phone_number') as string).replace(/[^0-9+]/g, '');
      const groups = (formData.get('groups') as string).replace(/[^a-zA-Z0-9,]/g, '') || '';
      const roles = (formData.get('roles') as string).replace(/[^a-zA-Z0-9,-]/g, '') || '';
      const userGroup = formData.get('userGroup') as string;
      const province = formData.get('province') as string;

      if (!id || !name || !phone_number) {
        return fail(400, 'User ID, name and phone number are required');
      }

      if (phone_number[0] !== '+') {
        if (phone_number.slice(0, 2) !== '90') {
          phone_number = '90' + phone_number;
        }
      } else {
        phone_number = phone_number.replace('+', '');
      }

      try {
        await sql`UPDATE users SET name = ${name}, phone_number = ${phone_number}, groups = ${groups}, roles = ${roles}, user_group = ${userGroup}, province = ${province} WHERE id = ${id}`;
        return { success: true, message: 'User updated successfully' };
      } catch (e) {
        console.error(e);
        return fail(500, 'Error updating user');
      }
    }
  },
  toggleUser: async ({ request, cookies }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);

    if (!user) {
      return fail(403, 'Forbidden');
    }

    const allgroups = await getAllGroups("groups");

    if (!user.roles.includes('admin') && user.roles.some(role => allgroups.some(group => group === role))) {
      const formData = await request.formData();
      const id = (formData.get('id') as string).replace(/[^0-9]/g, '');
      const state = formData.get('state'); // "on" or null

      let active = false;

      if (state === 'on') {
        active = true;
      }

      if (!id) {
        return fail(400, 'User ID is required');
      }

      try {
        const userFromSameGroup = await sql`SELECT id FROM users WHERE id = ${id} AND groups LIKE ${'%' + user.groups[0] + '%'}`;
        if (userFromSameGroup.length === 0) {
          return fail(403, 'Forbidden');
        }

        await sql`UPDATE users SET active = ${active} WHERE id = ${id}`;
        return { success: true, message: 'User state updated successfully' };
      } catch (e) {
        console.error(e);
        return fail(500, 'Error updating user state');
      }
    }

    if (user.roles.includes('admin')) {
      const formData = await request.formData();
      const id = (formData.get('id') as string).replace(/[^0-9]/g, '');
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
  }
};
