<script lang="ts">
	import { Input } from '$lib/components/ui/input/index';
	import { Button } from '$lib/components/ui/button/index';
	import * as Card from '$lib/components/ui/card/index';
	import * as Table from '$lib/components/ui/table/index';
	import * as Dialog from '$lib/components/ui/dialog/index';
	import * as Select from '$lib/components/ui/select/index';

	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	let { data } = $props();
	let users = $state(data?.users ?? []);
	const groups = data?.groups ?? [];

	let newUser: boolean = $state(false);
	let newUserName: string = $state('');
	let newUserPhoneNumber: string = $state('');
	let newUserRoles: string = $state('');
	let newUserGroups: string = $state('');

	async function newUserAdd() {
		const formData = new FormData();
		formData.append('name', newUserName);
		formData.append('phone_number', newUserPhoneNumber);
		if (rolesMultiSelectEnabled && newUserRolesMulti.length > 0) {
			newUserRoles = newUserRolesMulti.join(',');
		}
		formData.append('roles', newUserRoles);
		formData.append('groups', newUserGroups);

		const response = await fetch(`/users?/addUser`, {
			method: 'POST',
			body: formData
		});

		if (!response.ok) {
			toast.error('Error while creating user');
		}

		if (response.ok) {
			const data = await response.json();

			if (data?.type === 'failure') {
				toast.error(JSON.parse(data?.data)[0] ?? 'Error while creating user');
			}

			if (data?.type === 'success') {
				toast.success('User created successfully');
				window.location.reload();
			}
		}
	}

	let userToggleState: Record<string, boolean> = $derived(
		Object.fromEntries(users.map((u) => [u.id, u.active]))
	);

	let rolesMultiSelectEnabled: boolean = $state(true);
	let newUserRolesMulti: string[] = $state([]);

	let tenantsMultiSelectEnabled: boolean = $state(true);

	let toggleFormState: Record<string, HTMLFormElement> = $derived(
		Object.fromEntries(users.map((u) => [u.id]))
	);

	let filters = $state({
		name: '',
		phone_number: '',
		roles: '',
		groups: '',
		active: ''
	});

	const originalUsers = data.users ?? [];

	const urlParams = new URLSearchParams(page.url.search);

	let filteringApplied = $derived(users.length !== originalUsers.length);

	if (
		urlParams.get('name') !== '' ||
		urlParams.get('phone_number') !== '' ||
		urlParams.get('roles') !== '' ||
		urlParams.get('groups') !== '' ||
		urlParams.get('active') !== ''
	) {
		filters = {
			name: urlParams.get('name') ?? '',
			phone_number: urlParams.get('phone_number') ?? '',
			roles: urlParams.get('roles') ?? '',
			groups: urlParams.get('groups') ?? '',
			active: urlParams.get('active') ?? ''
		};

		console.log(filters);

		applyFilters();
	}

	function applyFilters() {
		const filteredUsers = originalUsers.filter((user) => {
			if (filters.name !== '' && !user.name.toLowerCase().includes(filters.name.toLowerCase())) {
				return false;
			}

			if (filters.phone_number !== '' && !user.phone_number.includes(filters.phone_number)) {
				return false;
			}

			if (filters.roles !== '' && !user.roles.includes(filters.roles)) {
				return false;
			}

			if (filters.groups !== '' && !user.groups.includes(filters.groups)) {
				return false;
			}

			if (filters.active !== '' && !(user.active.toString() === filters.active)) {
				return false;
			}

			return true;
		});

		users = filteredUsers;
	}

	function clearFilters() {
		filters = {
			name: '',
			phone_number: '',
			roles: '',
			groups: '',
			active: ''
		};

		const url = new URL(page.url);
		url.search = '';
		goto(url.toString(), { replaceState: true, noScroll: true });

		users = originalUsers;
	}
</script>

