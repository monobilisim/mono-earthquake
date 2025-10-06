<script lang="ts">
	import { Input } from '$lib/components/ui/input/index';
	import { Button } from '$lib/components/ui/button/index';
	import * as Card from '$lib/components/ui/card/index';
	import * as Table from '$lib/components/ui/table/index';
	import * as Dialog from '$lib/components/ui/dialog/index';
	import * as Select from '$lib/components/ui/select/index';

	import type { ActionResult } from '@sveltejs/kit';

	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	let { data } = $props();
	let users = $state(data?.users ?? []);
	const groups = data?.groups ?? [];
	const userGroups = $state(data?.userGroups ?? []);

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
		formData.append('userGroup', newUserUserGroup);

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

	let userToggleState: Record<string, boolean> = $state(
		// svelte-ignore state_referenced_locally
		Object.fromEntries(users.map((u) => [u.id, u.active]))
	);

	let rolesMultiSelectEnabled: boolean = $state(true);
	let newUserRolesMulti: string[] = $state([]);

	let tenantsMultiSelectEnabled: boolean = $state(true);

	let toggleFormState: Record<string, HTMLFormElement> = $state(
		// svelte-ignore state_referenced_locally
		Object.fromEntries(users.map((u) => [u.id]))
	);

	let filters = $state({
		name: '',
		phone_number: '',
		roles: '',
		groups: '',
		active: '',
		user_group: ''
	});

	const originalUsers = data.users ?? [];

	const urlParams = new URLSearchParams(page.url.search);

	let filteringApplied = $derived(users.length !== originalUsers.length);

	if (
		urlParams.get('name') !== '' ||
		urlParams.get('phone_number') !== '' ||
		urlParams.get('roles') !== '' ||
		urlParams.get('groups') !== '' ||
		urlParams.get('active') !== '' ||
		urlParams.get('user_group') !== ''
	) {
		filters = {
			name: urlParams.get('name') ?? '',
			phone_number: urlParams.get('phone_number') ?? '',
			roles: urlParams.get('roles') ?? '',
			groups: urlParams.get('groups') ?? '',
			active: urlParams.get('active') ?? '',
			user_group: urlParams.get('user_group') ?? ''
		};

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

			if (filters.user_group !== '' && !(user.user_group === filters.user_group)) {
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
			active: '',
			user_group: ''
		};

		const url = new URL(page.url);
		url.search = '';
		goto(url.toString(), { replaceState: true, noScroll: true });

		users = originalUsers;
	}

	let usersEditState = $state<Record<string, boolean>>(
		// svelte-ignore state_referenced_locally
		Object.fromEntries(users.map((u) => [u.id, false]))
	);

	type AppUser = {
		id: number;
		name: string;
		phone_number: string;
		groups: string[];
		user_group: string;
		roles: string[];
		active: boolean;
	};

	interface EditableAppUser extends AppUser {
		rolesMultiSelect: boolean;
		rolesMulti: string[];
		tenantMultiSelect: boolean;
		tenantMulti: string[];
	}

	let usersEditData = $state<Record<string, EditableAppUser>>(
		Object.fromEntries(
			// svelte-ignore state_referenced_locally
			users.map((u) => [
				u.id,
				{
					...u,
					rolesMultiSelect: true,
					rolesMulti: u.roles,
					tenantMultiSelect: true,
					tenantMulti: u.groups
				}
			])
		)
	);

	let usersEditFormState: Record<string, HTMLFormElement> = $derived(
		Object.fromEntries(users.map((u) => [u.id]))
	);

	let newUserUserGroup: string = $state('');
</script>

