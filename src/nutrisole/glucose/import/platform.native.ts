// Android/iOS import platform. Files: @react-native-documents/picker. Camera:
// react-native-image-picker. OCR: Google ML Kit text recognition, on-device (no cloud).
// Devices: Health Connect (react-native-health-connect), Bluetooth GLS
// (react-native-ble-plx). HealthKit is a typed path only (no native module in this build).
// BETA: none of the device paths has been exercised with real hardware or a real phone.
import { PermissionsAndroid, Platform } from 'react-native';
import { pick, keepLocalCopy, types, isErrorWithCode, errorCodes } from '@react-native-documents/picker';
import { launchCamera } from 'react-native-image-picker';
import TextRecognition from '@react-native-ml-kit/text-recognition';
import { getSdkStatus, initialize, requestPermission, getGrantedPermissions, readRecords, openHealthConnectSettings, SdkAvailabilityStatus } from 'react-native-health-connect';
import { BleManager, State, type Device, type Subscription } from 'react-native-ble-plx';
import type { ConnectionStatus } from '../types';
import type { ImportPlatform, BleBridge, HealthSourceBridge } from './platform.types';
import type { PickedFile, OcrResult } from './fileImport';
import type { HealthConnectGlucoseResult, HealthKitGlucoseSample } from './devices';
import { GLS_SERVICE_UUID, GLS_MEASUREMENT_UUID, GLS_CONTEXT_UUID, GLS_RACP_UUID, downloadRecords, type GlsTransport } from './gls';
import { base64ToBytes, bytesToBase64 } from './base64';

async function readUri(uri: string): Promise<Uint8Array> {
  const blob = await (await fetch(uri)).blob();
  const dataUrl: string = await new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result)); r.onerror = () => reject(new Error('The file could not be read.')); r.readAsDataURL(blob); });
  return base64ToBytes(dataUrl.slice(dataUrl.indexOf(',') + 1));
}

async function pickFile(): Promise<PickedFile | null> {
  try {
    const [res] = await pick({ type: [types.csv, types.plainText, types.xlsx, types.pdf, types.images], mode: 'import' });
    const [copy] = await keepLocalCopy({ files: [{ uri: res.uri, fileName: res.name ?? 'import' }], destination: 'cachesDirectory' });
    if (copy.status !== 'success') throw new Error(`The file could not be copied for reading (${copy.copyError}).`);
    return { name: res.name ?? 'import', mime: res.type ?? null, bytes: await readUri(copy.localUri), uri: copy.localUri } as PickedFile & { uri: string };
  } catch (e) {
    if (isErrorWithCode(e) && e.code === errorCodes.OPERATION_CANCELED) return null;
    throw e;
  }
}

async function captureReport(): Promise<PickedFile | null> {
  if (Platform.OS === 'android') {
    const r = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA, { title: 'Camera for report scanning', message: 'NutriSole uses the camera only to photograph a lab report or meter screen. Text is read on this phone; the photo is not uploaded.', buttonPositive: 'Allow', buttonNegative: 'Not now' });
    if (r !== PermissionsAndroid.RESULTS.GRANTED) throw new Error('Camera permission was denied. You can attach a photo of the report instead, or allow the camera in Settings.');
  }
  const res = await launchCamera({ mediaType: 'photo', includeBase64: true, saveToPhotos: false, quality: 0.9, maxWidth: 2400, maxHeight: 2400 });
  if (res.didCancel) return null;
  if (res.errorCode) throw new Error(res.errorCode === 'camera_unavailable' ? 'No camera is available on this device.' : res.errorCode === 'permission' ? 'Camera permission was denied.' : res.errorMessage || 'The camera could not be opened.');
  const a = res.assets?.[0]; if (!a?.uri || !a.base64) return null;
  return { name: a.fileName || 'scan.jpg', mime: a.type || 'image/jpeg', bytes: base64ToBytes(a.base64), uri: a.uri } as PickedFile & { uri: string };
}

