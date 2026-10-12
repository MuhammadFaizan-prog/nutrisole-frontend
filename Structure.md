# NutriSole source structure

`src/Prototype.tsx` integrates app with the protected preview runtime. `src/prototype.css` supplies app-specific fonts, surfaces, and secondary-state styles. `src/nutrisole/` contains domain, fixture store, measured layouts, reusable UI, six screens, and web/native adapters. `assets/source/` holds recovered assets and provenance. `public/nutrisole/` serves those assets for preview. `native/` is the plain React Native 0.86 app (no Expo) and its npm dependency context.

`tests/` holds domain checks. `artifacts/qa/` contains rendered evidence and comparison artifacts. `design-qa.md` records the final visual gate. `assets/icons/` holds pinned library SVG assets and license. `native/responsive/` holds the native screen adapters; `native/src/cv/` holds the pure-TypeScript computer-vision contract and pipeline (preprocess, postprocess, tracker, rules, labels). `README.md`, `UI_BUILD_PROMPT.md` and `UI-Reference.json` provide the handoff. Existing `src/mobile/`, protected root runtime/config files, and template assets remain unchanged.


`ml/` holds the computer-vision data, training, evaluation, grading and export code (`ml/data`, `ml/configs`, `ml/train`, `ml/eval`, `ml/grading`, `ml/export`, `ml/runs`, `ml/models`); `docs/cv/` holds the CV data register, licences, labelling handbook, dashboard and gauntlet reports. Raw data and weights are git-ignored.
