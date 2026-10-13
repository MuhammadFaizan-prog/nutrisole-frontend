import csv, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "/workspace/work/nutrisole/ml/runs/G9/fp"; R = list(csv.DictReader(open(f"{O}/dev_threshold_curves.csv")))
thr = json.load(open(f"{O}/thresholds_A1.json"))["thresholds"]
cls = [c for c in thr if c != "guava"]
fig, ax = plt.subplots(3, 4, figsize=(16, 10.5))
for a, c in zip(ax.flat, cls + ["guava"]):
    S = [r for r in R if r["cls"] == c]; t = [float(r["t"]) for r in S]
    f = lambda k: [float(r[k]) if r[k] not in ("", "None") else float("nan") for r in S]
    a.plot(t, f("P"), label="precision"); a.plot(t, f("R"), label="recall"); a.plot(t, f("F1"), label="F1")
    a2 = a.twinx(); a2.bar(t, [int(r["fp"]) for r in S], width=0.03, alpha=0.25, color="grey"); a2.set_ylabel("val FP boxes", fontsize=8)
    a.axvline(thr[c], color="red", ls="--"); a.set_ylim(0, 1.02)
    a.set_title(f"{c} (n={S[0]['n']}) t={thr[c]}", fontsize=10); a.set_xlabel("score threshold", fontsize=8)
ax.flat[0].legend(fontsize=8, loc="lower left")
fig.suptitle("G9 Stage A DEV: G3 per-class P/R/F1 vs threshold on val stills (n=402); red = frozen A1 threshold (R drop <= 5 pp)", fontsize=12)
fig.tight_layout(); fig.savefig(f"{O}/dev_threshold_curves.png", dpi=80); print("ok")
