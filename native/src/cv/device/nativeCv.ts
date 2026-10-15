// G9 Stage J8: thin, optional wrapper around the QA-only native helpers in NsModelAssets (ModelAssetsModule.kt). Every call is
// optional: on an older APK without these methods the debug layer keeps working and logs only through console.log.
export type NsCvNative = {
  log?: (line: string) => void;
  runtimeStats?: () => Promise<{ thermal: number; nativeHeapMb: number; javaHeapMb: number; sdk: number }>;
  diagDir?: () => Promise<string>;
  appendDiag?: (line: string) => Promise<boolean>;
  saveRgbJpeg?: (name: string, rgbBase64: string, w: number, h: number) => Promise<string>;
};
export const LOGCAT_TAG = 'NutriSoleCV';

/** Log sink for nscv(): console (ReactNativeJS tag) + native Log.i("NutriSoleCV", ...) when available. */
export function nscvSink(n: NsCvNative | undefined) {
  return (line: string) => { console.log(line); try { n?.log?.(line); } catch { /* never let logging break the camera */ } };
}

/** JS heap in MB from Hermes, when the engine exposes it; otherwise null (never estimated). */
export function jsHeapMb(): number | null {
  const h = (globalThis as { HermesInternal?: { getInstrumentedStats?: () => Record<string, number> } }).HermesInternal;
  const s = h?.getInstrumentedStats?.(); const v = s?.js_heapSize ?? s?.js_allocatedBytes;
  return typeof v === 'number' && v > 0 ? Math.round((v / 1048576) * 10) / 10 : null;
}
