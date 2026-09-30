export const storage = {
  async get(): Promise<string | null> { try { return localStorage.getItem('nutrisole.demo.v1'); } catch { return null; } },
  async set(value: string): Promise<void> { try { localStorage.setItem('nutrisole.demo.v1', value); } catch { /* Session still works when storage is unavailable. */ } },
};
