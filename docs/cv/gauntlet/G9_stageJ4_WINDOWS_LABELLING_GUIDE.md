# NutriSole G9 Stage J4: Windows labelling guide (Phase 1 = evaluation, 265 + 335 photos)

Written 2026-10-15 (PKT). Applies to the zips checked by `j4_verify_handoff.py` (result: **PASS**, all hashes match `HANDOFF_MANIFEST.json`,
annotator, training and team zips clean of AI material). Human-verified images today: **0**. Grades stay blocked.

Three different people are needed: **Annotator A**, **Annotator B**, **Adjudicator**. Nobody fills anything in for anyone else, and
the AI never fills an export or an attestation.

---

## Part 1. Annotators A and B (about 50–70 minutes per batch)

You need only **your own** zip: A gets `NutriSole_G9J_ANNOTATOR_A.zip`, B gets `NutriSole_G9J_ANNOTATOR_B.zip`.
Do not open any other NutriSole zip (training, adjudicator or "AI_POSTHOC").

### 1. Unzip (File Explorer)
1. Right-click the zip → **Extract All…** → Extract. Pick Desktop if unsure.
2. Inside, right-click `nutrisole_G9J_pilot_annotator1.zip` (B: `..._annotator2.zip`) → **Extract All…**.

### 2. Label in the browser (no internet needed)
1. Double-click `NutriSole_labelling_pilot_annotator1.html`. It opens in **Edge** or **Chrome**. If Windows asks which app, choose Edge.
2. Type your **real name** (it becomes part of the exported file name). Press **?** once to read the Help screen.
3. Keys: **1–9** answer (1 apple, 2 banana, 3 citrus/orange, 4 tomato, 5 carrot, 6 other produce, 7 printed/screen, 8 occluded,
   9 uncertain) · **C / B / M / X** tags (cut, bag, multiple, rotten/damaged) · **←/→** move · **U** next unlabelled · **E** export.
4. Choose **9 = uncertain** whenever you honestly cannot tell. That is a correct answer.
5. Work saves itself in that browser. You may close and come back on the **same PC and same browser**. Do not clear browsing data.
   At the end of each sitting press **Export CSV** as a backup (the tool can restore it with *Import a CSV (restore)*).

### 3. Export (when every photo is done)
Press **Export CSV**. Edge/Chrome saves it in **Downloads** with a name like:

| Batch | Expected file name (example name "Ali Khan") |
|---|---|
| Pilot (265) | `G9J-pilot_annotator1_Ali_Khan_265of265.csv` |
| Pilot 2 (335) | `G9J-pilot2_annotator1_Ali_Khan_335of335.csv` |

