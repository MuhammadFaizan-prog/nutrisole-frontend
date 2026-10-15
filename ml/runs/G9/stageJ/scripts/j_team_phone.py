"""G9 Stage J: ingestion for FYP-team phone photos (source "team_phone"). No training, no labels decided here.

Spec: docs/cv/gauntlet/G9_stageJ_team_photo_shotlist.md.
Input : a folder of session sub-folders plus sessions.csv
          sessions.csv columns: session_id,photographer,date,place,purpose,licence,consent_confirmed
          purpose  = eval  (bagged/packaged + partly hidden; J-eval only)  |  train  (apple training; J-train only)
          licence  = CC-BY-4.0 | internal-FYP
        file names  TP_<session_id>_<intended>_<condition>_<nnn>.jpg   e.g. TP_S20261018-AB-01_banana_bag-mesh_003.jpg
Rules (frozen with the shot list):
  * the split is decided by the SESSION, never per photo; a session is all-train or all-eval;
  * a photographer may appear in eval sessions OR train sessions, never both (source separation, like the Commons uploader rule);
  * EARLIER-REFERENCE CHECK BY DEFAULT (Stage J3): every photo is compared (64-bit pHash, Hamming <= 10) with the complete committed
    reference manifest out/j3_reference_hashes.json (G0-G7 data, G3 train/DEV, G7 keyframes, Stage D/E/F pools, M-DEV + M-TEST stored
    hashes, CU, Stage H, Stage I candidates, Stage J/J2 candidates; hashes only). Extra lists via --ref-hashes are ADDED to it.
      - a TRAIN photo near an eval photo of this batch or near any reference is QUARANTINED;
      - an EVAL photo near any reference is QUARANTINED too (role named in the reason: training source / earlier eval set), because
        an eval photo that collides with a training source would leak and one that repeats an earlier eval set is not new evidence;
      - eval photos within Hamming <= 6 of each other share a group (burst shots), so one group counts once;
  * `intended` / `condition` in the name are photographer metadata only: they are kept in the lead-only manifest/blind key, NEVER in an
    annotator pack, and never become ground truth. Every team_phone photo still goes through the two independent human annotators;
  * photos carrying EXIF GPS are refused (location must be off); byte-identical files are recorded (exact_duplicate_of) and handled by the pHash rules (Hamming 0);
  * provenance record per photo: sha256, session, photographer, date, place, licence, consent, ingested_at;
  * pixels are not committed to git; only the manifest / provenance / blind key (ids, sha256, pHash, split, quarantine reason) are.
Blind packs (--packs): non-quarantined eval photos -> batch `team_eval` (ids Q001...), train photos -> `team_train` (ids R001...).
  Blind ids are assigned in sha256 order (content hash, not the file name), so they encode neither class nor condition. Packs are
  built by j2_pack.build_from (same tool, guide, seeds 101/202, fallback CSV and contact sheets as Pilot 1/2).
Usage: python3 j_team_phone.py ROOT [--ref-hashes refs.json] [--out manifest.json] [--out-dir DIR --packs]
"""
import argparse, csv, hashlib, json, re, sys, os, shutil, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = "team_phone"
INTENDED = {"apple", "banana", "citrus_orange", "tomato", "carrot", "none"}
CONDITIONS = {"bag-clear", "bag-mesh", "tray-film", "hid-hand", "hid-fruit", "hid-edge", "hid-object", "open"}
EVAL_CONDITIONS = CONDITIONS - {"open"}
# Stage J4: training sessions may cover the identified training shortages (gaps table section 7 + user brief 2026-10-15:
# apple ~65, tomato ~8, banana ~4 projected). Citrus/carrot training sessions stay refused this round (lead decision needed).
TRAIN_CLASSES = {"apple", "banana", "tomato"}
LICENCES = {"CC-BY-4.0", "internal-FYP"}
NAME = re.compile(r"^TP_(S\d{8}-[A-Z]{2,3}-\d{2})_([a-z_]+?)_([a-z]+-[a-z]+|open)_(\d{3})\.(jpe?g|png)$", re.I)
SESSION = re.compile(r"^S\d{8}-[A-Z]{2,3}-\d{2}$")
CROSS, GROUP = 10, 6
COLUMNS = ["session_id", "photographer", "date", "place", "purpose", "licence", "consent_confirmed"]   # shot list section 8
DEFAULT_REFS = HERE.parent / "out" / "j3_reference_hashes.json"
BLANK = {"0000000000000000", "8000000000000000", "ffffffffffffffff"}
INTENT_FIELDS = ("intended_by_photographer", "condition", "file", "session_id", "photographer")   # must never reach an annotator pack


