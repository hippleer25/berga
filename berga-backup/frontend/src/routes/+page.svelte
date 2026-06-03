<script lang="ts">
    import { browser } from '$app/environment';
    import { onMount } from 'svelte';
    import { t } from 'svelte-i18n';

    let ready = $state(false);
    let checking = $state(false);

    onMount(async () => {
        if (!browser || checking) return;
        checking = true;

        try {
            const res = await fetch('/api/feed/recommendations', {
                credentials: 'include'
            });

            if (res.ok) {
                window.location.replace('/home');
            } else {
                ready = true;
            }
        } catch {
            ready = true;
        }
    });
</script>

<style>
.gloock-regular {
font-family: var(--font-page-title);
      font-weight: 400;
      font-style: normal;
    }

    .berga-title {
      text-shadow:
        0 2px 12px rgba(0, 0, 0, 0.6),
        0 1px 3px rgba(0, 0, 0, 0.8);
    }
</style>

{#if ready}
<div class="hero min-h-screen bg-base-200 relative overflow-hidden">

  <!-- MOBILE LAYOUT -->
  <div class="md:hidden relative w-full min-h-screen flex flex-col">
    <div class="absolute inset-0 bg-[url('/landing.jpg')] bg-cover bg-center">
      <div class="absolute inset-0 bg-gradient-to-r from-black/60 via-black/30 to-transparent"></div>
    </div>
    <div class="relative z-10 flex-1 flex items-end pl-10 pb-35b">
      <h1 class="gloock-regular berga-title text-8xl text-white font-bold">Berga</h1>
    </div>
    <div class="relative z-10 bg-base-100 rounded-t-3xl px-8 py-8 flex flex-col gap-4 shadow-lg">
      <a href="/login" class="btn btn-md btn-primary w-full border-[1.5px] font-bold">{$t('welcome.login')}</a>
      <a href="/signup" class="btn btn-md btn-outline w-full border-[1.5px] font-bold bg-base-200">{$t('welcome.signup')}</a>
    </div>
  </div>

  <!-- DESKTOP LAYOUT -->
  <div class="hidden md:grid absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] max-w-3xl bg-base-100 border-primary border-1 rounded-2xl shadow-lg overflow-hidden z-10
              grid-cols-[6fr_4fr] items-stretch">
    <div class="relative bg-[url('/landing.jpg')] bg-cover bg-center flex items-center pl-10 py-36">
      <div class="absolute inset-0 bg-gradient-to-r from-black/60 via-black/30 to-transparent"></div>
      <h1 class="gloock-regular berga-title text-7xl text-white font-bold relative z-10">Berga</h1>
    </div>
    <div class="flex flex-col items-center justify-center gap-4 px-10">
      <a href="/login" class="btn btn-md btn-primary w-full border-[1.5px] font-bold">{$t('welcome.login')}</a>
      <a href="/signup" class="btn btn-md btn-outline w-full border-[1.5px] font-bold bg-base-200">{$t('welcome.signup')}</a>
    </div>
  </div>

</div>
{/if}