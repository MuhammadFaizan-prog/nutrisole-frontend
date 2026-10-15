# Pilot 2 validation record — AI-assisted, 2026-10-15

All 335 annotation rows pass exact 15-column `G9J-pilot2` validation, complete stable-ID coverage, original annotator1 display-index mapping, per-ID image identity, saved decision/note/tag/subtype consistency and AI provenance checks. The detail table has 335 rows; the queue has 233 unique rows (77 HIGH, 65 MEDIUM, 91 LOW), exactly matching its documented selection rule.

| Check actually run | Result |
|---|---|
| Both supplied original Pilot 2 ZIPs, including CRC and all embedded JPEG decoding | PASS: 335 each, same per-ID bytes, different orders |
| Existing offline browser smoke test, each original HTML, disposable profiles, network disabled | PASS: 335 export rows each; autosave/reload, import, ID mapping, quoted/comma/newline/Unicode CSV, no external requests or page errors |
| All three CSVs through bundled artifact-tool value getter round-trip | PASS: 335 x 15, 335 x 22, 233 x 22; rendered sample inspected |
| Saved review / CSV / queue / image-hash reproduction check, including both ZIPs | PASS; see `G9J_pilot2_visual_review_validation.json` |
| Stage J agreement/handoff regressions after the new AI CSV entered the automatic registry | **42 passed** |
| Complete ML pytest suite, UTF-8 and temporary checkout-root adapter for the historical camera-test path | **111 passed** |
| `npm run check:runtime` | PASS: **28 protected files** |
| Historical frozen Git-LF content hashes | PASS: **30** |
| Existing J2 gap-artifact byte hashes | PASS: **14** |
| Combined J1/J2 stored source metadata and pHashes via existing split auditor | 0 cross-split conflicts in available records; earlier external reference store unavailable |
| `git diff --check` | PASS |

The validator change was preceded by a failing Pilot 2 regression: the old API could not accept an explicit Pilot 2 batch. The new keyword keeps `pilot` as default, accepts `pilot2` explicitly, and rejects wrong or mixed pack IDs. The existing new J2-key test also failed on Windows because it compared backslashes with a slash-only suffix; its assertion now normalizes paths using `Path.as_posix()`.

This record does not establish label accuracy, source-original identity, human independence, completed adjudication, device acceptance or a model-performance improvement. The review used 17 contact sheets and 100 additional native-package detail views, with no full-resolution Pilot 2 source original viewed. Three source-original requests returned HTTP 429. Neither the 63 packaging nor the 74 hidden-query source categories establishes a verified evaluation quota.

Human-verified images **0**; authentic independent exports **0**; kappa **null**; H3 **BLOCKED**; training **not started**. Main, live deployment, model promotion and frozen dataset memberships are unchanged. Previous native/rendered/device acceptance limitations remain documented in the earlier handoff and are not retested by this data-only follow-up.

The first consistency JSON was saved before the final handoff checksum manifest existed, so its `checksums_checked` field is 0. A subsequent fresh run checked every listed file against `SHA256SUMS.txt`; the manifest and ZIP are also byte-verified when packaging. Re-run `REPRODUCE.py` for the current checksum result. Use `--output` only with a new destination.
