<script lang="ts">
  import { Button } from '$lib/components/ui/button/index';
  import * as Card from '$lib/components/ui/card/index';
  import { Textarea } from '$lib/components/ui/textarea/index';

  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';

  let { data } = $props();

  const authorized: boolean = data?.authorized ?? false;
  const isAdmin: boolean = data?.isAdmin ?? false;
  const groups: string[] = data?.groups ?? [];
  const recipientCount: number = data?.recipientCount ?? 0;

  const MAX_MESSAGE_LENGTH = 4096;

  // svelte-ignore state_referenced_locally
  let message = $state('');
  // svelte-ignore state_referenced_locally
  let organization = $state(isAdmin ? '' : (data?.organization ?? ''));
  let sending = $state(false);

  const remaining = $derived(MAX_MESSAGE_LENGTH - message.length);
  const canSubmit = $derived(
    message.trim().length > 0 &&
      message.length <= MAX_MESSAGE_LENGTH &&
      (!isAdmin || organization !== '') &&
      !sending
  );
</script>

<svelte:head>
  <title>Mesaj Gönder · Mono Afet</title>
</svelte:head>

<div class="h-full w-full p-4">
  <Card.Root class="mx-auto w-full max-w-2xl">
    <Card.Header>
      <Card.Title>Mesaj Gönder</Card.Title>
      <Card.Description>
        {#if !authorized}
          Bu sayfaya erişim yetkiniz bulunmuyor.
        {:else if isAdmin}
          Seçtiğiniz organizasyondaki aktif kullanıcılara WhatsApp üzerinden kendi mesajınızı
          gönderin.
        {:else}
          <b>{organization}</b> organizasyonundaki aktif kullanıcılara ({recipientCount} kişi)
          WhatsApp üzerinden kendi mesajınızı gönderin.
        {/if}
      </Card.Description>
    </Card.Header>

    {#if authorized}
      <Card.Content>
        <form
          method="POST"
          action="?/sendMessage"
          class="flex flex-col gap-4"
          use:enhance={() => {
            sending = true;
            return async ({ result, update }) => {
              sending = false;
              if (result.type === 'success') {
                const d = (result.data ?? {}) as {
                  sent?: number;
                  failed?: number;
                  total?: number;
                };
                toast.success(
                  `Mesaj gönderildi — ${d.sent ?? 0} başarılı, ${d.failed ?? 0} başarısız (toplam ${d.total ?? 0})`
                );
                message = '';
              } else if (result.type === 'failure') {
                const d = (result.data ?? {}) as { message?: string };
                toast.error(d.message ?? 'Mesaj gönderilemedi');
              } else {
                toast.error('Beklenmeyen bir hata oluştu');
              }
              await update({ reset: false });
            };
          }}
        >
          {#if isAdmin}
            <div class="flex flex-col gap-1.5">
              <label for="organization" class="text-sm font-medium">Organizasyon</label>
              <select
                id="organization"
                name="organization"
                bind:value={organization}
                class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
              >
                <option value="" disabled>Organizasyon seçin</option>
                {#each groups as g}
                  <option value={g}>{g}</option>
                {/each}
              </select>
            </div>
          {/if}

          <div class="flex flex-col gap-1.5">
            <label for="message" class="text-sm font-medium">Mesaj</label>
            <Textarea
              id="message"
              name="message"
              bind:value={message}
              maxlength={MAX_MESSAGE_LENGTH}
              rows={6}
              placeholder="Organizasyonunuza göndermek istediğiniz mesajı yazın..."
            />
            <span class="text-xs text-muted-foreground">{remaining} karakter kaldı</span>
          </div>

          <div class="flex items-center justify-end gap-2">
            <Button type="submit" disabled={!canSubmit}>
              {sending ? 'Gönderiliyor...' : 'Gönder'}
            </Button>
          </div>
        </form>
      </Card.Content>
    {/if}
  </Card.Root>
</div>
