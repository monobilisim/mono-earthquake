<script lang="ts">
  import '../app.css';
  import favicon from '$lib/assets/favicon.svg';
  import { isPortrait } from '$lib/utils';
  import { Toaster } from '$lib/components/ui/sonner/index';
  import { ModeWatcher } from 'mode-watcher';
  let { children, data } = $props();
  // svelte-ignore state_referenced_locally
  const sessionActive = data?.sessionActive;
  // svelte-ignore state_referenced_locally
  const user = data?.user;
  // svelte-ignore state_referenced_locally
  const appState = data?.appState;
  const tenants = appState?.tenants || [];

  import SunIcon from '@lucide/svelte/icons/sun';
  import MoonIcon from '@lucide/svelte/icons/moon';
  import HomeIcon from '@lucide/svelte/icons/home';
  import UsersIcon from '@lucide/svelte/icons/users';
  import LayersIcon from '@lucide/svelte/icons/layers';
  import ActivityIcon from '@lucide/svelte/icons/activity';
  import MenuIcon from '@lucide/svelte/icons/menu';
  import * as Sidebar from '$lib/components/ui/sidebar/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { toggleMode } from 'mode-watcher';
  import { page } from '$app/state';

  const sidebarData = {
    navItems: [
      {
        title: 'Dashboard',
        url: '/',
        icon: HomeIcon
      },
      {
        title: 'Users',
        url: '/users',
        icon: UsersIcon,
        role: 'admin'
      },
      {
        title: 'Groups',
        url: '/usergroups',
        icon: UsersIcon,
        role: 'admin'
      },
      {
        title: 'Tenants',
        url: '/tenants',
        icon: LayersIcon,
        role: 'admin'
      }
    ],
    branding: {
      name: 'Mono Afet',
      logo: ActivityIcon
    }
  };

  // Get current page to highlight active nav item
  const currentPath = $derived(page.url.pathname);

  let sidebarOpen: boolean = $state(true);

  let isInPortrait = $state(false);

  $effect(() => {
    isInPortrait = isPortrait(window);

    if (isInPortrait) {
      sidebarOpen = false;
    }
  });

  let userIsAdminOnATenant: boolean = $state(false);
  // masked users can't be admins
  if (user && !user?.roles.includes('masked')) {
    userIsAdminOnATenant = user?.roles.some((role: string) =>
      tenants.some((tenant: string) => role === tenant)
    );
  }
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>Mono Afet</title>
</svelte:head>

<Toaster />
<ModeWatcher />

{#if !sidebarOpen}
  <div class="absolute top-4 left-4 z-50">
    <Button variant="ghost" onclick={() => (sidebarOpen = !sidebarOpen)} size="icon">
      <MenuIcon class="h-4 w-4" />
    </Button>
  </div>
{/if}

<main class="h-screen w-screen overflow-hidden">
  {#if sessionActive && isInPortrait}
    <div class="p-4">
      {#if sidebarOpen}
        <Button variant="ghost" onclick={() => (sidebarOpen = !sidebarOpen)} size="icon">
          <MenuIcon class="h-4 w-4" />
        </Button>

        {#each sidebarData.navItems as item}
          {#if item.role == 'admin' && !userIsAdminOnATenant}
            <!-- Do not render admin routes if user is not admin -->
          {:else}
            <Sidebar.MenuItem class="*:decoration-none">
              <Sidebar.MenuButton isActive={currentPath === item.url} class="w-full py-0!">
                <a href={item.url} class="flex w-full items-center gap-2 py-4">
                  <item.icon class="h-4 w-4" />
                  <span>{item.title}</span>
                </a>
              </Sidebar.MenuButton>
            </Sidebar.MenuItem>
          {/if}
        {/each}
      {/if}
    </div>
  {/if}

  {#if sessionActive && !isInPortrait}
    <Sidebar.Provider open={sidebarOpen} onOpenChange={() => (sidebarOpen = !sidebarOpen)}>
      <Sidebar.Root>
        <div class="flex h-12 items-center justify-between border-b px-3">
          <div class="flex items-center gap-2">
            <sidebarData.branding.logo class="h-5 w-5 text-primary" />
            <span class="text-sm font-semibold group-data-[collapsible=icon]:hidden">
              {sidebarData.branding.name}
            </span>
          </div>
          <div class="flex gap-2">
            <Button onclick={toggleMode} variant="ghost" size="icon">
              <SunIcon
                class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all! dark:scale-0 dark:-rotate-90"
              />
              <MoonIcon
                class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all! dark:scale-100 dark:rotate-0"
              />
              <span class="sr-only">Toggle theme</span>
            </Button>

            <div>
              <Button variant="ghost" onclick={() => (sidebarOpen = !sidebarOpen)} size="icon">
                <MenuIcon class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        <Sidebar.Content class="gap-0">
          <Sidebar.Group>
            <!-- <Sidebar.GroupLabel>Navigation</Sidebar.GroupLabel> -->
            <Sidebar.GroupContent>
              <Sidebar.Menu>
                {#each sidebarData.navItems as item}
                  {#if item.role == 'admin' && !userIsAdminOnATenant}
                    <!-- Do not render admin routes if user is not admin -->
                  {:else}
                    <Sidebar.MenuItem>
                      <Sidebar.MenuButton isActive={currentPath === item.url} class="w-full py-0!">
                        <a href={item.url} class="flex w-full items-center gap-2">
                          <item.icon class="h-4 w-4" />
                          <span>{item.title}</span>
                        </a>
                      </Sidebar.MenuButton>
                    </Sidebar.MenuItem>
                  {/if}
                {/each}
              </Sidebar.Menu>
            </Sidebar.GroupContent>
          </Sidebar.Group>
        </Sidebar.Content>

        <Sidebar.Rail />
      </Sidebar.Root>

      {@render children?.()}
    </Sidebar.Provider>
  {:else}
    {@render children?.()}
  {/if}
</main>
