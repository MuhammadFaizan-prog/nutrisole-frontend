import sys,os,json,collections,cv2,numpy as np,onnxruntime as ort
sys.path.insert(0,'ml/eval'); from geometry import letterbox,dst_to_src,decode
N=["banana","apple","mango","citrus","guava","pomegranate","lemon_lime","tomato","potato","cucumber","carrot","capsicum"]
s=ort.InferenceSession('/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx',providers=['CPUExecutionProvider']);inp=s.get_inputs()[0].name
def iou(a,b):
    x1,y1=max(a[0],b[0]),max(a[1],b[1]);x2,y2=min(a[2],b[2]),min(a[3],b[3]);i=max(0,x2-x1)*max(0,y2-y1)
    return i/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-i+1e-9)
conf=collections.Counter(); crops=[]; per_img=[]
for p in open('/workspace/work/cv/g3data/det_v3/test_rf.txt').read().split():
    lp=p.replace('/images/','/labels/').rsplit('.',1)[0]+'.txt'
    rows=[list(map(float,r.split())) for r in open(lp) if r.strip()] if os.path.exists(lp) else []
    caps=[r for r in rows if int(r[0])==11]
    if not caps: continue
    im=cv2.imread(p);H,W=im.shape[:2]
    x,tf=letterbox(im,480);out=s.run(None,{inp:x})[0]
    preds=[(dst_to_src(d['box'],tf),d['classId'],d['score']) for d in decode(out,'raw',0.25)]
    for r in caps:
        c,cx,cy,w,h=r;g=[(cx-w/2)*W,(cy-h/2)*H,(cx+w/2)*W,(cy+h/2)*H]
        best=max(preds,key=lambda q:iou(q[0],g),default=None)
        lab='miss' if best is None or iou(best[0],g)<0.5 else N[best[1]]
        conf[lab]+=1
        cr=im[int(max(0,g[1])):int(g[3]),int(max(0,g[0])):int(g[2])]
        if cr.size and len(crops)<48:
            cr=cv2.resize(cr,(128,128));cv2.putText(cr,lab[:9],(2,12),0,0.4,(0,255,255),1);crops.append(cr)
    per_img.append(dict(img=os.path.basename(p),n_caps=len(caps),n_boxes=len(rows),box_wh=[round(r[3]*r[4],4) for r in caps][:5]))
rowsimg=[np.hstack(crops[i:i+8]+[np.zeros((128,128,3),np.uint8)]*(8-len(crops[i:i+8]))) for i in range(0,len(crops),8)]
cv2.imwrite('/workspace/work/cv/g4logs/capsicum_testrf_sheet.jpg',np.vstack(rowsimg))
json.dump(dict(pred_for_gt_capsicum=conf,images=per_img),open('ml/runs/G4/capsicum_testrf_inspect.json','w'),indent=1)
print(conf, len(per_img))
