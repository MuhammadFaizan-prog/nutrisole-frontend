#!/usr/bin/env python3
"""G9 Stage J4: read-only integrity check of the J3 human handoff zips (never rebuilds them).

Checks, against ml/runs/G9/stageJ/out/handoff/j3_handoff_manifest.json:
  1. sha256 of every outer zip in the handoff folder == manifest
  2. member list of every outer zip == manifest
  3. sha256 + item count of every inner pack (annotator / training) == manifest
  4. AI-leak grep (recursive, names + bytes) over every annotator, training and team zip: must be clean.
     The adjudicator zip may only mention the AI marker in its instruction text (expected, it explains the post-hoc zip).
  5. the HANDOFF_MANIFEST.json copy in the handoff folder == repo manifest
Exit code 0 = PASS, 1 = FAIL. Writes nothing unless --out is given.

Usage (Linux):    python3 j4_verify_handoff.py --handoff <folder> [--out report.json]
Usage (Windows):  py j4_verify_handoff.py --handoff "$HOME\\Downloads\\handoff"
"""
import argparse, hashlib, io, json, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE.parent / "out/handoff/j3_handoff_manifest.json"
AI_MARKERS = [b"AI_ASSISTED_NOT_HUMAN", b"AI_ASSISTED", b"visual_review", b"review_queue", b"G9J_AI_", b"ai_review",
              b"j_blind_key", b"source_label", b"AI_visual", b"per_image_review", b"_v2_hark", b"model_pred", b"pred_label"]
ADJ_ALLOWED = {"ADJUDICATION_INSTRUCTIONS.md"}  # may explain the post-hoc AI zip in prose


def sha(b): return hashlib.sha256(b).hexdigest()


def scan(b, path=""):
    hits = []
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        for n in z.namelist():
            d = z.read(n)
            if n.endswith(".zip"):
                hits += scan(d, path + n + "/"); continue
            for m in AI_MARKERS:
                if m.lower() in n.lower().encode() or m in d:
                    hits.append(f"{path}{n}: {m.decode()}")
    return hits


def count_items(b):
    """Photos are embedded in the offline HTML tool; the fallback CSV has one row per photo (header excluded)."""
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        csvs = [n for n in z.namelist() if n.startswith("fallback/") and n.endswith(".csv")]
        if len(csvs) != 1: return -1
        rows = [l for l in z.read(csvs[0]).decode("utf-8-sig").splitlines()[1:] if l.strip()]
        return len(rows)


def verify(handoff: Path, manifest_path: Path = MANIFEST):
    man = json.loads(manifest_path.read_text())
    rep = dict(zips={}, inner_packs={}, ai_leak={}, manifest_copy=None, failures=[])
    for zn, z in man["zips"].items():
        p = handoff / zn
        if not p.exists():
            rep["failures"].append(f"missing {zn}"); continue
        b = p.read_bytes()
        ok_sha = sha(b) == z["sha256"]
        with zipfile.ZipFile(io.BytesIO(b)) as zf:
            names = zf.namelist()
            ok_mem = names == z["members"]
            for n in names:
                if n in man["inner_packs"]:
                    ib = zf.read(n); ip = man["inner_packs"][n]
                    ok_i = sha(ib) == ip["sha256"] == ip["recorded_sha256"]
                    items = count_items(ib)
                    rep["inner_packs"][n] = dict(sha_ok=ok_i, items=items, items_expected=ip["items"])
                    if not ok_i: rep["failures"].append(f"inner sha {n}")
                    if items != ip["items"]: rep["failures"].append(f"inner items {n}: {items} != {ip['items']}")
        rep["zips"][zn] = dict(sha_ok=ok_sha, members_ok=ok_mem)
        if not ok_sha: rep["failures"].append(f"zip sha {zn}")
        if not ok_mem: rep["failures"].append(f"zip members {zn}")
        if "AI_POSTHOC" in zn:
            continue
        hits = scan(b)
        if "ADJUDICATOR" in zn:
            bad = [h for h in hits if h.split(":")[0] not in ADJ_ALLOWED]
        else:
            bad = hits
        rep["ai_leak"][zn] = "clean" if not hits else ("instruction-text only (expected)" if not bad else bad)
        if bad: rep["failures"].append(f"AI leak {zn}: {bad[:3]}")
    missing_inner = set(man["inner_packs"]) - set(rep["inner_packs"])
    for n in sorted(missing_inner): rep["failures"].append(f"inner pack not found {n}")
    cp = handoff / "HANDOFF_MANIFEST.json"
    rep["manifest_copy"] = cp.exists() and json.loads(cp.read_text()) == man
    if not rep["manifest_copy"]: rep["failures"].append("HANDOFF_MANIFEST.json copy differs or missing")
    rep["result"] = "PASS" if not rep["failures"] else "FAIL"
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True)
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--out")
    a = ap.parse_args()
    r = verify(Path(a.handoff), Path(a.manifest))
    s = json.dumps(r, indent=1)
    if a.out: Path(a.out).write_text(s)
    print(s)
    sys.exit(0 if r["result"] == "PASS" else 1)
