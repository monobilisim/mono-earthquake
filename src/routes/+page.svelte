<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Slider } from '$lib/components/ui/slider/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Chart from '$lib/components/ui/chart/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { cubicInOut } from 'svelte/easing';
	import * as Devalue from 'devalue';
	import { goto } from '$app/navigation';
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	const { data } = $props();

	import { isPortrait } from '$lib/utils';

	let phone_number: string = $state('');
	let activation_token: string = $state('');

	const user = data?.user;
	const earthquakes = data?.earthquakes;
	const last30DaysFeedbackStats = data?.last30DaysStats.messages;
	const last30DaysEarthquakeStats = data?.last30DaysStats.earthquakes;

	let sendTokenError: string = $state('');

	let verifyTokenError: string = $state('');

	let selectedEarthquake: number = $state(0);

	let feedbacks: Record<string, string>[] = $state([]);

	let isFeedbacksEmpty: boolean = $state(true);

	phone_number = page.url.searchParams.get('phone_number') ?? '';

	async function getFeedbacks(id: number) {
		let formData = new FormData();
		// @ts-expect-error ignore
		formData.append('id', id);

		const response = await fetch('/?/getFeedbackStatsByEarthquakeID', {
			method: 'POST',
			body: formData
		});

		const result = await response.json();

		feedbacks = JSON.parse(JSON.stringify(Devalue.parse(result.data)));

		if (feedbacks.length > 0) {
			isFeedbacksEmpty = false;
		} else {
			isFeedbacksEmpty = true;
		}
	}

	import { PieChart, Text, BarChart, type ChartContextValue } from 'layerchart';

	const chartData = [
		{
			stats: 'successful',
			value: last30DaysFeedbackStats.successful,
			color: 'var(--color-successful)'
		},
		{ stats: 'failed', value: last30DaysFeedbackStats.failed, color: 'var(--color-failed)' }
	];

	const chartConfig = {
		total: { label: 'Total' },
		successful: { label: 'Successful', color: 'var(--chart-2)' },
		failed: { label: 'Failed', color: 'var(--chart-5)' }
	} satisfies Chart.ChartConfig;

	const totalMessages = chartData.reduce((acc, curr) => acc + curr.value, 0);

	const chart2Data = last30DaysEarthquakeStats.days;

	const chart2Config = {
		count: { label: 'Earthquakes', color: 'hsl(var(--chart-1))' }
	} satisfies Chart.ChartConfig;

	let context = $state<ChartContextValue>();

	import { getLocalTimeZone, today } from '@internationalized/date';
	import { RangeCalendar } from '$lib/components/ui/range-calendar/index.js';

	const start = today(getLocalTimeZone()).subtract({ days: 14 });
	const end = start.add({ days: 14 });

	let earthquakeFilters = $state({
		magnitude: [0, 10],
		date: { start, end }
	});

	const url = new URL(page.url);

	if (url.searchParams.get('min_magnitude')) {
		earthquakeFilters.magnitude[0] = url.searchParams.get('min_magnitude') as never;
	}
	if (url.searchParams.get('max_magnitude')) {
		earthquakeFilters.magnitude[1] = url.searchParams.get('max_magnitude') as never;
	}

	let isInPortrait = $state(false);

	$effect(() => {
		isInPortrait = isPortrait(window);
	});
</script>

