// G9 Stage J7 (cv-gauntlet-device): onnxruntime-react-native 1.24.3's android/build.gradle uses org.gradle.util.VersionNumber,
// which Gradle 9 removed ("Could not get unknown property 'VersionNumber'"), so the project's pinned Gradle 9.3.1 cannot evaluate
// it. Replace that single RN-version check (< 0.71, false for RN 0.86) with an equivalent numeric comparison. Idempotent; no other
// line of the library changes; exits quietly when the package or the pattern is absent. Runs as native postinstall.
const fs = require('fs');
const path = require('path');
const f = path.join(__dirname, '..', 'node_modules', 'onnxruntime-react-native', 'android', 'build.gradle');
if (!fs.existsSync(f)) process.exit(0);
const s = fs.readFileSync(f, 'utf8');
const from = 'if (VersionNumber.parse(REACT_NATIVE_VERSION) < VersionNumber.parse("0.71")) {';
const to = 'if (REACT_NATIVE_VERSION.tokenize(".")[0].toInteger() == 0 && REACT_NATIVE_VERSION.tokenize(".")[1].toInteger() < 71) { // patched for Gradle 9 (J7)';
if (s.includes(from)) { fs.writeFileSync(f, s.replace(from, to)); console.log('patched onnxruntime-react-native build.gradle for Gradle 9'); }
else if (s.includes(to)) console.log('onnxruntime-react-native build.gradle already patched');
else console.warn('onnxruntime-react-native build.gradle: VersionNumber pattern not found, left unchanged');
