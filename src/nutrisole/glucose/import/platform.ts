// Web import platform: <input type=file>, camera capture input, pdf.js text layer and
// tesseract.js OCR, all in the browser. The image/PDF never leaves the device, and the OCR
// engine (worker + WASM core) and English model are self-hosted with the app (no CDN).
import type { ImportPlatform } from './platform.types';
import type { OcrResult, PickedFile } from './fileImport';
import type { TextLine } from './labText';

function chooseFile(accept: string, capture = false): Promise<PickedFile | null> {
  return new Promise(resolve => {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = accept; if (capture) input.setAttribute('capture', 'environment');
    input.style.position = 'fixed'; input.style.left = '-1000px'; input.setAttribute('data-testid', capture ? 'glucose-camera-input' : 'glucose-file-input');
    let settled = false;
    const done = (v: PickedFile | null) => { if (settled) return; settled = true; input.remove(); resolve(v); };
    input.addEventListener('change', async () => {
      const f = input.files?.[0]; if (!f) return done(null);
      done({ name: f.name, mime: f.type || null, bytes: new Uint8Array(await f.arrayBuffer()) });
    });
    input.addEventListener('cancel', () => done(null));
    document.body.appendChild(input); input.click();
  });
}

type Worker = { recognize(img: unknown): Promise<{ data: { text: string; confidence: number } }>; setParameters(p: Record<string, string>): Promise<unknown> };
let workerPromise: Promise<Worker> | null = null;
async function ocrWorker(onProgress?: (p: string) => void): Promise<Worker> {
  if (!workerPromise) workerPromise = (async () => {
    onProgress?.('Loading the in-browser OCR engine…');
    const [{ createWorker }, workerUrl, coreUrl] = await Promise.all([
      import('tesseract.js'),
      import('tesseract.js/dist/worker.min.js?url'),
      import('tesseract.js-core/tesseract-core-simd-lstm.wasm.js?url'),
    ]);
    const base = (import.meta as unknown as { env?: { BASE_URL?: string } }).env?.BASE_URL || '/';
    return await createWorker('eng', 1, { workerPath: (workerUrl as { default: string }).default, corePath: (coreUrl as { default: string }).default, langPath: `${base}tesseract`, gzip: true, workerBlobURL: false }) as unknown as Worker;
  })().catch(e => { workerPromise = null; throw new Error(`The OCR engine could not load (${(e as Error).message || 'offline?'}). Check your connection and try again; your file was not uploaded.`); });
  return workerPromise;
}
async function recognize(image: unknown, mode: 'document' | 'sparse', onProgress?: (p: string) => void): Promise<OcrResult> {
  const w = await ocrWorker(onProgress);
  onProgress?.(mode === 'sparse' ? 'Reading large text (meter screen)…' : 'Reading the report…');
  await w.setParameters({ tessedit_pageseg_mode: mode === 'sparse' ? '11' : '3' });
  const { data } = await w.recognize(image);
  const conf = data.confidence / 100;
  const lines: TextLine[] = data.text.split('\n').map((text, i) => ({ text, confidence: conf, locator: `line ${i + 1}` })).filter(l => l.text.trim());
  return { lines, confidence: conf, engine: 'tesseract.js' };
}

export function createImportPlatform(): ImportPlatform {
  return {
    kind: 'web', os: 'web', ocrEngine: 'tesseract.js (in your browser)', devices: null,
    pickFile: () => chooseFile('.csv,.tsv,.txt,.xlsx,.pdf,image/*,text/csv,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    captureReport: () => chooseFile('image/*', true),
    extractors: {
      pdfText: async bytes => { const { pdfTextLines } = await import('./pdfText'); return pdfTextLines(bytes); },
      pdfOcr: async (bytes, onProgress) => {
        const { pdfPageImages } = await import('./pdfText');
        const pages = await pdfPageImages(bytes); const lines: TextLine[] = []; let confSum = 0;
        for (const [i, canvas] of pages.entries()) { onProgress?.(`OCR page ${i + 1} of ${pages.length}…`); const r = await recognize(canvas, 'document', onProgress); confSum += r.confidence || 0; lines.push(...r.lines.map(l => ({ ...l, locator: `page ${i + 1} ${l.locator}` }))); }
        return { lines, confidence: pages.length ? confSum / pages.length : null, engine: 'tesseract.js' };
      },
      imageOcr: (file, onProgress, mode = 'document') => recognize(new Blob([file.bytes.slice()], { type: file.mime || 'image/png' }), mode, onProgress),
    },
  };
}
