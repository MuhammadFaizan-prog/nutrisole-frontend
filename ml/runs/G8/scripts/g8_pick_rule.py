import json,glob,os
rows=[]
for d in sorted(glob.glob("ml/runs/G7/tracking/tune/nt*")):
    if not os.path.exists(d+"/gauntlet.json"): continue
    g=json.load(open(d+"/gauntlet.json"))["clips"]; c=g["det"]; ng=g.get("neg",{})
    rows.append(dict(cfg=os.path.basename(d),seg=c["segment_acc"],frame=c["frame_acc"],ttfc_p90=c["ttfc_ms"]["p90"],flick=c["label_flicker_per_10s_static"],ids=c["id_switches"],frag=c.get("fragmentations"),missed_s=c.get("missed_s_total"),fa_min=ng.get("false_alarms_per_min")))
ref=[r for r in rows if r["cfg"]=="nt0.35_mt0.8_mh2"][0]
ok=[r for r in rows if r["flick"]<=0.625 and (r["fa_min"] or 0)<=(ref["fa_min"] or 0)]
pick=sorted(ok,key=lambda r:(-r["seg"],r["ttfc_p90"] or 1e9))[0] if ok else ref
print(json.dumps(dict(rule="prereg addendum C",rows=rows,ref=ref["cfg"],pick=pick["cfg"]),indent=1))
