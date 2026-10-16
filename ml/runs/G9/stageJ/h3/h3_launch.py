"""G9 H3 launcher. `--dry-run` runs the kernel locally on a tiny synthetic set (CPU, seconds) and never needs the guard.
A real launch runs h3_guard.py first and REFUSES (exit 2) unless the guard returns PASS (verified human manifests pass the frozen
gates AND the user's own USER_TRAINING_GO.json names this plan and those manifests). Even then this script only prepares the Kaggle
folder and prints the push command; one attempt plus at most one infrastructure retry, free GPU only.
Usage: h3_launch.py --dry-run [--out DIR] | h3_launch.py --prepare"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

H3 = Path(__file__).resolve().parent


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--dry-run", action="store_true"); a.add_argument("--prepare", action="store_true")
    a.add_argument("--out", default="/tmp/h3_dry"); a.add_argument("--inputs"); a.add_argument("--go")
    x = a.parse_args(argv)
    if x.dry_run:
        sys.path.insert(0, str(H3 / "kernel")); import run_h3
        return 0 if run_h3.main(["--dry-run", "--out", x.out])["mode"] == "dry_run" else 1
    sys.path.insert(0, str(H3)); import h3_guard
    args = (["--inputs", x.inputs] if x.inputs else []) + (["--go", x.go] if x.go else [])
    if h3_guard.main(args) != 0:
        print("H3 LAUNCH REFUSED: guard did not pass. No kernel prepared, nothing pushed.", file=sys.stderr); return 2
    if x.prepare:
        dst = H3 / "kaggle_push"; dst.mkdir(exist_ok=True)
        shutil.copyfile(H3 / "kernel/run_h3.py", dst / "run_h3.py")
        meta = json.loads((H3 / "kernel/kernel-metadata.TEMPLATE.json").read_text()); meta.pop("_note", None)
        (dst / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
        print(f"prepared {dst}; push with: kaggle kernels push -p {dst}  (one attempt + at most one infrastructure retry)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
