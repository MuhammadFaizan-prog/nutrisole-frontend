"""I2 EXPLORATORY run of the unchanged Stage H stack on the Stage I candidates (group representatives; labels = SOURCE METADATA, not
human labels; no accuracy claim). Per item: wide G3 at the centre tap (id_policy), Stage H close-up crop (h_ident.native_crop, exact),
H2 on that crop and on the whole image, P-a with FROZEN_VERIFY. Images are the <=640 px candidate copies. Resumable -> out/i_explore.jsonl."""
import json, os, sys, time, cv2
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageG/scripts"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageH/scripts"); sys.path.insert(0, os.path.dirname(__file__))
from h_ident import native_crop
from i_audit import stageh_tensor, onx
O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; D = "/workspace/work/g9i/cands"; OUT = f"{O}/i_explore.jsonl"
L = json.load(open(f"{O}/i_leak_split.json"))["items"]; lim = float(sys.argv[1]); t0 = time.time()
have = {json.loads(l)["key"] for l in open(OUT)} if os.path.exists(OUT) else set()
with open(OUT, "a") as f:
    for k, v in L.items():
        if v["group_rep"] != k or k in have: continue
        if time.time() - t0 > lim: break
        im = cv2.imread(f"{D}/img/{k}.jpg"); crop, wide, src, side = native_crop(im, [0.5, 0.5])
        f.write(json.dumps(dict(key=k, split=v["split"], source=v["source"], group=v["group"], truth=v["label"], roi=src, side=side, wide=wide,
                                h2_crop=[round(float(x), 5) for x in onx(stageh_tensor(crop))], h2_full=[round(float(x), 5) for x in onx(stageh_tensor(im))])) + "\n"); have.add(k)
print(len(have), "done", round(time.time() - t0), "s")
