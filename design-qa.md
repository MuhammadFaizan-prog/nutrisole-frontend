# NutriSole design QA — 2026-09-30

The original six-screen frontend and its existing Figma recreation are preserved. The 30 added concepts are implemented as code with two supporting routes. Build/type/tests and runtime integrity pass. Added-screen browser captures are fresh. **The full handoff remains blocked:** live Figma expansion import and post-import verification are unavailable, and a 100% image match is not verified.

## Added-flow QA

The expansion lives in `src/nutrisole/extensions/`; 119 original implementation/artwork hashes and 28 runtime hashes pass. The existing browser tab became available through its original CUA API on 2026-09-30. All 30 selected concepts were freshly captured after the account/input/button/selection refinements, then paired with references in `artifacts/expansion/browser/comparison-1.jpg` through `comparison-5.jpg`.

Direct browser checks passed for selected-food nutrition and portions, invalid quantities, reviewed manual glucose entry, concern-based activity deferral, keyboard submission, account validation, reviewed report submission and disabled staff gates. Pixel food selection has no horizontal page overflow. A retry photo was initially pending at the immediate DOM check; a fresh follow-up confirmed it loaded and recaptured it. The run observed no console errors. Detailed evidence is in `artifacts/expansion/browser-checks.json` and `browser/capture-evidence.json`.

The comparisons prompted corrections to account field-card anatomy, solid input borders, button arrows, food selection borders, heading weight/fit and duplicate radio-row actions. Matching remains approximate: protected device chrome is present, paper/shadows differ, icons are editable library vectors, and exact source font metrics are unknown. No similarity percentage or 100% identity is claimed.

Eight expansion tests, five original domain tests and four Sites packaging tests pass, alongside root/native TypeScript, web build, Expo lint and native exports. Latest web output has a 642.37 kB main chunk and a 13.93 kB lazy expansion view chunk; the 500 kB warning is non-failing. Native exports pass with 122 assets. No physical-device or emulator result is claimed.

The Figma development-plugin package has 32 primary scenes, 53 state scenes, 80 dialog scenes, reusable components/variables/text styles and six continuation copies. Local mock-SDK construction and an official Plugin API typing check pass. **These are not a live Figma import.** The Starter connector limit and unavailable native control prevent that remaining step. [Import notes](artifacts/figma-expansion/README.md) record the concrete package and post-import checks. The six original Figma frames have not been edited during this expansion.

The sections below describe the historical original-six implementation and evidence; they should not be read as current expansion screenshots.

## Reference and comparison method

The six individual 863 × 1822 PNGs override the overview poster. `src/nutrisole/ui.tsx` supplies each inner-display crop. Layout uses uniform scaling, horizontal centering, and top alignment at 393 × 852. Weekly Plan and Profile have shorter source proportions and retain extra cream space below. The protected preview clock, bezel, cutout, and home indicator have their own geometry and are excluded from app-content fidelity claims.

The most recent usable comparisons are in [artifacts/qa/exact-refinement](artifacts/qa/exact-refinement/). Full-page browser captures were cropped at the observed device rectangle, 503.5 / 174 / 393 / 852, rather than using an incomplete viewport capture. `scripts/compare-ui.py` creates actual/reference pairs, 50% overlays, and diagnostic differences. JPEG/browser capture softness and protected chrome contribute to those differences; no similarity percentage is claimed.

| Screen | Last usable comparison | Capture freshness |
| --- | --- | --- |
| Onboarding | [Pair](artifacts/qa/exact-refinement/onboarding-comparison.png), [overlay](artifacts/qa/exact-refinement/onboarding-overlay.png) | Precedes the last calibrated paper reconstruction and headline baseline adjustments. |
| Home | [Pair](artifacts/qa/exact-refinement/home-comparison.png), [overlay](artifacts/qa/exact-refinement/home-overlay.png) | Shows source icon artwork and measured layout; final fresh pass unavailable. |
| Scan | [Pair](artifacts/qa/exact-refinement/scan-comparison.png), [overlay](artifacts/qa/exact-refinement/scan-overlay.png) | Precedes the final close/flash/overlay mask and pointer alignment changes. |
| Log Meal | [Pair](artifacts/qa/exact-refinement/log-meal-comparison.png), [overlay](artifacts/qa/exact-refinement/log-meal-overlay.png) | Shows real portion controls and source artwork; final fresh pass unavailable. |
| Weekly Plan | [Pair](artifacts/qa/exact-refinement/weekly-plan-comparison.png), [overlay](artifacts/qa/exact-refinement/weekly-plan-overlay.png) | Shows source artwork, dates and meal cards; final fresh pass unavailable. |
| Profile | [Pair](artifacts/qa/exact-refinement/profile-comparison.png), [overlay](artifacts/qa/exact-refinement/profile-overlay.png) | Shows original preference icons and avatar; final fresh pass unavailable. |

Older evidence in `artifacts/qa/` records earlier iterations. Neither directory proves every latest refinement.

## Completed refinements

