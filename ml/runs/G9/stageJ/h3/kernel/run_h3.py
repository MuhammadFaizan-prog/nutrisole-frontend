# NutriSole G9 H3: targeted fine-tune of the existing H2 v2 close-up identity classifier (timm mobilenetv3_small_100, 13 outputs).
# Frozen plan: docs/cv/gauntlet/G9_stageJ3_H3_frozen_plan_v2.md (supersedes nothing; extends G9_stageI_finetune_prereg.md).
# Initialised from the EXISTING weights h2_mnv3s.pt (sha256 02b402a1...bd82). Head kept at 13 classes; no class dropped or merged.
# Training data = human-verified J-train only (+ capped legacy Kaggle pools); thresholds tuned on J-dev only; J-eval is never read here.
# Free Kaggle GPU only, one attempt + at most one infrastructure retry. state_dict (.pt) saved BEFORE ONNX export.
#   --dry-run : local CPU smoke test on a tiny synthetic set (seconds); tiny CNN stand-in when timm/weights are absent. No real data.
import argparse, csv, hashlib, json, os, random, sys, time

C = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum", "unknown"]
CI = {c: i for i, c in enumerate(C)}
PRIORITY = {"apple", "banana", "citrus", "tomato", "carrot"}
H2_SHA = "02b402a1302a437cab59c8ddecae1cfd117fbc4a511529cdb9e7be6a7b09bd82"
CFG = dict(epochs=12, batch=64, lr_head=3e-4, lr_backbone=1e-4, wd=0.05, priority_weight=2.0, legacy_draw_cap=0.30, img=224, seed=0,
           early_stop_patience=3, phash_max=10)


def synth(root, n_per_class=6, size=64):
    from PIL import Image
    import numpy as np
    rows = []; os.makedirs(root, exist_ok=True)
    rng = np.random.default_rng(0)
    for split in ("J-train", "J-dev"):
        for ci, c in enumerate(C):
            for k in range(n_per_class if split == "J-train" else 2):
                a = np.zeros((size, size, 3), np.uint8); a[...] = ((ci * 19) % 255, (ci * 53) % 255, (ci * 97) % 255)
                a = np.clip(a + rng.integers(0, 40, a.shape), 0, 255).astype(np.uint8)
                p = os.path.join(root, f"{split}_{c}_{k}.jpg"); Image.fromarray(a).save(p)
                rows.append(dict(path=p, class13=c, role="supported" if c != "unknown" else "unsupported", split=split, source="synthetic"))
    return rows


def tiny_model():
    import torch.nn as nn
    return nn.Sequential(nn.Conv2d(3, 8, 3, 2, 1), nn.ReLU(), nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(8, len(C)))


