"""Fetch open font candidates from their official Google Fonts source and compare glyph shapes."""
from urllib.request import Request, urlopen
from pathlib import Path
import hashlib, json
from PIL import Image, ImageFont, ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'artifacts/qa/font-candidates'
TARGET.mkdir(exist_ok=True)
records=[]
for family in ['gelasio','librebaskerville','dmserifdisplay']:
    url=f'https://api.github.com/repos/google/fonts/contents/ofl/{family}'
    entries=json.loads(urlopen(Request(url,headers={'User-Agent':'NutriSole-font-calibration'})).read())
    for item in entries:
        if item['name']=='OFL.txt' or (item['name'].endswith('.ttf') and 'Italic' not in item['name']):
            data=urlopen(item['download_url']).read()
            path=TARGET/(family+'-'+item['name'])
            path.write_bytes(data)
            records.append({'file':str(path),'url':item['download_url'],'sha256':hashlib.sha256(data).hexdigest()})
(TARGET/'provenance.json').write_text(json.dumps(records,indent=2))
regions=[('headline',(102,288,688,374),'Healthy choices,'),('headline-second',(102,374,585,455),'made simple.'),('brand',(163,193,393,254),'NutriSole')]
source=Image.open(next((ROOT.parent/'NutriSole-UI-Concepts').glob('*01_21_15 AM-1.png'))).convert('L')
fonts=list(TARGET.glob('*.ttf'))+[ROOT/'assets/fonts/LibreCaslonText-Regular.ttf',ROOT/'assets/fonts/LibreCaslonText-Bold.ttf',ROOT/'native/node_modules/@expo-google-fonts/libre-caslon-display/400Regular/LibreCaslonDisplay_400Regular.ttf']
summary={}
for name,bounds,text in regions:
    mask=source.crop(bounds).point(lambda v:255 if v<100 else 0)
    mask=mask.crop(mask.getbbox());target=np.asarray(mask,dtype=float)/255
    scores=[]
    for path in fonts:
        for weight in [400,500,600,700]:
            f=ImageFont.truetype(str(path),100)
            try:f.set_variation_by_axes([weight])
            except OSError:
                if weight!=400:continue
            for spacing in [-2,-1,0,1,2]:
                render=Image.new('L',(1800,180));d=ImageDraw.Draw(render);x=10
                for char in text:
                    d.text((x,0),char,font=f,fill=255);x+=d.textlength(char,font=f)+spacing
                glyph=render.crop(render.getbbox());p=np.asarray(glyph.resize(mask.size,Image.Resampling.LANCZOS),dtype=float)/255
                score=float(np.minimum(target,p).sum()/np.maximum(target,p).sum())
                scores.append((score,path,weight,spacing,glyph))
    scores.sort(key=lambda item:item[0],reverse=True)
    summary[name]=[{'iou':round(s,4),'path':str(p),'weight':w,'spacing':sp,'ratio':round((g.width/g.height)/(mask.width/mask.height),4)} for s,p,w,sp,g in scores[:10]]
    canvas=Image.new('RGB',(750,(mask.height+45)*11),'white');d=ImageDraw.Draw(canvas)
    d.text((10,5),'Source '+name,fill='black');canvas.paste(Image.eval(mask,lambda p:255-p),(10,30))
    for i,(s,p,w,sp,g) in enumerate(scores[:10]):
        y=(i+1)*(mask.height+45);d.text((10,y),f'{s:.3f} {p.stem} weight={w} spacing={sp}',fill='black');canvas.paste(Image.eval(g.resize(mask.size,Image.Resampling.LANCZOS),lambda p:255-p),(10,y+25))
    canvas.save(TARGET/f'{name}.png')
(TARGET/'comparison.json').write_text(json.dumps(summary,indent=2))
for name,entries in summary.items():print(name,json.dumps(entries[:3]))
