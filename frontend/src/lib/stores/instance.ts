import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const DEFAULT_INSTANCE = 'bergamota.net.br';

function createInstanceStore() {
  const saved = browser ? localStorage.getItem('instance_url') : null;
  const isNative = browser && !!(window as any).Capacitor?.isNativePlatform?.();
  const initial = saved || (isNative ? DEFAULT_INSTANCE : (browser ? window.location.host : ''));
  const { subscribe, set } = writable(initial);

  return {
    subscribe,
    /* Persisting only real changes keeps the mount-run of the login/signup
       debounce effect from saving the pristine default over a later manual
       pick (localStorage 'instance_url' would otherwise be poisoned with
       'bergamota.net.br' on every cold start). */
    setInstance: (url: string) => {
      const cleaned = url.replace(/^https?:\/\//, '').replace(/\/+$/, '');
      let current = '';
      const unsub = subscribe(v => (current = v));
      unsub();
      if (cleaned === current) return;
      if (browser) localStorage.setItem('instance_url', cleaned);
      set(cleaned);
    },
    getInstance: (): string => {
      let val: string = '';
      subscribe(v => val = v)();
      return val;
    },
  };
}

export const instance = createInstanceStore();
