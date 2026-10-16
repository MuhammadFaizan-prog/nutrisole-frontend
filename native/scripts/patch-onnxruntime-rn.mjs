// Makes onnxruntime-react-native 1.24.3's android/build.gradle work under Gradle 9 (CI QA APK).
// 1. Gradle 9 removed org.gradle.util.VersionNumber; the RN < 0.71 fbjni branch is dead for RN 0.86,
//    so compare the already-computed minor version instead.
// 2. Pin the extracted onnxruntime-android AAR to the JS package version instead of
//    `latest.integration`, so the native lib matches the bindings and builds are reproducible.
// Idempotent; fails loudly if the upstream file no longer matches.
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const pkgPath = require.resolve('onnxruntime-react-native/package.json');
const { version } = JSON.parse(readFileSync(pkgPath, 'utf8'));
const gradle = pkgPath.replace(/package\.json$/, 'android/build.gradle');
let s = readFileSync(gradle, 'utf8');
const before = s;
s = s.replace('if (VersionNumber.parse(REACT_NATIVE_VERSION) < VersionNumber.parse("0.71")) {', 'if (REACT_NATIVE_VERSION.startsWith("0.") && REACT_NATIVE_MINOR_VERSION < 71) {');
s = s.replace(/(com\.microsoft\.onnxruntime:onnxruntime-android(?:-qnn)?):latest\.integration@aar/g, `$1:${version}@aar`);
if (s.includes('VersionNumber.parse')) { console.error('patch-onnxruntime-rn: VersionNumber still present; upstream build.gradle changed'); process.exit(1); }
if (s !== before) writeFileSync(gradle, s);
console.log(`patch-onnxruntime-rn: ${s === before ? 'already patched' : 'patched'} ${gradle} (onnxruntime-android ${version})`);
