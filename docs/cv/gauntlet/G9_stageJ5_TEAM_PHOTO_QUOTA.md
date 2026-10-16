# G9 Stage J5: team phone-photo quota sheet (orange training enabled)

Written 2026-10-15 (PKT). Supersedes only §1 "Training sessions" of `G9_stageJ4_TEAM_PHOTO_INGESTION_RUNBOOK.md`; every other rule there
(phone settings, consent, file names, PowerShell rename, ingestion, what to commit) is unchanged. Machine-readable copy:
`G9_stageJ5_TEAM_PHOTO_QUOTA.csv`. The user approved collecting the missing orange training photos and the apple/banana/tomato shortfalls
on 2026-10-15 22:53 PKT. Photos are **candidates**: the file name is the photographer's intent; two independent annotators + the adjudicator
decide every label. Nothing is trained.

## Training sessions (J-train; condition `open` only; a photographer who shoots NO eval session)
| Priority | Class (file-name word) | Candidates | Why |
|---|---|---|---|
| 1 | `apple` | **≥ 75** | projected T1 shortfall 65 |
| 1 | `citrus_orange` (orange / kinnow / malta / mandarin) | **≥ 20** | **new in J5**: approved; projected shortfall 8 and T1 needs a hand-held source per class |
| 1 | `tomato` | **≥ 15** | projected shortfall 8 |
| 1 | `banana` | **≥ 10** | projected shortfall 4 |

`j_team_phone.py` now accepts training sessions for **apple, banana, tomato, citrus_orange** (`TRAIN_CLASSES`); `carrot` and `none` training
sessions are still refused, and packaging/hidden conditions are still refused in training (tests: `test_j5.py::test_orange_training_sessions_accepted_carrot_still_refused`,
`test_j4.py`). At least 3 training sessions on different days/places, at most ~25 photos per session, varied light/background/distance.
Example names: `TP_S20261018-AB-01_citrus_orange_open_001.jpg`, `TP_S20261018-AB-01_apple_open_014.jpg`.

## Evaluation sessions (unchanged from J4; eval photographers only)
apple / banana / tomato: 10 bagged + 10 partly hidden each; citrus_orange / carrot: 8 + 8 each; optional 5 `none`. These fill the R2
packaging and occluded sub-quotas, which the AI-assisted pilot review shows are short (pilot + pilot2: 4 bagged, 3 occluded items).

## Candidate pool from open licences (sandbox, J5)
`ml/runs/G9/stageJ/scripts/j5_candidate_pool.py` gathered **162 unverified training candidates** from Wikimedia Commons per-file CC BY /
CC BY-SA / CC0 / PD (orange 53, apple 42, tomato 39, banana 28; 10 more dropped as pHash near-duplicates of earlier sets). No Pexels,
Pixabay, Mixkit or Unsplash. Uploaders/artists who own any J-eval / J-dev item were excluded. They are **J-train candidates only**, never
eval, and carry no label until annotated. List + attribution: `ml/runs/G9/stageJ/out/j5/candidates/j5_candidate_pool.csv`.
