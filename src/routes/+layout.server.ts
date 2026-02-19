import { getUser, type User } from '$lib/db';
import sql from '$lib/db';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ cookies }) => {
  let sessionActive: boolean = false;
  let user: User | null = null;

  type State = {
    sessionActive: boolean;
    user: User | null;
    tenants: string[];
  };

  let appState: State = {
    sessionActive: false,
    user: null,
    tenants: ["admin"]
  };

  const allGroups = await sql`SELECT name FROM groups`;
  allGroups.forEach((group: { name: string }) => {
    appState.tenants.push(group.name);
  });

  try {
    const session = cookies.get('session');

    if (session) {
      user = await getUser(session);
      appState.user = user;

      if (!user.name || user.name === '') {
        cookies.delete('session', { secure: true, sameSite: 'strict', httpOnly: true, path: '/' });

        appState.sessionActive = false;
        sessionActive = false;

        return { sessionActive, user, appState };
      }

      appState.sessionActive = true;
      sessionActive = true;

      return { sessionActive, user, appState };
    } else {
      appState.sessionActive = false;
      sessionActive = false;
      return { sessionActive, user, appState };
    }
  } catch (error) {
    appState.sessionActive = false;
    sessionActive = false;
    return { sessionActive, user, appState };
  }
};
