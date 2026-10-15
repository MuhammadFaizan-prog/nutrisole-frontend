# NutriSole G9 Stage J4: team phone-photo ingestion runbook (Windows)

Written 2026-10-15 (PKT). Extends `G9_stageJ_team_photo_shotlist.md` (unchanged rules). Purpose: genuine hand-held photos with a
recorded source, session and consent, aimed at the identified shortages. Photos are **candidates**: two independent annotators and the
adjudicator decide every label. The class/condition in a file name is the photographer's intent only. No training happens here.

## 1. Priority quotas (collection targets, not guaranteed verified counts)

**Why:** projected training shortfall after Stage J2 (`G9_stageJ_gaps.md` §7, human-verified still 0): apple **65**, tomato **8**,
banana **4** (citrus 8 also open; carrot 0). The AI-assisted Pilot 2 review found **0 definite occluded** and only **8 bagged** real-produce
photos, so bagged and partly hidden conditions are short for evaluation.

### Evaluation sessions (J-eval; eval photographers only)
| Priority | Class | Bagged / packaged (`bag-clear`, `bag-mesh`, `tray-film`) | Partly hidden (`hid-hand`, `hid-fruit`, `hid-edge`, `hid-object`) | Total |
|---|---|---|---|---|
| 1 | apple | 10 (4 / 3 / 3) | 10 (4 / 2 / 3 / 1) | 20 |
| 1 | banana | 10 (4 / 3 / 3) | 10 (4 / 2 / 3 / 1) | 20 |
| 1 | tomato | 10 (4 / 3 / 3) | 10 (4 / 2 / 3 / 1) | 20 |
| 2 | citrus_orange | 8 (3 / 3 / 2) | 8 (3 / 2 / 2 / 1) | 16 |
| 2 | carrot | 8 (3 / 3 / 2) | 8 (3 / 2 / 2 / 1) | 16 |
| opt. | none (empty bag/tray, onions in a net) | 5 | – | 5 |

Hidden shots: per class about two thirds with **60–70 % covered** and one third **~30 % covered controls** (shot list §4). Packaging shots
keep about half or more of the fruit visible. Do not aim at exactly 50 %. Shoot priority 1 first.

### Training sessions (J-train; one *other* photographer; condition `open` only)
| Priority | Class | Candidates | Why |
|---|---|---|---|
| 1 | apple | **≥ 75** | 65 projected short; allows for duplicates/rejections |
| 1 | tomato | **≥ 15** | 8 projected short |
| 1 | banana | **≥ 10** | 4 projected short |

`j_team_phone.py` (Stage J4 change) accepts training sessions for **apple, banana, tomato** only and refuses packaging/hidden conditions in
training. Citrus/carrot training sessions stay refused until the lead decides otherwise. Lighting, background and distance variety as in
shot list §5; at least 3 training sessions (different days/places), at most ~25 photos per session.

## 2. Phone settings and consent (every photographer)
- Default camera app, 1× lens, no zoom, no portrait/beauty/AI filter. **Location off.** iPhone: Settings → Camera → Formats → *Most Compatible* (JPEG, not HEIC).
- No faces; hands only of team members who agree; ask a stall owner before shooting at a stall; no screenshots, downloads or AI images.
- Per session the photographer chooses the licence: `CC-BY-4.0` or `internal-FYP`, and confirms consent (`consent_confirmed = yes` means:
  I took these photos, I agree to the licence, anyone visible agreed). Only the photographer fills their own row.

## 3. Hand-over layout
```
team_drop_2026-10-18\
  sessions.csv
  S20261018-AB-01\  TP_S20261018-AB-01_banana_bag-mesh_001.jpg ...
  S20261019-CD-01\  ...
```
`sessions.csv` (UTF-8, exactly these 7 columns, one row per session):
```
session_id,photographer,date,place,purpose,licence,consent_confirmed
S20261018-AB-01,Ali B,2026-10-18,home kitchen,eval,CC-BY-4.0,yes
S20261020-EF-01,Omar F,2026-10-20,Township market,train,internal-FYP,yes
```
Keep any extra notes (phone model, time of day) in a separate `session_notes.csv` **outside** the drop folder: the ingest script refuses
any unknown file inside it. Deliver by Google Drive or USB, never WhatsApp (it recompresses photos and strips data).

### Renaming on Windows (PowerShell)
Easiest: inside each session folder make sub-folders named `<class>_<condition>` (e.g. `apple_bag-clear`, `citrus_orange_hid-hand`,
`tomato_open`) and drop the photos in. Then run once per session:
```powershell
$sess = Get-Item "$HOME\Desktop\team_drop_2026-10-18\S20261018-AB-01"
$n = 1
Get-ChildItem $sess.FullName -Directory | ForEach-Object {
  $parts = $_.Name -split '_(?=(?:[a-z]+-[a-z]+|open)$)'; $cls = $parts[0]; $cond = $parts[1]
  Get-ChildItem "$($_.FullName)\*" -Include *.jpg, *.jpeg | Sort-Object LastWriteTime | ForEach-Object {
    Move-Item $_.FullName (Join-Path $sess.FullName ("TP_{0}_{1}_{2}_{3:D3}.jpg" -f $sess.Name, $cls, $cond, $n)); $n++ }
  Remove-Item $_.FullName   # removes the now-empty sub-folder
}
Get-ChildItem $sess.FullName | Select-Object Name
```

## 4. Ingestion (lead, PowerShell, repo on `cv-gauntlet`)
```powershell
cd $HOME\nutrisole-frontend; git switch cv-gauntlet; git pull
py -3 -m pip install pillow imagehash numpy
$S = "ml\runs\G9\stageJ\scripts"
$DROP = "$HOME\Desktop\team_drop_2026-10-18"
$OUT  = "$HOME\nutrisole_team_ingest\2026-10-18"           # OUTSIDE the repo: pack images must not be committed
py -3 $S\j_team_phone.py $DROP --out-dir $OUT --packs
```
What it checks (refuses the whole drop on any error, with the file named): exact `sessions.csv` columns, session id format, licence,
consent = yes, one photographer never in both eval and train, file name grammar, session folder, eval = bagged/hidden only, train =
apple/banana/tomato `open` only, **EXIF GPS present → refused**. Then pHash against the committed reference manifest (57,575 hashes incl.
M-TEST stored hashes; pixels never opened): eval photo near a training source or an earlier eval set → quarantined; training photo near a
batch eval photo or a reference → quarantined; eval bursts (Hamming ≤ 6) grouped so one group counts once.

Outputs in `$OUT`: `team_phone_manifest.json`, `team_phone_provenance.csv` (sha256, session, photographer, date, place, purpose,
licence, consent, ingested_at), `team_blind_key.csv` (lead only: photographer intent kept here, never in a pack), and blind annotator packs
for `team_eval` (ids Q###) and `team_train` (R###), ordered by content hash.

Commit (or upload to the agent) **only** the manifest, provenance CSV and blind key, into `ml/runs/G9/stageJ/out/team/<date>/`. Never the
photos or the packs. Then the packs go to annotators A and B like Pilot 1/2, with `j_agree.py agree ... --batch team_eval --key <blind key>`.

## 5. Per-drop checklist
- [ ] every photographer filled their own `sessions.csv` row (licence + consent)
- [ ] no photographer in both eval and train
- [ ] location off; JPEG; no faces
- [ ] ingestion ran without refusal; quarantine count noted
- [ ] only manifest / provenance / blind key committed
- [ ] packs labelled by A and B independently, then adjudicated (until then human-verified stays 0)
