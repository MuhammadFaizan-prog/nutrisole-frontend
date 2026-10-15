"""G9 Stage J: ingestion STUB for FYP-team phone photos (source "team_phone"). No training, no labels decided here.

Spec: docs/cv/gauntlet/G9_stageJ_team_photo_shotlist.md.
Input : a folder of session sub-folders plus sessions.csv
          sessions.csv columns: session_id,photographer,date,place,purpose,licence,consent_confirmed
          purpose  = eval  (bagged/packaged + partly hidden; J-eval only)  |  train  (apple training; J-train only)
          licence  = CC-BY-4.0 | internal-FYP
        file names  TP_<session_id>_<intended>_<condition>_<nnn>.jpg   e.g. TP_S20261018-AB-01_banana_bag-mesh_003.jpg
Rules (frozen with the shot list):
  * the split is decided by the SESSION, never per photo; a session is all-train or all-eval;
  * a photographer may appear in eval sessions OR train sessions, never both (source separation, like the Commons uploader rule);
  * 64-bit pHash: any train photo within Hamming <= 10 of any eval photo or of a reference hash (earlier J sets, M-TEST hashes)
    is QUARANTINED; eval photos are never dropped by this check. Eval photos within Hamming <= 6 of each other share a group
    (burst shots) so one group counts once;
  * `intended` / `condition` in the name are photographer metadata only. Every team_phone photo still goes through the two independent
    human annotators; nothing here makes an item human-verified;
  * photos carrying EXIF GPS are refused (location must be off);
  * pixels are not committed to git; only the manifest (ids, sha256, pHash, split, quarantine reason) is.
Usage: python3 j_team_phone.py ROOT [--ref-hashes refs.json] [--out manifest.json]
"""
import argparse, csv, hashlib, json, re, sys
from pathlib import Path

SOURCE = "team_phone"
INTENDED = {"apple", "banana", "citrus_orange", "tomato", "carrot", "none"}
CONDITIONS = {"bag-clear", "bag-mesh", "tray-film", "hid-hand", "hid-fruit", "hid-edge", "hid-object", "open"}
EVAL_CONDITIONS = CONDITIONS - {"open"}
LICENCES = {"CC-BY-4.0", "internal-FYP"}
NAME = re.compile(r"^TP_(S\d{8}-[A-Z]{2,3}-\d{2})_([a-z_]+?)_([a-z]+-[a-z]+|open)_(\d{3})\.(jpe?g|png)$", re.I)
SESSION = re.compile(r"^S\d{8}-[A-Z]{2,3}-\d{2}$")
CROSS, GROUP = 10, 6
COLUMNS = ["session_id", "photographer", "date", "place", "purpose", "licence", "consent_confirmed"]   # shot list section 8


def phash(path):
    import imagehash
    from PIL import Image
    return str(imagehash.phash(Image.open(path).convert("RGB")))


def has_gps(path):
    from PIL import Image
    try: return bool(Image.open(path).getexif().get(34853))
    except Exception: return False


def ham(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


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


def ingest(root, ref_hashes=()):
    root = Path(root)
    S = load_sessions(root / "sessions.csv")
    items, errors = [], []
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name != "sessions.csv" and not x.name.startswith(".")):
        m = NAME.match(p.name)
        if not m: errors.append(f"bad file name: {p.name}"); continue
        sid, intended, cond = m.group(1), m.group(2).lower(), m.group(3).lower()
        if sid not in S: errors.append(f"{p.name}: session {sid} not in sessions.csv"); continue
        if intended not in INTENDED or cond not in CONDITIONS: errors.append(f"{p.name}: unknown class/condition"); continue
        split = "J-eval" if S[sid]["purpose"] == "eval" else "J-train"
        if split == "J-eval" and cond not in EVAL_CONDITIONS: errors.append(f"{p.name}: eval session photo must be bagged or partly hidden"); continue
        if split == "J-train" and intended != "apple": errors.append(f"{p.name}: train sessions this round are apple-only"); continue
        if has_gps(p): errors.append(f"{p.name}: EXIF GPS present (turn location off / strip before hand-over)"); continue
        b = p.read_bytes()
        items.append(dict(file=p.name, source=SOURCE, session_id=sid, photographer=S[sid]["photographer"], split=split,
                          intended_by_photographer=intended, condition=cond, licence=S[sid]["licence"],
                          sha256=hashlib.sha256(b).hexdigest(), phash=phash(p), human_verified=False))
    if errors: raise ValueError("; ".join(errors[:20]))
    ev = [i for i in items if i["split"] == "J-eval"]
    refs = list(ref_hashes)
    for i in items:
        if i["split"] != "J-train": continue
        d_eval = min((ham(i["phash"], e["phash"]), e["file"]) for e in ev) if ev else (99, None)
        d_ref = min(ham(i["phash"], h) for h in refs) if refs else 99
        if d_eval[0] <= CROSS: i["quarantine"] = f"near-dup (Hamming {d_eval[0]}) of eval photo {d_eval[1]}"
        elif d_ref <= CROSS: i["quarantine"] = f"near-dup (Hamming {d_ref}) of a reference set"
    for k, e in enumerate(ev):                                   # burst grouping inside eval (one group counts once)
        e["group"] = next((o["group"] for o in ev[:k] if ham(e["phash"], o["phash"]) <= GROUP), e["file"])
    counts = {}
    for i in items:
        key = f"{i['split']}{'/quarantined' if i.get('quarantine') else ''}"
        counts[key] = counts.get(key, 0) + 1
    return dict(source=SOURCE, sessions=len(S), counts=counts, eval_groups=len({e["group"] for e in ev}), items=items,
                note="photographer intent is metadata only; human labels decide; pixels not committed")


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("root"); a.add_argument("--ref-hashes"); a.add_argument("--out")
    x = a.parse_args()
    refs = json.load(open(x.ref_hashes)) if x.ref_hashes else []
    res = ingest(x.root, refs.values() if isinstance(refs, dict) else refs)
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    (open(x.out, "w", encoding="utf-8").write(txt) if x.out else print(txt))
    print(json.dumps(res["counts"]), file=sys.stderr)


if __name__ == "__main__":
    main()
