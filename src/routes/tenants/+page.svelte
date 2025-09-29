<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import Input from '$lib/components/ui/input/input.svelte';
	import * as Card from '$lib/components/ui/card/index';
	import * as Table from '$lib/components/ui/table/index';
	import * as Dialog from '$lib/components/ui/dialog/index';
	import * as Select from '$lib/components/ui/select/index';

	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	let { data } = $props();

	let groups = $state(data?.groups ?? []);
	const originalGroups = $state(data?.groups ?? []);

	let newGroup: boolean = $state(false);
	let newGroupName: string = $state('');
	let newGroupPolls: string = $state('');

	async function newGroupAdd() {
		let formData = new FormData();
		formData.append('name', newGroupName);
		if (newGroupPollsMultiSelectEnabled && newGroupPollsMulti.length > 0) {
			newGroupPolls = newGroupPollsMulti.join(',');
		}
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
	}

	let newGroupPollsMultiSelectEnabled: boolean = $state(true);
	let newGroupPollsMulti: string[] = $state([]);

	let groupToggleState: Record<number, boolean> = $state(
		Object.fromEntries(groups.map((g) => [g.id, g.active]))
	);

	let toggleFormState: Record<string, HTMLFormElement> = $state(
		Object.fromEntries(groups.map((g) => [g.id]))
	);

	let filters = $state({
		name: '',
		polls: '',
		active: ''
	});

	const url = new URL(page.url);

	if (
		url.searchParams.get('name') !== '' ||
		url.searchParams.get('polls') !== '' ||
		url.searchParams.get('active') !== ''
	) {
		filters = {
			name: url.searchParams.get('name') ?? '',
			polls: url.searchParams.get('polls') ?? '',
			active: url.searchParams.get('active') ?? ''
		};

		applyFilters();
	}

	function applyFilters() {
		groups = originalGroups.filter((group) => {
			if (filters.name !== '' && !group.name.includes(filters.name)) {
				return false;
			}
			if (filters.polls !== '' && !group.polls.includes(filters.polls)) {
				return false;
			}
			if (filters.active !== '' && group.active.toString() !== filters.active) {
				return false;
			}

			return true;
		});
	}

	function clearFilters() {
		const url = new URL(page.url);
		url.search = '';

		filters = {
			name: '',
			polls: '',
			active: ''
		};

		goto(url.toString(), { replaceState: true });
	}
</script>

<div class="h-full w-full p-4">
	<Card.Root class="h-[98vh] overflow-auto">
		<Card.Header class="flex items-center justify-between">
			<Card.Title>Tenants</Card.Title>
			<div class="flex gap-1">
				<Dialog.Root>
					<Dialog.Trigger>
						<Button>Filters</Button>
					</Dialog.Trigger>
					<Dialog.Content>
						<Dialog.Title>Filters</Dialog.Title>
						<label
							>Name
							<Input bind:value={filters.name} />
						</label>
						<label
							>Polls
							<Input bind:value={filters.polls} />
						</label>
						<label
							>Status
							<Select.Root type="single" bind:value={filters.active}>
								<Select.Trigger class="w-full">
									{filters.active !== '' ? (filters.active === '1' ? 'Active' : 'Passive') : 'All'}
								</Select.Trigger>
								<Select.Content>
									<Select.Item value="" label="All" />
									<Select.Item value="1" label="Active" />
									<Select.Item value="0" label="Passive" />
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

										url.searchParams.set('name', filters.name);
										url.searchParams.set('polls', filters.polls);
										url.searchParams.set('active', filters.active);

										goto(url.toString());

										applyFilters();
									}}>Apply filters</Button
								>
							</Dialog.Close>
						</div>
					</Dialog.Content>
				</Dialog.Root>
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
						}}>Add new tenant</Button
					>
				{/if}
			</div>
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
					{#if newGroup == true}
						<Table.Row>
							<Table.Cell></Table.Cell>
							<Table.Cell>
								<Input
									name="name"
									placeholder="Tenant Name"
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
								/>
							</Table.Cell>
							<Table.Cell>
								{#if newGroupPollsMultiSelectEnabled}
									<Select.Root type="multiple" bind:value={newGroupPollsMulti}>
										<Select.Trigger class="w-full">
											{newGroupPollsMulti.length > 0
												? newGroupPollsMulti.join(',')
												: 'Select Polls'}
										</Select.Trigger>
										<Select.Content>
											<Select.Item value="deprem" label="deprem" />
											<Select.Item
												value=""
												label="custom poll"
												onclick={() =>
													(newGroupPollsMultiSelectEnabled = !newGroupPollsMultiSelectEnabled)}
											/>
										</Select.Content>
									</Select.Root>
								{:else}
									<Input
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
									/>
								{/if}
							</Table.Cell>
						</Table.Row>
					{/if}

					{#each groups as group (group.id)}
						<Table.Row>
							<Table.Cell class="font-medium">{group.id}</Table.Cell>
							<Table.Cell>{group.name}</Table.Cell>
							<Table.Cell>{group.polls}</Table.Cell>
							<Table.Cell>
								<div class="flex items-center justify-between">
									<div class="mr-8 flex items-center justify-center gap-2">
										<div>{group.active ? 'Active' : 'Passive'}</div>
										<form
											bind:this={toggleFormState[group.id]}
											action="?/toggleGroup"
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
											<Input
												type="checkbox"
												name="state"
												bind:checked={groupToggleState[group.id]}
												onchange={() => {
													toggleFormState[group.id]?.requestSubmit();
												}}
											/>
										</form>
									</div>

									<Dialog.Root>
										<Dialog.Trigger>
											<Button variant="ghost" class="p-0! text-red-500">Delete Tenant</Button>
										</Dialog.Trigger>
										<Dialog.Content class="h-64 w-64">
											<Dialog.Title>Are you sure?</Dialog.Title>
											<Dialog.Description
												>The Tenant ({groups.find((g: Record<string, string>) => g.id === group.id)
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
													<Button variant="destructive" type="submit">Delete Tenant</Button>
												</form>
											</div>
										</Dialog.Content>
									</Dialog.Root>
								</div>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</Card.Content>
	</Card.Root>
</div>
