# six-screen-baseline.json: approved changes

AGENTS.md reserves changes to the protected six original screens and to this baseline for the user. Each entry below records one
change the user explicitly approved, the exact files, and the hashes before and after. Nothing else in the baseline was touched.

| Date (PKT) | File | Before (sha256) | After (sha256) | Approval | Change |
|---|---|---|---|---|---|
| 2026-10-15 22:53 | `src/nutrisole/Scan.tsx` | `2a13b25514bfc563908755a2c22bc1eed216cf3d8513acb881b306ccc0c03710` | `725ab709247ff491a176ab622fd76d19f8dbc487607a23104571264bcb198c97` | M Faizan, chat message 2026-10-15 22:53 PKT: "APPROVED: apply the Scan.tsx demo-label diff (G9_stageJ4.md §6.1)" | `Confidence 97%` -> `{demoBadge()}` ("Demo data"); default/sample identity `'Apple'` -> `DEMO_PLACEHOLDER.identity` (same text, now the central demo source). Same coordinates, font sizes, colours, assets, hit areas, sheets and actions; no grade added. |

Verify: `npm run test:expansion` (first test hashes every baseline file) and `node --experimental-strip-types --test native/tests/demoPlaceholderScan.test.ts`.
