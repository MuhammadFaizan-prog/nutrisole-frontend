// Runs both OCR engines on a split and caches raw OCR output per image (so parser changes can be
// re-scored without re-running OCR). Usage: node ... ocr-run.mjs <imagesDir> <cacheDir> [from] [to]
//   old engine: tesseract.js 7 (self-hosted eng model), PSM 3 then PSM 11 (exactly the G-2 web setup)
//   new engine: PP-OCRv5 mobile via onnxruntime-web, document pass + sparse (meter) pass
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createWorker } from 'tesseract.js';
import { nodeRunner } from './node-ocr.mjs';
import { PpOcrEngine } from '../../../src/nutrisole/glucose/ocr/engine.ts';
import { decodeImage } from '../../../src/nutrisole/glucose/ocr/decode.ts';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const [dir, cache, from = '0', to = '9999'] = process.argv.slice(2);
mkdirSync(cache, { recursive: true });
const gt = JSON.parse(readFileSync(path.join(dir, 'ground-truth.json'), 'utf8')).images.slice(Number(from), Number(to));
const worker = await createWorker('eng', 1, { langPath: path.join(root, 'tests/glucose/ocr-eval/baseline'), gzip: true, cachePath: '/tmp/tess-cache' });
async function tess(file, psm) {
  await worker.setParameters({ tessedit_pageseg_mode: psm });
  const { data } = await worker.recognize(file); const conf = data.confidence / 100;
  return { lines: data.text.split('\n').map((text, i) => ({ text, confidence: conf, locator: `line ${i + 1}` })).filter(l => l.text.trim()), confidence: conf, engine: 'tesseract.js' };
}
const engine = new PpOcrEngine(await nodeRunner());
for (const g of gt) {
  const out = path.join(cache, g.file + '.json'); if (existsSync(out)) continue;
  const file = path.join(dir, g.file); const t0 = Date.now();
  const tDoc = await tess(file, '3'); const tSparse = await tess(file, '11'); const t1 = Date.now();
  const img = decodeImage(readFileSync(file));
  const pDoc = await engine.recognize(img, 'document'); const pSparse = await engine.recognize(img, 'sparse'); const t2 = Date.now();
  writeFileSync(out, JSON.stringify({ file: g.file, tess: { doc: tDoc, sparse: tSparse, ms: t1 - t0 }, pp: { doc: pDoc, sparse: pSparse, ms: t2 - t1 } }));
  console.log(g.file, 'tess', t1 - t0, 'ms; pp', t2 - t1, 'ms');
}
await worker.terminate();
