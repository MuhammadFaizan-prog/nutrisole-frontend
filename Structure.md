# NutriSole source structure

`src/Prototype.tsx` integrates app with the protected preview runtime. `src/prototype.css` supplies app-specific fonts, surfaces, and secondary-state styles. `src/nutrisole/` contains domain, fixture store, measured layouts, reusable UI, six screens, and web/native adapters. `assets/source/` holds recovered assets and provenance. `public/nutrisole/` serves those assets for preview. `native/` is the Expo entry and npm dependency context.

`tests/` holds domain checks. `artifacts/qa/` contains rendered evidence and comparison artifacts. `design-qa.md` records the final visual gate. `assets/icons/` holds pinned library SVG assets and license. `native/src/app/` contains Expo Router entries. `README.md`, `UI_BUILD_PROMPT.md` and `UI-Reference.json` provide the handoff. Existing `src/mobile/`, protected root runtime/config files, and template assets remain unchanged.
