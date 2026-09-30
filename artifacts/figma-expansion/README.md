# NutriSole editable design and prototype importer

**Status: live editable import completed and all 32 primary frames visually reviewed.** After user authorization and Windows unlock, the local development plugin recovered expansion page `34:254`. Live inspection recorded 1,837 native text nodes, 2,254 instances and 716 nodes with prototype reactions. All six original screens passed preservation checks; all inspected navigation destinations exist. The 32 primary frames were exported for QA and 455 native icon instances were refined. `live-validation.json` and `live-render/capture-evidence.json` record the actual live evidence. Full manual prototype navigation QA remains pending; no exact pixel-identity claim is made.

The destination is [the existing NutriSole file](https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko). The importer creates a separate **NutriSole · Expanded flows** page. It requires the original six frame IDs to exist, snapshots them before construction, checks them afterward, and refuses a repeated import. It does not add reactions or layers to those originals.

## Package content

- 32 primary editable frames: 30 missing concepts, a flow directory and a separate portion view.
- 53 selection/filled-example state frames and 80 review/detail dialog frames.
- Reusable surface, button, input, toggle, radio, photo and vector-icon components; color variables and text styles.
- 7 discrete photo assets and 52 library SVGs. Text, layout shapes and icons remain editable; no complete screen screenshot is used as a design.
- Prototype links for account, food, glucose, plan/foot, Assistant, privacy/report/history and staff journeys. Inputs link to filled examples; Figma does not execute the frontend's validation code.
- Six editable continuation copies on the new page connect journeys to the existing UI without changing the original six. Prototype links stay on one page.

`../expansion/importer-simulation.json` records the separate mock-SDK test. Mock counts are distinct from the live counts above. A separate check uses [Figma's official Plugin API typings](https://github.com/figma/plugin-typings/blob/master/plugin-api.d.ts). Fresh native exports were compared with frontend captures after icon refinement; interaction behaviour still needs full manual testing in Figma.

## Import into the existing file

1. Open the existing NutriSole file in Figma Design on desktop with edit access. Make Roboto Regular/SemiBold, Libre Caslon Display Regular and Libre Caslon Text Bold available. The importer checks Figma's available font names before writing and accepts equivalent spacing in style names; it stops if a required font is absent.
2. Extract the ZIP while keeping `manifest.json`, `code.js` and `ui.html` together. Use **Plugins → Development → Import plugin from manifest** and select this manifest. This is Figma's [development-plugin import workflow](https://help.figma.com/hc/en-us/articles/360042786733-Create-a-plugin-for-development).
3. Run **NutriSole · Add missing flows** and click **Create / recover design**. Wait for the completion report; check that all six `originalScreensUnchanged` values are true. Recovery is permitted only for the known failed page `34:254`: it retains its previous nodes in a hidden recovery archive and rebuilds on that same page. It deletes no nodes.
4. Present the **NutriSole · Consumer flows** starting point. Also check Account journey and the four staff starting points. Verify selections, filled-input examples, dialogs, back paths and the continuation copies.
5. Capture each primary frame and compare it with the selected concepts in `../screen-coverage/images/`. Check font availability, clipping, overlay positions and long-page scrolling before declaring the Figma handoff complete.

The manifest uses a local development identifier, not a published Community plugin ID. If Figma asks for an assigned ID, create a development plugin through **New plugin**, retain its Figma-assigned `id`, and copy the other manifest fields and these `code.js`/`ui.html` files into that plugin folder. Figma assigns publishing IDs through its [manifest workflow](https://developers.figma.com/docs/plugins/manifest/).

Use **Inspect live design** for a fresh preservation/link check. **Export QA frames** produces PNGs of the actual native frames for inspection, without flattening the design. Other existing or completed expansion pages are refused. Do not delete the existing six frames. A font-loading or invalid-colour failure happens before construction.

## Source and reproducibility

`scripts/build-expansion-figma.mjs` derives scenes from `src/nutrisole/extensions/model.ts` and embeds discrete assets into the local plugin UI. `scripts/figma-expansion-plugin.js` builds native Figma nodes and reactions. `scene-manifest.json` records the payload without image bytes. The plugin makes no external network requests.

The successful live report and fresh native frame exports confirm the import. The package is an editable design/prototype handoff, not a `.fig` binary or a set of flattened UI images. Exact pixel identity and exhaustive manual prototype behaviour remain unverified.
