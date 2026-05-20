<script lang="ts">
 import { onMount } from 'svelte';

 let { children }: { children: () => import('svelte').Snippet } = $props();
 let host: HTMLDivElement;

  onMount(() => {
    const el = host;
    document.body.appendChild(el);
    return () => el.remove();
  });
</script>

<div bind:this={host} style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9998">
  {@render children()}
</div>
