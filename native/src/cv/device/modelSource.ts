// G9 Stage J7 (cv-gauntlet-device): where the debug camera's ONNX weights come from, in this order:
//   1. bundled: the QA APK carries them as Android assets (assets/models/<file>); the NsModelAssets native module copies the asset to
//      the app's internal files dir and returns its path, size and SHA-256 (computed natively);
//   2. adb_push (fallback): the hash-verified PowerShell push to DEVICE_MODEL_DIR (G9 Stage J5 P1 guide), hashed by the same module.
// A candidate is accepted ONLY when its size and SHA-256 equal DEVICE_MODELS (models.ts). Missing module, missing file or a mismatch
// is reported as "Models not loaded" with the reasons; there is never a mock / placeholder model or a fake prediction.
import { DEVICE_MODELS, modelPath } from './models.ts';

export type ModelKey = 'h2' | 'g3_det';
export type ModelFileInfo = { path: string; bytes: number; sha256: string };
/** Shape of NativeModules.NsModelAssets (native/android/app/src/main/java/com/muhammadfaizan/nutrisole/ModelAssetsModule.kt). */
export type ModelNative = {
  prepareBundled: (file: string) => Promise<ModelFileInfo>;
  describeFile: (path: string) => Promise<ModelFileInfo>;
};
export type ModelSource = 'bundled' | 'adb_push';
export type ModelResolution =
  | { ok: true; key: ModelKey; path: string; source: ModelSource; tried: string[] }
  | { ok: false; key: ModelKey; reason: string; tried: string[] };

export const BUNDLED_MODEL_ASSET_DIR = 'models';
export const MODELS_NOT_LOADED = 'Models not loaded';

const msg = (e: unknown) => String((e as { message?: unknown })?.message ?? e).slice(0, 120);

export async function resolveModel(key: ModelKey, native: ModelNative | null | undefined): Promise<ModelResolution> {
  const spec = DEVICE_MODELS[key];
  const tried: string[] = [];
  if (!native || typeof native.prepareBundled !== 'function' || typeof native.describeFile !== 'function') {
    return { ok: false, key, reason: 'native module NsModelAssets not available in this build', tried };
  }
  const attempt = async (source: ModelSource, get: () => Promise<ModelFileInfo>): Promise<ModelResolution | null> => {
    try {
      const f = await get();
      const sha = String(f?.sha256 ?? '').toLowerCase();
      if (sha === spec.sha256 && Number(f.bytes) === spec.bytes && typeof f.path === 'string' && f.path) {
        return { ok: true, key, path: f.path, source, tried: [...tried, `${source}: sha256 ok`] };
      }
      tried.push(`${source}: sha256 mismatch (got ${sha.slice(0, 8) || '-'}, bytes ${f?.bytes ?? '-'}; want ${spec.sha256.slice(0, 8)}, bytes ${spec.bytes})`);
    } catch (e) {
      tried.push(`${source}: ${msg(e)}`);
    }
    return null;
  };
  return (await attempt('bundled', () => native.prepareBundled(spec.file)))
    ?? (await attempt('adb_push', () => native.describeFile(modelPath(key))))
    ?? { ok: false, key, reason: tried.join('; '), tried };
}

/** Both sessions are required; returns the paths or one human-readable "Models not loaded" message. */
export async function resolveDebugModels(native: ModelNative | null | undefined): Promise<
  { ok: true; paths: Record<ModelKey, string>; lines: string[] } | { ok: false; message: string; lines: string[] }> {
  const rs = [await resolveModel('h2', native), await resolveModel('g3_det', native)];
  const lines = rs.map((r) => r.ok
    ? `NSCV model_source model=${r.key} source=${r.source} sha256=ok`
    : `NSCV model_source model=${r.key} source=none reason=${r.reason.replace(/\s+/g, '_').slice(0, 160)}`);
  const bad = rs.filter((r) => !r.ok) as Extract<ModelResolution, { ok: false }>[];
  if (bad.length) {
    return { ok: false, lines, message: `${MODELS_NOT_LOADED}: ${bad.map((b) => `${DEVICE_MODELS[b.key].file} (${b.reason})`).join('; ')}` };
  }
  const ok = rs as Extract<ModelResolution, { ok: true }>[];
  return { ok: true, lines, paths: { h2: ok[0].path, g3_det: ok[1].path } };
}
