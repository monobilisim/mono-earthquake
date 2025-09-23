<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	import { Toaster } from '$lib/components/ui/sonner/index';
	import { ModeWatcher } from 'mode-watcher';
	let { children, data } = $props();

	const sessionActive = data?.sessionActive;
	const user = data?.user;

	import SunIcon from '@lucide/svelte/icons/sun';
	import MoonIcon from '@lucide/svelte/icons/moon';
	import HomeIcon from '@lucide/svelte/icons/home';
	import UsersIcon from '@lucide/svelte/icons/users';
	import LayersIcon from '@lucide/svelte/icons/layers';
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import PanelLeftOpen from '@lucide/svelte/icons/panel-left-open';
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
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Mono Afet</title>
</svelte:head>

<Toaster />
<ModeWatcher />

<main class="h-screen w-screen overflow-hidden">
	{#if sessionActive}
		<Sidebar.Provider>
			<Sidebar.Root>
				<div class="flex h-12 items-center justify-between border-b px-3">
					<div class="flex items-center gap-2">
						<sidebarData.branding.logo class="h-5 w-5 text-primary" />
						<span class="text-sm font-semibold group-data-[collapsible=icon]:hidden">
							{sidebarData.branding.name}
						</span>
					</div>
					<Button onclick={toggleMode} variant="ghost" size="icon">
						<SunIcon
							class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 !transition-all dark:scale-0 dark:-rotate-90"
						/>
						<MoonIcon
							class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 !transition-all dark:scale-100 dark:rotate-0"
						/>
						<span class="sr-only">Toggle theme</span>
					</Button>
					<!-- <Sidebar.Trigger>
					<Button variant="ghost" size="icon" class="h-7 w-7">
						<PanelLeftOpen class="h-4 w-4" />
						<span class="sr-only">Toggle Sidebar</span>
					</Button>
				</Sidebar.Trigger> -->
				</div>

				<Sidebar.Content class="gap-0">
					<Sidebar.Group>
						<!-- <Sidebar.GroupLabel>Navigation</Sidebar.GroupLabel> -->
						<Sidebar.GroupContent>
							<Sidebar.Menu>
								{#each sidebarData.navItems as item}
									{#if item.role == 'admin' && !user.roles.includes(item.role)}
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
