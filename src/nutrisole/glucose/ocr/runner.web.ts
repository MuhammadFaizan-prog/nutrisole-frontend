// Web adapter for the PP-OCRv5 pipeline: onnxruntime-web (WASM, single-threaded unless the page
// is cross-origin isolated). The WASM runtime and both models are served by the app itself
// (Vite asset + public/ocr/ppocrv5), so OCR works offline and nothing is sent to a server.
import type { OcrRunner, Rgba } from './ppocr';
import { PpOcrEngine } from './engine';

type Ort = typeof import('onnxruntime-web/wasm');
let enginePromise: Promise<PpOcrEngine> | null = null;

export function webOcrEngine(onProgress?: (p: string) => void): Promise<PpOcrEngine> {
  if (!enginePromise) enginePromise = (async () => {
    onProgress?.('Loading the on-device OCR engine…');
    const ort: Ort = await import('onnxruntime-web/wasm');
    ort.env.wasm.wasmPaths = { wasm: new URL('../../../../node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm', import.meta.url).href };
    ort.env.wasm.numThreads = typeof crossOriginIsolated !== 'undefined' && crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
    ort.env.logLevel = 'error';
    const base = (import.meta as unknown as { env?: { BASE_URL?: string } }).env?.BASE_URL || '/';
    const load = async (name: string) => { const r = await fetch(`${base}ocr/ppocrv5/${name}`); if (!r.ok) throw new Error(`model ${name}: HTTP ${r.status}`); return new Uint8Array(await r.arrayBuffer()); };
    const opts = { executionProviders: ['wasm'], logSeverityLevel: 3 as const };
    const [det, rec] = await Promise.all([ort.InferenceSession.create(await load('det.onnx'), opts), ort.InferenceSession.create(await load('rec_en.onnx'), opts)]);
    const sessions = { det, rec };
    const runner: OcrRunner = { async run(model, input) { const s = sessions[model]; const out = await s.run({ [s.inputNames[0]]: new ort.Tensor('float32', input.data, input.dims) }); const t = out[s.outputNames[0]]; return { data: t.data as Float32Array, dims: t.dims as number[] }; } };
    return new PpOcrEngine(runner);
  })().catch(e => { enginePromise = null; throw new Error(`The OCR engine could not load (${(e as Error).message || 'offline?'}). Reload the page and try again; your file was not uploaded.`); });
  return enginePromise;
}

/** Image file / canvas → RGBA pixels (EXIF orientation applied by the browser), long side <= maxSide. */
export async function toRgba(src: Blob | HTMLCanvasElement, maxSide = 2000): Promise<Rgba> {
  const bmp: ImageBitmap | HTMLCanvasElement = src instanceof Blob ? await createImageBitmap(src) : src;
  const s = Math.min(1, maxSide / Math.max(bmp.width, bmp.height)); const w = Math.max(1, Math.round(bmp.width * s)), h = Math.max(1, Math.round(bmp.height * s));
  const c = document.createElement('canvas'); c.width = w; c.height = h; const ctx = c.getContext('2d', { willReadFrequently: true })!;
  ctx.imageSmoothingQuality = 'high'; ctx.drawImage(bmp, 0, 0, w, h);
  if ('close' in bmp) bmp.close();
  return { width: w, height: h, data: ctx.getImageData(0, 0, w, h).data };
}
