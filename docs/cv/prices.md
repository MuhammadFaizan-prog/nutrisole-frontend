# Official market-price reference (G4.6)

NutriSole shows an **official reference price** next to a graded item. It is never an offer or a valuation. Only official Pakistani government sources are used, and no private apps or marketplaces are scraped. Each site is fetched at most once a day.

## Sources (checked 2026-10-12)
| priority | source | URL | what it gives | unit | staleness |
|---|---|---|---|---|---|
| 1 | Market Committee Lahore / PAMRA daily **retail** rate lists (District Lahore, Govt of Punjab) | https://lahore.punjab.gov.pk/fruits-rate-list, https://lahore.punjab.gov.pk/vegetables-rate-list | one JPEG per date ("Retail Price" link); columns grade 1 (اول) and grade 2 (دوم) per item | Rs/kg ("فی کلوگرام" in the header) unless the item name says درجن (dozen) or فی عدد (per piece) | stale if the list date is more than 2 days old |
| 2 | Punjab AMIS (Agriculture Marketing Information Service) | http://www.amis.pk/ | home-page ticker "Avg. WholeSale Prices Of Commodities in Rs/100Kg", one section per city (we read Lahore only) | **Rs/100 kg, stated on the page** (confirmed 2026-10-12), converted to Rs/kg; items marked (DOZEN) / (100Pcs) keep those units | the ticker has no date, so the fetch date is used and the record says so; stale after 2 days |
| 3 | Pakistan Bureau of Statistics weekly SPI | https://www.pbs.gov.pk/price-statistics/ | national weekly average (17 cities) | per SPI annexure | stale after 7 days. **Interface only in G4:** the annexure parser is not written, so SPI always returns no rows |

On 2026-10-12 the "Wholesale Price" column on the Lahore pages was empty. Both pages listed one row per date (Oct 7-12, 2026).

## Pipeline (`ml/prices/`)
1. `rate_list.parse_index` reads the dated rows and retail JPEG links from the listing page.
2. `grid.parse_table` finds the table grid with morphology (7 vertical rules = two 3-column blocks). It OCRs each price cell with Tesseract 5 (`eng`, digits and '-' only, `--psm 7`) and each name cell with Tesseract `urd` (tessdata_best, Apache-2.0). If a name comes back empty, it retries once at a larger scale with `--psm 8`.
3. `rate_list.match_rows` assigns OCR rows to the hand-built lexicon (`lexicon.py`: Urdu name, English name, NutriSole class, unit) one-to-one, using the Hungarian method on name similarity. A +0.35 layout bonus applies when the row sits where the item sat on the 2026-10-12 lists.
4. A row is **dropped, never guessed**, in any of these cases:
   - its name matches nothing (similarity < 0.45, or < 0.25 at the expected layout position);
   - a price cell does not read as an integer or '-';
   - Tesseract confidence is < 0.60;
   - grade 2 > grade 1.
5. `build_daily.py` writes `prices_<date>.json` with, for every source:
   - source name, source URL, list date and fetch time;
   - parsed rows (item, English name, class, unit, grade-1/grade-2 Rs, OCR text, per-row confidence);
   - dropped rows with the reason.
6. `reference.price_reference(class, grade, sources, today)` is mirrored exactly in `native/src/cv/prices/reference.ts` (parity fixture `ml/prices/fixtures/reference_parity.json`, 120 cases). The app grades map to list grades as follows:
   - **A -> grade 1**;
   - **B -> grade 2**;
   - **C / Reject -> no price**, with the note "Below market grade; expect a discount";
   - ungradable -> no price.

   The range runs across every listed variety of the class in the same unit, and the varieties are named. If the class is not on the list, there is no price. Kinnow, malta and musambi are separate lexicon rows; kinnow is not on the October lists, so it has no price yet.

## OCR accuracy on a hand-checked sample
The sample is 4 lists (fruit and vegetable, 2026-10-10 and 2026-10-12), 146 item rows and 132 rows with a price. Every cell was checked by eye against the JPEG (`ml/prices/fixtures/handcheck_gt.json`). Device: sandbox CPU, Tesseract 5.5.0. Raw results: `ml/runs/G4/prices_ocr_eval.json`.

| version | kept price cells correct | priced rows recovered (recall) | wrong rows kept |
|---|---|---|---|
| name-only matching (first version) | 224 / 230 (97.4%) | 106 / 132 (0.80) | 3 rows (e.g. capsicum's price assigned to peas) |
| **shipped: + layout prior + psm-8 retry** | **254 / 254 (100%)** | **117 / 132 (0.89)** | 0 |

Caveats:
- The lexicon and layout prior were built from the 2026-10-12 lists, so those lists are in-sample for name matching. The 2026-10-10 lists are held out but have the same item set and order; only the prices differ.
- A new item, or a re-ordered layout, falls back to name-only matching (97.4% cell accuracy in the first version). Urdu Nastaliq OCR is weak: most dropped rows are names Tesseract returned empty.
- The first weeks of lists still need the per-row human check that the G4 plan asks for.

## Units and grades to watch
- Banana, musambi, meetha and malta are priced **per dozen**; grapefruit and coconut **per piece**. The app shows the unit and never converts dozens to kg.
- Tomato appears as two rows, "ٹماٹر اول" and "ٹماٹر دوم" (first/second class). Each row has its own grade-1 and grade-2 columns. Both rows feed the tomato range.
