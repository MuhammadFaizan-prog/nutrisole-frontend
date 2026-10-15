# G9 Stage J5: recognition → grading → price → nutrition connection audit (report only; nothing rewritten, every module kept)

Checked 2026-10-15 on `cv-gauntlet` (source read + a Node probe of the real functions).

| Link | Module(s) | Input key | Output | Status |
|---|---|---|---|---|
| Wide recognition | `pipeline/postprocess.ts` (G3 decode + NMS), `tracker.ts`/`bytetrack.ts`, `closeup.ts idPolicy` | detector class id 0–11 (`models/labels.ts`, `citrus` = 3) | `IdResult` | functional, tested; **not imported by any screen** on cv-gauntlet |
| Close-up verification | `pipeline/verify.ts` (`h2Decision`, `verifyIdentity` FROZEN_VERIFY P-a, `stageHDecision`), `camera.ts` (tap → still crop → H2 tensor) | H2 class id 0–12 (`H2_CLASSES`, same order + `unknown`) | `StageHOutcome` | functional, tested; wired only into the device-branch debug layer (`cv-gauntlet-device`) |
| Display state | `pipeline/result.ts` (`fromStageH`, `fromAssessment`, `checkDisplayResult`) | outcome + label function | `DisplayResult` (Unknown / Not graded / Poor capture; grade and confidence always null) | functional; used by the debug layer only |
| Grading | `pipeline/rules.ts grade()`, `closeup.ts GradeGate`, `ripeness.ts`, `contracts.ts CvAssessment` | produce + quality probs + measurements | A/B/C/Reject internally | **connected internally only**: `stageHDecision` turns a passing gate into `quality_check_unavailable`, `result.ts` drops grades, `prices/display.ts GRADE_DISPLAY_ENABLED = false`. By design (grades blocked). |
| Price | (a) `prices/lookup.ts lahoreProducePrice(produceType)`; (b) `prices/display.ts categoryPrice / closeupDisplay(appClass)`; `reference.ts` | (a) **showcase key** `apple / banana / citrus_orange / tomato / carrot`; (b) **app class** `citrus` | `ProducePrice` / `PriceDisplay` | functional, tested; **no price-source feed or store in the app**: callers must pass `PriceSource[]`; with none, (a) returns `unavailable: no_lahore_source` |
| Nutrition | `data/nutrition.ts nutritionFor(produceType)`, `forPortion` (USDA FDC SR Legacy) | **showcase key** (`citrus_orange`) | `NutritionRecord` (GI missing) | functional, tested; **UI nutrition screen still uses the demo `foods` catalog** in `src/nutrisole/extensions/model.ts` (Apple/Banana/Tomato), not FDC |

Probe (real functions): `nutritionFor('citrus')` → **null**, `nutritionFor('citrus_orange')` → record; `lahoreProducePrice('citrus')` →
`unknown_produce_type`; `H2_CLASSES` contains `citrus`, not `citrus_orange`. Apple/banana/tomato/carrot use the same key everywhere.

## Gaps (to fix later, additively, after approval)
1. **Key mismatch citrus ↔ citrus_orange.** Recognition emits `citrus` (id 3); nutrition and the Lahore lookup expect `citrus_orange`.
   Needed: one small adapter (class id → showcase key + display label), e.g. reusing `SHOWCASE_APP_CLASS` inverted. Lemon/lime (id 6)
   must not map to orange.
2. **No screen consumes the CV chain.** Scan → analysis-result → nutrition-details → market-reference in the app read the demo store.
   The device-branch debug layer is the only consumer, and it shows the title only.
3. **Price data ingestion is absent.** The contracts are ready; no official Lahore list is fetched or cached in the app.
4. **Nutrition source split.** FDC records exist for all five showcase classes; the demo catalog (no carrot, no orange) is what the UI shows.
5. **Portion grams** come only from the user's portion screen; `forPortion` is ready but not called by the UI.
6. Grading → price (`gradedPrice`) remains intentionally unreachable while grades are blocked.

Nothing above was changed in J5.
