// What each platform provides to the import flow. Web: file + camera input, pdf.js and
// tesseract.js. Android/iOS: document picker, camera, ML Kit OCR, Health Connect /
// HealthKit and Bluetooth GLS. Device import does not exist on web.
import type { ConnectionStatus } from '../types';
import type { PickedFile, TextExtractors } from './fileImport';
import type { HealthConnectGlucoseResult, HealthKitGlucoseSample } from './devices';
import type { GlsDownload } from './gls';

export type HealthSourceBridge<T> = {
  status(): Promise<ConnectionStatus>;
  /** Shows the OS permission sheet (after our own rationale screen). */
  requestPermission(): Promise<ConnectionStatus>;
  read(days: number): Promise<T[]>;
  openSettings?(): void;
};
export type BleBridge = {
  status(): Promise<ConnectionStatus>;
  requestPermission(): Promise<ConnectionStatus>;
  scan(seconds: number): Promise<{ id: string; name: string | null; rssi: number | null }[]>;
  download(deviceId: string, sinceSequence: number | null): Promise<GlsDownload>;
};
export type DeviceBridges = { healthConnect: HealthSourceBridge<HealthConnectGlucoseResult> | null; healthKit: HealthSourceBridge<HealthKitGlucoseSample> | null; ble: BleBridge | null };

export type ImportPlatform = {
  kind: 'web' | 'native';
  os: 'web' | 'android' | 'ios' | 'other';
  /** Resolves null when the user cancels the picker. */
  pickFile(): Promise<PickedFile | null>;
  /** Opens the camera; resolves null when cancelled. */
  captureReport(): Promise<PickedFile | null>;
  extractors: TextExtractors;
  /** OCR engine shown in provenance and UI ("tesseract.js 7 (in-browser)", "ML Kit (on-device)"). */
  ocrEngine: string;
  devices: DeviceBridges | null;
};
