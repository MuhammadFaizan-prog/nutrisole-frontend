# G9 Stage J: team phone shot list (source `team_phone`)

**FYP scope.** This collection supports the dataset-development and CV-validation parts of **FYP-proposal edit one.docx**
(objectives in section 4, scope in section 6, methodology figures 7.1–7.3). NutriSole still includes visible ripeness/defect assessment,
quality grading, verified reference pricing, nutrition, glucose records, weekly diet/exercise guidance, footwear support and the assistant.
The five showcase classes are a supported-library milestone, not a reduction of the full FYP. See
[the proposal alignment](G9_stageJ_FYP_scope_alignment.md).

**Why these photos.** The AI-assisted Pilot 2 review (2026-10-15) found **0 definite occluded** photos and only
**8 bagged real-produce photos (5 with a showcase class)**. The supplied Commons collection has not established those evaluation quotas;
team phone photographs provide relevant real-camera candidates. Apples are also short for training. No training happens in this stage.

Initial collection: **~80 eval candidates** (bagged/packaged + partly hidden, J-eval only) and **~70 whole-apple training candidates**
(J-train only). These are collection targets, not proposal requirements or guaranteed verified counts. Human review, duplicate grouping,
source separation and permission checks determine what is usable; collect more if the existing readiness floors are still unmet.
Showcase classes: **apple, banana, citrus_orange (orange/kinnow/malta; not lemon or lime), tomato, carrot.**

## 1. Who shoots what (keep train and eval apart)

| Group | Photographers | Shoots | Split |
|---|---|---|---|
| Eval | 2 team members (A, B) | §3 bagged + §4 partly hidden | J-eval |
| Train | 1 *other* team member (C) | §5 apples | J-train |

- A photographer is **either eval or train** for this round, never both. The script refuses a photographer who appears in both.
- The split is fixed per **session** (one person, one day, one place). Never mix eval and train shots in a session.
- Use different fruit for eval and train (buy separately, or at least different pieces) and different rooms/places where possible.
- If the team has only 2 people: A = eval, B = train, different days, different fruit, different places. Write it in `sessions.csv`.
- Eval photographers do not see or reuse train photos, and nobody trains on eval photos later.

## 2. Phone settings (everyone)

Default camera app, 1× lens, no digital zoom, no portrait/beauty/AI-scene filter, no stickers or text. HDR auto is fine.
Save **JPEG** (iPhone: Settings → Camera → Formats → *Most Compatible*). Turn **location tagging off**. Hold the phone the way a user
would scan food: 20–60 cm away, fruit filling about ⅓ to ⅔ of the frame. Between shots move the fruit or yourself; **at most 2 near-identical
shots per setup** (bursts are grouped and count once).

## 3. Eval: bagged / packaged (~40, 8 per class)

| Per class (×5) | Shots | Notes |
|---|---|---|
| Clear plastic bag (`bag-clear`) | 3 | thin shop bag and zip bag; some glare and creases are good |
| Mesh / net bag (`bag-mesh`) | 3 | orange/onion-style nets; also a cloth-mesh bag if available |
| Tray + cling film (`tray-film`) | 2 | foam or plastic tray, film tight; one with a price sticker |

Mix: single item and several items; on a counter, in a hand, in a shopping basket. The fruit must still be identifiable by a person.
Keep about half or more of the central fruit visible for these packaging examples. A transparent bag is B, not automatic occlusion;
an opaque covering that leaves less than about half visible belongs in the hidden-condition assessment. The final human labels decide.
Optional (+5, label `none`): an empty bag/tray or a bag of a non-target item (e.g. onions), as negatives.

## 4. Eval: partly hidden (~40, 8 per class)

| Per class (×5) | Shots | Hidden |
|---|---|---|
| Hand (`hid-hand`) | 3 | one ~30% covered control; two ~60–70% covered |
| Other fruit/veg in front (`hid-fruit`) | 2 | ~60–70% covered by a different item |
| Frame edge (`hid-edge`) | 2 | one ~30% outside-frame control; one ~60–70% outside |
| Object (`hid-object`) | 1 | bowl rim, cloth, cup or box covering ~60–70% |

Per class this gives **six majority-hidden candidates and two mostly-visible controls** (30 and 10 across all five classes).
The unchanged guide calls an established real main item `occluded` only when **less than about half is visible**. A 30%-covered item
has about 70% visible and normally keeps its produce label; `hid-*` in the filename is shooting intent, not an annotation.
Avoid the ambiguous 50% boundary as a quota target. Do not fully hide the item. Vary the side (left, right, top).

## 5. Training: whole apples (~70 initial candidates)