def phash(path):
    import imagehash
    from PIL import Image, ImageOps
    return str(imagehash.phash(ImageOps.exif_transpose(Image.open(path)).convert("RGB")))


def has_gps(path):
    from PIL import Image
    try: return bool(Image.open(path).getexif().get(34853))
    except Exception: return False


def ham(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def load_refs(extra=(), default=True, path=None):
    """[(hash, role, set_name)] from the committed manifest (default) plus any extra hash list (role train_source)."""
    out = []
    p = Path(path) if path else DEFAULT_REFS
    if default:
        if not p.exists(): raise FileNotFoundError(f"reference manifest {p} missing: the earlier-reference check cannot be skipped silently")
        m = json.loads(p.read_text())
        sha = (Path(str(p) + ".sha256").read_text().split()[0] if Path(str(p) + ".sha256").exists() else None)
        if sha and hashlib.sha256(p.read_bytes()).hexdigest() != sha: raise ValueError("reference manifest hash mismatch")
        for name, s in m["sets"].items():
            role = "train_source" if s["role"] in ("train_source", "mixed") else "earlier_eval"
            out += [(h, role, name) for h in s["hashes"]]
    for h in extra:
        out.append((h, "train_source", "extra --ref-hashes"))
    return [r for r in out if r[0] not in BLANK]


class RefIndex:
    def __init__(self, refs):
        import numpy as np
        self.np = np; self.refs = refs
        self.A = np.array([int(h, 16) for h, _, _ in refs], dtype=np.uint64) if refs else np.zeros(0, np.uint64)
        self.masks = {r: np.array([x[1] == r for x in refs], bool) for r in ("train_source", "earlier_eval")}

    def nearest(self, h, role=None):
        np = self.np
        if not len(self.A): return 99, None
        x = self.A ^ np.uint64(int(h, 16))
        d = np.bitwise_count(x) if hasattr(np, "bitwise_count") else np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(1)
        if role:
            mask = self.masks[role]
            if not mask.any(): return 99, None
            d = np.where(mask, d, 99)
        j = int(d.argmin()); return int(d[j]), self.refs[j]


def load_sessions(path):
    rd = csv.DictReader(open(path, encoding="utf-8-sig", newline=""))
    cols = [c.strip() for c in (rd.fieldnames or [])]
    if cols != COLUMNS:
        raise ValueError(f"sessions.csv columns must be exactly {','.join(COLUMNS)} (got {','.join(cols)})")
    rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k is not None} for r in rd]
    S, owner = {}, {}
    for r in rows:
        sid = r["session_id"].strip()
        if not SESSION.match(sid): raise ValueError(f"bad session_id {sid!r}")
        if sid in S: raise ValueError(f"duplicate session {sid}")
        if r["purpose"] not in ("train", "eval"): raise ValueError(f"{sid}: purpose must be train or eval")
        if r["licence"] not in LICENCES: raise ValueError(f"{sid}: licence must be one of {sorted(LICENCES)}")
        if r.get("consent_confirmed", "").strip().lower() != "yes": raise ValueError(f"{sid}: consent_confirmed must be yes")
        who = r["photographer"].strip().lower()
        if not who: raise ValueError(f"{sid}: photographer required")
        if owner.setdefault(who, r["purpose"]) != r["purpose"]:
            raise ValueError(f"photographer {r['photographer']!r} has both train and eval sessions (source leak)")
        S[sid] = dict(r, session_id=sid)
    return S


