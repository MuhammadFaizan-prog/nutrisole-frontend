"""Compare clean surface patches, excluding text, photos, icons and device chrome."""
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'artifacts/qa/exact-refinement'
regions={
 'onboarding':[(350,155,500,170),(540,615,690,630),(330,1610,570,1660),(450,1120,680,1135)],
 'home':[(370,275,580,295),(310,510,470,560),(315,750,550,785),(150,985,330,1010)],
 'profile':[(250,220,330,250),(310,372,550,398),(250,1530,650,1630)],
 'log-meal':[(250,1450,650,1560),(380,352,600,374)],
 'weekly-plan':[(180,355,600,380),(310,533,650,553),(310,1308,650,1321)],
}
crops={'onboarding':[38,38,786,1748],'home':[42,38,777,1737],'profile':[50,166,760,1564],'log-meal':[55,120,750,1604],'weekly-plan':[57,149,749,1537]}
for route,rects in regions.items():
    ref=Image.open(QA/f'{route}-reference.png').convert('RGB')
    act=Image.open(QA/f'{route}.png').convert('RGB')
    x,y,w,h=crops[route];scale=min(393/w,852/h);offset=(393-w*scale)/2
    for box in rects:
        r=(round((box[0]-x)*scale+offset),round((box[1]-y)*scale),round((box[2]-x)*scale+offset),round((box[3]-y)*scale))
        samples=[np.asarray(im.crop(r)).mean(axis=(0,1)).round(1).tolist() for im in [ref,act]]
        print(route,box,'ref/actual',samples)
