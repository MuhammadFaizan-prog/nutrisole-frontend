"""De-duplicated view of G7 ripeness test_cc0: drop test images whose pHash min Hamming to train <= threshold (near_dup flag from Kaggle kernel nutrisole-g7-ripe-neardup). Unconditional 15-way top-1 (argmax)."""
import json, collections
R='ml/runs/G7/ripeness/'
nd={x['name']:x['near_dup'] for x in json.load(open(R+'ripe_test_neardup.json'))}
P=json.load(open(R+'ripeness_g7_preds.json'))['test_cc0']
out={}
for view,keep in (('all',lambda f:True),('dedup',lambda f:not nd[f]),('neardup_only',lambda f:nd[f])):
    rows=[p for p in P if keep(p['file'])]
    ok=[max(p['probs'],key=p['probs'].get)==f"{p['fruit']}_{p['stage']}" for p in rows]
    pf=collections.defaultdict(lambda:[0,0])
    for p,o in zip(rows,ok): pf[p['fruit']][0]+=o; pf[p['fruit']][1]+=1
    out[view]={'n':len(rows),'top1_15way':round(sum(ok)/max(1,len(rows)),4),'per_fruit':{k:{'n':v[1],'top1':round(v[0]/v[1],4)} for k,v in sorted(pf.items())}}
out['meta']={'split':'test_cc0 (Kaggle CC0 asadullahprl/fruits-ripeness-classification-dataset)','model':'yolo11n-cls G7 ripeness','imgsz':224,'device_of_preds':'Tesla T4 (Kaggle)','near_dup_def':'pHash min Hamming to any train image <= 4'}
json.dump(out,open(R+'ripeness_dedup.json','w'),indent=1); print(json.dumps({k:(v['n'],v['top1_15way']) for k,v in out.items() if k!='meta'}))
