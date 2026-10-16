"""Assemble M-DEV v2 edit file from the agent decisions (v2_ops.py): v1 crowd decisions + new-image labels + global duplicate check.
Usage: make_edits_v2.py OPS.py OUT_EDITS.json"""
import json, sys
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageF/scripts"); import build_labels_v2 as B
D = {}; FLAGS = {}; NEW = {}
def add(I, *ops): D.setdefault(I, {"ops": []})["ops"].extend(ops)
REVERT = set()
exec(open(sys.argv[1]).read())
for I, k in REVERT:
    D[I]["ops"] = [o for o in D[I]["ops"] if not (o[0] in ("conv", "convpx", "recrowd", "ignpx", "crowdpx", "delsmallpx") and o[1] == k)] + [["keep", k, "proposal-based conversion rejected at zoom QA (OWLv2 boxes misaligned/fragmented in the pile); crowd kept"]]
rows = json.load(open("/workspace/work/cv/g9f/crowd_stats.json")); done = {(I, o[1]) for I, v in D.items() for o in v["ops"] if o[0] in ("conv", "convpx", "keep")}
for I, k, c, n, med in rows:
    if (I, k) not in done and med < 20: add(I, ["keep", k, f"items ~{med} px median at native 1280-px resolution; not separable"])
for I, v in B.V1.items():
    for k, c in enumerate(v.get("crowd", [])):
        if c[4] < 0 and (I, k) not in done: add(I, ["keep", k, "ignore region kept (class not verifiable / non-target mix)"])
for I in B.V1: add(I, ["dupx", 0.7])
E = {I: dict(ops=v["ops"]) for I, v in D.items()}
for I, v in NEW.items():
    E[I] = dict(new=True, note=v[0], ops=([] if v[1] and v[1][0] == ["del", 0, 0, 1, 1] else [["del", 0, 0, 1, 1]]) + v[1])
json.dump(dict(edits=E, flags=FLAGS, reverted=sorted(map(list, REVERT))), open(sys.argv[2], "w"), indent=0)
unres = [(I, k) for I, k, c, n, med in rows if (I, k) not in {(I, o[1]) for I, v in D.items() for o in v["ops"] if o[0] in ("conv", "convpx", "keep")}]
print("edits", len(E), "new", len(NEW), "unresolved crowd regions", unres)
