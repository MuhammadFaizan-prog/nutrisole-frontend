"""G9 Stage J3: build the exact HUMAN_HANDOFF (no labels, no training).

Output (not in git; zips embed images): /workspace/work/g9j3/HUMAN_HANDOFF/ and the project files folder files/g9/stageJ/handoff/.
  NutriSole_G9J_ANNOTATOR_A.zip            pilot + pilot2 annotator1 packs (original zips, byte-identical), guide, one-page instructions,
                                           blank attestation for annotator 1
  NutriSole_G9J_ANNOTATOR_B.zip            the same with the annotator2 packs
  NutriSole_G9J_ANNOTATOR_A_training.zip   phase 2: train + train2 annotator1 packs (only after the pilot exports are in)
  NutriSole_G9J_ANNOTATOR_B_training.zip   phase 2: annotator2 copies
  NutriSole_G9J_TEAM_PHOTOS.zip            shot list, sessions.csv template, submission steps
  NutriSole_G9J_ADJUDICATOR.zip            recovered originals (adjudicator-only zip), adjudication instructions, guide. NO AI suggestions.
  NutriSole_G9J_ADJUDICATOR_AI_POSTHOC_release_after_exports.zip
                                           AI_ASSISTED_NOT_HUMAN reviews (v1 265, v1 335, v2 corrections). Released to the adjudicator only
                                           after both independent exports + attestations are hash-recorded.
  MISSING_INPUTS_CHECKLIST.md, HANDOFF_MANIFEST.json (sha256 of every zip and inner pack, AI-leak grep results)
Each inner pack's sha256 is re-verified against out/j_packs.json / out/gaps/j2_packs.json before it is copied; any mismatch aborts.
Usage: j3_handoff_build.py"""
import hashlib, io, json, os, re, shutil, sys, zipfile
from pathlib import Path

ROOT = Path("/workspace/work/nutrisole"); J = ROOT / "ml/runs/G9/stageJ"; D = ROOT / "docs/cv/gauntlet"
PF = Path("/workspace/projects/9399e4e3-d6d0-4c6b-a760-12b4c7c9c514/files/g9/stageJ")
STAGE = Path("/workspace/work/g9j3/HUMAN_HANDOFF"); DEST = PF / "handoff"
PACKS = {"pilot": PF / "labeling", "train": PF / "labeling", "pilot2": PF / "gaps/labeling", "train2": PF / "gaps/labeling"}
ORIGINALS = PF / "gaps/nutrisole_G9J2_originals_2048_ADJUDICATOR_ONLY.zip"
AI_FILES = [J / "out/handoff/20261015_visual_review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv",
            J / "out/handoff/20261015_visual_review/G9J_AI_per_image_review.csv",
            J / "out/handoff/20261015_pilot2_visual_review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335.csv",
            J / "out/handoff/20261015_pilot2_visual_review/G9J_pilot2_AI_per_image_review.csv",
            J / "out/handoff/20261015_pilot2_visual_review_v2_hark/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335_v2_hark.csv",
            J / "out/handoff/20261015_pilot2_visual_review_v2_hark/G9J_pilot2_ai_review_corrections_v2.csv",
            J / "out/handoff/20261015_pilot2_visual_review_v2_hark/README.md"]
AI_MARKERS = [b"AI_ASSISTED_NOT_HUMAN", b"AI_ASSISTED", b"visual_review", b"review_queue", b"G9J_AI_", b"ai_review", b"j_blind_key", b"source_label"]


def sha(b): return hashlib.sha256(b).hexdigest()


def recorded():
    r = {}
    for f in ("out/j_packs.json", "out/gaps/j2_packs.json"):
        for batch, lst in json.loads((J / f).read_text()).items():
            for x in lst: r[Path(x["zip"]).name] = (x["sha256"], x["items"])
    return r