{#if user.name}
	<div class="flex h-screen w-full flex-col gap-2 overflow-scroll p-4 lg:p-8">
		<div class="mb-4 grid grid-cols-1 grid-rows-2 gap-4 pb-0! md:grid-cols-2 md:grid-rows-1">
			<Card.Root class="h-96">
				<Card.Header>
					<Card.Title class="flex w-full items-center justify-between">
						<div class="flex items-center gap-2">
							<div>Last Earthquakes</div>
							{#if url.searchParams.get('min_magnitude') || url.searchParams.get('start_date')}
								<p class="text-sm text-slate-500">(filtered)</p>
							{/if}
						</div>
						<Dialog.Root>
							<Dialog.Trigger><Button>Filters</Button></Dialog.Trigger>
							<Dialog.Content>
								<Dialog.Header>
									<Dialog.Title>Filters</Dialog.Title>
								</Dialog.Header>
								<div class="justfify-between flex w-full gap-4">
									<div class="w-1/2 text-left">{earthquakeFilters.magnitude[0]}</div>
									<div class="">Magnitude</div>
									<div class="w-1/2 text-right">{earthquakeFilters.magnitude[1]}</div>
								</div>
								<Slider
									type="multiple"
									min={0}
									max={10}
									step={0.1}
									bind:value={earthquakeFilters.magnitude}
								/>

								<RangeCalendar bind:value={earthquakeFilters.date} class="rounded-md border" />

								<Dialog.Close>
									<Button
										onclick={async () => {
											const url = new URL(window.location.pathname, window.location.origin);

											window.location.href = url.toString();
										}}>Clear Filters</Button
									>

									<Button
										onclick={async () => {
											const url = new URL(window.location.pathname, window.location.origin);
											url.searchParams.set('min_magnitude', String(earthquakeFilters.magnitude[0]));
											url.searchParams.set('max_magnitude', String(earthquakeFilters.magnitude[1]));
											url.searchParams.set('start_date', earthquakeFilters.date.start.toString());
											url.searchParams.set('end_date', earthquakeFilters.date.end.toString());

											window.location.href = url.toString();
											// goto(url.toString(), { replaceState: true, invalidateAll: true });
										}}>Apply Filters</Button
									>
								</Dialog.Close>
							</Dialog.Content>
						</Dialog.Root>
					</Card.Title>
				</Card.Header>
				<Card.Content class="h-96 overflow-scroll">
					<Table.Root>
						<Table.Header>
							<Table.Row>
								<Table.Head class="w-[100px] text-center">ID</Table.Head>
								<Table.Head class="w-[100px] text-center">Magnitude</Table.Head>
								<Table.Head class="text-center">Location</Table.Head>
								<Table.Head class="text-center">Time</Table.Head>
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each earthquakes as earthquake}
								<Table.Row
									class={'cursor-pointer' +
										(selectedEarthquake === earthquake.id ? ' bg-muted' : '')}
									onclick={() =>
										(selectedEarthquake = earthquake.id) && getFeedbacks(earthquake.id)}
								>
									<Table.Cell class="text-center font-medium">{earthquake.id}</Table.Cell>
									<Table.Cell class="text-center font-medium">{earthquake.magnitude}</Table.Cell>
									<Table.Cell class="text-center">{earthquake.location}</Table.Cell>
									<Table.Cell class="text-center">{earthquake.time}</Table.Cell>
								</Table.Row>
							{/each}
						</Table.Body>
					</Table.Root>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Additional statistics (last 30 days)</Card.Title>
				</Card.Header>

				<Card.Content class="h-full w-full">
					{#if isInPortrait}
						<div>
							Messages sent
							<br />
							Successful:
							{last30DaysFeedbackStats.successful}
							<br />
							Failed:
							{last30DaysFeedbackStats.failed}
							<br />
							Total: {totalMessages}
						</div>
						<div>
							Earthquakes
							{#each last30DaysEarthquakeStats.days as day}
								{#if Number(day.count) > 0}
									<div class="mt-2">
										{day.date}: {day.count}
									</div>
								{/if}
							{/each}
						</div>
					{:else}
						<div class="grid grid-cols-3 grid-rows-1 gap-4">
							<div class="col-span-1 h-full w-full">
								<label class="bold mb-2"
									>Messages sent
									<Chart.Container config={chartConfig} class="max-h-64 w-full md:max-h-80">
										<PieChart
											data={chartData}
											key="stats"
											value="value"
											c="color"
											innerRadius={isInPortrait ? 40 : 60}
											padding={isInPortrait ? 12 : 24}
											props={{ pie: { motion: 'tween' } }}
										>
											{#snippet aboveMarks()}
												<Text
													value={String(totalMessages)}
													textAnchor="middle"
													verticalAnchor="middle"
													class="fill-foreground text-3xl! font-bold"
													dy={3}
												/>
												<Text
													value={isInPortrait ? '' : 'Total'}
													textAnchor="middle"
													verticalAnchor="middle"
													class="fill-muted-foreground! text-muted-foreground"
													dy={22}
												/>
											{/snippet}
											{#snippet tooltip()}
												<Chart.Tooltip hideLabel />
											{/snippet}
										</PieChart>
									</Chart.Container>
								</label>
							</div>

							<div class="col-span-2">
								<label class="bold">
									Daily earthquake count
									<Chart.Container config={chart2Config} class="aspect-auto h-[200px] w-full">
										<BarChart
											bind:context
											data={chart2Data}
											x="date"
											y="count"
											axis="x"
											series={[{ key: 'count', label: 'Earthquakes', color: 'var(--chart-1)' }]}
											props={{
												bars: {
													stroke: 'none',
													rounded: 'none',
													initialY: context?.height,
													initialHeight: 0,
													motion: {
														y: { type: 'tween', duration: 500, easing: cubicInOut },
														height: { type: 'tween', duration: 500, easing: cubicInOut }
													}
												},
												xAxis: {
													format: (d: Date) => {
														if (isInPortrait) {
															return '';
														}

														const str = d.toString();
														return str.slice(-2);
													}
												}
											}}
										/>
									</Chart.Container>
								</label>
							</div>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		</div>
		<Card.Root>
			<Card.Header>
				<Card.Title>Feedbacks</Card.Title>
			</Card.Header>
			<Card.Content class="oveflow-hidden p-0">
				<div class="h-96 flex-1 overflow-auto 2xl:h-128">
					{#if selectedEarthquake === 0}
						<p class="text-sm text-muted-foreground">
							Please select an earthquake to see feedbacks.
						</p>
					{:else}
						<!-- Get by id -->
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Cell class="w-16">ID</Table.Cell>
									<Table.Cell class="w-64">Name</Table.Cell>
									<Table.Cell class="w-64">Phone Number</Table.Cell>
									<Table.Cell class="w-128">Status</Table.Cell>
									<Table.Cell class="w-128">Message</Table.Cell>
									<Table.Cell>Updated At</Table.Cell>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#if isFeedbacksEmpty}
									<Table.Row>
										<Table.Cell colspan={6} class="text-center">
											<p class="text-sm text-muted-foreground">
												No feedbacks available for this earthquake.
											</p>
										</Table.Cell>
									</Table.Row>
								{/if}

								{#each feedbacks as feedback (feedback.id)}
									<Table.Row>
										<Table.Cell>{feedback.user_id}</Table.Cell>
										<Table.Cell>{feedback.name}</Table.Cell>
										<Table.Cell>{feedback.phone_number}</Table.Cell>
										<Table.Cell>
											<div class="rounded-lg *:px-4 *:py-1">
												{#if feedback.is_read}
													<span class="bg-green-300 font-medium dark:text-black">Read</span>
												{:else}
													<span class="bg-red-300 font-medium dark:text-black">Not Read</span>
												{/if}
											</div>
										</Table.Cell>
										<Table.Cell>{feedback.message}</Table.Cell>
										<Table.Cell>{feedback.updated_at}</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					{/if}
				</div>
			</Card.Content>
		</Card.Root>
	</div>
{:else}
	<div class="flex h-full w-full flex-col items-center justify-center gap-4">
		<Card.Root class="h-104 w-[350px]">
			<Card.Header>
				<Card.Title class="text-2xl">Login or Sign Up</Card.Title>
				<Card.Description class="text-muted-foreground">
					Enter your phone number to get started
				</Card.Description>
			</Card.Header>
			<Card.Content>
				{#if sendTokenError}
					<p class="text-sm text-red-500">{sendTokenError}</p>
				{/if}
				<form
					action="?/sendToken"
					method="POST"
					use:enhance={async () => {
						return async ({ result, update }) => {
							console.log(result);

							if (result.type === 'failure') {
								toast.error(result.data);
							}

							if (result.type === 'success') {
								toast.success('Successfully sent the token. Please check your Whatsapp.');
							}

							const url = new URL(window.location.pathname, window.location.origin);
							url.searchParams.set('phone_number', phone_number);

							goto(url.toString());
						};
					}}
				>
					<label
						>Phone Number
						<Input name="phone_number" placeholder="905554443322" bind:value={phone_number} />
					</label>

					<Button class="mt-2" type="submit">Send code</Button>
				</form>

				<br />

				{#if verifyTokenError}
					<p class="text-sm text-red-500">{verifyTokenError}</p>
				{/if}
				<form
					action="?/verifyToken"
					method="POST"
					use:enhance={async () => {
						return async ({ result, update }) => {
							console.log(result);

							if (result.type === 'failure') {
								toast.error(result.data);
							}

							if (result.type === 'success') {
								toast.success('Successfully verified the token. You are now logged in.');
							}

							window.location.reload();
						};
					}}
				>
					<label
						>Phone Number
						<Input name="phone_number" placeholder="905554443322" bind:value={phone_number} />
					</label>
					<label
						>Token
						<Input
							name="activation_token"
							placeholder="6 letter token"
							bind:value={activation_token}
						/>
					</label>

					<Button class="mt-2" type="submit">Verify</Button>
				</form>
			</Card.Content>
		</Card.Root>
	</div>
{/if}
