"""G9 Stage J3: versioned AI review v2 of Pilot 2 after viewing the recovered full-resolution originals of P729, P756, P773.

Provenance: AI_ASSISTED_NOT_HUMAN (Hark). This NEVER edits the project lead's review
(out/handoff/20261015_pilot2_visual_review/, SHA256SUMS untouched). It writes a NEW folder
out/handoff/20261015_pilot2_visual_review_v2_hark/ with:
  * AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335_v2_hark.csv  (full 335-row export schema, the 3 rows revised;
    sits under the AI_ASSISTED_NOT_HUMAN glob so j_annotation.validate_human_pair refuses it and near-copies of it as human evidence)
  * G9J_pilot2_ai_review_corrections_v2.csv / .json  (old label, new label, tags, reason, evidence, original sha256)
  * README.md, SHA256SUMS.txt
Nothing here is a human label; it is post-hoc adjudicator material only and must not reach the two independent annotators.
Usage: j3_ai_review_v2.py [--check]"""
import csv, hashlib, io, json, sys
from pathlib import Path

J = Path(__file__).resolve().parents[1]
V1 = J / "out/handoff/20261015_pilot2_visual_review"
V1_CSV = V1 / "AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335.csv"
V1_SHA = "6c17debff4bb545bc8841abc140242d86a1fed86dc303ade4274eac35048d2aa"
V2 = J / "out/handoff/20261015_pilot2_visual_review_v2_hark"
V2_CSV = V2 / "AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335_v2_hark.csv"
REVIEWED_AT = "2026-10-15T20:45:00+05:00"
ORIG = json.loads((V1 / "G9J_pilot2_source_original_retry_hark.json").read_text())["items"]
ORIG = {o["item_id"]: o for o in ORIG}