ATTEST = lambda copy, batches: json.dumps(dict(schema_version=1, provenance="HUMAN_INDEPENDENT", copy=copy, name="",
                                             batches={b: f"<exported csv file name for {b}>" for b in batches},
                                             independently_labelled=False, no_ai_or_peer_labels_seen=False, attested_at="",
                                             _how_to="YOU fill this in yourself after exporting: your real name, the exact CSV file names, set both "
                                                     "statements to true only if they are true, attested_at like 2026-10-20T18:00:00+05:00. "
                                                     "Nobody else may fill it in for you."), indent=2)

INSTR = """# NutriSole photo labelling: instructions for annotator {L} (copy {copy})

You are one of **two people who label the same photos independently**. A third person settles disagreements later.
Your labels are the ground truth for the project's camera evaluation, so honesty matters more than speed.

## What is in this zip
- `{p1}` (265 photos) and `{p2}` (335 photos): each holds an offline HTML labelling tool, the guide, and a spreadsheet fallback.
- `annotation_guide.md`: the full rules (read once, about 5 minutes).
- `attestation_{copy}.json`: a short statement you fill in **yourself** after exporting.

## Steps
1. Unzip this file, then unzip `{p1}` first. Double-click the `.html` file (Chrome / Edge / Firefox, no internet needed).
2. Type your real name, read the Help screen, label every photo: keys **1-9** choose the answer, **C/B/M/X** add tags, **U** jumps to
   the next unlabelled photo. Work is saved in that browser automatically; do not clear browser history before exporting.
3. Press **Export CSV** when all photos are done. Keep the file name the tool gives you.
4. Repeat for `{p2}`.
5. Open `attestation_{copy}.json` in Notepad: write your name, the two exact CSV file names, set `independently_labelled` and
   `no_ai_or_peer_labels_seen` to `true` only if both are true, and the date/time (e.g. `2026-10-20T18:00:00+05:00`).
6. Send the two CSVs and the attestation to the project lead by Google Drive or email (not WhatsApp).

## Rules
- Label **alone**. Do not discuss photos with the other annotator until **both** of you have exported.
- Do **not** use ChatGPT, Google Lens, any AI tool, or anyone else's labels. Do not search for the photos online.
- Do not open any other NutriSole file you may be sent; you only need this zip.
- Choose **9 = uncertain** whenever you honestly cannot tell. That is a correct answer, not a failure.
- The fruit name you might guess from context does not matter: label only what you see in the photo.
"""

TEAM_STEPS = """# Team phone photos: how to submit

Read `G9_stageJ_team_photo_shotlist.md` first (who shoots what, phone settings, file names, consent).

1. **Before shooting**, decide who is on the **eval** side (bagged / partly hidden photos) and who is on the **train** side (whole apples).
   One person is never on both sides. Turn **location off** in the camera app. JPEG, 1x, no filters.
2. Shoot in **sessions**: one person, one day, one place. Name each session `S<YYYYMMDD>-<initials>-<nn>`, e.g. `S20261018-AB-01`.
3. Put each session's photos in a folder named exactly by the session id. Rename the files
   `TP_<session>_<class>_<condition>_<nnn>.jpg` (classes and conditions are listed in the shot list section 6). The class in the file
   name is only what you intended to photograph; two independent annotators will label every photo blind and only their labels count.
4. Fill **one** `sessions.csv` (use `sessions_TEMPLATE.csv`; keep the header row exactly, delete the example row):
   `session_id,photographer,date,place,purpose,licence,consent_confirmed`
   - `purpose` = `eval` or `train`; `licence` = `CC-BY-4.0` or `internal-FYP` (**each photographer decides per session**);
   - `consent_confirmed` = `yes` only if you took the photos, agree to that licence, and anyone visible agreed. No faces.
5. Zip all session folders + `sessions.csv` together and share with the lead by **Google Drive link or USB** (WhatsApp recompresses
   photos and is not accepted).
6. The lead runs `j_team_phone.py <folder> --out-dir <run> --packs`: it checks names, sessions, photographer separation, consent,
   GPS, and compares every photo with ~57,600 earlier dataset hashes; duplicates are quarantined. It then builds **blind** labelling
   packs (no file names, sessions, classes or conditions inside) for the two annotators.
"""

