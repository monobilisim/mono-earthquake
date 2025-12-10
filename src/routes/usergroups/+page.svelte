<script lang="ts">
  import Button from '$lib/components/ui/button/button.svelte';
  import Input from '$lib/components/ui/input/input.svelte';
  import * as Card from '$lib/components/ui/card/index';
  import * as Table from '$lib/components/ui/table/index';
  import * as Dialog from '$lib/components/ui/dialog/index';
  import * as Select from '$lib/components/ui/select/index';

  import type { UserGroup } from '$lib/types';

  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';

  let { data } = $props();

  // svelte-ignore state_referenced_locally
  let groups: UserGroup[] = $state(data?.userGroups ?? []);
  // svelte-ignore state_referenced_locally
  const originalGroups = $state(data?.userGroups ?? []);
  // svelte-ignore state_referenced_locally
  let tenants = data?.tenants ?? [];

  let newGroup: boolean = $state(false);
  let newGroupName: string = $state('');
  let newGroupPolls: string = $state('');

  async function newGroupAdd() {
    let formData = new FormData();
    formData.append('name', newGroupName);
    formData.append('tenant', newGroupTenant);

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

  let filters = $state({
    name: '',
    tenant: ''
  });

  const url = new URL(page.url);

  if (url.searchParams.get('name') !== '' || url.searchParams.get('tenant') !== '') {
    filters = {
      name: url.searchParams.get('name') ?? '',
      tenant: url.searchParams.get('tenant') ?? ''
    };

    applyFilters();
  }

  function applyFilters() {
    groups = originalGroups.filter((group) => {
      if (filters.name !== '' && !group.name.includes(filters.name)) {
        return false;
      }
      if (filters.tenant !== '' && !group.tenant.includes(filters.tenant)) {
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
      tenant: ''
    };

    goto(url.toString(), { replaceState: true });
    window.location.reload();
  }

  let newGroupTenant = $state('');
</script>

<div class="h-full w-full p-4">
  <Card.Root class="h-[98vh] overflow-auto">
    <Card.Header class="flex items-center justify-between">
      <Card.Title>Groups</Card.Title>
      <div class="flex gap-1">
        <Dialog.Root>
          <Dialog.Trigger>
            <Button>Filters</Button>
          </Dialog.Trigger>
          <Dialog.Content>
            <Dialog.Title>Filters</Dialog.Title>
            <label>
              Name
              <Input bind:value={filters.name} />
            </label>
            <label>
              Tenant
              <Input bind:value={filters.tenant} />
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
                    url.searchParams.set('tenant', filters.tenant);

                    goto(url.toString());

                    applyFilters();
                  }}
                >
                  Apply filters
                </Button>
              </Dialog.Close>
            </div>
          </Dialog.Content>
        </Dialog.Root>
        {#if newGroup}
          <div>
            <Button
              class="bg-green-500 text-white hover:bg-green-600 focus:ring-green-600"
              onclick={() => {
                newGroup = false;
                newGroupAdd();
              }}
            >
              Save
            </Button>
            <Button
              class="bg-red-500 text-white hover:bg-red-600 focus:ring-red-600"
              onclick={() => {
                newGroup = false;
              }}
              >Cancel
            </Button>
          </div>
        {:else}
          <Button
            onclick={() => {
              newGroup = true;
            }}
          >
            Add new Group
          </Button>
        {/if}
      </div>
    </Card.Header>
    <Card.Content>
      <Table.Root>
        <Table.Header>
          <Table.Row>
            <Table.Head class="w-32">ID</Table.Head>
            <Table.Head class="w-lg">Name</Table.Head>
            <Table.Head class="w-lg">Tenant</Table.Head>
            <Table.Head></Table.Head>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {#if newGroup == true}
            <Table.Row>
              <Table.Cell></Table.Cell>
              <Table.Cell>
                <Input name="name" placeholder="Name" bind:value={newGroupName} />
              </Table.Cell>
              <Table.Cell>
                <Select.Root type="single" bind:value={newGroupTenant}>
                  <Select.Trigger class="w-full">
                    {newGroupTenant.length > 0 ? newGroupTenant : 'Select Tenant'}
                  </Select.Trigger>
                  <Select.Content>
                    {#each tenants as tenant (tenant)}
                      <Select.Item value={tenant.toString()} label={tenant.toString()} />
                    {/each}
                  </Select.Content>
                </Select.Root>
              </Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>
          {/if}

          {#each groups as group (group.id)}
            <Table.Row>
              <Table.Cell class="font-medium">{group.id}</Table.Cell>
              <Table.Cell>{group.name}</Table.Cell>
              <Table.Cell>{group.tenant}</Table.Cell>
              <Table.Cell class="flex justify-end gap-2">
                <Dialog.Root>
                  <Dialog.Trigger>
                    <Button variant="ghost" class="p-0! text-red-500">Delete Tenant</Button>
                  </Dialog.Trigger>
                  <Dialog.Content class="h-64 w-64">
                    <Dialog.Title>Are you sure?</Dialog.Title>
                    <Dialog.Description>
                      The Tenant ({groups.find((g: UserGroup) => g.id === group.id)?.name ??
                        'name'}) will be deleted.
                    </Dialog.Description>
                    <div class="flex flex-col text-center">
                      <form
                        action="?/deleteGroup"
                        method="POST"
                        use:enhance={() => {
                          return async ({ result }) => {
                            if (result.type === 'failure') {
                              const error = String(result.data ?? 'Error while deleting group');
                              toast.error(error);
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
              </Table.Cell>
            </Table.Row>
          {/each}
        </Table.Body>
      </Table.Root>
    </Card.Content>
  </Card.Root>
</div>
