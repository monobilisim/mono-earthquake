<script lang="ts">
	import { Input } from '$lib/components/ui/input/index';
	import { Button } from '$lib/components/ui/button/index';
	import * as Card from '$lib/components/ui/card/index';
	import * as Table from '$lib/components/ui/table/index';
	import * as Dialog from '$lib/components/ui/dialog/index';

	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';

	import Pencil from '@lucide/svelte/icons/pencil';
	import PencilOff from '@lucide/svelte/icons/pencil-off';
	import Save from '@lucide/svelte/icons/save';

	let { data } = $props();
	const users = data?.users ?? [];

	let newUser: boolean = $state(false);
	let newUserName: string = $state('');
	let newUserPhoneNumber: string = $state('');
	let newUserRoles: string = $state('');
	let newUserGroups: string = $state('');

	async function newUserAdd() {
		const formData = new FormData();
		formData.append('name', newUserName);
		formData.append('phone_number', newUserPhoneNumber);
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

	let editUser: number = $state(0);
	let editUserState: boolean = $state(false);

	function seteditUser(id: number) {
		editUser = id;
		editUserState = <any>users.find((g) => g.id === id)?.active;
	}
</script>

<div class="h-full w-full p-4">
	<Card.Root>
		<Card.Header class="flex items-center justify-between">
			<Card.Title>Users</Card.Title>
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
		</Card.Header>
		<Card.Content>
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head class="w-16">ID</Table.Head>
						<Table.Head class="w-32">Name</Table.Head>
						<Table.Head class="w-32">Phone Number</Table.Head>
						<Table.Head class="w-64">Roles</Table.Head>
						<Table.Head class="w-64">Group</Table.Head>
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
									{#if editUser === user.id}
										<div class="flex items-center gap-2">
											<div>{editUserState ? 'Active' : 'Passive'}</div>
											<form
												action="?/toggleUser"
												method="POST"
												use:enhance={() => {
													editUser = 0;
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
												<Input type="checkbox" name="state" bind:checked={editUserState} />
												<Button variant="ghost" class="p-0!" type="submit">
													<Save class="h-4 w-4" />
												</Button>
												<Button variant="ghost" class="p-0!" onclick={() => (editUser = 0)}>
													<PencilOff class="h-4 w-4" />
												</Button>
											</form>
										</div>
									{:else}
										<div class="flex items-center gap-2">
											<div>{user.active ? 'Active' : 'Passive'}</div>
											<Button
												variant="ghost"
												class="p-0!"
												onclick={() => {
													seteditUser(user.id);
												}}
											>
												<Pencil class="h-4 w-4" />
											</Button>
										</div>
									{/if}

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
							<Table.Cell
								><Input
									name="roles"
									placeholder="admin,group-masked"
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
								/></Table.Cell
							>
							<Table.Cell
								><Input
									name="groups"
									placeholder="group"
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
								/></Table.Cell
							>
						</Table.Row>
					{/if}
				</Table.Body>
			</Table.Root>
		</Card.Content>
	</Card.Root>
</div>
