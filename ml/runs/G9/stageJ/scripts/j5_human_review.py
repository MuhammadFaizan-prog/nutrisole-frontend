"""G9 Stage J5: record the project lead's review of the AI-assisted pilot labels as a NEW, versioned provenance record.

Provenance tier: HUMAN_REVIEWED_AI_ASSISTED (j_agree.PROVENANCE_TIERS). One reviewer (M Faizan), NOT blind (he reviewed AI labels that were
already filled in), NOT independent double annotation, NOT kappa evidence. The original AI review CSVs and the v2 corrections are only
referenced by sha256; they are never modified or copied over. No CSV, identity, attestation or kappa is invented here.

  python3 j5_human_review.py            # write out/j5/human_review_ai_assisted_v1/ (refuses to overwrite: versioned)
  python3 j5_human_review.py --check    # re-verify the record against the referenced files (hashes, IDs) without writing

What the record does: binds the reviewer's chat statement (verbatim, timestamp) to the exact AI CSV bytes he reviewed, checks the image IDs
against the frozen blind keys, reports completeness / class balance / disputed rows / train-eval independence, and evaluates every frozen
R/T/E gate with this tier (j_gates.tier_gate_report). It never writes verified_manifest_*, agreement.json or USER_TRAINING_GO.json.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent; J = HERE.parent; OUT = J / "out"; HO = OUT / "handoff"
sys.path.insert(0, str(HERE))
import j_agree as JA   # noqa: E402
import j_gates as G    # noqa: E402

TIER = "HUMAN_REVIEWED_AI_ASSISTED"
REC_DIR = OUT / "j5" / "human_review_ai_assisted_v1"
STATEMENT = ("I have manually reviewed the AI annotation files against the images and confirm that the labels match my assessment. "
             "Do not unnecessarily recreate the same annotations or restart Stage J. Preserve the existing CSV labels and image IDs. "
             "Record my confirmation as human review of AI-assisted labels, not as fabricated independent blind annotation. "
             "Use the existing Stage J workflow to record this review, identify which frozen H3 requirements are satisfied and which "
             "genuinely remain pending, and prepare the next steps for improving the existing H2 model.")
STATED_AT = "2026-10-15T22:53:00+05:00"
SOURCES = {
    "pilot": dict(csv=HO / "20261015_visual_review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv",
                  sha256="4bf78b68f47831c17e6872218f46dc3027210acaf7c03f0a28458377844b6ef9", n=265),
    "pilot2": dict(csv=HO / "20261015_pilot2_visual_review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335.csv",
                   sha256="6c17debff4bb545bc8841abc140242d86a1fed86dc303ade4274eac35048d2aa", n=335),
}
V2 = dict(csv=HO / "20261015_pilot2_visual_review_v2_hark/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335_v2_hark.csv",
          sha256="09ad0c9d08463c623ffc828fda6b3b627b8ebc3fb81d169fe638a0e8e6596b7c",
          corrections_csv=HO / "20261015_pilot2_visual_review_v2_hark/G9J_pilot2_ai_review_corrections_v2.csv",
          corrections_sha256="c78d96a89204074af283a7a117fc8767a307231272453605c3142b8d5bffefc6")
IMG = {"pilot": "/workspace/work/g9i/cands/img", "pilot2": "/workspace/work/g9j2/eval2/img",
       "train": "/workspace/work/g9j/train/img", "train2": "/workspace/work/g9j2/train2/img"}
UPLOADS = Path("/workspace/projects/9399e4e3-d6d0-4c6b-a760-12b4c7c9c514/files/uploads")


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 16), b""): h.update(ch)
    return h.hexdigest()


def rows(p):
    with open(p, newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))


def role(r):
    lab = JA.norm_label(r.get("label", "")) or ""
    return JA.role_of(lab, JA.flag(r.get("cut")), JA.flag(r.get("bag")), (r.get("other_produce_name") or "").strip()) if lab not in ("", "uncertain") else ("excluded", "")


def check_sources(problems):
    info = {}
    for b, s in SOURCES.items():
        got = sha(s["csv"]); R = rows(s["csv"]); key = JA.load_key(b); ids = [r["item_id"] for r in R]
        dup = sorted(i for i, c in Counter(ids).items() if c > 1)
        ok = dict(sha256_matches=got == s["sha256"], n_rows=len(R), n_expected=s["n"], duplicate_ids=dup,
                  ids_equal_frozen_key=set(ids) == set(key), missing_ids=sorted(set(key) - set(ids)), extra_ids=sorted(set(ids) - set(key)),
                  blank_labels=sum(1 for r in R if not (r.get("label") or "").strip()),
                  invalid_labels=sorted({r["label"] for r in R if JA.norm_label(r.get("label", "")) is None}),
                  annotator_column=sorted({r.get("annotator", "") for r in R}), frozen_key_sha256=JA.V.frozen_digest(JA.key_path(b)))
        for k, bad in (("sha256_matches", not ok["sha256_matches"]), ("duplicate_ids", dup), ("ids", not ok["ids_equal_frozen_key"]),
                       ("blank", ok["blank_labels"]), ("invalid", ok["invalid_labels"]), ("count", len(R) != s["n"])):
            if bad: problems.append(f"{b}: {k} check failed")
        info[b] = ok
    v2 = dict(sha256_matches=sha(V2["csv"]) == V2["sha256"], corrections_sha256_matches=sha(V2["corrections_csv"]) == V2["corrections_sha256"])
    if not all(v2.values()): problems.append("v2 Hark files changed")
    info["pilot2_v2_hark"] = v2
    return info


def balance(b):
    R = rows(SOURCES[b]["csv"]); key = JA.load_key(b)
    roles = Counter(); sup = Counter(); split = Counter(key[r["item_id"]]["split"] for r in R)
    for r in R:
        ro, c13 = role(r); roles[ro] += 1
        if ro == "supported" and key[r["item_id"]]["split"] == "J-eval": sup[c13] += 1
    return dict(labels=dict(Counter(r["label"] for r in R)), roles=dict(roles), clean_supported_J_eval=dict(sup), splits=dict(split),
                uncertain=sum(1 for r in R if r["label"] == "uncertain"))


def disputed():
    """Rows where the record is NOT settled by the reviewer's statement: the v2 Hark change he has not explicitly accepted, plus every
    row whose reviewed label is `uncertain` (excluded under R3 either way, never guessed)."""
    v1 = {r["item_id"]: r for r in rows(SOURCES["pilot2"]["csv"])}; v2 = {r["item_id"]: r for r in rows(V2["csv"])}
    changed = [dict(item_id=i, batch="pilot2", v1_label=v1[i]["label"], v2_hark_label=v2[i]["label"],
                    v1_tags="".join(t for t, k in (("C", "cut"), ("B", "bag"), ("M", "multi"), ("X", "rotten_damaged")) if JA.flag(v1[i].get(k))),
                    status="NEEDS_REVIEWER_CONFIRMATION (statement does not say whether v2 was accepted)")
               for i in sorted(v1) if (v1[i]["label"], v1[i]["cut"], v1[i]["bag"], v1[i]["multi"]) != (v2[i]["label"], v2[i]["cut"], v2[i]["bag"], v2[i]["multi"])]
    unc = {b: sorted(r["item_id"] for r in rows(s["csv"]) if r["label"] == "uncertain") for b, s in SOURCES.items()}
    return changed, unc


def independence(max_img=None):
    """Train/eval separation for the reviewed eval items: cand-key overlap, uploader/source owner overlap, and pHash Hamming <= 10
    between every reviewed eval image and every J-train/J-dev image on disk (imagehash; skipped honestly if images are absent)."""
    keys = {b: JA.load_key(b) for b in ("pilot", "pilot2", "train", "train2")}
    ev = {v["key"]: (b, v) for b in ("pilot", "pilot2") for v in keys[b].values()}
    tr = {v["key"]: (b, v) for b in ("train", "train2") for v in keys[b].values()}
    owner = lambda v: (v["source"], v["uploader"]) if v["source"] == "commons" else (v["source"], "")
    ev_own = {owner(v) for _, v in ev.values()}; tr_own = {owner(v) for _, v in tr.values()}
    shared_src = sorted({s for s, _ in ev_own} & {s for s, _ in tr_own})
    res = dict(eval_items=len(ev), train_dev_items=len(tr), cand_key_overlap=sorted(set(ev) & set(tr)),
               commons_uploader_overlap=sorted(u for s, u in ev_own & tr_own if s == "commons"),
               dataset_overlap_non_commons=sorted(s for s in shared_src if s != "commons"),
               eval_only_sources_in_train=sorted({v["source"] for _, v in tr.values()} & {"fruitnet", "carrot_m", "tomato_m"}),
               train_splits=dict(Counter(v["split"] for _, v in tr.values())))
    try:
        import imagehash, numpy as np
        from PIL import Image
    except Exception as e:
        res["phash"] = f"not run: {e}"; return res
    def ph(b, k):
        p = Path(IMG[b]) / f"{k}.jpg"
        if not p.exists(): return None
        with Image.open(p) as im: return int(str(imagehash.phash(im.convert("RGB"))), 16)
    E = [(k, ph(b, k)) for k, (b, _) in list(ev.items())[:max_img]]; T = [(k, ph(b, k)) for k, (b, _) in list(tr.items())[:max_img]]
    miss = sum(1 for _, h in E + T if h is None); E = [x for x in E if x[1] is not None]; T = [x for x in T if x[1] is not None]
    ta = np.array([h for _, h in T], dtype=np.uint64); close = []
    for k, h in E:
        x = np.bitwise_xor(ta, np.uint64(h)); d = np.array([bin(int(v)).count("1") for v in x]) if len(ta) else np.array([64])
        if d.min() <= 10: close.append(dict(eval_key=k, train_key=T[int(d.argmin())][0], hamming=int(d.min())))
    res["phash"] = dict(rule="Hamming <= 10", eval_hashed=len(E), train_hashed=len(T), images_missing=miss, near_duplicates=close)
    return res


def uploads_state():
    """The 22:23 PKT uploads: are any of them human exports, or byte-identical blank packs?"""
    packs = json.loads((HO / "j3_handoff_manifest.json").read_text())["inner_packs"]
    blank = {v["sha256"]: k for k, v in packs.items()}
    out = {}
    if UPLOADS.exists():
        for p in sorted(UPLOADS.glob("nutrisole_G9J_*annotator*")):
            h = sha(p); out[p.name] = dict(sha256=h, identical_blank_pack=blank.get(h))
        out["_csv_or_json_files_in_uploads"] = sorted(p.name for p in UPLOADS.iterdir() if p.suffix.lower() in (".csv", ".json"))
    return out


def build(check_only=False, phash=True):
    problems = []
    src = check_sources(problems)
    bal = {b: balance(b) for b in SOURCES}
    changed, unc = disputed()
    ind = independence() if phash else dict(phash="skipped (--no-phash)")
    record = dict(
        schema_version=1, record_id="G9J5-HRAI-v1", provenance=TIER,
        tier_properties=JA.PROVENANCE_TIERS[TIER],
        reviewer=dict(name="M Faizan", role="project lead", count=1),
        review_mode=dict(blind=False, independent_double_annotation=False, reviewed_ai_prefilled_labels=True,
                         note="The reviewer saw the AI-assisted labels while reviewing. This is a confirmation of AI-assisted labels, not a blind annotation."),
        stated_at=STATED_AT, stated_at_display="Thu 2026-10-15 10:53 PM PKT (UTC+05:00)",
        source=dict(kind="chat statement to Hark (relayed in the Stage J5 brief)", verbatim=STATEMENT,
                    not_a_file="No exported CSV or signed attestation accompanies this statement; none was created on his behalf."),
        reviewed_files={b: dict(path=str(s["csv"].relative_to(J)), sha256=s["sha256"], rows=s["n"], kept_unmodified=True) for b, s in SOURCES.items()},
        hark_v2_corrections=dict(path=str(V2["csv"].relative_to(J)), sha256=V2["sha256"], corrections_csv=str(V2["corrections_csv"].relative_to(J)),
                                 corrections_sha256=V2["corrections_sha256"], changed_rows=changed,
                                 acceptance="UNCONFIRMED: the statement does not say whether he accepted the v2 P729 change (uncertain -> carrot B M). "
                                            "The record therefore keeps his v1 label (uncertain) as the reviewed label and lists P729 as disputed."),
        id_checks=src, class_balance=bal, uncertain_rows=dict((b, dict(n=len(v), item_ids=v)) for b, v in unc.items()),
        train_eval_independence=ind, uploads_22_23=uploads_state(),
        gates=G.tier_gate_report(TIER), problems=problems)
    if check_only: return record
    REC_DIR.mkdir(parents=True, exist_ok=False)  # versioned: never overwrite
    rp = REC_DIR / "human_review_record.json"
    rp.write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
    Path(str(rp) + ".sha256").write_text(sha(rp) + "  human_review_record.json\n")
    # per-item reviewed-label table: the AI CSV labels exactly as reviewed, plus the provenance tier (no label edited)
    for b, s in SOURCES.items():
        key = JA.load_key(b); out = []
        for r in rows(s["csv"]):
            ro, c13 = role(r)
            out.append(dict(item_id=r["item_id"], batch=b, split=key[r["item_id"]]["split"], label=r["label"], other_produce_name=r["other_produce_name"],
                            cut=r["cut"], bag=r["bag"], multi=r["multi"], rotten_damaged=r["rotten_damaged"], role_if_accepted=ro, class13_if_accepted=c13,
                            ai_csv_sha256=s["sha256"], provenance=TIER, reviewer="M Faizan", blind="no", independent="no",
                            disputed="P729 v2 change unconfirmed" if (b == "pilot2" and r["item_id"] in {c["item_id"] for c in changed}) else ""))
        mp = REC_DIR / f"reviewed_labels_{b}.csv"
        with open(mp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
        Path(str(mp) + ".sha256").write_text(sha(mp) + f"  {mp.name}\n")
    return record


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--check", action="store_true"); a.add_argument("--no-phash", action="store_true")
    x = a.parse_args()
    r = build(check_only=x.check, phash=not x.no_phash)
    print(json.dumps(dict(provenance=r["provenance"], problems=r["problems"], gates=r["gates"]["summary"],
                          independence={k: v for k, v in r["train_eval_independence"].items() if k != "phash"},
                          phash=r["train_eval_independence"].get("phash")), indent=1, default=str))
