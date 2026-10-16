# Validation results — 2026-10-15

**Stage J preparation is audited; human verification and H3 remain BLOCKED.**
All test annotations were synthetic temporary fixtures. No genuine human CSV or AI handoff was supplied. No model was trained,
promoted or evaluated on pilot photos. M-TEST image content was never opened.

| Check | Actual result |
|---|---|
| Full existing Python suite, including new Stage J tests | **105 passed**; UTF-8 mode and temporary checkout-root adapter for the existing Linux-only camera test |
| Stage J subset (included in 105) | **36 passed**, including AI-copy rejection, H3 without human evidence, immutable agreement and adjudication/readiness regressions |
| Native TypeScript tests | **122 passed** |
| Root domain tests | **5 passed** |
| Original-screen/expansion tests | **8 passed**, original-screen/shared-asset baseline preserved |
| Sites packaging tests | **4 passed** |
| Protected mobile runtime hashes | **28 protected files passed** |
| Web production build | **Passed**; existing large-chunk warning remains |
| Original offline labeling HTML, both copies | **Passed**, offline contexts, 265 exported rows each, save/reload/import, tags and Unicode/quote/comma/newline escaping; zero external requests/page errors |
| Pilot ZIP/photo integrity | **Passed**: 265 matching IDs, same JPEG SHA256 per ID, different orders, both recorded package SHA256 values match; zero corrupt/missing/duplicate IDs |
| Pilot duplicate candidates | **5 perceptual candidate pairs**, zero exact JPEG duplicates; review pending, no images removed |
| Stored source/split audit | **956 items checked**, zero current cross-split conflicts or manifest split mismatches; earlier reference/source/session/original-byte checks unavailable |
| Frozen historical text inputs | **30 files preserved**; exact initial checkout hashes plus portable LF-normalized committed-text hashes |
| Native typecheck | **Fails** in unchanged CV test files: Buffer/URL overload and `URLSearchParamsIterator[Symbol.dispose]` type incompatibilities. Native source/tests/dependencies were not edited by this change |
| Standard rendered runtime command | **Could not launch** any of 8 tests: requested `chromium_headless_shell-1228` executable is not installed |
| Runtime with isolated cached Chromium 145 override | **6 passed / 2 failed**: first-test navigation timeout and keyboard-dock dismissal assertion |
| Keyboard assertion on untouched checkpoint | **Same failure reproduced** on an extracted `4d35a7c426cbb2820fa80d98e2a7a357bc0c3d36` baseline with identical dependencies/browser; this is not a Stage J regression |
| Per-file Commons live metadata refresh | **Not verified**; direct API probe for excluded c0350 failed with connection reset (see JSON). Existing exclusion remains |
| Publisher dataset page spot-checks | Six source version-1 pages checked; recorded permissions still lack original-byte binding. See separate source permission notes |
| Independent code review | Three actionable findings fixed and regression-tested; reviewer rechecked all three and 36 tests, with no further actionable findings |

The first full Python attempt could not collect ByteTrack because Ultralytics was missing; installing the existing test dependency
in the isolated environment enabled the final **105/105** run. Windows default encoding caused Urdu fixture failures before
`-X utf8` was used. The legacy camera-test root was adapted **only in the test process**, preserving its original assertions and
all checked-in evaluation code. Exact dependency versions are in `G9J_test_environment.txt`.

The existing optional H2 ONNX test returns when its binary is absent. Its collected pass is **not actual checkpoint/ONNX
validation**. G3/H2 weight binaries and original source image stores do not exist in this Windows checkout; existing references,
configurations and evaluation history remain unchanged. Tests do not replace physical-device, camera, backend or installer QA.

## Scope and protection evidence

Checkpoint: `checkpoint/g9j-before-handoff-20261015` at `4d35a7c426cbb2820fa80d98e2a7a357bc0c3d36`.
`git diff --quiet` against that checkpoint passed for `src`, `native`, `ml/eval`, `ml/grading`, `ml/prices`, `ml/data`, G3,
Stage H/I, and the frozen Stage J readiness document. Only Stage J workflow scripts/tests, new versioned handoff reports,
evidence-preserving Git attributes and usage documentation are changed. No merge into main.

Current candidate membership is preserved. The earlier Stage I-to-J change (486 to 485 eval images by excluding c0350 for
license reasons) is documented rather than repeated as an unconditional unchanged-membership claim.

## Reproduce the rendered comparison

Use the original `npm run test:runtime -- --reporter=line --workers=1` for the standard launch. To reproduce the cached-browser
run without editing protected project configuration, use a temporary Playwright configuration that imports the repository's
`playwright.config.ts`, retains its tests/assertions, and sets `use.launchOptions.executablePath` to the cached
`chromium-1208/chrome-win64/chrome.exe`. Retain the original test directory and set webServer cwd to the repository.

The checkpoint comparison extracted the original tracked `src`, `public`, `assets`, `tests`, `scripts`, `worker`, `.openai`,
package/config files and `mobile-runtime.lock.json` into a fresh temporary directory, with a junction to the same node_modules.
Its temporary config used port 4186 and a 60-second test budget to allow cold startup. The unchanged 5-second keyboard assertion
still failed (`data-visible` remained `true`, expected `false`). No production runtime file was changed to make this pass.

See `docs/cv/gauntlet/G9J_handoff_workflow.md` for every dataset, agreement, adjudication and preservation command. Current
readiness is machine-readable in `G9J_H3_readiness.json`. Real independent exports and third-human decisions are the next input.
