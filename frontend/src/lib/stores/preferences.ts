import { writable } from 'svelte/store';
import { browser } from '$app/environment';

function createCoverImagesStore() {
  const saved = browser ? localStorage.getItem('show-cover-images') : null;
  const initial = saved === 'true';
  const { subscribe, set } = writable<boolean>(initial);

  return {
    subscribe,
    setEnabled: (enabled: boolean) => {
      if (browser) {
        localStorage.setItem('show-cover-images', enabled ? 'true' : 'false');
      }
      set(enabled);
    },
    getEnabled: (): boolean => {
      let val = false;
      subscribe(v => val = v)();
      return val;
    },
  };
}

export const showCoverImages = createCoverImagesStore();

export type CoverPosition = 'right' | 'bottom';

function createCoverPositionStore() {
  const saved = browser ? (localStorage.getItem('cover-image-position') as CoverPosition | null) : null;
  const initial: CoverPosition = saved === 'bottom' ? 'bottom' : 'right';
  const { subscribe, set } = writable<CoverPosition>(initial);

  return {
    subscribe,
    setPosition: (position: CoverPosition) => {
      if (browser) {
        localStorage.setItem('cover-image-position', position);
      }
      set(position);
    },
    getPosition: (): CoverPosition => {
      let val: CoverPosition = 'right';
      subscribe(v => val = v)();
      return val;
    },
  };
}

export const coverImagePosition = createCoverPositionStore();