- Replaced primary reference icon approximations with 44 separate unlabeled source icon/badge/button crops, inside real accessible controls. Those are raster artwork assets, not original vector files. Library icons remain for inferred secondary states.
- Reused food thumbnails, avatar, leaf and progress-ring artwork at measured source bounds. Original source files remain unchanged.
- Recovered ten clean paper/control texture strips and reconstructed onboarding paper lighting from seven clean source bands. No text, icon, photograph or device UI is baked into that background. Occluded lighting is still an estimate.
- Calibrated Roboto 400/600, Libre Caslon Display 400, and Libre Caslon Text 400/700 with source positions, sizes, fixed line breaks, tracking and selected horizontal text transforms. Exact original font identities are unknown.
- Moved the onboarding photograph transition, matched card border widths, and aligned the camera confidence pointer and rounded exclusions.
- Masked every source control out of scene photographs. The main apple keeps original visible photo pixels; clean recovery and neighboring patches supply only unavailable background behind original UI.
- Fixed decorative layers intercepting clicks, first-tap form submission, keyboard dismissal, post-sheet scroll origin, invalid portions, duplicate consumption, and saved-quantity preservation.
- Kept long edited profile values on one line with ellipsis. Both native bundles resolve the intended native React dependency and Expo Router entries.

## Verification

| Check | Outcome |
| --- | --- |
| Domain tests | 5 passed: portion conversion, invalid quantities, drafts excluded, idempotent consumption, draft conversion preserving quantity. |
| Protected runtime | 28 protected file hashes pass. |
| TypeScript | Root and native target pass. |
| Web production build | Latest build passes; 587.95 kB JS / 188.43 kB gzip, with a non-failing chunk-size warning. |
| Expo lint | Pass. |
| Native export | Latest iOS and Android exports pass, with 119 assets. No physical device/emulator or signed installer test. |
| Browser flows | Prior iteration passes; [recorded checks](artifacts/qa/browser-final-checks.json). Final refresh after the newest visual changes is blocked. |
| Browser responsive checks | Prior iteration checked iPhone/Pixel, desktop, tablet 900 × 1000 and narrow 390 × 940; no page overflow observed. |
| Latest source preservation | [Source integrity](artifacts/qa/source-integrity.json); six original screen files unchanged. |

Earlier browser flows exercised onboarding → Home → Scan → Apple portion; quantity 2 → 190 cal; zero weight rejected; 91 g → 48 cal; consumed totals; drafts excluded from totals; logging a saved 91 g draft once and removing it; day/nutrition tabs; acceptance → 5/5; substitution; feedback; invalid email rejection; persisted account/unit edits; truncation; Reset; flash/gallery/photo/video demos. Earlier reload/traversal had no new errors or broken images, plus one non-failing RN Web `pointerEvents` warning. These describe the earlier tested iteration, not a fresh final run.

Health/history and editing sheets are inferred states beyond the pictured six screens. Health shows no fabricated glucose readings. Camera, Apple recognition, confidence, connection, nutrition and dates use synthetic fixtures; there is no backend or real health integration.

## Editable Figma output

[NutriSole — Mobile UI](https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko?node-id=2-4) contains six top-level 393 × 852 screens, 132 live text layers in the main frames including six static status-clock fixtures, 79 reusable components, color/spacing/radius variables, five text styles, and 16 navigation links. Figma's clock is a static design fixture; the frontend's protected clock stays live.

Text, surfaces, camera-frame/status vectors, action layers and component instances are editable. Food/photo/paper/icon artwork is held in separate image fills. Small source icons are swappable raster assets, not editable vector paths. No complete UI screenshot was imported as a screen.

The first composition review exposed a Windows text-decoding error in the export adapter. Explicit UTF-8 reading fixed apostrophes, approximation signs and en dashes; successful Figma writes updated all 126 source text values in both main frames and QA copies, restored mixed font runs, reduced overlapping Alex glyphs, and corrected the camera pointer's rotation origin. The local ledger records these writes. The final post-fix screenshot is **pending**, because the Figma Starter MCP call limit was reached. `artifacts/figma/composition.png` is the **pre-fix diagnostic**, not final proof.

A temporary editable QA composition at node `2:2`, x=4000, contains six copies for comparison. It does not replace the six main prototype frames. Its final review/cleanup is pending. [Figma handoff](artifacts/figma/README.md) records frame IDs and reproducible source-export steps.

## Remaining findings

| Priority | Finding | Consequence |
| --- | --- | --- |
| P2 | Exact source fonts remain unverified; Figma cannot apply frontend affine glyph stretching directly. | Typography is calibrated from PNGs but not certified identical. Figma uses editable approximations for transformed text. |
| P2 | Occluded paper lighting, some alpha/shadow treatment and camera recovery regions are reconstructed. | Color/texture identity cannot be asserted for those pixels. Clean photographic/source assets are unavailable. |
| P2 | Final frontend and post-fix Figma captures are unavailable. | Latest changes require visual rechecking before an exact-match pass. |
| P2 | Large accessibility text, translated copy and native assistive technology are untested. | Fixed reference-coordinate layouts need production adaptation beyond the default fixture. |
| Informational | Protected live device chrome and shorter source canvases differ from source phone renders. | Expected under the protected Product Design runtime contract. |

Automatic browser review rejected reopening `http://localhost:4173/`; no alternate browser driver or native-browser workaround was used. Figma's Starter MCP limit blocked its final screenshot and cleanup. The selected Figma Agent launch exposed no targetable window; existing Figma desktop returned `failed to activate captured window`, including the one recovery retry. These blockers are recorded rather than treated as passing visual checks.
