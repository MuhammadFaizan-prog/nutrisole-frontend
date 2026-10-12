"""Seeded, resumable Ultralytics training with run metadata (rule 8.16).

  python ml/train/train.py det  --model yolo26n.pt --name det_yolo26n --epochs 12 --imgsz 320
  python ml/train/train.py cls  --model yolo26n-cls.pt --data <dir> --name cls_q2 --epochs 15 --imgsz 192
Re-running the same command resumes from <project>/<name>/weights/last.pt if it exists.
Writes <project>/<name>/run_meta.json (git commit + dirty flag, data manifest sha256,
package versions, hardware, wall time).
"""
import argparse, hashlib, json, os, platform, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def git_state():
    try:
        c = subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()
        d = bool(subprocess.check_output(["git", "-C", REPO, "status", "--porcelain"], text=True).strip())
        return c, d
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["det", "cls"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", default=os.path.join(REPO, "ml/configs/det_v1.yaml"))
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--name", required=True)
    ap.add_argument("--project", default=os.path.join(REPO, "ml/runs/G1"))
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--fraction", type=float, default=1.0)
    ap.add_argument("--no-val", action="store_true", help="skip per-epoch validation (final weights = last.pt; avoids selecting on val)")
    a = ap.parse_args()
    import torch, ultralytics
    from ultralytics import YOLO
    torch.set_num_threads(os.cpu_count() or 2)
    run_dir = os.path.join(a.project, a.name)
    last = os.path.join(run_dir, "weights", "last.pt")
    t0 = time.time()
    common = dict(device="cpu", workers=2, seed=0, deterministic=True, plots=True, verbose=False)
    if a.no_val:
        common["val"] = False
    if os.path.exists(last):
        print("resuming", last, flush=True)
        YOLO(last).train(resume=True, **common)
    else:
        m = YOLO(a.model)
        if a.task == "det":
            # phone-camera-ish augmentation within what Ultralytics exposes; the rest
            # (WB shift, blur, JPEG) is evaluated in the robustness sweep (G1) and added
            # as custom augmentation in G2.
            m.train(data=a.data, imgsz=a.imgsz, epochs=a.epochs, batch=a.batch, project=a.project, name=a.name, exist_ok=True,
                    cos_lr=True, close_mosaic=max(1, a.epochs // 4), hsv_h=0.015, hsv_s=0.6, hsv_v=0.5, degrees=10, fliplr=0.5,
                    mixup=0.0, cache="ram", save_period=1, patience=100, fraction=a.fraction, **common)
        else:
            m.train(data=a.data, imgsz=a.imgsz, epochs=a.epochs, batch=a.batch, project=a.project, name=a.name, exist_ok=True,
                    hsv_v=0.5, erasing=0.2, cos_lr=True, cache="ram", save_period=1, patience=100, **common)
    man = a.manifest
    meta = dict(task=a.task, no_val=a.no_val, model=a.model, data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, fraction=a.fraction, seed=0,
                manifest=man, manifest_sha256=hashlib.sha256(open(man, "rb").read()).hexdigest() if man and os.path.exists(man) else None,
                git=dict(zip(["commit", "dirty"], git_state())), versions=dict(ultralytics=ultralytics.__version__, torch=torch.__version__, python=sys.version.split()[0]),
                hardware=dict(device="cpu", cores=os.cpu_count(), machine=platform.machine(), gpu=None), wall_seconds_this_invocation=round(time.time() - t0, 1),
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    prev = os.path.join(run_dir, "run_meta.json")
    if os.path.exists(prev):
        old = json.load(open(prev))
        meta["wall_seconds_total"] = round(old.get("wall_seconds_total", old.get("wall_seconds_this_invocation", 0)) + meta["wall_seconds_this_invocation"], 1)
    else:
        meta["wall_seconds_total"] = meta["wall_seconds_this_invocation"]
    json.dump(meta, open(prev, "w"), indent=1)
    print("DONE", run_dir, flush=True)


if __name__ == "__main__":
    main()
