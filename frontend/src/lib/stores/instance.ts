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
    setInstance: (url: string) => {
      const cleaned = url.replace(/^https?:\/\//, '').replace(/\/+$/, '');
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
