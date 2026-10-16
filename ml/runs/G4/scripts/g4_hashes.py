import hashlib, os, json, glob
R="/workspace/work/cv/g3data/det_v3"; B="/workspace/work/nutrisole/ml/data/builds/v3"; out={}
for sp in ["test","test_rf","neg_test","test_oiv7"]:
    files=[l.strip() for l in open(f"{R}/{sp}.txt") if l.strip()]
    lh=hashlib.sha256("\n".join(os.path.basename(f) for f in files).encode()).hexdigest()
    ref=open(f"{B}/det_{sp}_list_sha256.txt").read().strip()
    h=hashlib.sha256()
    for f in files:
        h.update(open(f,"rb").read()); lp=f.replace("/images/","/labels/")[:-4]+".txt"
        h.update(open(lp,"rb").read() if os.path.exists(lp) else b"")
    out[sp]=dict(n=len(files), list_sha256=lh, v3_reference=ref, list_identical=lh==ref, content_sha256=h.hexdigest())
clips={}
for d in ["/workspace/work/cv/g1clips","/workspace/work/cv/g2clips_negtest"]:
    for f in sorted(glob.glob(d+"/**/*",recursive=True)):
        if os.path.isfile(f) and f.endswith((".mp4",".json",".avi")): clips[f.replace("/workspace/work/cv/","")]=hashlib.sha256(open(f,"rb").read()).hexdigest()
out["clips_sha256"]=clips
prev="/workspace/work/nutrisole/ml/runs/G3/locked_hashes.json"
json.dump(out,open("/workspace/work/nutrisole/ml/runs/G4/locked_hashes.json","w"),indent=1)
print({k:(v["list_identical"],v["n"]) for k,v in out.items() if k!="clips_sha256"}, len(clips))
