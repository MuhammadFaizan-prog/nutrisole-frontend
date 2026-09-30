# NutriSole added frontend flows

The 30 missing-screen concepts from the document coverage audit are implemented as real React Native/TypeScript components. A flow directory and a separate selected-food portion screen bring the expansion to 32 routes. The original six screen modules, their shared UI and source artwork are unchanged; 119 baseline file hashes and 28 protected runtime hashes pass.

[Open the running frontend](http://localhost:4173/). The preview is left on **flow directory**. The screen selector also opens every new view. The existing Health and History destinations now reach the expanded glucose/history views. The new flow session is separate from the original demo store and clears on reload.

## Included views

| Area | Screens |
| --- | --- |
| Accounts | Sign in, create account, verify email, recover account, reset password |
| Food | Assessment result, market reference, capture retry, food selector, nutrition details |
| Health | Glucose overview, add reading, reading detail, health connections |
| Plans | Plan generation, activity plan, plan rationale |
| Foot support | Questionnaire, general guidance |
| Assistance and controls | Assistant, privacy/data rights, reminders |
| Records | Report output, report status, personal history |
| Staff | Catalog queue/review, model release, operations audit, report triage |
| Added navigation | Flow directory, selected-food portion confirmation |

Text, shapes, controls, inputs, icons and state are code. Three new individual photo crops supplement the existing avatar/food/leaf assets. No complete UI concept PNG is rendered as a screen or hidden behind hotspots. `asset-provenance.json` records the crops.

## Behaviour and limits

Account validation, verification/recovery states, food correction, portion calculations, reading review/edit/removal, plan/foot choices, scripted Assistant answers, report review, privacy exports, reminder preferences and staff gate previews are interactive. Invalid portions/readings are rejected. A recorded foot concern visibly defers activity. Publishing and model activation remain disabled while their sample evidence gates are incomplete.

This is frontend only. There is no real authentication, password recovery, AI inference, price feed, camera upload, health-provider import, notification scheduling or staff access control. New passwords are never persisted. Health readings and other new records are session data. Original demo fixtures retain their previous storage behaviour.

## Verification

- 8 expansion tests, 5 original domain tests and 4 Sites packaging tests pass.
- Root/native TypeScript, Expo lint, web build and iOS/Android exports pass. No device/emulator or signed-app verification is claimed.
- Fresh browser captures cover all 30 concept screens, with a loaded-photo follow-up for the retry view. No console errors were observed in this run.
- Browser actions verified food correction/portion logging, invalid quantities, manual glucose review/save, foot concern deferral, first-tap keyboard submission, account validation, report confirmation, and disabled staff publishing/activation. Pixel 10 food selection has no page horizontal overflow.
- Figma importer passes a local mock-SDK construction test and a check against Figma's official API typings. Those checks do **not** prove a successful live import.

`browser/capture-evidence.json` records the latest rendered screens. `browser/comparison-1.jpg` through `comparison-5.jpg` pair code captures with all 30 concepts. Individual viewport captures and key interaction captures remain alongside them. `browser-checks.json` distinguishes directly exercised behaviours from structural checks.

## Fidelity and Figma status

Layout, account cards, input borders, typography, button arrows, source photos and selection outlines were refined after browser comparison. The concepts omit OS chrome; the frontend preserves the template's live status bar, device cutout and home indicator. Exact fonts, texture/shadow treatment and several component details remain approximations. **A 100% image match is not certified.**

The live Figma additions are **imported as native editable design** on page `34:254`. The user-authorized local plugin recovered the page after Windows was unlocked. The live design has 32 primary frames, 53 states, 80 overlays and six editable continuation copies. Inspection found no missing navigation destinations and confirmed all six original frames were unchanged. All 32 primary frames received native-export visual review, with 455 icon instances refined afterward. Full manual prototype navigation QA remains pending. The package and live evidence are in `../figma-expansion/`.

## Implementation

`src/nutrisole/extensions/model.ts` defines semantic layers shared by code and the Figma importer. `ExpansionScreen.tsx`, platform adapters, `domain.ts` and `useExpansion.ts` render and operate the added flows. Only routing wrappers/types were adjusted to expose the additions. Existing screen implementations and protected device code remain intact.

`npm run test:expansion` checks the expansion; `npm run figma:build` rebuilds the package. `scripts/compare-expansion.py` prepares the diagnostic contact sheets from fresh screenshots. Original documents and the coverage artifacts are preserved.
