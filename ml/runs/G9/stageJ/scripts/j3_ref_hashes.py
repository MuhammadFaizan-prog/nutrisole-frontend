"""G9 Stage J3: build the COMPLETE earlier-reference pHash manifest used by j_team_phone.py (hashes only, no paths, no pixels).

Sets (each tagged role = train_source | earlier_eval | mixed; mixed is treated as train_source by the ingestion check):
  stored lists (never re-opened):
    g9e ref list   /workspace/work/cv/g9e/ref_hashes.json via g9h/refhash.json "g9e": G3 det_v3 train, G7 clip keyframes,
                   Stage D candidates/S, DEV val / DEV clips
    M-DEV+M-TEST   g9h/refhash.json "m" (= cv/g9f/m_hashes.json). M-TEST PIXELS ARE NEVER OPENED; /workspace/work/cv/g9e is skipped.
    D/E/F pools    g9h/refhash.json "pool";  CU (Stage G close-ups) "cu";  Stage H in-kernel list g9h/eval_hashes.json;
    Stage H set    g9h/hset/hhash.json with split from stageH/out/h_leak_split.json
    Stage J        out/j_partitions.json items (+split);  Stage J2 out/gaps/j2_candidates.json (+split)
  hashed here from local copies (64-bit imagehash.phash; JPEG draft decode to >= 256 px for speed, which can move a hash by a few
  bits, well inside the Hamming-10 tolerance):
    G1 cv/g1data, G2 cv/g2data, G3 cv/g3data, G4 cv/g4data, G5 cv/g5data, G7 cv/g7data, G0 cv/data, Stage D cv/g9d, Stage F cv/g9f,
    Stage I candidates g9i/cands/img (incl. items later dropped), Stage J train g9j/train/img, Stage J2 g9j2/eval2/img + train2/img.
  Role of a hashed file: earlier_eval if its path has a test/holdout/neg_test component, otherwise train_source (conservative).
Resumable: cache /workspace/work/g9j3/refhash_cache.json; each call hashes for at most --seconds then exits (rerun until done).
Output: out/j3_reference_hashes.json  {sets:{name:{role,count,hashes[]}}, all_unique, sha256 ...}. Usage: j3_ref_hashes.py [--seconds 100] [--build]"""
import argparse, glob, hashlib, json, os, re, sys, time
from multiprocessing import Pool
from pathlib import Path

W = "/workspace/work"; J = Path(__file__).resolve().parents[1]; CACHE = f"{W}/g9j3/refhash_cache.json"; OUT = J / "out/j3_reference_hashes.json"
DIRS = {"G0_cv_data": f"{W}/cv/data", "G1_data": f"{W}/cv/g1data", "G2_data": f"{W}/cv/g2data", "G3_data": f"{W}/cv/g3data",
        "G4_data": f"{W}/cv/g4data", "G5_data": f"{W}/cv/g5data", "G6_data": f"{W}/cv/g6data", "G7_data": f"{W}/cv/g7data", "G9_stageD_pool": f"{W}/cv/g9d",
        "G9_stageF_pool": f"{W}/cv/g9f", "G9_stageI_candidates": f"{W}/g9i/cands/img", "G9_stageJ_train_img": f"{W}/g9j/train/img",
        "G9_stageJ2_eval2_img": f"{W}/g9j2/eval2/img", "G9_stageJ2_train2_img": f"{W}/g9j2/train2/img"}
FORBIDDEN = (f"{W}/cv/g9e/",)            # M-TEST / Stage E market pixels: hashes only, from the stored list
EVALISH = re.compile(r"/(test|tests|holdout|neg_test|m_test|mtest)(/|_|$)", re.I)
EXT = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG", ".webp")
ROLE_OVERRIDE = {"G9_stageI_candidates": "mixed", "G9_stageJ2_eval2_img": "earlier_eval", "G9_stageJ_train_img": "train_source",
                 "G9_stageJ2_train2_img": "train_source"}   # Stage I candidates feed J-eval, J-dev and J-train
BLANK = {"0000000000000000", "8000000000000000", "ffffffffffffffff"}


def ph(p):
    try:
        import imagehash
        from PIL import Image
        im = Image.open(p)
        if im.format == "JPEG": im.draft("RGB", (256, 256))
        return p, str(imagehash.phash(im.convert("RGB")))
    except Exception:
        return p, None


def files():
    out = []
    for name, d in DIRS.items():
        for p in sorted(glob.glob(f"{d}/**/*", recursive=True)):
            if p.endswith(EXT) and not p.startswith(FORBIDDEN) and "contact_sheet" not in p and "/sheets/" not in p: out.append((name, p))
    return out


