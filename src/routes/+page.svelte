<script lang="ts">
  import { Input } from '$lib/components/ui/input/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Slider } from '$lib/components/ui/slider/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import * as Table from '$lib/components/ui/table/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { cubicInOut } from 'svelte/easing';
  import * as Devalue from 'devalue';
  import { goto } from '$app/navigation';
  import { enhance } from '$app/forms';
  import { page } from '$app/state';
  import { toast } from 'svelte-sonner';
  import { onMount } from 'svelte';
  import Chart, { type ChartItem } from 'chart.js/auto';

  const { data } = $props();

  import { isPortrait } from '$lib/utils';

  let whatsappMessageSent = $state(false);
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

  // @ts-expect-error ignore
  let canvasEl: HTMLCanvasElement = $state();
  // @ts-expect-error ignore
  let canvas2El: HTMLCanvasElement = $state();

  let chart2Data: Record<string, string>[] | string[] = last30DaysEarthquakeStats.days; // e.g. [{ date: '2025-10-01', count: 5 }, ...]
  const labels = chart2Data.map((d) => {
    return d.date.toString().slice(-2);
  });
  chart2Data = chart2Data.map((d) => d.count);

  onMount(() => {
    const chartData = [
      {
        label: 'Successful',
        value: last30DaysFeedbackStats.successful,
        color: getComputedStyle(document.documentElement).getPropertyValue('--color-successful')
      },
      {
        label: 'Failed',
        value: last30DaysFeedbackStats.failed,
        color: getComputedStyle(document.documentElement).getPropertyValue('--color-failed')
      }
    ];

    const totalMessages = chartData.reduce((acc, curr) => acc + curr.value, 0);

    const centerTextPlugin = {
      id: 'centerText',
      afterDraw(chart: any) {
        const {
          ctx,
          chartArea: { left, right, top, bottom, width, height }
        } = chart;

        ctx.save();
        ctx.font = 'bold 20px sans-serif';
        ctx.fillStyle =
          getComputedStyle(document.documentElement).getPropertyValue('--foreground') || '#000';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // center of chart area
        const centerX = left + width / 2;
        const centerY = top + height / 2;

        ctx.fillText(String(totalMessages), centerX, centerY);

        if (!isInPortrait) {
          ctx.font = '14px sans-serif';
          ctx.fillStyle =
            getComputedStyle(document.documentElement).getPropertyValue('--muted-foreground') ||
            '#fff';
          ctx.fillText('Messages Sent', centerX, centerY + 24);
        }
        ctx.restore();
      }
    };

    // @ts-ignore
    new Chart(canvasEl, {
      type: 'doughnut',
      data: {
        labels: chartData.map((d) => d.label),
        datasets: [
          {
            data: chartData.map((d) => d.value),
            backgroundColor: chartData.map((d) => d.color),
            borderWidth: 0
          }
        ]
      },
      options: {
        cutout: '60%',
        plugins: {
          tooltip: {
            enabled: true,
            displayColors: true,
            callbacks: {
              label: (context) => `${context.label}: ${context.parsed}`
            }
          },
          legend: { display: true, position: 'bottom' }
        }
      },
      plugins: [centerTextPlugin]
    });

    const chart2Config = {
      type: 'bar' as const,
      data: {
        labels,
        datasets: [
          {
            label: 'Earthquakes',
            data: chart2Data,

            backgroundColor: getComputedStyle(document.documentElement)
              .getPropertyValue('--chart2-color')
              .trim(),
            borderRadius: 0
          }
        ]
      },
      options: {
        animation: {
          duration: 500,
          easing: 'easeInOutCubic'
        },
        scales: {
          x: {
            ticks: {
              callback: (value: any, index: number) => labels[index]
            }
          },
          y: {
            beginAtZero: true
          }
        },
        plugins: {
          legend: {
            display: true
          }
        },
        responsive: true,
        maintainAspectRatio: true
      }
    };

    // @ts-expect-error ignore
    new Chart(canvas2El, chart2Config);
  });
</script>

