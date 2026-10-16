# G9 Stage J3: missing-input checklist (what we need from the team)

Written 2026-10-15 (PKT). Human-verified images today: **0**. Independent human exports: **0**. H3: **BLOCKED**, nothing trained.
Grades stay blocked. The hard-coded `97% / Grade A` UI demo values are **not CV evidence** (see `G9_FYP_requirement_status.md`).

Fill each line; the lead keeps this file with the handoff. Nothing below may be filled in by the AI on anyone's behalf.

## 1. People (three different humans)

| Role | Name | Confirmed not the same person as the others | Has NOT seen any AI suggestion for these batches |
|---|---|---|---|
| Annotator A (copy `annotator1`) | ____________ | [ ] | [ ] |
| Annotator B (copy `annotator2`) | ____________ | [ ] | [ ] |
| Adjudicator (third person) | ____________ | [ ] | n/a (receives AI post-hoc zip only after both exports) |

## 2. Labelling exports (phase 1: evaluation)

| Item | From | File | Received | sha256 recorded |
|---|---|---|---|---|
| Pilot CSV (265) | A | exported from `nutrisole_G9J_pilot_annotator1.zip` | [ ] | [ ] |
| Pilot CSV (265) | B | exported from `nutrisole_G9J_pilot_annotator2.zip` | [ ] | [ ] |
| Pilot 2 CSV (335) | A | exported from `nutrisole_G9J_pilot2_annotator1.zip` | [ ] | [ ] |
| Pilot 2 CSV (335) | B | exported from `nutrisole_G9J_pilot2_annotator2.zip` | [ ] | [ ] |
| `attestation_annotator1.json` (pilot, pilot2) | A, self-filled | | [ ] | [ ] |
| `attestation_annotator2.json` (pilot, pilot2) | B, self-filled | | [ ] | [ ] |

Then the lead runs, per batch: `j3_merge_evidence.py` -> `j_agree.py agree ... --evidence` -> adjudicator fills the sheet -> `j_agree.py verify`.

## 3. Labelling exports (phase 2: training; after phase 1 is sent)

| Item | From | Received |
|---|---|---|
| Train CSV (461) + Train 2 CSV (646) | A | [ ] |
| Train CSV (461) + Train 2 CSV (646) | B | [ ] |
| `attestation_annotator1_training.json` / `attestation_annotator2_training.json` | A / B, self-filled | [ ] |

## 4. Adjudication

| Item | Received |
|---|---|
| Completed `adjudication_sheet.csv` for pilot, pilot2 (every row: final label, adjudicator name, reason) | [ ] |
| Completed `adjudication_sheet.csv` for train, train2 | [ ] |

## 5. Team phone photos (source `team_phone`)

| Item | Received |
|---|---|
| Who shoots **eval** (bagged / partly hidden): ____________ ; who shoots **train** (whole apples): ____________ (nobody on both) | [ ] |
| Session folders named `S<YYYYMMDD>-<initials>-<nn>`, files `TP_<session>_<class>_<condition>_<nnn>.jpg`, location off | [ ] |
| One `sessions.csv` with the exact 7-column header | [ ] |
| **Licence decision per session**, made by each photographer: `CC-BY-4.0` or `internal-FYP` (one line per session in `sessions.csv`) | [ ] |
| `consent_confirmed = yes` for every session (own photos, licence agreed, no faces / visible people agreed) | [ ] |
| Delivered by Google Drive link or USB (not WhatsApp) | [ ] |
| After ingestion: two independent labels + adjudication of the team packs (`team_eval`, `team_train`) like Pilot 1/2 | [ ] |

## 6. Decisions only the user can give

| Decision | Answer |
|---|---|
| Training go for H3 (only after R1-R4 and T1-T5 pass): write `ml/runs/G9/stageJ/h3/USER_TRAINING_GO.json` yourself or tell the agent "H3 training go" with the date | [ ] |
| Whether team photos marked `internal-FYP` may appear in the FYP report figures (they are never redistributed) | [ ] |