def ingest(root, ref_hashes=(), default_refs=True, ref_manifest=None, ingested_at=None):
    root = Path(root)
    S = load_sessions(root / "sessions.csv")
    items, errors, seen = [], [], {}
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name != "sessions.csv" and not x.name.startswith(".")):
        m = NAME.match(p.name)
        if not m: errors.append(f"bad file name: {p.name}"); continue
        sid, intended, cond = m.group(1), m.group(2).lower(), m.group(3).lower()
        if sid not in S: errors.append(f"{p.name}: session {sid} not in sessions.csv"); continue
        if p.parent != root and p.parent.name != sid: errors.append(f"{p.name}: lies in folder {p.parent.name}, not its session folder {sid}"); continue
        if intended not in INTENDED or cond not in CONDITIONS: errors.append(f"{p.name}: unknown class/condition"); continue
        split = "J-eval" if S[sid]["purpose"] == "eval" else "J-train"
        if split == "J-eval" and cond not in EVAL_CONDITIONS: errors.append(f"{p.name}: eval session photo must be bagged or partly hidden"); continue
        if split == "J-train" and intended not in TRAIN_CLASSES: errors.append(f"{p.name}: train sessions this round cover {sorted(TRAIN_CLASSES)} only"); continue
        if split == "J-train" and cond != "open": errors.append(f"{p.name}: train session photos use condition 'open' (no packaging/hiding)"); continue
        if has_gps(p): errors.append(f"{p.name}: EXIF GPS present (turn location off / strip before hand-over)"); continue
        b = p.read_bytes(); h = hashlib.sha256(b).hexdigest()
        dup = seen.setdefault(h, p.name)
        items.append(dict(exact_duplicate_of=dup if dup != p.name else "", file=p.name, path=str(p), source=SOURCE, session_id=sid, photographer=S[sid]["photographer"], split=split,
                          intended_by_photographer=intended, condition=cond, licence=S[sid]["licence"],
                          sha256=h, phash=phash(p), human_verified=False))
    if errors: raise ValueError("; ".join(errors[:20]))
    refs = load_refs(ref_hashes, default=default_refs, path=ref_manifest); R = RefIndex(refs)
    ev = [i for i in items if i["split"] == "J-eval"]
    for i in items:
        d_ref, hit = R.nearest(i["phash"])
        i["ref_dmin"] = d_ref
        if i["split"] == "J-eval":
            d_tr, hit_tr = R.nearest(i["phash"], "train_source")
            if d_tr <= CROSS: i["quarantine"] = f"eval photo near-dup (Hamming {d_tr}) of an earlier TRAINING source ({hit_tr[2]})"
            elif d_ref <= CROSS: i["quarantine"] = f"eval photo near-dup (Hamming {d_ref}) of an earlier evaluation/holdout set ({hit[2]})"
            continue
        d_eval = min((ham(i["phash"], e["phash"]), e["file"]) for e in ev) if ev else (99, None)
        if d_eval[0] <= CROSS: i["quarantine"] = f"near-dup (Hamming {d_eval[0]}) of eval photo {d_eval[1]}"
        elif d_ref <= CROSS: i["quarantine"] = f"near-dup (Hamming {d_ref}) of a reference set ({hit[2]})"
    kept_ev = [e for e in ev if not e.get("quarantine")]
    for k, e in enumerate(kept_ev):                              # burst grouping inside eval (one group counts once)
        e["group"] = next((o["group"] for o in kept_ev[:k] if ham(e["phash"], o["phash"]) <= GROUP), e["file"])
    counts = {}
    for i in items:
        key = f"{i['split']}{'/quarantined' if i.get('quarantine') else ''}"
        counts[key] = counts.get(key, 0) + 1
    at = ingested_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    provenance = [dict(sha256=i["sha256"], source=SOURCE, session_id=i["session_id"], photographer=i["photographer"], date=S[i["session_id"]]["date"],
                       place=S[i["session_id"]]["place"], purpose=S[i["session_id"]]["purpose"], licence=i["licence"],
                       consent_confirmed=S[i["session_id"]]["consent_confirmed"].lower(), ingested_at=at, file=i["file"]) for i in items]
    refsets = sorted({r[2] for r in refs})
    return dict(source=SOURCE, sessions=len(S), counts=counts, eval_groups=len({e["group"] for e in kept_ev}), items=items, provenance=provenance,
                reference_check=dict(default_manifest=bool(default_refs), n_reference_hashes=len(refs), n_reference_sets=len(refsets),
                                     manifest_sha256=hashlib.sha256(Path(ref_manifest or DEFAULT_REFS).read_bytes()).hexdigest() if default_refs else None),
                note="photographer intent is metadata only; human labels decide; pixels not committed")