<div class="h-full w-full p-4">
	<Card.Root>
		<Card.Header class="flex items-center justify-between">
			{#if filteringApplied}
				<div class="flex gap-2">
					<Card.Title>Users</Card.Title>
					<p class="text-sm text-slate-500">(filtered)</p>
				</div>
			{:else}
				<Card.Title>Users</Card.Title>
			{/if}
			<div class="flex gap-1">
				<Dialog.Root>
					<Dialog.Trigger>
						<Button>Filters</Button>
					</Dialog.Trigger>
					<Dialog.Content>
						<Dialog.Title>Filters</Dialog.Title>
						<Dialog.Description
							>Filter users by name, phone number, roles, tenant or status.</Dialog.Description
						>
						<div class="grid grid-cols-2 grid-rows-2 gap-2">
							<label
								>Name
								<Input bind:value={filters.name} />
							</label>
							<label
								>Phone Number
								<Input bind:value={filters.phone_number} />
							</label>
							<label
								>Roles
								<Input bind:value={filters.roles} />
							</label>
							<label
								>Tenant
								<Select.Root type="single" bind:value={filters.groups}>
									<Select.Trigger>
										{filters.groups != '' ? filters.groups : 'Select a tenant'}
									</Select.Trigger>
									<Select.Content>
										{#each groups as group}
											<Select.Item value={group} label={group} />
										{/each}
										<Select.Item value="" label="None" />
									</Select.Content>
								</Select.Root>
							</label>
						</div>
						<label
							>Status

							<Select.Root type="single" bind:value={filters.active}>
								<Select.Trigger
									>{filters.active != '' ? (filters.active == '1' ? 'Active' : 'Passive') : 'All'}
								</Select.Trigger>
								<Select.Content>
									<Select.Item value="1" label="Active" />
									<Select.Item value="0" label="Passive" />
									<Select.Item value="" label="All" />
								</Select.Content>
							</Select.Root>
						</label>
						<div class="flex justify-end gap-2">
							<Dialog.Close>
								<Button onclick={() => clearFilters()}>Clear filters</Button>
							</Dialog.Close>
							<Dialog.Close>
								<Button
									onclick={() => {
										const url = new URL(page.url);
										filters.name !== '' && url.searchParams.set('name', filters.name);
										filters.phone_number !== '' &&
											url.searchParams.set('phone_number', filters.phone_number);
										filters.roles !== '' && url.searchParams.set('roles', filters.roles);
										filters.groups !== '' && url.searchParams.set('groups', filters.groups);
										filters.active !== '' && url.searchParams.set('active', filters.active);
										goto(url.toString());
										applyFilters();
									}}>Apply filters</Button
								>
							</Dialog.Close>
						</div>
					</Dialog.Content>
				</Dialog.Root>

				{#if newUser}
					<div>
						<Button
							onclick={() => {
								newUser = false;
								newUserAdd();
							}}>Save</Button
						>
						<Button
							onclick={() => {
								newUser = false;
							}}>Cancel</Button
						>
					</div>
				{:else}
					<Button
						onclick={() => {
							newUser = true;
						}}>Add new user</Button
					>
				{/if}
			</div>
		</Card.Header>
		<Card.Content>
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head class="w-16">ID</Table.Head>
						<Table.Head class="w-32">Name</Table.Head>
						<Table.Head class="w-32">Phone Number</Table.Head>
						<Table.Head class="w-64">Roles</Table.Head>
						<Table.Head class="w-64">Tenant</Table.Head>
						<Table.Head class="w-128">Status</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each users as user}
						<Table.Row>
							<Table.Cell class="font-medium">{user.id}</Table.Cell>
							<Table.Cell>{user.name}</Table.Cell>
							<Table.Cell>{user.phone_number}</Table.Cell>
							<Table.Cell>{user.roles}</Table.Cell>
							<Table.Cell>{user.groups}</Table.Cell>
							<Table.Cell
								><div class="flex items-center justify-between">
									<div class="flex gap-2">
										<div>{user.active ? 'Active' : 'Passive'}</div>
										<form
											bind:this={toggleFormState[user.id]}
											action="?/toggleUser"
											method="POST"
											use:enhance={() => {
												return async ({ result }) => {
													if (result.type === 'failure') {
														toast.error(result.data);
													}

													if (result.type === 'success') {
														window.location.reload();
													}
												};
											}}
										>
											<Input type="hidden" name="id" value={user.id} />
											<Input
												type="checkbox"
												name="state"
												bind:checked={userToggleState[user.id]}
												onchange={() => {
													toggleFormState[user.id]?.requestSubmit();
												}}
											/>
										</form>
									</div>

									<Dialog.Root>
										<Dialog.Trigger>
											<Button variant="ghost" class="p-0! text-red-500">Delete User</Button>
										</Dialog.Trigger>
										<Dialog.Content class="h-64 w-64">
											<Dialog.Title>Are you sure?</Dialog.Title>

											<Dialog.Description>
												The user ({users.find((u) => u.id === user.id).name}) will be deleted.</Dialog.Description
											>
											<div class="flex flex-col text-center">
												<form
													action="?/deleteUser"
													method="POST"
													use:enhance={() => {
														return async ({ result }) => {
															if (result.type === 'failure') {
																toast.error(result.data);
															}

															if (result.type === 'success') {
																window.location.reload();
															}
														};
													}}
												>
													<Input type="hidden" name="id" value={user.id} />
													<Button variant="destructive" type="submit">Delete User</Button>
												</form>
											</div>
										</Dialog.Content>
									</Dialog.Root>
								</div></Table.Cell
							>
						</Table.Row>
					{/each}

					{#if newUser == true}
						<Table.Row>
							<Table.Cell></Table.Cell>
							<Table.Cell
								><Input
									name="name"
									placeholder="Name Surname"
									bind:value={newUserName}
									onbeforeinput={(e) => {
										const type = e.inputType;

										if (
											type === 'deleteContentBackward' ||
											type === 'deleteContentForward' ||
											type === 'insertLineBreak'
										) {
											return;
										}

										e.preventDefault();

										if (newUserName.length < 64) {
											newUserName += e.data;
										}
									}}
								/></Table.Cell
							>
							<Table.Cell
								><Input
									name="phone_number"
									placeholder="905554443322"
									bind:value={newUserPhoneNumber}
									onbeforeinput={(e) => {
										const type = e.inputType;

										if (
											type === 'deleteContentBackward' ||
											type === 'deleteContentForward' ||
											type === 'insertLineBreak'
										) {
											return;
										}

										e.preventDefault();

										if (e.data && /[0-9]/.test(e.data) && newUserPhoneNumber.length < 20) {
											newUserPhoneNumber += e.data;
										}
									}}
								/></Table.Cell
							>
							<Table.Cell>
								{#if rolesMultiSelectEnabled}
									<Select.Root type="multiple" bind:value={newUserRolesMulti} name="roles">
										<Select.Trigger
											>{newUserRolesMulti.length > 0
												? newUserRolesMulti.join(',')
												: 'Select roles'}</Select.Trigger
										>

										<Select.Content>
											<Select.Item value="admin" label="admin" />
											<Select.Item value="masked" label="masked" />
											<Select.Item
												value=""
												label="custom role"
												onclick={() => (rolesMultiSelectEnabled = !rolesMultiSelectEnabled)}
											/>
										</Select.Content>
									</Select.Root>
								{:else}
									<Input
										name="roles"
										placeholder="tenant,tenant-masked"
										bind:value={newUserRoles}
										onbeforeinput={(e) => {
											const type = e.inputType;

											if (
												type === 'deleteContentBackward' ||
												type === 'deleteContentForward' ||
												type === 'insertLineBreak'
											) {
												return;
											}

											e.preventDefault();

											if (e.data && /[a-zA-Z0-9,-]/.test(e.data) && newUserRoles.length < 255) {
												newUserRoles += e.data;
											}
										}}
									/>
								{/if}
							</Table.Cell>
							<Table.Cell>
								{#if tenantsMultiSelectEnabled}
									<Select.Root type="single" bind:value={newUserGroups} name="groups">
										<Select.Trigger
											>{newUserGroups != '' ? newUserGroups : 'Select a tenant'}</Select.Trigger
										>
										<Select.Content>
											{#each groups as group}
												<Select.Item value={group} label={group} />
											{/each}
											<Select.Item
												value=""
												label="custom tenant"
												onclick={() => (tenantsMultiSelectEnabled = !tenantsMultiSelectEnabled)}
											/>
										</Select.Content>
									</Select.Root>
								{:else}
									<Input
										name="groups"
										placeholder="tenant"
										bind:value={newUserGroups}
										onbeforeinput={(e) => {
											const type = e.inputType;

											if (
												type === 'deleteContentBackward' ||
												type === 'deleteContentForward' ||
												type === 'insertLineBreak'
											) {
												return;
											}

											e.preventDefault();

											if (e.data && /[a-zA-Z0-9,]/.test(e.data) && newUserGroups.length < 32) {
												newUserGroups += e.data;
											}
										}}
									/>
								{/if}
							</Table.Cell>
						</Table.Row>
					{/if}
				</Table.Body>
			</Table.Root>
		</Card.Content>
	</Card.Root>
</div>