def hash_step(seconds):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    c = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    todo = [p for _, p in files() if p not in c]; t0 = time.time(); n = 0
    with Pool(12) as pool:   # I/O-bound (network disk): many workers, little CPU
        for p, h in pool.imap_unordered(ph, todo, chunksize=32):
            c[p] = h; n += 1
            if time.time() - t0 > seconds: break
    json.dump(c, open(CACHE, "w"))
    left = len(todo) - n
    print(f"hashed {n} this call, cached {len(c)}, left {left}")
    return left


def stored():
    S = {}
    rh = json.load(open(f"{W}/g9h/refhash.json"))
    role_g9e = {"det_v3_train(G3 train)": "train_source", "g7_clip_keyframe": "mixed", "stageD_candidate_or_S": "train_source",
                "dev_val": "earlier_eval", "dev_neg_clip": "earlier_eval", "dev_det_clip": "earlier_eval", "dev_quality_clip": "earlier_eval"}
    for n, h in rh["g9e"]:
        k = n.split(":")[0]; S.setdefault(f"G3G7D_{re.sub(r'[^A-Za-z0-9]+', '_', k).strip('_')}", (role_g9e.get(k, "mixed"), set()))[1].add(h)
    S["G9_MDEV_MTEST_stored_hashes"] = ("earlier_eval", {h for _, h in rh["m"]})
    S["G9_DEF_commons_pools_stored"] = ("mixed", set(rh["pool"].values()))
    S["G9_stageG_CU_stored"] = ("earlier_eval", set(rh["cu"].values()))
    S["G9_stageH_inkernel_list"] = ("mixed", set(json.load(open(f"{W}/g9h/eval_hashes.json"))))
    hh = json.load(open(f"{W}/g9h/hset/hhash.json")); hs = json.load(open(J.parents[0] / "stageH/out/h_leak_split.json"))["split"]
    for k, h in hh.items():
        sp = hs.get(k, "dropped"); S.setdefault(f"G9_stageH_set_{sp}", ("earlier_eval" if sp in ("eval", "val") else "train_source" if sp == "train" else "mixed", set()))[1].add(h)
    for k, v in json.load(open(J / "out/j_partitions.json"))["items"].items():
        sp = v["split"]; S.setdefault(f"G9_stageJ_{sp}", ("train_source" if sp == "J-train" else "earlier_eval", set()))[1].add(v["phash"])
    for k, v in json.load(open(J / "out/gaps/j2_candidates.json")).items():
        sp = v["split"]; S.setdefault(f"G9_stageJ2_{sp}", ("train_source" if sp == "J-train" else "earlier_eval", set()))[1].add(v["phash"])
    return S


def build():
    c = json.load(open(CACHE)); S = stored(); missing = 0
    for name, p in files():
        h = c.get(p, "MISSING")
        if h == "MISSING": missing += 1; continue
        if not h: continue
        role = ROLE_OVERRIDE.get(name) or ("earlier_eval" if EVALISH.search(p) else "train_source")
        S.setdefault(f"{name}__{role}", (role, set()))[1].add(h)
    if missing: raise SystemExit(f"{missing} files not hashed yet; rerun without --build")
    sets = {k: dict(role=r, count=len(hs - BLANK), hashes=sorted(hs - BLANK)) for k, (r, hs) in sorted(S.items())}
    allh = sorted({h for v in sets.values() for h in v["hashes"]})
    body = dict(note="Earlier-reference pHash manifest (64-bit imagehash.phash hex). Hashes only: no file names, paths or pixels. M-TEST is "
                     "represented by its stored hashes only; its pixels were never opened. Roles: train_source / earlier_eval / mixed (mixed is "
                     "treated as a training source).", built_at="2026-10-15 PKT",
                hamming_rule=10, blank_hashes_excluded=sorted(BLANK), n_sets=len(sets), n_unique=len(allh),
                counts={k: (v["role"], v["count"]) for k, v in sets.items()}, m_test_pixels_opened=False, sets=sets)
    txt = json.dumps(body, separators=(",", ":"))
    OUT.write_text(txt); Path(str(OUT) + ".sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + f"  {OUT.name}\n")
    print(json.dumps(dict(n_sets=len(sets), n_unique=len(allh), mb=round(len(txt) / 1e6, 2)), indent=1))
    for k, v in sets.items(): print(f"{v['role']:13s} {v['count']:7d} {k}")


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--seconds", type=float, default=100); a.add_argument("--build", action="store_true"); x = a.parse_args()
    build() if x.build else hash_step(x.seconds)
