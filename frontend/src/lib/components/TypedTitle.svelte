<script lang="ts">
    import { onDestroy } from 'svelte';

    let { text, speed = 60 }: { text: string; speed?: number } = $props();

    let shown = $state('');
    let typing = $state(false);
    let timer: ReturnType<typeof setInterval> | undefined;

    const reducedMotion =
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function type() {
        if (timer) clearInterval(timer);
        if (reducedMotion || !text) {
            shown = text;
            typing = false;
            return;
        }
        shown = '';
        typing = true;
        let i = 0;
        timer = setInterval(() => {
            i++;
            shown = text.slice(0, i);
            if (i >= text.length) {
                clearInterval(timer);
                timer = undefined;
                // keep caret blinking briefly, then hide it
                setTimeout(() => {
                    typing = false;
                }, 1200);
            }
        }, speed);
    }

    $effect(type);
    onDestroy(() => {
        if (timer) clearInterval(timer);
    });
</script>

<span class="typed-title">
    {shown}<span class="typed-caret" class:active={typing} aria-hidden="true"></span>
</span>
<span class="sr-only">{text}</span>

<style>
    .typed-title {
        white-space: pre;
    }
    .typed-caret {
        display: inline-block;
        width: 2px;
        height: 0.9em;
        margin-left: 3px;
        vertical-align: baseline;
        background: currentColor;
        opacity: 0;
        transform: translateY(0.08em);
        transition: opacity 0.3s ease;
    }
    .typed-caret.active {
        opacity: 1;
        animation: caret-blink 0.9s steps(1) infinite;
    }
    @keyframes caret-blink {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0;
        }
    }
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
    @media (prefers-reduced-motion: reduce) {
        .typed-caret {
            display: none;
        }
    }
</style>
