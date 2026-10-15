"""G9 Stage J6: versioned amendment 001 to the HUMAN_REVIEWED_AI_ASSISTED record (G9J5-HRAI-v1) for item P729 only.

The reviewer (M Faizan, project lead) approved the Hark v2 correction in chat on 2026-10-16 00:06 PKT:
  P729: uncertain -> carrot; bag=true, multiple=true, cut=false, rotten=false, occluded=false (label is not `occluded`).
  His evidence: real orange carrots in transparent wrapping, sufficiently visible.

What this writes (new directory, refuses to overwrite; v1 is never touched):
  out/j5/human_review_ai_assisted_v2/amendment_001_P729.json   amendment (before/after, approval source, hashes of v1 files)
  out/j5/human_review_ai_assisted_v2/reviewed_labels_pilot2.csv  v1 table with ONLY the P729 row changed (+ amendment column)
  out/j5/human_review_ai_assisted_v2/*.sha256

Tier stays HUMAN_REVIEWED_AI_ASSISTED: non-blind, single reviewer, not kappa, not a verified manifest, not a training label, cannot unlock
H3. The original AI CSVs, the v2 Hark CSV and the v1 record stay unmodified (their sha256 are re-checked here and in tests).

  python3 j6_p729_amendment.py           # write v2 (refuses if it exists)
  python3 j6_p729_amendment.py --check   # verify v1 untouched + v2 consistent, write nothing
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j_agree as JA            # noqa: E402
import j5_human_review as HR    # noqa: E402

TIER = HR.TIER
V1 = HR.REC_DIR
V2DIR = HR.OUT / "j5" / "human_review_ai_assisted_v2"
ITEM = "P729"
APPROVED_AT = "Fri 2026-10-16 12:06 AM PKT (UTC+05:00)"
APPROVAL_SOURCE = dict(kind="chat message from M Faizan to Hark (relayed verbatim in the Stage J6 brief)", at=APPROVED_AT,
                       decision="approved the versioned correction P729 uncertain -> carrot",
                       evidence_stated="real orange carrots in transparent wrapping, sufficiently visible",
                       tags_stated=dict(bag=True, multiple=True, cut=False, rotten=False, occluded=False))
NEW = dict(label="carrot", cut="0", bag="1", multi="1", rotten_damaged="0", other_produce_name="")
V1_FILES = ["human_review_record.json", "reviewed_labels_pilot.csv", "reviewed_labels_pilot2.csv"]


def v1_hashes() -> dict:
    out = {}
    for f in V1_FILES:
        p = V1 / f; want = (V1 / (f + ".sha256")).read_text().split()[0]
        out[f] = dict(sha256=HR.sha(p), sha256_file_matches=HR.sha(p) == want)
    return out


def amended_rows():
    rows = HR.rows(V1 / "reviewed_labels_pilot2.csv"); hit = 0; before = None
    for r in rows:
        r["amendment"] = ""
        if r["item_id"] == ITEM:
            before = dict(r); hit += 1
            r.update(NEW)
            ro, c13 = JA.role_of("carrot", 0, 1, "")
            r["role_if_accepted"], r["class13_if_accepted"] = ro, c13
            r["disputed"] = ""
            r["amendment"] = f"amendment_001 approved by M Faizan {APPROVED_AT}"
    if hit != 1: raise SystemExit(f"{ITEM} found {hit} times in v1 pilot2 table")
    return rows, before


def build(check_only=False):
    problems = []
    h1 = v1_hashes()
    for f, v in h1.items():
        if not v["sha256_file_matches"]: problems.append(f"v1 {f} changed")
    ai_ok = HR.sha(HR.SOURCES["pilot2"]["csv"]) == HR.SOURCES["pilot2"]["sha256"]
    v2h_ok = HR.sha(HR.V2["csv"]) == HR.V2["sha256"]
    if not ai_ok: problems.append("original AI pilot2 CSV changed")
    if not v2h_ok: problems.append("Hark v2 CSV changed")
    v2hark = {r["item_id"]: r for r in HR.rows(HR.V2["csv"])}[ITEM]
    matches_v2 = all(str(v2hark[k]) == NEW[k] for k in ("label", "cut", "bag", "multi", "rotten_damaged"))
    if not matches_v2: problems.append("approved P729 tags differ from Hark v2 row")
    rows, before = amended_rows()
    after = next(r for r in rows if r["item_id"] == ITEM)
    amend = dict(schema_version=1, amendment_id="G9J5-HRAI-v1/amendment_001", amends_record="G9J5-HRAI-v1", supersedes_for_items=[ITEM],
                 record_version="v2 (= v1 + amendment_001; v1 kept byte-identical)", provenance=TIER, tier_properties=JA.PROVENANCE_TIERS[TIER],
                 reviewer=dict(name="M Faizan", role="project lead", count=1), blind=False, independent=False,
                 approval_source=APPROVAL_SOURCE, item=ITEM, batch="pilot2", split=after["split"],
                 before=dict((k, before[k]) for k in ("label", "cut", "bag", "multi", "rotten_damaged", "role_if_accepted", "class13_if_accepted", "disputed")),
                 after=dict((k, after[k]) for k in ("label", "cut", "bag", "multi", "rotten_damaged", "role_if_accepted", "class13_if_accepted")),
                 occluded=False, occluded_note="In the Stage J schema `occluded` is a label, not a tag; the approved label is carrot, so occluded=false.",
                 matches_hark_v2_row=matches_v2, hark_v2_sha256=HR.V2["sha256"],
                 original_annotation=dict(path=str(HR.SOURCES["pilot2"]["csv"].relative_to(HR.J)), sha256=HR.SOURCES["pilot2"]["sha256"],
                                          label="uncertain", kept_unmodified=ai_ok),
                 v1_files=h1, effect=dict(
                     role="supported_packaged (B=1): a must-not-grade packaged item, never a clean supported item",
                     uncertain_rows_pilot2="119 -> 118", disputed_rows="1 -> 0",
                     kappa_evidence=False, verified_manifest=False, counts_for_eval_gates=False, training_label=False, can_unlock_h3=False),
                 problems=problems)
    if check_only: return amend, rows
    V2DIR.mkdir(parents=True, exist_ok=False)
    ap = V2DIR / "amendment_001_P729.json"
    ap.write_text(json.dumps(amend, indent=1, ensure_ascii=False), encoding="utf-8")
    Path(str(ap) + ".sha256").write_text(HR.sha(ap) + f"  {ap.name}\n")
    mp = V2DIR / "reviewed_labels_pilot2.csv"
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    Path(str(mp) + ".sha256").write_text(HR.sha(mp) + f"  {mp.name}\n")
    (V2DIR / "README.md").write_text(
        "# HUMAN_REVIEWED_AI_ASSISTED record, version 2\n\nv2 = v1 (`../human_review_ai_assisted_v1/`, unchanged) + amendment_001 (P729 only).\n"
        f"P729: uncertain -> carrot, bag=1, multi=1, cut=0, rotten=0 (not occluded). Approved by M Faizan in chat, {APPROVED_AT}.\n"
        "Tier unchanged: non-blind single reviewer; never blind annotation, kappa evidence, verified manifest or training label.\n"
        "pilot (265) is unchanged and stays in v1 only.\n", encoding="utf-8")
    return amend, rows


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--check", action="store_true")
    x = a.parse_args(); am, _ = build(check_only=x.check)
    print(json.dumps(dict(before=am["before"], after=am["after"], problems=am["problems"], matches_hark_v2=am["matches_hark_v2_row"]), indent=1))
