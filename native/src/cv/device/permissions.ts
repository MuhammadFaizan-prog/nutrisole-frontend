// G9 Stage J5: camera-permission state machine for the debug CV pipeline (pure; mirrors VisionCamera 5 PermissionState).
export type CamPermissionStatus = 'not-determined' | 'authorized' | 'denied' | 'restricted';
export type PermissionAction = 'none' | 'request' | 'open_settings';
export type PermissionView = { state: 'off' | 'granted' | 'ask' | 'settings' | 'unavailable'; action: PermissionAction; showCamera: boolean; message: string };

/** What the debug overlay shows / does. With the debug flag off nothing is ever requested and no camera is shown. */
export function permissionView(debugOn: boolean, status: CamPermissionStatus | undefined, canRequest: boolean): PermissionView {
  if (!debugOn) return { state: 'off', action: 'none', showCamera: false, message: '' };
  switch (status) {
    case 'authorized': return { state: 'granted', action: 'none', showCamera: true, message: '' };
    case 'not-determined': return canRequest
      ? { state: 'ask', action: 'request', showCamera: false, message: 'Camera access is needed for the phone test.' }
      : { state: 'settings', action: 'open_settings', showCamera: false, message: 'Allow camera access in Settings.' };
    case 'denied': return { state: 'settings', action: 'open_settings', showCamera: false, message: 'Camera access was denied. Allow it in Settings.' };
    case 'restricted': return { state: 'unavailable', action: 'none', showCamera: false, message: 'Camera access is restricted on this device.' };
    default: return { state: 'unavailable', action: 'none', showCamera: false, message: 'Camera permission state unknown.' };
  }
}
