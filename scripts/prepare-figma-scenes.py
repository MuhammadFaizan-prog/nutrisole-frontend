"""Translate exported native component trees to a semantic Figma scene specification.
Only the two photographic scene assets are raster-masked; no UI is flattened.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import json, xml.etree.ElementTree as ET, hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/figma'
CROPS={'onboarding':[38,38,786,1748],'home':[42,38,777,1737],'scan':[41,37,781,1739],'log-meal':[55,120,750,1604],'weekly-plan':[57,149,749,1537],'profile':[50,166,760,1564]}
SCENES={'onboarding':[38,609,786,982],'scan':[41,37,781,1371]}
provenance=[]
for scene,(x,y,w,h) in SCENES.items():
    original=ROOT/f'assets/source/{scene}-photo-region.png'
    image=Image.open(original).convert('RGBA')
    multiplier=4
    mask=Image.new('L',(w*multiplier,h*multiplier),255)
    d=ImageDraw.Draw(mask)
    def rect(a,r=0):
        b=[int((a[0]-x)*multiplier),int((a[1]-y)*multiplier),int((a[2]-x)*multiplier),int((a[3]-y)*multiplier)]
        d.rounded_rectangle(b,radius=r*multiplier,fill=0)
    def circle(cx,cy,r):
        d.ellipse(((cx-r-x)*multiplier,(cy-r-y)*multiplier,(cx+r-x)*multiplier,(cy+r-y)*multiplier),fill=0)
    if scene=='onboarding': rect([62,1089,799,1594],52)
    else:
        for a,r in [([116,73,190,110],0),([304,53,559,130],39),([620,71,780,111],0),([264,412,748,568],49),([142,1226,725,1381],54)]:rect(a,r)
        circle(127.5,217.5,49);circle(739,217,49)
        d.polygon([((a-x)*multiplier,(b-y)*multiplier) for a,b in [(480,559),(520,559),(500,585)]],fill=0)
        paths=[[(218,706),(218,680),(218,640),(260,640),(285,640)],[(666,640),(688,640),(732,640),(732,683),(732,706)],[(218,1064),(218,1087),(218,1129),(260,1129),(285,1129)],[(666,1129),(688,1129),(732,1129),(732,1087),(732,1064)]]
        for points in paths:
            p0,p1,ctrl,p2,p3=points
            pts=[p0,p1]+[((1-t)**2*p1[0]+2*(1-t)*t*ctrl[0]+t*t*p2[0],(1-t)**2*p1[1]+2*(1-t)*t*ctrl[1]+t*t*p2[1]) for t in [i/32 for i in range(33)]]+[p3]
            d.line([((a-x)*multiplier,(b-y)*multiplier) for a,b in pts],fill=0,width=16*multiplier)
            for a,b in [p0,p3]:circle(a,b,8)
    image.putalpha(mask.resize((w,h),Image.Resampling.LANCZOS))
    target=OUT/f'{scene}-photo-masked.png';image.save(target)
    provenance.append({'asset':target.name,'source':str(original),'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'method':'Source photograph with alpha exclusions matching ScenePhoto.tsx. Original UI removed before Figma import.'})
def nodes(e):
    out=[]
    for child in e:
        p=json.loads(child.attrib['data-props'])
        if p['kind']=='box' and not p.get('style'):out.extend(nodes(child));continue
        if p['kind']=='text':
            p['text']=''.join(child.itertext())
            p['runs']=[{'text':''.join(c.itertext()),'style':json.loads(c.attrib['data-props']).get('style',{})} for c in child]
        else:p['children']=nodes(child)
        if p['kind']=='scene':
            p.update(dict(zip(['x','y','w','h'],SCENES[p['scene']])));p['asset']=f"{p['scene']}-photo-masked"
        out.append(p)
    return out
scenes=[]
for row in json.loads((OUT/'source-markup.json').read_text(encoding='utf-8')):
    scenes.append({'route':row['route'],'crop':CROPS[row['route']],'nodes':nodes(ET.fromstring(row['html']))})
(OUT/'scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'scenes.ascii.json').write_text(json.dumps(scenes,ensure_ascii=True),encoding='ascii')
(OUT/'photograph-provenance.json').write_text(json.dumps(provenance,indent=2))
print('Six semantic scenes:',[(s['route'],len(s['nodes'])) for s in scenes])
