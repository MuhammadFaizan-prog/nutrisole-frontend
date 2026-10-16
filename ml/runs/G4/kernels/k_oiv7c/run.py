# G4: Open Images V7 citrus subset (Lemon (plant) -> lemon_lime, Orange (fruit)/Grapefruit -> citrus). CPU kernel.
# G3 matched names exactly and "Lemon"/"Orange" did not resolve (OIV7 names are "Lemon (plant)", "Orange (fruit)").
# Annotations CC BY 4.0; images CC BY 2.0 per image (licence rows kept). All target-class boxes kept per image.
import pandas as pd, os, json, requests, io, concurrent.futures as cf
from PIL import Image
B="https://storage.googleapis.com/openimages/"
W="/kaggle/working/oiv7c"; os.makedirs(W+"/images",exist_ok=True); os.makedirs(W+"/labels",exist_ok=True)
NAMES=["banana","apple","mango","citrus","guava","pomegranate","lemon_lime","tomato","potato","cucumber","carrot","capsicum"]
mids={"/m/09k_b":"lemon_lime","/m/0cyhj_":"citrus","/m/0hqkz":"citrus","/m/0fldg":"mango","/m/0jwn_":"pomegranate","/m/0jg57":"capsicum",
      "/m/015x4r":"cucumber","/m/05vtc":"potato","/m/07j87":"tomato","/m/09qck":"banana","/m/014j1m":"apple","/m/0fj52s":"carrot"}
cd=pd.read_csv(B+"v7/oidv7-class-descriptions-boxable.csv",header=None,names=["mid","name"]); print(cd[cd.mid.isin(["/m/09k_b","/m/0cyhj_"])].to_dict("records"))
urls={"train":B+"v6/oidv6-train-annotations-bbox.csv","validation":B+"v5/validation-annotations-bbox.csv","test":B+"v5/test-annotations-bbox.csv"}
meta={"train":B+"2018_04/train/train-images-boxable-with-rotation.csv","validation":B+"2018_04/validation/validation-images-with-rotation.csv","test":B+"2018_04/test/test-images-with-rotation.csv"}
rows=[]
for sp,u in urls.items():
    for ch in pd.read_csv(u,chunksize=2_000_000,usecols=["ImageID","LabelName","XMin","XMax","YMin","YMax","IsGroupOf","IsDepiction"]):
        ch=ch[ch.LabelName.isin(mids)].copy(); ch["split"]=sp; rows.append(ch)
df=pd.concat(rows); df["cls"]=df.LabelName.map(mids); df=df[df.IsDepiction!=1]
cap={"/m/09k_b":1500,"/m/0cyhj_":700}  # lemon: all we can; orange: modest (citrus already 1543 train boxes)
keep=set()
for m,n in cap.items():
    ids=df[df.LabelName==m].ImageID.drop_duplicates(); keep|=set(ids.sample(min(n,len(ids)),random_state=0))
d=df[df.ImageID.isin(keep)]
stats=dict(images_per_cls=d.groupby("cls").ImageID.nunique().to_dict(),boxes_per_cls=d.cls.value_counts().to_dict(),
           images_per_split=d.groupby("split").ImageID.nunique().to_dict(),lemon_boxes_per_split=d[d.LabelName=="/m/09k_b"].groupby("split").size().to_dict())
print(stats,flush=True)
m=pd.concat([pd.read_csv(meta[s],usecols=["ImageID","License","Author","OriginalURL"]) for s in meta]); m[m.ImageID.isin(keep)].to_csv(f"{W}/image_licences.csv",index=False)
sp_of=d.groupby("ImageID").split.first().to_dict()
def fetch(i):
    p=f"{W}/images/{i}.jpg"
    try:
        r=requests.get(f"https://open-images-dataset.s3.amazonaws.com/{sp_of[i]}/{i}.jpg",timeout=30); r.raise_for_status()
        im=Image.open(io.BytesIO(r.content)).convert("RGB"); im.thumbnail((1024,1024)); im.save(p,quality=90); return True
    except Exception: return False
with cf.ThreadPoolExecutor(32) as ex: ok=dict(zip(list(keep),ex.map(fetch,list(keep))))
for i,g in d.groupby("ImageID"):
    if not ok.get(i): continue
    with open(f"{W}/labels/{i}.txt","w") as f:
        for r in g.itertuples(): f.write(f"{NAMES.index(r.cls)} {(r.XMin+r.XMax)/2:.6f} {(r.YMin+r.YMax)/2:.6f} {r.XMax-r.XMin:.6f} {r.YMax-r.YMin:.6f}\n")
d[["ImageID","split","cls","IsGroupOf"]].to_csv(f"{W}/boxes_index.csv",index=False)
stats["downloaded"]=sum(ok.values()); stats["failed"]=len(ok)-stats["downloaded"]
json.dump(stats,open(f"{W}/stats.json","w"),indent=1); print(stats)
os.system("cd /kaggle/working && tar czf oiv7c.tgz oiv7c && rm -rf oiv7c/images")
