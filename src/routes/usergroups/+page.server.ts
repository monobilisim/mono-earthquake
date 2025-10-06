import type { PageServerLoad, Actions } from './$types';
import sql, { getUser } from '$lib/db';
import { redirect, fail } from '@sveltejs/kit';
import { stripNonAlnumAscii } from '$lib/utils';

import type { UserGroup } from '$lib/types';

type Tenant = {
  name: string;
};

export const load: PageServerLoad = async ({ cookies }) => {
  let userGroups: UserGroup[] = [];
  let tenants: Tenant[] = [];

  const session = cookies.get('session') || null;

  if (!session) {
    throw redirect(303, '/');
  }

  const user = await getUser(session);

  if (!user || !user.roles.includes('admin')) {
    throw redirect(303, '/');
  }

  try {
    const userGroupsResult = await sql`SELECT id, name, tenant FROM user_groups`;

    const tenantsResult = await sql`SELECT name FROM groups`;

    tenants = tenantsResult.map((row: Record<string, string>) => row.name);

    userGroups = userGroupsResult.map((row: Record<string, string>) => ({
      id: row.id,
      name: row.name,
      tenant: row.tenant
    }));
  } catch (e) {
    console.error(e);
  }

  return { userGroups, tenants };
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
    const name = formData.get('name')?.toString().trim();
    const tenant = formData.get('tenant')?.toString().trim();

    if (!name) {
      return fail(400, 'Group name is required');
    }

    if (!tenant) {
      return fail(400, 'Tenant name is required');
    }

    try {
      await sql`INSERT INTO user_groups (name, tenant) VALUES (${name}, ${tenant})`;
      return { success: true, message: 'UserGroup added successfully' };
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
      return fail(400, 'Group ID is required');
    }

    try {
      await sql`DELETE FROM user_groups WHERE id = ${id}`;
      return { success: true, message: 'UserGroup deleted successfully' };
    } catch (e) {
      console.error(e);
      return fail(500, 'Database error');
    }
  }
};