# Decisions written after viewing each recovered original with read_file (whole frame + 50% centre crop).
DECISIONS = [
    dict(item_id="P729", new=dict(label="carrot", cut="0", bag="1", multi="1", rotten_damaged="0", other_produce_name="", occluded_or_printed_what=""),
         confidence="medium", change="LABEL_CHANGED",
         reason=("Full-resolution original (3333x2138) shows every produce item in the frame is a whole, uncut, real carrot; dozens are fully "
                 "visible through and above an open clear plastic bag. The opaque item is a cling-wrapped rectangular non-produce package lying "
                 "on top of the carrots (not ice, not a carrot). Guide rule for a pile of one kind (\"market stall of oranges ... citrus_orange + M "
                 "if they are all the same kind\") and the B-tag rule (\"if you can see it clearly through the bag, choose the fruit + B\") give "
                 "carrot + B + M. No individual carrot is the main item with < half visible, so `occluded` does not apply. The v1 revision to "
                 "`uncertain` was made from the 640 px package only and after source-context exposure; the original resolves the identity of the "
                 "surroundings and of the block. Residual edge: the geometric centre of the frame falls on the non-produce package, so the "
                 "adjudicator may still choose `uncertain`/`exclude`; with B=1 the item counts as supported_packaged (must-not-grade negative), "
                 "never as a clean supported item, so either choice is grading-safe."),
         evidence="read_file: whole frame downscaled to 1600 px + centre crop 1666x1069 of the native original; carrots' crowns, fine roots and "
                  "ring texture visible; package edge and cling-film wrinkles visible"),
    dict(item_id="P756", new=dict(label="other_produce", cut="0", bag="0", multi="0", rotten_damaged="0", other_produce_name="other", occluded_or_printed_what=""),
         confidence="high", change="CONFIRMED_NO_LABEL_CHANGE",
         reason=("Full-resolution original (1600x902): single elongated orange fruit with longitudinal ridges, a seam, a pointed apex and a "
                 "blossom scar, held between thumb and fingers against dry scrub. Not a carrot (no taproot taper, no crown, no root rings); "
                 "consistent with Jacaratia spinosa. More than half of the fruit is visible (thumb covers a small lower-left part), so not "
                 "`occluded`. The source-query stratum `occluded` is not borne out by the pixels. Label and tags unchanged; confidence raised "
                 "medium -> high."),
         evidence="read_file: whole frame at native 1600 px; skin texture, ridges and dark lenticel spots visible"),
    dict(item_id="P773", new=dict(label="apple", cut="0", bag="1", multi="1", rotten_damaged="0", other_produce_name="", occluded_or_printed_what=""),
         confidence="medium", change="CONFIRMED_NO_LABEL_CHANGE",
         reason=("The recovered original is 536x471, the SAME size as the pilot-2 package, so it adds no resolution (pHash distance 0). It shows "
                 "~20 red round fruits each tied in a clear plastic bag (green twist ties), inside an open white bin bag; one unwrapped red-yellow "
                 "apple with a stem cavity sits left of centre. Shape, colour gradient and stem cavity support apple; the fruits are seen clearly "
                 "through the clear wrap and from the open top, so `occluded` does not apply (unlike the guide's 'apples in a white bag, only tops "
                 "visible' example). Label and tags unchanged; confidence stays medium because the wrapping hides skin texture on most fruits."),
         evidence="read_file: native 536x471 frame and centre crop; no higher-resolution source exists on Commons for this file"),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build():
    if sha(V1_CSV) != V1_SHA: raise SystemExit("v1 AI CSV changed; refuse to build v2")
    rd = csv.DictReader(open(V1_CSV, newline="", encoding="utf-8")); cols = rd.fieldnames; rows = list(rd)
    by = {r["item_id"]: r for r in rows}
    corr = []
    for d in DECISIONS:
        r = by[d["item_id"]]; old = {k: r[k] for k in d["new"]}
        o = ORIG[d["item_id"]]
        corr.append(dict(item_id=d["item_id"], change=d["change"], old_label=old["label"],
                         old_tags="".join(t for t, k in (("C", "cut"), ("B", "bag"), ("M", "multi"), ("X", "rotten_damaged")) if old[k] == "1"),
                         new_label=d["new"]["label"],
                         new_tags="".join(t for t, k in (("C", "cut"), ("B", "bag"), ("M", "multi"), ("X", "rotten_damaged")) if d["new"][k] == "1"),
                         new_other_produce_name=d["new"]["other_produce_name"], new_confidence=d["confidence"], reason=d["reason"], evidence=d["evidence"],
                         original_sha256=o["sha256"], original_px=f"{o['width']}x{o['height']}", source_page_url=o["source_page_url"],
                         v1_note=r["note"], provenance="AI_ASSISTED_NOT_HUMAN", human_verified=False, reviewed_at=REVIEWED_AT,
                         source_context_used=True))
        r.update(d["new"]); r["note"] = f"[v2 hark {d['change']}] " + d["reason"][:300]; r["labelled_at"] = REVIEWED_AT
    (V2 / "AI_ASSISTED_NOT_HUMAN").mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    V2_CSV.write_text(buf.getvalue(), encoding="utf-8")
    ccols = list(corr[0])
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=ccols, lineterminator="\n"); w.writeheader(); w.writerows(corr)
    (V2 / "G9J_pilot2_ai_review_corrections_v2.csv").write_text(buf.getvalue(), encoding="utf-8")
    meta = dict(version="v2_hark", supersedes_nothing=True, base_review="20261015_pilot2_visual_review (unchanged)", base_csv_sha256=V1_SHA,
                provenance="AI_ASSISTED_NOT_HUMAN", human_verified_images=0, label_changes=sum(c["change"] == "LABEL_CHANGED" for c in corr),
                confirmations=sum(c["change"] != "LABEL_CHANGED" for c in corr), rows=len(rows), corrections=corr,
                rule="post-hoc adjudicator material only; never shown to annotator 1 or 2 before both independent exports are hash-recorded")
    (V2 / "G9J_pilot2_ai_review_corrections_v2.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    (V2 / "README.md").write_text(README, encoding="utf-8")
    files = sorted(p for p in V2.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (V2 / "SHA256SUMS.txt").write_text("".join(f"{sha(p)}  {p.relative_to(V2).as_posix()}\n" for p in files), encoding="utf-8")
    return meta


def check():
    for line in (V2 / "SHA256SUMS.txt").read_text().splitlines():
        h, f = line.split("  ", 1)
        if sha(V2 / f) != h: raise SystemExit(f"hash mismatch {f}")
    if sha(V1_CSV) != V1_SHA: raise SystemExit("v1 changed")
    print("v2 review OK; v1 untouched")


README = """# Pilot 2 AI review v2 (Hark): recovered full-resolution originals P729, P756, P773

**Provenance: `AI_ASSISTED_NOT_HUMAN`. Post-hoc adjudicator material. Keep away from both independent annotators until both
exports and attestations are hash-recorded.** Human-verified images remain **0**.

This is a NEW versioned review. The project lead's `20261015_pilot2_visual_review/` (CSV sha256 `6c17deb...d2aa`, its SHA256SUMS,
revision log and every other file) is unchanged. v2 = v1 with three rows re-examined against the originals recovered on 2026-10-15
(sha256 recorded in `G9J_pilot2_source_original_retry_hark.json`; pixels are not committed, they sit in the adjudicator-only zip).

| Item | v1 | v2 | Change | Why (short) |
|---|---|---|---|---|
| P729 | uncertain (B M) | **carrot (B M)** | label changed | Original shows only whole real carrots, most fully visible through an open clear bag; the opaque thing is a cling-wrapped non-produce package on top. Same-kind pile + clear-bag rules give carrot+B+M. Adjudicator may still pick uncertain/exclude because the frame centre falls on the package; with B it is a must-not-grade packaged negative either way. |
| P756 | other_produce / other | other_produce / other | confirmed | Ridged orange fruit (Jacaratia spinosa), not a carrot; > half visible in the hand, so not occluded. Confidence medium -> high. |
| P773 | apple (B M) | apple (B M) | confirmed | Original is 536x471, identical size to the package (no extra resolution). Apples individually clear-wrapped plus one unwrapped apple; visible through wrap, not occluded. |

The full 335-row v2 export lives under `AI_ASSISTED_NOT_HUMAN/` so `j_agree.py` / `j_annotation.validate_human_pair` reject it, and
any >=95% near-copy of it, as independent human evidence (same rule as v1). Source context (file names) was used for all three
items, so this review is not blind. Regenerate / verify: `python3 scripts/j3_ai_review_v2.py [--check]`.
"""

if __name__ == "__main__":
    check() if "--check" in sys.argv else print(json.dumps({k: v for k, v in build().items() if k != "corrections"}, indent=1))
