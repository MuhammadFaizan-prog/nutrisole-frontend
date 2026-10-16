// Base64 <-> bytes without Buffer/atob (Hermes-safe). Used for BLE values and file reads.
const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const L = new Int16Array(128).fill(-1); for (let i = 0; i < A.length; i++) L[A.charCodeAt(i)] = i; L['-'.charCodeAt(0)] = 62; L['_'.charCodeAt(0)] = 63;
export function base64ToBytes(b64: string): Uint8Array {
  const clean = b64.replace(/[^A-Za-z0-9+/_-]/g, '');
  const out = new Uint8Array(Math.floor(clean.length * 3 / 4)); let o = 0, buf = 0, bits = 0;
  for (let i = 0; i < clean.length; i++) { buf = (buf << 6) | L[clean.charCodeAt(i)]; bits += 6; if (bits >= 8) { bits -= 8; out[o++] = (buf >> bits) & 0xff; } }
  return out.subarray(0, o);
}
export function bytesToBase64(bytes: Uint8Array): string {
  let s = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const n = (bytes[i] << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0);
    s += A[(n >> 18) & 63] + A[(n >> 12) & 63] + (i + 1 < bytes.length ? A[(n >> 6) & 63] : '=') + (i + 2 < bytes.length ? A[n & 63] : '=');
  }
  return s;
}
