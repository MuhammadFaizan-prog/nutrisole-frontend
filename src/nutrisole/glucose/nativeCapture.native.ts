import { NativeEventEmitter, NativeModules } from 'react-native';
import type { GlucoseStorage } from './types';
import type { NativeCaptureResult } from './ocr/nativeResult';
import { nativeCaptureResult } from './ocr/nativeResult';
import type { OcrResult, PickedFile } from './import/fileImport';

type CaptureBridge = {
  readHistory(): Promise<string | null>;
  writeHistory(value: string): Promise<void>;
  recognize(uri: string, pdf: boolean, requestId: string): Promise<NativeCaptureResult>;
  cancelRecognition(requestId: string): void;
  addListener(event: string): void;
  removeListeners(count: number): void;
};
const bridge = () => {
  const b = NativeModules.NutriSoleGlucose as CaptureBridge | undefined;
  if (!b) throw new Error('The Android glucose reader is missing from this build. Install the updated NutriSole APK.');
  return b;
};
export const phoneGlucoseStorage: GlucoseStorage = { read: () => bridge().readHistory(), write: value => bridge().writeHistory(value) };

export async function recognizeOnAndroid(file: PickedFile, pdf: boolean, onProgress?: (message: string) => void, signal?: AbortSignal): Promise<OcrResult> {
  if (!file.uri) throw new Error('This file has no readable location on the phone. Choose it again.');
  if (signal?.aborted) throw new Error('Import cancelled.');
  const native = bridge(); const id = `glucose-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const events = new NativeEventEmitter(native);
  const sub = events.addListener('NutriSoleGlucoseProgress', (e: { requestId: string; message: string }) => { if (e.requestId === id) onProgress?.(e.message); });
  const cancel = () => native.cancelRecognition(id);
  signal?.addEventListener('abort', cancel, { once: true });
  try { return nativeCaptureResult(await native.recognize(file.uri, pdf, id)); }
  finally { sub.remove(); signal?.removeEventListener('abort', cancel); }
}
