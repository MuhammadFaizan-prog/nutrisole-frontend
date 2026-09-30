# NutriSole editable Figma handoff

[Open NutriSole — Mobile UI](https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko?node-id=2-4).

Six top-level 393 × 852 frames reproduce the app's reference fixture states. They are built from the actual shared React Native component trees, not UI screenshots.

| Screen | Main frame | Position |
| --- | --- | --- |
| Onboarding | `2:4` | 100, 100 |
| Home | `2:5` | 557, 100 |
| Scan | `2:6` | 1014, 100 |
| Log Meal | `2:8` | 100, 1016 |
| Weekly Plan | `2:9` | 557, 1016 |
| Profile & Preferences | `2:10` | 1014, 1016 |

The page is `0:1`. Main prototype frames have 16 ON_CLICK navigation connections, with Onboarding as the flow starting point. The reusable library frame `2:11` at x=1550 contains 76 independent source-asset components plus Label, Surface and Device/Cutout: 79 components total. Text has a Content property; 132 live text layers in the main frames include six static 9:41 status fixtures. The frontend clock remains live.

Colors, radii and spacing use the NutriSole / Reference variable collection. Five text styles use verified available Roboto Regular/SemiBold, Libre Caslon Display Regular and Libre Caslon Text Regular/Bold. These font families approximate the PNGs; the original font identity is unknown. Figma cannot directly apply affine glyph stretching, so transformed frontend text uses editable size/tracking approximations.

Photos, avatar, leaf, progress-ring artwork, clean paper textures and individual unlabeled source icons use separate image fills/components. The 44 source icons are raster artwork, not editable vector paths. The camera target and status indicators use editable paths. Cards, text, action layers and shapes remain independent. No complete UI screen was rasterized.

## Successful writes and remaining review

Asset uploads, fonts, frame population, prototype connections and text correction writes succeeded. The last update corrected UTF-8 decoding, mixed font runs, Alex spacing and the camera pointer's CSS-center rotation mapping in both the main frames and six QA copies. `design-system-state.json` contains the complete node/asset ledger and successful mutation IDs.

`composition.png` is the first, **pre-correction diagnostic**. It has since-fixed text-decoding and spacing issues; do not present it as the final current file. `composition-first.png` is a blank diagnostic from an empty review frame. Neither confirms the latest visual state.

A temporary editable QA composition `2:2` at 4000, 100 holds six copied screens for one-image inspection. The actual prototype screens remain separate and top-level. Final screenshot/review/cleanup is pending: Figma's Starter MCP call limit was reached; the chosen Figma Agent exposed no targetable window; Figma desktop activation failed, including one recovery retry. Do not create another file or blindly rerun construction.

## Reproducible local source export

From the frontend folder:

```powershell
node scripts/export-figma-scenes.mjs
& 'C:/Users/DELL/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/prepare-figma-scenes.py
```

The first script renders six fixture component trees into `source-markup.json` through a semantic adapter. The second reads explicit UTF-8, generates `scenes.json` and ASCII-escaped `scenes.ascii.json`, and masks source UI pixels out of the two photo assets. This is a source export; it does not capture or control the blocked browser.

Use `scenes.ascii.json` when transferring through a Windows shell to avoid accidental legacy-codepage decoding. Always parse the JSON escapes. `photograph-provenance.json` records masks; source icon/surface provenance lives under `assets/source/`. Signed asset-upload links are not retained.

`scripts/figma-build.js` is an embedded async construction helper requiring SCENES and STATE, intended for an empty discovered skeleton. It now incorporates the live-text and rotation fixes. It deliberately stops if screens/library are already populated. The current file is populated: resume validation and targeted edits from its ledger rather than running initial construction again.

Only claim exact identity after a fresh visual comparison of the corrected Figma and latest frontend state. See `../../design-qa.md` for the remaining font, recovered-lighting and verification limitations.

