// G9 Stage J4 CLI: model-runtime presence check. Read-only; installs nothing.
// Usage (from native/):  node --experimental-strip-types scripts/check-cv-runtime.ts [--models-dir <dir relative to native/>] [--json] [--strict]
// Exit code 0 always, unless --strict and not ready (then 1).
import { existsSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkRuntime, formatReport, CV_PACKAGES, MODEL_FILES, DEFAULT_MODELS_DIR } from '../src/cv/runtimeCheck.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const at = args.indexOf('--models-dir');
const modelsDir = at >= 0 ? args[at + 1] : DEFAULT_MODELS_DIR;
const pkg = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'));
const declared = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
const installed: Record<string, string | null> = {};
for (const p of CV_PACKAGES) {
  const pj = path.join(root, 'node_modules', p.name, 'package.json');
  installed[p.name] = existsSync(pj) ? JSON.parse(readFileSync(pj, 'utf8')).version ?? null : null;
}
const modelFiles: Record<string, number | null> = {};
for (const m of MODEL_FILES) {
  const fp = path.join(root, modelsDir, m.file);
  modelFiles[m.file] = existsSync(fp) ? statSync(fp).size : null;
}
const mf = path.join(root, 'android/app/src/main/AndroidManifest.xml');
const report = checkRuntime({ declared, installed, modelFiles, androidManifest: existsSync(mf) ? readFileSync(mf, 'utf8') : null, modelsDir });
console.log(args.includes('--json') ? JSON.stringify(report, null, 1) : formatReport(report));
if (args.includes('--strict') && !report.ready) process.exit(1);
