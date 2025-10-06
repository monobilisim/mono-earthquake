import type { PageServerLoad, Actions } from './$types';
import sql, { getUser } from '$lib/db';
import { redirect, fail } from '@sveltejs/kit';
import { stripNonAlnumAscii } from '$lib/utils';

type Group = {
  id: number;
  name: string;
  polls: string[];
  active: boolean;
};

export const load: PageServerLoad = async ({ cookies }) => {
  let groups: Group[] = [];

  const session = cookies.get('session') || null;

  if (!session) {
    throw redirect(303, '/');
  }

  const user = await getUser(session);

  if (!user || !user.roles.includes('admin')) {
    throw redirect(303, '/');
  }

  try {
    const groupsResult = await sql`SELECT id, name, polls, active FROM groups`;

    groups = groupsResult.map((row: Record<string, string>) => ({
      id: row.id,
      name: row.name,
      polls: row.polls ? row.polls.split(',') : [],
      active: row.active
    }));
  } catch (e) {
    console.error(e);
  }

  return { groups };
};

export const actions: Actions = {
  addGroup: async ({ cookies, request }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);

    if (!user || !user.roles.includes('admin')) {
      return fail(401, 'Unauthorized');
    }

    const formData = await request.formData();
    const name = formData
      .get('name')
      ?.toString()
      .trim()
      .replace(/[^A-Za-z0-9]/g, '');
    const polls = formData
      .get('polls')
      ?.toString()
      .trim()
      .replace(/[^A-Za-z0-9,]/g, '');

    if (!name) {
      return fail(400, 'Tenant name is required');
    }

    if (!polls) {
      return fail(400, 'At least one poll is required');
    }

    try {
      await sql`INSERT INTO groups (name, polls) VALUES (${name}, ${polls})`;
      return { success: true, message: 'Group added successfully' };
    } catch (e) {
      console.error(e);
      return fail(500, 'Database error');
    }
  },
  deleteGroup: async ({ cookies, request }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);

    if (!user || !user.roles.includes('admin')) {
      return fail(401, 'Unauthorized');
    }

    const formData = await request.formData();
    const id = stripNonAlnumAscii(formData.get('id')?.toString().trim() || '');

    if (!id) {
      return fail(400, 'Tenant ID is required');
    }

    try {
      await sql`DELETE FROM groups WHERE id = ${id}`;
      return { success: true, message: 'Group deleted successfully' };
    } catch (e) {
      console.error(e);
      return fail(500, 'Database error');
    }
  },
  toggleGroup: async ({ cookies, request }) => {
    const session = cookies.get('session') || null;

    if (!session) {
      return fail(401, 'Unauthorized');
    }

    const user = await getUser(session);

    if (!user || !user.roles.includes('admin')) {
      return fail(401, 'Unauthorized');
    }

    const formData = await request.formData();
    const id = formData
      .get('id')
      ?.toString()
      .trim()
      .replace(/[^A-Za-z0-9]/g, '');
    const state = formData
      .get('state')
      ?.toString()
      .trim()
      .replace(/[^A-Za-z0-9]/g, ''); // 'on' or 'off'

    let active = 0;

    if (state == 'on') {
      active = 1;
    }

    if (!id) {
      return fail(400, 'Tenant ID is required');
    }

    try {
      await sql`UPDATE groups SET active = ${active} WHERE id = ${id}`;
      return { success: true, message: 'Group state updated successfully' };
    } catch (e) {
      console.error(e);
      return fail(500, 'Database error');
    }
  }
};
