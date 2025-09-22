<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import Input from '$lib/components/ui/input/input.svelte';
	import * as Card from '$lib/components/ui/card/index';
	import * as Table from '$lib/components/ui/table/index';
	import * as Dialog from '$lib/components/ui/dialog/index';

	import Pencil from '@lucide/svelte/icons/pencil';
	import Save from '@lucide/svelte/icons/save';
	import PencilOff from '@lucide/svelte/icons/pencil-off';
	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';

	let { data } = $props();

	const groups = data?.groups ?? [];

	$effect(() => {
		console.log('Groups data:', groups);
	});

	let newGroup: boolean = $state(false);
	let newGroupName: string = $state('');
	let newGroupPolls: string = $state('');

	async function newGroupAdd() {
		let formData = new FormData();
		formData.append('name', newGroupName);
		formData.append('polls', newGroupPolls);

		const response = await fetch('?/addGroup', {
			method: 'POST',
			body: formData
		});

		if (!response.ok) {
			toast.error('Failed to add new group');
		}

		if (response.ok) {
			const data = await response.json();
			if (data?.type === 'failure') {
				toast.error(JSON.parse(data.data)[0]);
			}

			if (data?.type === 'success') {
				toast.success('New group added successfully');
				window.location.reload();
			}
		}

		//window.location.reload();
	}

	// editing the active passive state of a group
	let editGroup: number = $state(0);
	let editGroupState: boolean = $state(false);

	function setEditGroup(id: number) {
		editGroup = id;
		editGroupState = <any>groups.find((g: Record<string, string>) => g.id === id)?.active;
	}
</script>

<div class="h-full w-full p-4">
	<Card.Root>
		<Card.Header class="flex items-center justify-between">
			<Card.Title>Groups</Card.Title>
			{#if newGroup}
				<div>
					<Button
						onclick={() => {
							newGroup = false;
							newGroupAdd();
						}}>Save</Button
					>
					<Button
						onclick={() => {
							newGroup = false;
						}}>Cancel</Button
					>
				</div>
			{:else}
				<Button
					onclick={() => {
						newGroup = true;
					}}>Add new group</Button
				>
			{/if}
		</Card.Header>
		<Card.Content>
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head class="w-16">ID</Table.Head>
						<Table.Head class="w-64">Name</Table.Head>
						<Table.Head class="w-64">Polls</Table.Head>
						<Table.Head class="w-128">Status</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each groups as group (group.id)}
						<Table.Row>
							<Table.Cell class="font-medium">{group.id}</Table.Cell>
							<Table.Cell>{group.name}</Table.Cell>
							<Table.Cell>{group.polls}</Table.Cell>
							<Table.Cell>
								<div class="flex items-center justify-between">
									{#if editGroup === group.id}
										<div class="flex items-center gap-2">
											<div>{editGroupState ? 'Active' : 'Passive'}</div>
											<form
												action="?/toggleGroup"
												method="POST"
												use:enhance={() => {
													editGroup = 0;
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
												<Input type="hidden" name="id" value={group.id} />
												<Input type="checkbox" name="state" bind:checked={editGroupState} />
												<Button variant="ghost" class="p-0!" type="submit">
													<Save class="h-4 w-4" />
												</Button>
												<Button variant="ghost" class="p-0!" onclick={() => (editGroup = 0)}>
													<PencilOff class="h-4 w-4" />
												</Button>
											</form>
										</div>
									{:else}
										<div class="flex items-center gap-2">
											<div>{group.active == 1 ? 'Active' : 'Passive'}</div>
											<Button
												variant="ghost"
												class="p-0!"
												onclick={() => {
													setEditGroup(group.id);
												}}
											>
												<Pencil class="h-4 w-4" />
											</Button>
										</div>
									{/if}

									<Dialog.Root>
										<Dialog.Trigger>
											<Button variant="ghost" class="p-0! text-red-500">Delete Group</Button>
										</Dialog.Trigger>
										<Dialog.Content class="h-64 w-64">
											<Dialog.Title>Are you sure?</Dialog.Title>
											<Dialog.Description
												>The Group ({groups.find((g: Record<string, string>) => g.id === group.id)
													.name}) will be deleted.</Dialog.Description
											>
											<div class="flex flex-col text-center">
												<form
													action="?/deleteGroup"
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
													<Input type="hidden" name="id" value={group.id} />
													<Button variant="destructive" type="submit">Delete Group</Button>
												</form>
											</div>
										</Dialog.Content>
									</Dialog.Root>
								</div>
							</Table.Cell>
						</Table.Row>
					{/each}

					{#if newGroup == true}
						<Table.Row>
							<Table.Cell></Table.Cell>
							<Table.Cell
								><Input
									name="name"
									placeholder="Group Name"
									bind:value={newGroupName}
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

										if (e.data && /[a-zA-Z0-9]/.test(e.data) && newGroupName.length < 32) {
											newGroupName += e.data;
										}
									}}
								/></Table.Cell
							>
							<Table.Cell
								><Input
									name="polls"
									placeholder="poll1,poll2"
									bind:value={newGroupPolls}
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

										if (e.data && /[a-zA-Z0-9,]/.test(e.data) && newGroupPolls.length < 32) {
											newGroupPolls += e.data;
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