def assign_blind(res):
    """Blind ids by content hash order: team_eval Q###, team_train R###. Quarantined photos get no blind id."""
    out = {}
    for split, batch, pre in (("J-eval", "team_eval", "Q"), ("J-train", "team_train", "R")):
        ok = sorted((i for i in res["items"] if i["split"] == split and not i.get("quarantine")), key=lambda i: i["sha256"])
        for n, i in enumerate(ok, 1):
            i["blind_id"] = f"{pre}{n:03d}"; i["batch"] = batch; i["key"] = "tp_" + i["sha256"][:16]
        out[batch] = ok
    return out


def write_outputs(res, out_dir, packs=False, lab=None, stage_dir=None):
    """Writes (lead-only) manifest, provenance.csv, team_blind_key.csv and, with packs=True, the blind annotator zips."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    B = assign_blind(res)
    man = dict(res, items=[{k: v for k, v in i.items() if k != "path"} for i in res["items"]])
    (out / "team_phone_manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "team_phone_provenance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res["provenance"][0]) if res["provenance"] else ["sha256"]); w.writeheader(); w.writerows(res["provenance"])
    cols = ["blind_id", "batch", "key", "page_url", "split", "source", "uploader", "source_label", "source_kind", "stageI_item",
            "session_id", "sha256", "intended_by_photographer_NOT_A_LABEL", "condition_NOT_A_LABEL", "file"]
    with open(out / "team_blind_key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for batch, rows in B.items():
            for i in rows:
                w.writerow(dict(blind_id=i["blind_id"], batch=batch, key=i["key"], page_url="", split=i["split"], source=SOURCE,
                                uploader=i["photographer"], source_label="", source_kind="", stageI_item="", session_id=i["session_id"],
                                sha256=i["sha256"], intended_by_photographer_NOT_A_LABEL=i["intended_by_photographer"],
                                condition_NOT_A_LABEL=i["condition"], file=i["file"]))
    rec = {}
    if packs:
        import j2_pack
        stage = Path(stage_dir or out / "img"); stage.mkdir(parents=True, exist_ok=True)
        lab = lab or str(out / "packs")
        for batch, rows in B.items():
            if not rows: continue
            img_of = {}
            for i in rows:
                dst = stage / f"{i['key']}{Path(i['path']).suffix.lower()}"; shutil.copyfile(i["path"], dst); img_of[i["blind_id"]] = str(dst)
            title = {"team_eval": "Team phone photos (evaluation)", "team_train": "Team phone photos (training)"}[batch]
            rec[batch] = j2_pack.build_from(batch, [i["blind_id"] for i in rows], img_of, title, lab, transpose=True)
        (out / "team_packs.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return dict(blind={b: len(r) for b, r in B.items()}, packs=rec)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("root"); a.add_argument("--ref-hashes", help="EXTRA hash list (added to the default manifest)"); a.add_argument("--out")
    a.add_argument("--out-dir", help="write manifest, provenance, blind key (and packs) here"); a.add_argument("--packs", action="store_true")
    a.add_argument("--ref-manifest", help="alternative complete reference manifest (default out/j3_reference_hashes.json)")
    x = a.parse_args()
    refs = json.load(open(x.ref_hashes)) if x.ref_hashes else []
    res = ingest(x.root, refs.values() if isinstance(refs, dict) else refs, ref_manifest=x.ref_manifest)
    if x.out_dir:
        print(json.dumps(write_outputs(res, x.out_dir, packs=x.packs), indent=1))
    else:
        txt = json.dumps(dict(res, items=[{k: v for k, v in i.items() if k != "path"} for i in res["items"]]), indent=1, ensure_ascii=False)
        (open(x.out, "w", encoding="utf-8").write(txt) if x.out else print(txt))
    print(json.dumps(res["counts"]), file=sys.stderr)


if __name__ == "__main__":
    main()
