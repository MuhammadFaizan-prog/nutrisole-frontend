// PDF text layer → lines, with pdf.js (web only; loaded lazily so it never enters the
// main bundle or the native bundle). Pure grouping is separate for tests.
import type { TextLine } from './labText';

export type PdfTextItem = { str: string; x: number; y: number; width: number; height: number };

/** Group positioned text items into reading-order lines (same baseline ± tolerance). */
export function groupTextItems(items: PdfTextItem[], page: number): TextLine[] {
  const rows: { y: number; h: number; items: PdfTextItem[] }[] = [];
  for (const it of items.filter(i => i.str.trim())) {
    const tol = Math.max(2, (it.height || 10) * 0.5);
    const row = rows.find(r => Math.abs(r.y - it.y) <= tol);
    if (row) row.items.push(it); else rows.push({ y: it.y, h: it.height, items: [it] });
  }
  return rows.sort((a, b) => b.y - a.y).map((r, i) => {
    const sorted = r.items.sort((a, b) => a.x - b.x);
    let text = ''; let end = -Infinity;
    for (const it of sorted) { const gap = it.x - end; text += text && gap > 1 ? (gap > (it.height || 10) * 1.5 ? '   ' : ' ') : ''; text += it.str; end = it.x + it.width; }
    return { text: text.replace(/\s+$/, ''), confidence: null, locator: `page ${page} line ${i + 1}` };
  });
}

type PdfJs = typeof import('pdfjs-dist');
let pdfjsPromise: Promise<PdfJs> | null = null;
async function loadPdfJs(): Promise<PdfJs> {
  if (!pdfjsPromise) pdfjsPromise = (async () => {
    const lib = await import('pdfjs-dist');
    const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url');
    lib.GlobalWorkerOptions.workerSrc = (worker as { default: string }).default;
    return lib;
  })();
  return pdfjsPromise;
}

export async function pdfTextLines(bytes: Uint8Array, lib?: PdfJs): Promise<TextLine[]> {
  const pdfjs = lib ?? await loadPdfJs();
  const task = pdfjs.getDocument({ data: bytes.slice() });
  const doc = await task.promise;
  const out: TextLine[] = [];
  for (let p = 1; p <= Math.min(doc.numPages, 10); p++) {
    const page = await doc.getPage(p); const content = await page.getTextContent();
    const items = (content.items as { str?: string; transform?: number[]; width?: number; height?: number }[]).filter(i => typeof i.str === 'string').map(i => ({ str: i.str!, x: i.transform![4], y: i.transform![5], width: i.width || 0, height: i.height || Math.abs(i.transform![3]) || 10 }));
    out.push(...groupTextItems(items, p));
  }
  await task.destroy();
  return out;
}

/** Render pages to canvases for OCR (scanned PDFs). Browser only. */
export async function pdfPageImages(bytes: Uint8Array, maxPages = 3): Promise<HTMLCanvasElement[]> {
  const pdfjs = await loadPdfJs();
  const task = pdfjs.getDocument({ data: bytes.slice() });
  const doc = await task.promise;
  const canvases: HTMLCanvasElement[] = [];
  for (let p = 1; p <= Math.min(doc.numPages, maxPages); p++) {
    const page = await doc.getPage(p); const viewport = page.getViewport({ scale: 2 });
    const canvas = document.createElement('canvas'); canvas.width = viewport.width; canvas.height = viewport.height;
    await page.render({ canvas, canvasContext: canvas.getContext('2d')!, viewport }).promise;
    canvases.push(canvas);
  }
  await task.destroy();
  return canvases;
}
