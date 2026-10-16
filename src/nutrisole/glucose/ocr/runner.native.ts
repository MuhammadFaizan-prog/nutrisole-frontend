// Android adapter for the PP-OCRv5 pipeline: onnxruntime-react-native (JSI, CPU). The two
// .onnx models are bundled into the APK as Metro raw resources (the same files the web app
// serves from public/ocr/ppocrv5), read once on first use; no network, nothing uploaded.
import { Image, Platform } from 'react-native';
import { InferenceSession, Tensor } from 'onnxruntime-react-native';
import type { OcrRunner } from './ppocr';
import { PpOcrEngine } from './engine';
import { base64ToBytes } from '../import/base64';

const APP_ID = 'com.muhammadfaizan.nutrisole';
/* eslint-disable @typescript-eslint/no-require-imports */
const MODELS = { det: require('../../../../public/ocr/ppocrv5/det.onnx'), rec: require('../../../../public/ocr/ppocrv5/rec_en.onnx') } as const;

/** Release builds: Metro puts non-image assets in res/raw and reports the resource name; dev: a Metro URL. */
export function modelUri(asset: number): string {
  const src = Image.resolveAssetSource(asset); const uri = src?.uri || '';
  if (/^(https?|file|content|android\.resource):/.test(uri)) return uri;
  return Platform.OS === 'android' ? `android.resource://${APP_ID}/raw/${uri}` : uri;
}

async function readBytes(uri: string): Promise<Uint8Array> {
  const blob = await (await fetch(uri)).blob();
  const dataUrl: string = await new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result)); r.onerror = () => reject(new Error('The OCR model could not be read from the app package.')); r.readAsDataURL(blob); });
  return base64ToBytes(dataUrl.slice(dataUrl.indexOf(',') + 1));
}

let enginePromise: Promise<PpOcrEngine> | null = null;
export function nativeOcrEngine(onProgress?: (p: string) => void): Promise<PpOcrEngine> {
  if (!enginePromise) enginePromise = (async () => {
    onProgress?.('Loading the on-device OCR engine…');
    const make = async (asset: number) => { const b = await readBytes(modelUri(asset)); return InferenceSession.create(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer); };
    const sessions = { det: await make(MODELS.det), rec: await make(MODELS.rec) };
    const runner: OcrRunner = {
      async run(model, input) {
        const s = sessions[model];
        const out = await s.run({ [s.inputNames[0]]: new Tensor('float32', input.data, input.dims) });
        const t = out[s.outputNames[0]];
        return { data: t.data as Float32Array, dims: t.dims as number[] };
      },
    };
    return new PpOcrEngine(runner);
  })().catch(e => { enginePromise = null; throw new Error(`The on-device OCR engine could not start (${(e as Error).message}).`); });
  return enginePromise;
}
