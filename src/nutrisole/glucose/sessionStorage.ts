import type { GlucoseStorage } from './types';
// Namespace by project so a development server cannot adopt another project's token.
export function accountSessionStorage(url: string): GlucoseStorage | undefined {
  if (typeof localStorage === 'undefined') return undefined;
  const key = `nutrisole-session:${url}`;
  return { read: async () => localStorage.getItem(key), write: async value => { if (value) localStorage.setItem(key, value); else localStorage.removeItem(key); } };
}