<div class="h-full w-full p-4">
	<Card.Root class="h-[98vh] overflow-y-auto">
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
						<Dialog.Description>
							Filter users by name, phone number, roles, tenant or status.
						</Dialog.Description>
						<div class="grid grid-cols-2 grid-rows-3 gap-2">
							<label>
								Name
								<Input bind:value={filters.name} />
							</label>
							<label>
								Phone Number
								<Input bind:value={filters.phone_number} />
							</label>
							<label>
								Roles
								<Input bind:value={filters.roles} />
							</label>
							<label>
								Tenant
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

							<label>
								Group
								<Select.Root
									type="single"
									bind:value={filters.user_group}
									disabled={filters.groups == ''}
								>
									<Select.Trigger>
										{filters.groups
											? filters.user_group != ''
												? filters.user_group
												: 'Select a group'
											: 'Select a tenant'}
									</Select.Trigger>
									<Select.Content>
										{#each userGroups
											.filter((ug) => {
												if (ug.tenant === (Array.isArray(filters.groups) ? filters.groups[0] : filters.groups)) {
													return true;
												}
											})
											.flatMap((ug) => [...ug.userGroups]) as group}
											<Select.Item value={group} label={group} />
										{/each}
										<Select.Item value="" label="None" />
									</Select.Content>
								</Select.Root>
							</label>

							<label>
								Status

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
						</div>

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
										filters.user_group !== '' &&
											url.searchParams.set('user_group', filters.user_group);
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
							class="bg-green-500 text-white hover:bg-green-600 focus:ring-green-600"
							onclick={() => {
								newUser = false;
								newUserAdd();
							}}>Save</Button
						>
						<Button
							class="bg-red-500 text-white hover:bg-red-600 focus:ring-red-600"
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
						<Table.Head class="w-128"></Table.Head>
						<Table.Head></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
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
									placeholder="5554443322"
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
							<Table.Cell>
								<Select.Root type="single" bind:value={newUserUserGroup} name="userGroup">
									<Select.Trigger>
										{newUserGroups
											? newUserUserGroup
												? newUserUserGroup
												: 'Select a group'
											: 'Select a tenant'}
									</Select.Trigger>
									<Select.Content>
										<Select.Item value={''} label={'Empty'} />
										{#each userGroups
											.filter((ug) => {
												if (ug.tenant === (Array.isArray(newUserGroups) ? newUserGroups[0] : newUserGroups)) {
													return true;
												}
											})
											.flatMap((ug) => [...ug.userGroups]) as group}
											<Select.Item value={group} label={group} />
										{/each}
									</Select.Content>
								</Select.Root>
							</Table.Cell>
						</Table.Row>
					{/if}

					{#each users as user}
						{#if usersEditState[user.id] == false}
							<Table.Row>
								<Table.Cell class="font-medium">{user.id}</Table.Cell>
								<Table.Cell>{user.name}</Table.Cell>
								<Table.Cell>{user.phone_number}</Table.Cell>
								<Table.Cell>{user.roles}</Table.Cell>
								<Table.Cell>{user.groups}</Table.Cell>
								<Table.Cell
									><div class="flex items-center justify-between">
										<div class={'mr-8 flex ' + (user.active ? 'gap-4' : 'gap-2')}>
											<div>
												{user.active ? 'Active' : 'Passive'}
											</div>
											<form
												bind:this={toggleFormState[user.id]}
												action="?/toggleUser"
												method="POST"
												use:enhance={() => {
													return async ({ result }) => {
														if (result.type === 'failure') {
															const error = String(result.data ?? 'Error while toggling the user');
															toast.error(error);
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
									</div>
								</Table.Cell>
								<Table.Cell>
									<Button onclick={() => (usersEditState[user.id] = true)}>Edit User</Button>
								</Table.Cell>
								<Table.Cell>
									<Dialog.Root>
										<Dialog.Trigger>
											<Button variant="ghost" class="bg-red-500 text-white hover:bg-red-600">
												Delete User
											</Button>
										</Dialog.Trigger>
										<Dialog.Content class="h-64 w-64">
											<Dialog.Title>Are you sure?</Dialog.Title>

											<Dialog.Description>
												The user ({users.find((u) => u.id === user.id)?.name ?? ''}) will be
												deleted.
											</Dialog.Description>
											<div class="flex flex-col text-center">
												<form
													action="?/deleteUser"
													method="POST"
													use:enhance={() => {
														return async ({ result }: { result: ActionResult }) => {
															if (result.type === 'failure') {
																const error = String(result.data ?? 'Error while deleting user');
																toast.error(error);
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
								</Table.Cell>
							</Table.Row>
						{/if}

						{#if usersEditState[user.id] == true}
							<form
								bind:this={usersEditFormState[user.id]}
								action="?/editUser"
								method="POST"
								use:enhance={() => {
									return ({ result }) => {
										if (result.type === 'failure') {
											const error = String(result.data ?? 'Error while deleting user');
											toast.error(error);
										}

										if (result.type === 'success') {
											window.location.reload();
										}
									};
								}}
							>
								<Input type="hidden" name="id" value={user.id} />
								<Input type="hidden" name="name" value={usersEditData[user.id].name} />
								<Input
									type="hidden"
									name="phone_number"
									value={usersEditData[user.id].phone_number}
								/>
								<Input
									type="hidden"
									name="roles"
									value={Array.isArray(usersEditData[user.id].rolesMulti)
										? usersEditData[user.id].rolesMulti.join(',')
										: usersEditData[user.id].rolesMulti}
								/>
								<Input type="hidden" name="groups" value={usersEditData[user.id].tenantMulti[0]} />
								<Input type="hidden" name="userGroup" value={usersEditData[user.id].user_group} />
							</form>

							<Table.Row>
								<Table.Cell></Table.Cell>
								<Table.Cell
									><Input
										name="name"
										placeholder="Name Surname"
										bind:value={usersEditData[user.id].name}
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

											if (usersEditData[user.id].name.length < 64) {
												usersEditData[user.id].name += e.data;
											}
										}}
									/></Table.Cell
								>
								<Table.Cell
									><Input
										name="phone_number"
										placeholder="5554443322"
										bind:value={usersEditData[user.id].phone_number}
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

											if (
												e.data &&
												/[0-9+]/.test(e.data) &&
												usersEditData[user.id].phone_number.length < 20
											) {
												usersEditData[user.id].phone_number += e.data;
											}
										}}
									/></Table.Cell
								>
								<Table.Cell>
									{#if usersEditData[user.id].rolesMultiSelect}
										<Select.Root
											type="multiple"
											bind:value={usersEditData[user.id].rolesMulti}
											name="roles"
										>
											<Select.Trigger
												>{usersEditData[user.id].rolesMulti.length > 0
													? usersEditData[user.id].rolesMulti.join(',')
													: 'Select roles'}
											</Select.Trigger>

											<Select.Content>
												<Select.Item value="admin" label="admin" />
												<Select.Item value="masked" label="masked" />
												{#each user.roles as role (role)}
													{#if role != 'admin' && role != 'masked'}
														<Select.Item value={role} label={role} />
													{/if}
												{/each}
												<Select.Item
													value=""
													label="custom role"
													onclick={() =>
														(usersEditData[user.id].rolesMultiSelect =
															!usersEditData[user.id].rolesMultiSelect)}
												/>
											</Select.Content>
										</Select.Root>
									{:else}
										<Input
											name="roles"
											placeholder="tenant,tenant-masked"
											bind:value={usersEditData[user.id].rolesMulti}
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

												if (
													e.data &&
													/[a-zA-Z0-9,-]/.test(e.data) &&
													usersEditData[user.id].rolesMulti.length < 255
												) {
													usersEditData[user.id].rolesMulti += e.data;
												}
											}}
										/>
									{/if}
								</Table.Cell>
								<Table.Cell>
									{#if usersEditData[user.id].tenantMultiSelect}
										<Select.Root
											type="single"
											bind:value={usersEditData[user.id].tenantMulti[0]}
											name="groups"
										>
											<Select.Trigger
												>{usersEditData[user.id].tenantMulti[0] != ''
													? usersEditData[user.id].tenantMulti[0]
													: 'Select a tenant'}
											</Select.Trigger>
											<Select.Content>
												{#each groups as group}
													<Select.Item value={group} label={group} />
												{/each}
												<Select.Item
													value=""
													label="custom tenant"
													onclick={() =>
														(usersEditData[user.id].tenantMultiSelect =
															!usersEditData[user.id].tenantMultiSelect)}
												/>
											</Select.Content>
										</Select.Root>
									{:else}
										<Input
											name="groups"
											placeholder="tenant"
											bind:value={usersEditData[user.id].tenantMulti[0]}
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

												if (
													e.data &&
													/[a-zA-Z0-9,]/.test(e.data) &&
													usersEditData[user.id].tenantMulti[0].length < 32
												) {
													usersEditData[user.id].tenantMulti[0] += e.data;
												}
											}}
										/>
									{/if}
								</Table.Cell>
								<Table.Cell>
									<Select.Root
										type="single"
										bind:value={usersEditData[user.id].user_group}
										name="userGroup"
									>
										<Select.Trigger>
											{usersEditData[user.id].user_group ??
												(usersEditData[user.id].user_group === ''
													? 'Select a group'
													: 'Select a tenant')}
										</Select.Trigger>
										<Select.Content>
											{#each userGroups
												.filter((ug) => {
													if (ug.tenant === (Array.isArray(usersEditData[user.id].tenantMulti) ? usersEditData[user.id].tenantMulti[0] : usersEditData[user.id].tenantMulti)) {
														return true;
													}
												})
												.flatMap((ug) => [...ug.userGroups]) as group}
												<Select.Item value={group} label={group} />
											{/each}
											<Select.Item value={''} label={'Empty'} />
										</Select.Content>
									</Select.Root>
								</Table.Cell>
								<Table.Cell>
									<Button
										class="bg-green-500 text-white hover:bg-green-600"
										onclick={() => usersEditFormState[user.id]?.requestSubmit()}>Save</Button
									>
								</Table.Cell>
								<Table.Cell>
									<Button
										class="bg-red-500  text-white hover:bg-red-600"
										onclick={() => (usersEditState[user.id] = false)}>Discard</Button
									>
								</Table.Cell>
							</Table.Row>
						{/if}
					{/each}
				</Table.Body>
			</Table.Root>
		</Card.Content>
	</Card.Root>
</div>