- **Kinds:** red, green, yellow/bi-colour; single, 2–3, a pile; all counted candidates whole and clearly visible. Optional cut or clearly
  damaged examples are additional, labelled separately, and do not substitute for the clean-whole training floor.
- **Lighting** (≥10 each): window daylight, warm bulb, white tube light, dim evening room, outdoor shade; a few with phone flash.
- **Backgrounds:** kitchen counter, plate/bowl, wooden table, cloth, held in hand, market cart/stall, fridge shelf.
- **Distance/angle:** close (~20 cm), normal (~40 cm), arm's length; top-down, side, 45°.
- Some realistic clutter (other foods next to it) is good. No packaging or heavy hiding here: that is the eval's job.
- At least **3 sessions** (different days/places), at most ~25 photos per session.
- Keep the majority under the proposal's reasonable-lighting assumption; dim/flash examples are additional robustness conditions.
- The existing gap table projects **65 more usable clean apples**, not 65 camera files. Seventy candidates only close that projected gap
  if at least 65 survive independent human review and grouping. Recalculate from actual verified counts; the starting 85 is itself a
  projection, with human-verified still 0. Smaller projected banana/citrus/tomato shortages also remain pending. No target is waived.

## 6. File naming

`TP_<session>_<class>_<condition>_<nnn>.jpg`

- `session` = `S<YYYYMMDD>-<initials>-<nn>`, e.g. `S20261018-AB-01` (date, photographer's initials, session number that day).
- `class` = apple | banana | citrus_orange | tomato | carrot | none
- `condition` = bag-clear | bag-mesh | tray-film | hid-hand | hid-fruit | hid-edge | hid-object | open (train apples)
- Examples: `TP_S20261018-AB-01_banana_bag-mesh_003.jpg`, `TP_S20261020-CD-02_apple_open_017.jpg`

Renaming can be done after shooting (a bulk rename app or the lead does it). The class in the name is the **photographer's intent only**;
the two independent annotators still label every photo blind, and only their labels count.

## 7. Consent and licence

- Photos are **team-owned**. Each photographer picks, per session, **CC BY 4.0** (may be shared with the FYP repo/report, credited) or
  **internal-FYP** (used for evaluation/training inside the project only, not redistributed). Record it in `sessions.csv`.
- `consent_confirmed = yes` means: I took these photos, I agree to the licence above, and anyone visible gave permission.
- **No faces.** Hands only of team members who agree. No shop staff/customers recognisable; ask a stall owner before shooting there.
- No screenshots, downloaded or AI-generated images. Location off: the ingest script refuses photos that carry EXIF GPS.

## 8. Hand-over

1. One folder per session, named by the session id, with that session's JPEGs.
2. One shared `sessions.csv` (UTF-8):
   `session_id,photographer,date,place,purpose,licence,consent_confirmed`
   e.g. `S20261018-AB-01,Ali B,2026-10-18,home kitchen,eval,CC-BY-4.0,yes`
3. Zip the folders + `sessions.csv` and share via Google Drive link or USB to the lead. **Not WhatsApp** (it recompresses and strips files).
4. The lead runs: `python3 ml/runs/G9/stageJ/scripts/j_team_phone.py <unzipped folder> --ref-hashes <earlier J/M-TEST hash list> --out team_phone_manifest.json`
   - split by session (eval ↔ J-eval, train ↔ J-train), photographer leak check, name/licence/consent checks;
   - pHash: any train photo within Hamming ≤ 10 of an eval photo or a reference hash is quarantined (eval never changes);
     eval bursts within ≤ 6 are grouped.
5. Pixels stay out of git. Only the manifest (file/session references, sha256, pHash, split, quarantine reason) is committed. Eval photos then go into a blind
   annotator pack like Pilot 1/2; apples go into the train pack. Human-verified stays 0 until the two annotators finish.

The current `j_team_phone.py` is an **ingestion stub**, not a completed human-label/permission/readiness pipeline. It checks submitted
session ownership, filenames, consent fields and EXIF GPS, groups eval bursts, and quarantines training hashes against supplied references
and the current eval batch. It does not authenticate photographers, measure visible percentage, establish photo quality, or clear new eval
photos against every earlier training/holdout source. References are optional in the stub; omitting them cannot establish no leakage.
Preserve the manifest as preparation only until complete reference/source checks, blind packaging, human review and adjudication are done.
Follow the existing `G9_stageJ_readiness.md`; do not infer H3 permission from successful ingestion.

## 9. Checklist per photographer

- [ ] I am on one side only (eval or train) · [ ] JPEG, 1×, no filters, location off · [ ] hidden candidates and visible controls follow §4
- [ ] ≤ 2 near-identical shots per setup · [ ] no faces/strangers · [ ] files named, `sessions.csv` row filled, consent = yes