ADJ = """# Adjudicator instructions (third person; not one of the two annotators)

You settle disagreements **after** both independent annotators have exported and their attestations are recorded.
You must not have labelled these batches yourself.

## Order of work
1. Wait until the lead confirms both exports + attestations are hash-recorded (`j_agree.py agree ...` has written
   `adjudication_sheet.csv` for the batch). Do not talk to either annotator about specific photos before that.
2. The lead sends you `adjudication_sheet.csv` (+ optional review sheets with both labels). For every row fill:
   `final_label` (one of the 9 labels or `exclude`), the `final_*` tags when they matter, your **name** in `adjudicator`, and a short
   `adjudicator_reason`. Every row needs a reason.
3. Use the photo in either annotator pack, the source page URL in the sheet, and `nutrisole_G9J2_originals_2048_ADJUDICATOR_ONLY.zip`
   (18 recovered originals at <=2048 px: pilot P014...P260 and pilot-2 P729, P756, P773) when a higher resolution helps.
4. Follow `annotation_guide.md` exactly (main centre item; `occluded` only when less than about half is visible; B for clear bags).
   Never use a model output, a grade, or the source's search term as the answer.
5. Return the completed sheet to the lead, who runs `j_agree.py verify` to freeze the verified manifest.

## AI suggestions
A separate zip `NutriSole_G9J_ADJUDICATOR_AI_POSTHOC_release_after_exports.zip` holds **AI_ASSISTED_NOT_HUMAN** reviews. The lead gives
it to you only after both independent exports exist. Treat it as a second opinion to look at **after** forming your own view; an AI
note is never a reason on its own ("AI said so" is not an acceptable `adjudicator_reason`). Never pass it to the annotators.
"""

POSTHOC = """POST-HOC AI MATERIAL - provenance AI_ASSISTED_NOT_HUMAN - NOT HUMAN LABELS
Release to the adjudicator ONLY after both independent annotator exports and attestations are hash-recorded (j_agree.py agree has run).
Never give to annotator A or B. These files are refused as human evidence by j_annotation.validate_human_pair (exact or >=95% near-copy).
Contents: v1 AI review of Pilot (265), v1 AI review of Pilot 2 (335) [project lead's], v2 Hark corrections after viewing the recovered
originals of P729 (uncertain -> carrot B M), P756 (confirmed other_produce), P773 (confirmed apple B M).
"""

SESSIONS_TEMPLATE = "session_id,photographer,date,place,purpose,licence,consent_confirmed\nS20261018-AB-01,Ali B,2026-10-18,home kitchen,eval,CC-BY-4.0,yes\n"


def add_bytes(z, name, b): z.writestr(name, b)


