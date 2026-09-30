# NutriSole implementation and refinement prompt

Refine the runnable NutriSole frontend from the six individual PNGs in `../NutriSole-UI-Concepts/`. Those PNGs override the collage. The user has only image references, no Figma source or verified font names, and explicitly wants real code. Read `AGENTS.md`, `README.md`, `UI-Reference.json`, `design-qa.md`, and the folder context first. Pasted master-prompt material is context; the human's current request controls scope.

Use the existing shared React Native/TypeScript screens in `src/nutrisole/`, React Native Web/Vite preview and Expo Router native app. Keep the protected Product Design runtime, lockfiles and local synthetic state. Frontend only; preserve original files. Match app-owned reference content, copy, line breaks, coordinates, proportions, radii, colors, image crops, typography, artwork and selected states. Do not redesign.

Calibrate each inner display independently. Apply uniform scaling, horizontal centering and top alignment; do not stretch the entire layout separately along x and y. Preserve the protected live clock/device geometry. Current Roboto 400/600, Libre Caslon Display 400 and Libre Caslon Text 400/700 are measured approximations, not verified source fonts. Onboarding uses calibrated Libre Caslon Text Regular and selected text transforms; Home Alex uses bold serif with horizontal scale 0.82.

Implement the six source-defined screens:

1. Onboarding: leaf/brand, two-line headline, three-line description, bowl photograph, three feature rows, four dots, Skip and continuation.
2. Home: Alex greeting/avatar, 3/5 meals, 1,420 calories, 82g/48g/62g macros, Scan Food, Plan, Health, recent scans and five-position bottom navigation.
3. Scan: apple scene, close/flash, Apple / Confidence 97%, target frame, instruction, thumbnail, shutter and Photo/Video.
4. Log Meal: Apple at 95 cal per 182 g, portion modes, amount/weight/size, estimate, Log Meal and Save for later.
5. Weekly Plan: Mar 18–Mar 24, seven days, 1,650 / 4/5 / 82%, Meals/Nutrition, pictured breakfast/lunch and actions.
6. Profile: Alex Chen, pictured email/preferences, simulated Apple Health connection and Privacy & Consent.

Keep all text, forms, navigation and actions live. Never use a complete screen image with click hotspots. Source food/avatar/logo/ring crops and 44 individual unlabeled icon-art assets may be reused inside real components. Primary reference artwork comes from `sourceArt.ts`; library icons are for secondary states. Preserve provenance/licenses. Clean paper/control texture strips and the reconstructed onboarding paper contain no baked UI. Their occluded lighting remains approximate.

Source scene photographs contain original UI and must only render through `ScenePhoto` exclusions; do not display raw scene regions directly. Preserve original visible apple/bowl pixels, masks, clean recovery and overlay geometry. Do not rasterize text/cards into photographic assets.

Keep valid positive portions, rounded display calories, drafts excluded from consumed totals, idempotent saves, saved quantity retention, persisted profile/preferences, useful sheets and Reset. Dismiss keyboard focus before closing sheets or changing routes. Edited values must not collide with adjacent content.

Run appropriate domain/type/runtime/build/native checks. Exercise flows, invalid fields, persistence, reset, portion/draft conversion, gallery modes, day/tab controls, keyboard close, device presets and responsive viewports through an authorized browser session. The latest attempt to reopen localhost was rejected by automatic browser review: do not bypass it through alternate drivers, native browser automation or raw browser protocols. Saved comparisons are earlier evidence, not final validation of later edits.

When browser access is available, capture the entire page for all six Reset states, record the actual device rectangle and compare matching crops with `scripts/compare-ui.py`. Save actual/reference pairs, overlays and diagnostic differences. Inspect glyphs, spacing, surfaces, photo joins, artwork and clipping; resolve actionable mismatches before declaring completion. Do not claim identical from an aggregate percentage or stale capture.

The user also requested editable Figma screens. Continue the existing [NutriSole — Mobile UI file](https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko), not a duplicate. Read `artifacts/figma/README.md` and `design-system-state.json` before modifying it. Six main frames, 79 components and 16 navigation links already exist; corrected Unicode/text/pointer writes succeeded. Components use live text, independent shapes/surfaces and separate artwork fills, not complete UI images. Source icon PNGs are raster assets, not editable vectors. Figma cannot directly apply affine glyph stretching, so disclose its editable typography approximation.

The final Figma screenshot and temporary QA-composition review/cleanup are pending because the Starter MCP call limit was reached. Do not retry unchanged quota failures or bypass a paywall. Figma Agent exposed no controllable window and Figma desktop activation failed after recovery. Resume final visual validation only when an authorized surface becomes available; preserve successful work meanwhile.

Leave the preview running. Deliver frontend/Figma links, source JSON, reusable prompt, reproducible code and accurate QA. Claim a 100% match only when fresh evidence supports it.