def build_model(weights, dry):
    import torch
    try:
        import timm
    except ImportError:
        timm = None
    if timm is None or not weights or not os.path.exists(weights):
        if not dry: raise SystemExit("real run needs timm and the existing H2 v2 weights")
        return tiny_model(), "tiny_cnn_dry_run"
    h = hashlib.sha256(open(weights, "rb").read()).hexdigest()
    if not dry and h != H2_SHA: raise SystemExit(f"initial weights are not the frozen H2 v2 .pt ({h[:12]})")
    m = timm.create_model("mobilenetv3_small_100", pretrained=False, num_classes=len(C))
    m.load_state_dict(torch.load(weights, map_location="cpu")); return m, f"mobilenetv3_small_100<-h2v2:{h[:12]}"


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("--dry-run", action="store_true"); a.add_argument("--manifest", help="CSV path,class13,role,split,source (J-train/J-dev only)")
    a.add_argument("--weights", default="/kaggle/input/nutrisole-h2v2/h2_mnv3s.pt"); a.add_argument("--eval-hashes", help="JSON list of J-eval/M-TEST pHashes")
    a.add_argument("--out", default="/kaggle/working"); a.add_argument("--max-steps", type=int, default=0)
    x = a.parse_args(argv)
    import numpy as np, torch, torch.nn as nn
    from PIL import Image
    t0 = time.time(); random.seed(CFG["seed"]); np.random.seed(CFG["seed"]); torch.manual_seed(CFG["seed"])
    os.makedirs(x.out, exist_ok=True); order = []
    if x.dry_run:
        rows = synth(os.path.join(x.out, "synthetic")); cfg = dict(CFG, epochs=1, batch=8, img=64)
    else:
        rows = list(csv.DictReader(open(x.manifest))); cfg = CFG
        if any(r["split"] not in ("J-train", "J-dev") for r in rows): raise SystemExit("manifest contains non-training splits (J-eval must never be read)")
    # in-kernel leakage drop: any training image within Hamming <= 10 of an eval/M-TEST hash is dropped
    dropped = 0
    if x.eval_hashes:
        import imagehash
        ev = np.array([int(h, 16) for h in json.load(open(x.eval_hashes))], dtype=np.uint64); keep = []
        for r in rows:
            h = np.uint64(int(str(imagehash.phash(Image.open(r["path"]).convert("RGB"))), 16))
            if len(ev) and int(np.bitwise_count(ev ^ h).min()) <= cfg["phash_max"]: dropped += 1; continue
            keep.append(r)
        rows = keep
    tr = [r for r in rows if r["split"] == "J-train"]; dv = [r for r in rows if r["split"] == "J-dev"]
    model, arch = build_model(x.weights, x.dry_run); dev = "cuda" if torch.cuda.is_available() and not x.dry_run else "cpu"; model.to(dev)
    import torchvision.transforms as T
    tf = T.Compose([T.Resize((cfg["img"], cfg["img"])), T.ToTensor(), T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))])
    w = np.array([cfg["priority_weight"] if r["class13"] in PRIORITY else 1.0 for r in tr]); cls = np.array([CI[r["class13"]] for r in tr])
    for c in set(cls): w[cls == c] /= (cls == c).sum()
    samp = torch.utils.data.WeightedRandomSampler(torch.tensor(w, dtype=torch.double), num_samples=len(tr), replacement=True)
    class DS(torch.utils.data.Dataset):
        def __init__(s, it): s.it = it
        def __len__(s): return len(s.it)
        def __getitem__(s, i): r = s.it[i]; return tf(Image.open(r["path"]).convert("RGB")), CI[r["class13"]]
    dl = torch.utils.data.DataLoader(DS(tr), batch_size=cfg["batch"], sampler=samp)
    is_head = lambda n: n.startswith(("classifier", "conv_head", "4."))          # timm mnv3 head / tiny-CNN linear
    groups = [dict(params=[p for n, p in model.named_parameters() if is_head(n)], lr=cfg["lr_head"]),
              dict(params=[p for n, p in model.named_parameters() if not is_head(n)], lr=cfg["lr_backbone"])]
    opt = torch.optim.AdamW([g for g in groups if g["params"]], weight_decay=cfg["wd"]); lossf = nn.CrossEntropyLoss()
    steps = 0; best = (-1, None); hist = []
    for ep in range(cfg["epochs"]):
        model.train()
        for xb, yb in dl:
            opt.zero_grad(); l = lossf(model(xb.to(dev)), yb.to(dev)); l.backward(); opt.step(); steps += 1
            if x.max_steps and steps >= x.max_steps: break
        model.eval()
        with torch.no_grad():
            pc = {}
            for r in dv:
                p = int(model(tf(Image.open(r["path"]).convert("RGB"))[None].to(dev)).argmax(1)); pc.setdefault(r["class13"], []).append(p == CI[r["class13"]])
        macro = float(np.mean([np.mean(v) for c, v in pc.items() if c in PRIORITY])) if pc else 0.0
        hist.append(dict(epoch=ep, dev_priority_macro_acc=round(macro, 4)))
        if macro > best[0]: best = (macro, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()})
        if len(hist) > cfg["early_stop_patience"] and all(h["dev_priority_macro_acc"] <= best[0] for h in hist[-cfg["early_stop_patience"]:]) and macro < best[0]: break
    model.load_state_dict(best[1])
    pt = os.path.join(x.out, "h3_mnv3s.pt"); torch.save(model.state_dict(), pt); order.append("pt_saved")      # .pt BEFORE export
    onnx_ok = False
    try:
        torch.onnx.export(model.cpu(), torch.zeros(1, 3, cfg["img"], cfg["img"]), os.path.join(x.out, "h3_mnv3s.onnx"), opset_version=17,
                          input_names=["input"], output_names=["logits"], dynamo=False); onnx_ok = True
    except Exception as e:
        hist.append(dict(onnx_error=str(e)[:200]))
    order.append("onnx_export_attempted")
    model.eval(); lat = []
    with torch.no_grad():
        z = torch.zeros(1, 3, cfg["img"], cfg["img"])
        for _ in range(20): s = time.perf_counter(); model(z); lat.append((time.perf_counter() - s) * 1000)
    rep = dict(mode="dry_run" if x.dry_run else "real", arch=arch, n_train=len(tr), n_dev=len(dv), dropped_near_eval=dropped, steps=steps,
               history=hist, best_dev_priority_macro_acc=round(best[0], 4), pt_sha256=hashlib.sha256(open(pt, "rb").read()).hexdigest(),
               onnx_exported=onnx_ok, artefact_order=order, model_cpu_latency_ms_p95=round(float(np.percentile(lat, 95)), 2), seconds=round(time.time() - t0, 1),
               config=cfg, grades="blocked (not produced by this kernel)", eval_split_read=False)
    json.dump(rep, open(os.path.join(x.out, "h3_report.json"), "w"), indent=1); print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    main()