(B's files say `annotator2`.) **Do not rename or open/save the CSV in Excel.** If the name says less than `265of265` / `335of335`,
press **U** to find the photo you missed, then export again and send only the complete file.

Repeat steps 1–3 for `nutrisole_G9J_pilot2_annotator1.zip`.

### 4. Optional: record the file fingerprint (PowerShell)
Start → type **PowerShell** → open it, then:
```powershell
cd $HOME\Downloads
Get-FileHash .\G9J-pilot_annotator1_*_265of265.csv, .\G9J-pilot2_annotator1_*_335of335.csv -Algorithm SHA256 | Format-List
```
Paste the two hashes into your email / Drive note. The lead's script recomputes them from the exact bytes.

### 5. Attestation (you fill it yourself)
1. Right-click `attestation_annotator1.json` (B: `attestation_annotator2.json`) → **Open with → Notepad**.
2. Fill it like this (your own values):
```json
{
  "schema_version": 1,
  "provenance": "HUMAN_INDEPENDENT",
  "copy": "annotator1",
  "name": "Ali Khan",
  "batches": {
    "pilot": "G9J-pilot_annotator1_Ali_Khan_265of265.csv",
    "pilot2": "G9J-pilot2_annotator1_Ali_Khan_335of335.csv"
  },
  "independently_labelled": true,
  "no_ai_or_peer_labels_seen": true,
  "attested_at": "2026-10-20T18:00:00+05:00",
  "_how_to": "leave this line as it is"
}
```
   - `name`: your real name. `batches`: the **exact** exported file names (copy them from File Explorer, F2 → Ctrl+C → Esc).
   - Set the two statements to `true` **only if they are true**. If you looked at anyone else's labels or any AI output, write `false`
     and tell the lead; the batch is then re-labelled by someone else. Nothing bad happens to you for being honest.
   - `attested_at`: date and time **with** `+05:00`, in exactly that format.
3. **File → Save** (keep UTF-8). Check it is valid:
```powershell
Get-Content .\attestation_annotator1.json -Raw | ConvertFrom-Json | Format-List name, copy, independently_labelled, no_ai_or_peer_labels_seen, attested_at
```
   An error message means a missing comma or quote. Fix it in Notepad and run the line again.

### 6. Send
Send **three files**: the two CSVs and your attestation JSON, to the project lead (M Faizan) by **Google Drive folder or email**.
Not WhatsApp. (The `START_HERE.txt` inside the hash-locked pack says WhatsApp is fine; these outer instructions replace that line.)

### Rules (both annotators)
- Label **alone**. Do not discuss photos with the other annotator until **both** of you have sent your exports.
- No ChatGPT, Google Lens, image search or any other AI tool, and nobody else's labels.
- Label what you **see**, not what the file or context suggests.

### If the HTML tool will not open
Use `fallback\fallback_pilot_annotator1.csv` with the pictures in `fallback\contact_sheets` (each photo shows its id in red).
Fill the `label` column with one of: `apple, banana, citrus_orange, tomato, carrot, other_produce, printed_or_screen, occluded, uncertain`,
your name in `annotator`. In Excel use **File → Save As → CSV UTF-8**, keep the file name, and put that exact name in the attestation.

---

## Part 2. Lead (M Faizan) on Windows, PowerShell

One-time setup (repo on the `cv-gauntlet` branch; Python 3.12 from python.org with "Add to PATH"):
```powershell
cd $HOME\nutrisole-frontend
git switch cv-gauntlet; git pull
py -3 -m pip install pillow imagehash numpy pytest      # only the team-photo tools need these; j_agree uses the standard library
$S = "ml\runs\G9\stageJ\scripts"
$IN = "$HOME\Downloads\g9j_phase1"                       # put the 6 received files here (4 CSVs, 2 attestations)
```
Optional integrity re-check of the zips you sent out (read-only):
```powershell
py -3 $S\j4_verify_handoff.py --handoff "$HOME\Downloads\handoff"
```
Per batch (`pilot`, then `pilot2`):
```powershell
$A = Get-ChildItem $IN\G9J-pilot_annotator1_*.csv; $B = Get-ChildItem $IN\G9J-pilot_annotator2_*.csv
py -3 $S\j3_merge_evidence.py --batch pilot --a $IN\attestation_annotator1.json --a-csv $A.FullName `
      --b $IN\attestation_annotator2.json --b-csv $B.FullName --out $IN\evidence_pilot.json
py -3 $S\j_agree.py agree $A.FullName $B.FullName --batch pilot --evidence $IN\evidence_pilot.json --out ml\runs\G9\stageJ\out\agree_pilot
```
(For `pilot2` replace `pilot` with `pilot2` in the file patterns, `--batch`, the evidence name and the output folder.)
The scripts refuse a CSV whose name differs from the attestation, an unattested or AI-matching CSV, the same name for A and B,
duplicate ids and invalid labels. A refusal is a result: send the message to the annotator, never edit their CSV.

Then:
1. Send the adjudicator `NutriSole_G9J_ADJUDICATOR.zip` + `ml\runs\G9\stageJ\out\agree_pilot\adjudication_sheet.csv` (and the pilot2 one).
2. Only **after both annotators' exports for that batch are received**, the adjudicator may also get
   `NutriSole_G9J_ADJUDICATOR_AI_POSTHOC_release_after_exports.zip` (provenance `AI_ASSISTED_NOT_HUMAN`; reference only, never a label).
3. When the adjudicator returns the completed sheet (every row: `final_label`, `adjudicator`, `adjudicator_reason`):
```powershell
py -3 $S\j_agree.py verify --batch pilot --agree-dir ml\runs\G9\stageJ\out\agree_pilot `
      --adjudicated $IN\adjudication_sheet_pilot.csv --out ml\runs\G9\stageJ\out\verified_pilot
```
4. Commit only the `agree_*` / `verified_*` outputs (manifests, summaries, `.sha256`) to `cv-gauntlet`, or send them to the agent to
   commit. This freezes the evaluation labels (gate R4) **before any model is run on these photos**.
5. Then release the Phase 2 training zips (see `G9_stageJ4_PHASE2_TRAINING_SCHEDULE.md`).

## Part 3. Adjudicator
Open `ADJUDICATION_INSTRUCTIONS.md` in the adjudicator zip. Fill every row of `adjudication_sheet.csv`: `final_label`
(one of the nine labels or `exclude`), `adjudicator` (your name) and `adjudicator_reason` (short reason); the `final_cut` / `final_bag`
columns where the row's `reason` mentions a tag mismatch. Save as CSV UTF-8 and send it back by Drive or email.
