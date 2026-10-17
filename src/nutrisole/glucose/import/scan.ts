export type BleMeter = { id: string; name: string | null; rssi: number | null };
export type MeterScanner = { start(found: (device: BleMeter) => void, fail: (error: Error) => void): void | Promise<void>; stop(): void | Promise<void> };

/** Discovery is event-driven; the deadline only stops the radio, never delays the list. */
export function scanGlucoseMeters(scanner: MeterScanner, opts: { timeoutMs: number; signal?: AbortSignal; onFound?: (device: BleMeter) => void }): Promise<BleMeter[]> {
  return new Promise((resolve, reject) => {
    const found = new Map<string, BleMeter>(); let finished = false;
    const finish = async (error?: Error) => {
      if (finished) return; finished = true;
      clearTimeout(timer); opts.signal?.removeEventListener('abort', abort);
      try { await scanner.stop(); } catch (e) { error ??= e instanceof Error ? e : new Error('Bluetooth could not stop scanning.'); }
      if (error) reject(error); else resolve([...found.values()]);
    };
    const abort = () => finish();
    const timer = setTimeout(() => finish(), opts.timeoutMs);
    opts.signal?.addEventListener('abort', abort, { once: true });
    if (opts.signal?.aborted) { finish(); return; }
    try { Promise.resolve(scanner.start(device => { if (finished) return; found.set(device.id, device); opts.onFound?.(device); }, error => { void finish(error); })).catch(e => { void finish(e instanceof Error ? e : new Error('Bluetooth scan failed.')); }); }
    catch (e) { finish(e instanceof Error ? e : new Error('Bluetooth scan failed.')); }
  });
}