async function mlKitOcr(file: PickedFile): Promise<OcrResult> {
  // ML Kit reads the local file:// / content:// copy; nothing is uploaded.
  const uri = (file as PickedFile & { uri?: string }).uri;
  if (!uri) throw new Error('This image could not be opened for on-device OCR.');
  const result = await TextRecognition.recognize(uri);
  const lines = result.blocks.flatMap((b, bi) => b.lines.map((l, li) => ({ text: l.text, confidence: null, locator: `block ${bi + 1} line ${li + 1}` })));
  return { lines, confidence: null, engine: 'ML Kit (on-device)' };
}

// ---- Health Connect ----
const HC_PERMISSION = [{ accessType: 'read' as const, recordType: 'BloodGlucose' as const }];
const healthConnect: HealthSourceBridge<HealthConnectGlucoseResult> = {
  async status(): Promise<ConnectionStatus> {
    if (Platform.OS !== 'android') return { state: 'unsupported-platform', reason: 'Health Connect is an Android service.' };
    if (Number(Platform.Version) < 26) return { state: 'unsupported-device', reason: 'Health Connect needs Android 8 or newer.' };
    const sdk = await getSdkStatus();
    if (sdk === SdkAvailabilityStatus.SDK_UNAVAILABLE) return { state: 'unavailable', reason: 'Health Connect is not installed or not available on this phone.' };
    if (sdk === SdkAvailabilityStatus.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED) return { state: 'needs-update', reason: 'Health Connect needs an update from the Play Store.' };
    if (!(await initialize())) return { state: 'unavailable', reason: 'Health Connect could not be started.' };
    const granted = await getGrantedPermissions();
    return granted.some(p => p.recordType === 'BloodGlucose' && p.accessType === 'read') ? { state: 'ready', reason: 'Blood glucose read access granted.' } : { state: 'permission-required' };
  },
  async requestPermission(): Promise<ConnectionStatus> {
    const st = await this.status(); if (st.state !== 'permission-required' && st.state !== 'ready') return st;
    const granted = await requestPermission(HC_PERMISSION);
    return granted.some(p => p.recordType === 'BloodGlucose') ? { state: 'ready', reason: 'Blood glucose read access granted.' } : { state: 'permission-denied', reason: 'Read access to blood glucose was not granted. You can change this in Health Connect settings.' };
  },
  async read(days: number) {
    const end = new Date(); const start = new Date(end.getTime() - days * 86_400_000);
    const out: HealthConnectGlucoseResult[] = []; let pageToken: string | undefined;
    do {
      const res = await readRecords('BloodGlucose', { timeRangeFilter: { operator: 'between', startTime: start.toISOString(), endTime: end.toISOString() }, pageSize: 500, pageToken }) as unknown as { records: HealthConnectGlucoseResult[]; pageToken?: string };
      out.push(...res.records); pageToken = res.pageToken || undefined;
    } while (pageToken && out.length < 5000);
    return out;
  },
  openSettings: () => openHealthConnectSettings(),
};

// ---- HealthKit: typed only (no HealthKit native module is linked in this build) ----
const healthKit: HealthSourceBridge<HealthKitGlucoseSample> = {
  async status() { return Platform.OS === 'ios' ? { state: 'unavailable', reason: 'Apple Health import is typed but not built into this app yet (needs an iOS build with a HealthKit module). Unverified.' } : { state: 'unsupported-platform', reason: 'Apple Health is only on iPhone.' }; },
  async requestPermission() { return this.status(); },
  async read() { throw new Error('Apple Health import is not available in this build.'); },
};