{#if user.name}
  <div class="flex h-screen w-full flex-col gap-2 overflow-scroll p-4 lg:p-8">
    <div class="mb-4 grid auto-rows-auto grid-cols-1 gap-4 md:grid-cols-2 md:gap-4">
      <Card.Root>
        <Card.Header>
          <Card.Title class="flex w-full items-center justify-between">
            <div class="flex items-center gap-2">
              <div>Last Earthquakes</div>
              {#if url.searchParams.get('min_magnitude') || url.searchParams.get('start_date')}
                <p class="text-sm text-slate-500">(filtered)</p>
              {/if}
            </div>
            <Dialog.Root>
              <Dialog.Trigger>
                <Button>Filters</Button>
              </Dialog.Trigger>
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
                    }}
                  >
                    Clear Filters
                  </Button>

                  <Button
                    onclick={async () => {
                      const url = new URL(window.location.pathname, window.location.origin);
                      url.searchParams.set('min_magnitude', String(earthquakeFilters.magnitude[0]));
                      url.searchParams.set('max_magnitude', String(earthquakeFilters.magnitude[1]));
                      url.searchParams.set('start_date', earthquakeFilters.date.start.toString());
                      url.searchParams.set('end_date', earthquakeFilters.date.end.toString());

                      window.location.href = url.toString();
                      // goto(url.toString(), { replaceState: true, invalidateAll: true });
                    }}
                  >
                    Apply Filters
                  </Button>
                </Dialog.Close>
              </Dialog.Content>
            </Dialog.Root>
          </Card.Title>
        </Card.Header>
        <Card.Content class="max-h-64 overflow-scroll md:max-h-96">
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

        <Card.Content class="flex h-full w-full items-center justify-center">
          <div class="flex flex-col gap-4 md:flex-row">
            <div class="h-64 w-full">
              <div class="bold mb-2 flex h-full w-full flex-col items-center justify-center">
                <canvas bind:this={canvasEl} class="h-full w-full"></canvas>
              </div>
            </div>

            <div class="h-48 w-80 md:h-64 md:w-128">
              <div class="bold flex h-full w-full flex-col items-center justify-center">
                <canvas bind:this={canvas2El} class="h-full w-full"></canvas>
              </div>
            </div>
          </div>
        </Card.Content>
      </Card.Root>
    </div>
    <Card.Root>
      <Card.Header>
        <Card.Title>Feedbacks</Card.Title>
      </Card.Header>
      <Card.Content class="oveflow-hidden p-0">
        <div class="flex-1 overflow-auto 2xl:h-128">
          {#if selectedEarthquake === 0}
            <p class="w-full text-center text-sm text-muted-foreground">
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
    <Card.Root class=" w-[350px]">
      <Card.Header>
        <Card.Title class="text-2xl">Login</Card.Title>
        <Card.Description class="text-muted-foreground">
          Enter your phone number to get started
        </Card.Description>
      </Card.Header>
      <Card.Content>
        {#if !whatsappMessageSent}
          <form
            action="?/sendToken"
            method="POST"
            use:enhance={async () => {
              return async ({ result }) => {
                if (result.type === 'failure') {
                  const error = String(result.data ?? 'Error while sending the token');
                  toast.error(error);
                }

                if (result.type === 'success') {
                  toast.success('Successfully sent the token. Please check your Whatsapp.');
                  whatsappMessageSent = true;
                }

                const url = new URL(window.location.pathname, window.location.origin);
                url.searchParams.set('phone_number', phone_number);

                goto(url.toString());
              };
            }}
          >
            <label
              >Phone Number
              <Input name="phone_number" placeholder="5554443322" bind:value={phone_number} />
            </label>

            <div class="mt-4 flex justify-between">
              <Button type="submit">Send code</Button>
              <Button onclick={() => (whatsappMessageSent = true)}>I have code</Button>
            </div>
          </form>
        {:else}
          <form
            action="?/verifyToken"
            method="POST"
            use:enhance={async () => {
              return async ({ result }) => {
                if (result.type === 'failure') {
                  const error = String(result.data ?? 'Error while verifying the token');
                  toast.error(error);
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
              <Input name="phone_number" placeholder="5554443322" bind:value={phone_number} />
            </label>
            <label
              >Token
              <Input
                name="activation_token"
                placeholder="6 letter token"
                bind:value={activation_token}
              />
            </label>

            <div class="mt-4 flex justify-between">
              <Button onclick={() => (whatsappMessageSent = false)}>Return</Button>

              <Button type="submit">Verify</Button>
            </div>
          </form>
        {/if}
      </Card.Content>
    </Card.Root>
  </div>
{/if}

<style>
  :root {
    --color-successful: #22c55e;
    --color-failed: #ef4444;
    --chart2-color: #3b82f6;
  }
</style>
