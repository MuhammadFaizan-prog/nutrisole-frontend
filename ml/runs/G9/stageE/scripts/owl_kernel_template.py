# NutriSole CV G9 Stage E: OWLv2 (non-G3, open-vocab, Apache-2.0) box PROPOSALS for M-DEV images. Proposals only, never ground truth:
# every box is corrected manually afterwards (prereg G9_stageE_prereg.md section 4). Images fetched from Wikimedia Commons by URL.
# Passes: whole image + 3x3 overlapping tiles (tile = 1/2 of each side, stride 1/4) so small items are seen larger; merged by class-agnostic
# NMS 0.5 keeping the best-scoring prompt.
import os, sys, json, time, subprocess, urllib.request, io
t0 = time.time()
LIST = __LIST__
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers>=4.44"], check=False)
import torch, torchvision
from transformers import Owlv2Processor, Owlv2ForObjectDetection
from PIL import Image
dev = "cuda" if torch.cuda.is_available() else "cpu"
M = "google/owlv2-base-patch16-ensemble"; proc = Owlv2Processor.from_pretrained(M); model = Owlv2ForObjectDetection.from_pretrained(M).to(dev).eval()
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
PROMPTS = {"banana": ["a bunch of bananas", "a banana"], "apple": ["an apple"], "mango": ["a mango"], "citrus": ["an orange", "a mandarin orange"],
           "guava": ["a guava"], "pomegranate": ["a pomegranate"], "lemon_lime": ["a lemon", "a lime"], "tomato": ["a tomato"], "potato": ["a potato"],
           "cucumber": ["a cucumber"], "carrot": ["a carrot"], "capsicum": ["a bell pepper"]}
OTHER = ["an onion", "a chili pepper", "an eggplant", "a cabbage", "a melon", "a gourd", "a printed picture of fruit", "a bag", "a person"]
texts = [p for c in NAMES for p in PROMPTS[c]] + OTHER; owner = [NAMES.index(c) for c in NAMES for p in PROMPTS[c]] + [-1] * len(OTHER)
pp = getattr(proc, "post_process_object_detection", None) or proc.image_processor.post_process_object_detection
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
def run(im):
    W, H = im.size; S = max(W, H)
    with torch.no_grad():
        o = model(**proc(text=[texts], images=im, return_tensors="pt").to(dev))
        r = pp(outputs=o, threshold=0.10, target_sizes=torch.tensor([[S, S]], device=dev))[0]
    return [(b, s, l) for b, s, l in zip(r["boxes"].tolist(), r["scores"].tolist(), r["labels"].tolist())]
out = {}; OUT = "/kaggle/working/owl_props.json"
for i, (f, url) in enumerate(LIST):
    try:
        im = None
        for k in range(3):
            try: im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())).convert("RGB"); break
            except Exception as e: time.sleep(3 + 5 * k); err = e
        if im is None: out[f] = dict(error=repr(err)); continue
        W, H = im.size; boxes, scores, labels = [], [], []
        for b, s, l in run(im): boxes.append(b); scores.append(s); labels.append(l)
        tw, th = W // 2, H // 2
        for ty in range(3):
            for tx in range(3):
                x0, y0 = tx * W // 4, ty * H // 4; crop = im.crop((x0, y0, x0 + tw, y0 + th))
                for b, s, l in run(crop):
                    bb = [b[0] + x0, b[1] + y0, b[2] + x0, b[3] + y0]
                    if (b[2] - b[0]) > 0.9 * tw or (b[3] - b[1]) > 0.9 * th: continue
                    boxes.append(bb); scores.append(s); labels.append(l)
        if boxes:
            B = torch.tensor(boxes).clamp(min=0); B[:, 2] = B[:, 2].clamp(max=W); B[:, 3] = B[:, 3].clamp(max=H); Sc = torch.tensor(scores)
            keep = torchvision.ops.nms(B, Sc, 0.5).tolist()
        else: keep = []
        out[f] = dict(w=W, h=H, dets=[dict(box=[round(B[k][0].item() / W, 5), round(B[k][1].item() / H, 5), round(B[k][2].item() / W, 5), round(B[k][3].item() / H, 5)],
                                          cls=owner[labels[k]], prompt=texts[labels[k]], score=round(scores[k], 4)) for k in keep])
    except Exception as e: out[f] = dict(error=repr(e))
    if i % 10 == 0 or i == len(LIST) - 1:
        json.dump(dict(model=M, licence="Apache-2.0", device=dev, threshold=0.10, prompts=PROMPTS, other=OTHER, n_done=i + 1, n=len(LIST), images=out), open(OUT, "w"))
        print(i + 1, "/", len(LIST), round(time.time() - t0), flush=True)
print("DONE", round(time.time() - t0), flush=True)
