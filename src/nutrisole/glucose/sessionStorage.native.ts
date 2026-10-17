import { NativeModules, Platform } from 'react-native';
import type { GlucoseStorage } from './types';
type SessionBridge = { readSession(project: string): Promise<string | null>; writeSession(project: string, value: string): Promise<void> };
export function accountSessionStorage(url: string): GlucoseStorage | undefined {
  if (Platform.OS !== 'android') return undefined;
  const bridge = NativeModules.NutriSoleSession as SessionBridge | undefined;
  if (!bridge) throw new Error('Install the latest NutriSole app to sign in securely.');
  return { read: () => bridge.readSession(url), write: value => bridge.writeSession(url, value) };
}