// ---- Bluetooth Glucose Profile ----
let manager: BleManager | null = null;
const ble = (): BleManager => (manager ??= new BleManager());
const bleState = async (): Promise<ConnectionStatus | null> => {
  const s = await ble().state();
  if (s === State.PoweredOff) return { state: 'bluetooth-off', reason: 'Bluetooth is off. Turn it on and try again.' };
  if (s === State.Unsupported) return { state: 'unsupported-device', reason: 'This phone does not support Bluetooth Low Energy.' };
  if (s === State.Unauthorized) return { state: 'permission-denied', reason: 'Bluetooth permission was denied.' };
  return null;
};
const androidBlePermissions = () => Number(Platform.Version) >= 31 ? [PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN, PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT] : [PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION];
const bleBridge: BleBridge = {
  async status() {
    if (Platform.OS === 'android') { const perms = androidBlePermissions(); const ok = await Promise.all(perms.map(p => PermissionsAndroid.check(p))); if (!ok.every(Boolean)) return { state: 'permission-required' }; }
    return (await bleState()) ?? { state: 'ready', reason: 'Bluetooth is on.' };
  },
  async requestPermission() {
    if (Platform.OS === 'android') {
      const res = await PermissionsAndroid.requestMultiple(androidBlePermissions());
      if (!Object.values(res).every(v => v === PermissionsAndroid.RESULTS.GRANTED)) return { state: 'permission-denied', reason: Number(Platform.Version) >= 31 ? 'Nearby devices permission (Bluetooth scan/connect) was denied.' : 'Location permission is required for Bluetooth scanning on Android 11 and older.' };
    }
    return (await bleState()) ?? { state: 'ready', reason: 'Bluetooth is on.' };
  },
  scan(seconds) {
    return new Promise((resolve, reject) => {
      const found = new Map<string, { id: string; name: string | null; rssi: number | null }>();
      ble().startDeviceScan([GLS_SERVICE_UUID], { allowDuplicates: false }, (error, device) => {
        if (error) { ble().stopDeviceScan(); reject(new Error(error.message)); return; }
        if (device) found.set(device.id, { id: device.id, name: device.name || device.localName || null, rssi: device.rssi ?? null });
      });
      setTimeout(() => { ble().stopDeviceScan(); resolve([...found.values()]); }, seconds * 1000);
    });
  },
  async download(deviceId, sinceSequence) {
    // Bonding: GLS meters require an encrypted link for RACP; Android shows the pairing/passkey
    // dialog automatically on the first secured write (the passkey is printed on/shown by the meter).
    let device: Device = await ble().connectToDevice(deviceId, { timeout: 15_000 });
    try {
      device = await device.discoverAllServicesAndCharacteristics();
      const uuidOf = { measurement: GLS_MEASUREMENT_UUID, context: GLS_CONTEXT_UUID, racp: GLS_RACP_UUID } as const;
      const transport: GlsTransport = {
        async subscribe(kind, onValue) {
          const sub: Subscription = ble().monitorCharacteristicForDevice(deviceId, GLS_SERVICE_UUID, uuidOf[kind], (err, ch) => { if (!err && ch?.value) onValue(base64ToBytes(ch.value)); });
          return () => sub.remove();
        },
        async writeRacp(bytes) { await ble().writeCharacteristicWithResponseForDevice(deviceId, GLS_SERVICE_UUID, GLS_RACP_UUID, bytesToBase64(bytes)); },
      };
      return await downloadRecords(transport, { sinceSequence, timeoutMs: 45_000 });
    } finally { await ble().cancelDeviceConnection(deviceId).catch(() => undefined); }
  },
};

export function createImportPlatform(): ImportPlatform {
  return {
    kind: 'native', os: Platform.OS === 'android' ? 'android' : Platform.OS === 'ios' ? 'ios' : 'other', ocrEngine: 'ML Kit (on this phone)',
    pickFile, captureReport,
    extractors: { pdfText: async () => null, imageOcr: file => mlKitOcr(file) },
    devices: { healthConnect: Platform.OS === 'android' ? healthConnect : null, healthKit, ble: bleBridge },
  };
}
