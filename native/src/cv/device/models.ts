// G9 Stage J5: where the debug build loads its ONNX weights from. Weights are NOT in this branch's Git history (repo policy). J7: the Android QA APK built by
// .github/workflows/android-qa-apk.yml bundles h2 + g3_det as assets/models/<file> (fetched from orphan branch qa-models-j7 + sha256-checked at build
// time, never committed to this branch); src/cv/device/modelSource.ts loads the bundled copy first and falls back to the adb push into DEVICE_MODEL_DIR
// (docs/cv/gauntlet/G9_stageJ5_ANDROID_P1.md). Either way the file must match bytes + sha256 below, or it is not loaded.
export const APP_ID = 'com.muhammadfaizan.nutrisole';
export const DEVICE_MODEL_DIR = `/sdcard/Android/data/${APP_ID}/files/models`;
export const DEVICE_MODELS = {
  h2: { file: 'h2_mnv3s.onnx', bytes: 6133032, sha256: '20898d7cdfc1f0580cdf3f58d6d3d63528b9c04178d4603b49dee4ba1b89a22e', from: 'G9 Stage H v2 (h2_mnv3s.pt 02b402a1...)' },
  g3_det: { file: 'det_yolo11n_640_raw.onnx', bytes: 10600677, sha256: 'c6fcb32a5fb2f51ba34e88ce9106a52d6bbd12ae385ca8361b292d54e3d340c1', from: 'G3 detector k11_480 (best.pt 29cc5212...)' },
  condition: { file: 'E_224_e15_b64_sgd01.onnx', bytes: 6161022, sha256: 'c51d21994444d2a5a43907cae66a36ac7fb63b19b1198dda891f24af751f709b', from: 'G3 E224 classifier (best.pt 320b84b0...); not used by the debug screen (grades blocked)' },
} as const;
export const modelPath = (k: keyof typeof DEVICE_MODELS) => `${DEVICE_MODEL_DIR}/${DEVICE_MODELS[k].file}`;