def build():
    rec = recorded(); man = dict(zips={}, inner_packs={}, ai_leak_check={}, note="no labels, no training; zips are not in git")
    if STAGE.exists(): shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True); DEST.mkdir(parents=True, exist_ok=True)
    def pack(batch, copy):
        n = f"nutrisole_G9J_{batch}_{copy}.zip"; b = (PACKS[batch] / n).read_bytes(); h = sha(b)
        if rec[n][0] != h: raise SystemExit(f"pack hash mismatch {n}")
        man["inner_packs"][n] = dict(sha256=h, recorded_sha256=rec[n][0], items=rec[n][1], verified=True); return n, b
    guide = (D / "G9_stageJ_annotation_guide.md").read_bytes()
    zips = {}
    for L, copy in (("A", "annotator1"), ("B", "annotator2")):
        (n1, b1), (n2, b2) = pack("pilot", copy), pack("pilot2", copy)
        zips[f"NutriSole_G9J_ANNOTATOR_{L}.zip"] = [(n1, b1), (n2, b2), ("annotation_guide.md", guide),
            (f"INSTRUCTIONS_ANNOTATOR_{L}.md", INSTR.format(L=L, copy=copy, p1=n1, p2=n2).encode()),
            (f"attestation_{copy}.json", ATTEST(copy, ["pilot", "pilot2"]).encode())]
        (t1, c1), (t2, c2) = pack("train", copy), pack("train2", copy)
        zips[f"NutriSole_G9J_ANNOTATOR_{L}_training.zip"] = [(t1, c1), (t2, c2), ("annotation_guide.md", guide),
            (f"INSTRUCTIONS_ANNOTATOR_{L}_training.md", INSTR.format(L=L, copy=copy, p1=t1, p2=t2).replace("(265 photos)", "(461 photos)")
                .replace("(335 photos)", "(646 photos)").replace("# NutriSole photo labelling:", "# PHASE 2 (start only after your pilot CSVs are sent). NutriSole photo labelling:").encode()),
            (f"attestation_{copy}_training.json", ATTEST(copy, ["train", "train2"]).encode())]
    zips["NutriSole_G9J_TEAM_PHOTOS.zip"] = [("G9_stageJ_team_photo_shotlist.md", (D / "G9_stageJ_team_photo_shotlist.md").read_bytes()),
                                            ("sessions_TEMPLATE.csv", SESSIONS_TEMPLATE.encode()), ("SUBMISSION_STEPS.md", TEAM_STEPS.encode())]
    zips["NutriSole_G9J_ADJUDICATOR.zip"] = [(ORIGINALS.name, ORIGINALS.read_bytes()), ("ADJUDICATION_INSTRUCTIONS.md", ADJ.encode()),
                                            ("annotation_guide.md", guide), ("G9_stageJ_readiness.md", (D / "G9_stageJ_readiness.md").read_bytes())]
    zips["NutriSole_G9J_ADJUDICATOR_AI_POSTHOC_release_after_exports.zip"] = [("README_POSTHOC_AI.txt", POSTHOC.encode())] + \
        [(f"AI_ASSISTED_NOT_HUMAN/{p.parent.parent.name if p.parent.name == 'AI_ASSISTED_NOT_HUMAN' else p.parent.name}/{p.name}", p.read_bytes()) for p in AI_FILES]
    for zn, members in zips.items():
        zp = STAGE / zn
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED if "ANNOTATOR" in zn or "ADJUDICATOR.zip" in zn else zipfile.ZIP_DEFLATED) as z:
            for n, b in members: add_bytes(z, n, b)
        man["zips"][zn] = dict(sha256=sha(zp.read_bytes()), mb=round(zp.stat().st_size / 1e6, 1), members=[n for n, _ in members])
    # AI-leak grep: every annotator and team zip, recursing into inner zips (html/csv/txt/md decoded)
    def scan(b, path=""):
        hits = []
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            for n in z.namelist():
                d = z.read(n)
                if n.endswith(".zip"): hits += scan(d, path + n + "/"); continue
                for m in AI_MARKERS:
                    if m.lower() in n.lower().encode() or m in d: hits.append(f"{path}{n}: {m.decode()}")
        return hits
    for zn in zips:
        if "AI_POSTHOC" in zn: continue
        hits = scan((STAGE / zn).read_bytes())
        man["ai_leak_check"][zn] = hits or "clean"
        if hits and "ANNOTATOR" in zn: raise SystemExit(f"AI material in {zn}: {hits[:5]}")
    (STAGE / "MISSING_INPUTS_CHECKLIST.md").write_text((D / "G9_stageJ3_missing_inputs_checklist.md").read_text())
    (STAGE / "HANDOFF_MANIFEST.json").write_text(json.dumps(man, indent=1))
    for p in STAGE.iterdir(): shutil.copyfile(p, DEST / p.name)
    return man


if __name__ == "__main__":
    m = build(); print(json.dumps({k: (v["mb"], v["sha256"][:16]) for k, v in m["zips"].items()}, indent=1)); print(json.dumps(m["ai_leak_check"], indent=1))
