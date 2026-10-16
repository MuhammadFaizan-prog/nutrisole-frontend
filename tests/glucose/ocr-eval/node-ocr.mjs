// Node adapter for the shared PP-OCR pipeline: onnxruntime-web (WASM, same runtime as the web app).
import * as ort from 'onnxruntime-web';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
ort.env.wasm.numThreads = 1; ort.env.logLevel = 'error';
let sessions = null;
export async function nodeRunner() {
  const opt = { logSeverityLevel: 3 };
  if (!sessions) sessions = { det: await ort.InferenceSession.create(readFileSync(path.join(root, 'public/ocr/ppocrv5/det.onnx')), opt), rec: await ort.InferenceSession.create(readFileSync(path.join(root, 'public/ocr/ppocrv5/rec_en.onnx')), opt) };
  return { async run(model, input) { const s = sessions[model]; const out = await s.run({ [s.inputNames[0]]: new ort.Tensor('float32', input.data, input.dims) }); const t = out[s.outputNames[0]]; return { data: t.data, dims: t.dims }; } };
}
