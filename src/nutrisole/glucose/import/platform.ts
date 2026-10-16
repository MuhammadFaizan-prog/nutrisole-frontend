// Web import platform: <input type=file>, camera capture input, pdf.js text layer and
// PP-OCRv5 mobile OCR (onnxruntime-web, WASM), all in the browser. The image/PDF never leaves
// the device; the OCR runtime and models are self-hosted with the app (no CDN, no cloud API).
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

async function recognize(image: Blob | HTMLCanvasElement, mode: 'document' | 'sparse', onProgress?: (p: string) => void): Promise<OcrResult> {
  const { webOcrEngine, toRgba } = await import('../ocr/runner.web');
  const engine = await webOcrEngine(onProgress);
  const img = rgbaCache.get(image) || await toRgba(image); rgbaCache.set(image, img);
  onProgress?.(mode === 'sparse' ? 'Reading large digits (meter screen)…' : 'Reading the report…');
  return engine.recognize(img, mode, onProgress);
}
const rgbaCache = new WeakMap<object, import('../ocr/ppocr').Rgba>();
const blobFor = new WeakMap<PickedFile, Blob>();

export function createImportPlatform(): ImportPlatform {
  return {
    kind: 'web', os: 'web', ocrEngine: 'PP-OCRv5 (in your browser)', devices: null,
    pickFile: () => chooseFile('.csv,.tsv,.txt,.xlsx,.pdf,image/*,text/csv,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    captureReport: () => chooseFile('image/*', true),
    extractors: {
      pdfText: async bytes => { const { pdfTextLines } = await import('./pdfText'); return pdfTextLines(bytes); },
      pdfOcr: async (bytes, onProgress) => {
        const { pdfPageImages } = await import('./pdfText');
        const pages = await pdfPageImages(bytes); const lines: TextLine[] = []; let confSum = 0;
        for (const [i, canvas] of pages.entries()) { onProgress?.(`OCR page ${i + 1} of ${pages.length}…`); const r = await recognize(canvas, 'document', onProgress); confSum += r.confidence || 0; lines.push(...r.lines.map(l => ({ ...l, locator: `page ${i + 1} ${l.locator}` }))); }
        return { lines, confidence: pages.length ? confSum / pages.length : null, engine: 'PP-OCRv5 mobile (on-device)' };
      },
      imageOcr: (file, onProgress, mode = 'document') => { let b = blobFor.get(file); if (!b) { b = new Blob([file.bytes.slice()], { type: file.mime || 'image/png' }); blobFor.set(file, b); } return recognize(b, mode, onProgress); },
    },
  };
}
