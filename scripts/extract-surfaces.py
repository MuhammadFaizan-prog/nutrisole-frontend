"""Extract clean original paper/texture strips; no letters, controls or device chrome."""
from pathlib import Path
from PIL import Image
import hashlib, json, re
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'NutriSole-UI-Concepts'
regions={
 'paper-onboarding-upper':('01_21_15 AM-1',(60,136,804,169)),
 'paper-onboarding-middle':('01_21_15 AM-1',(60,454,804,476)),
 'paper-onboarding-bottom':('01_21_15 AM-1',(300,1599,617,1677)),
 'paper-home':('01_21_16 AM-2',(300,278,780,306)),
 'paper-profile':('01_21_23 AM-6',(90,1440,740,1630)),
 'paper-weekly':('01_21_21 AM-5',(80,354,780,392)),
 'onboarding-card-paper':('01_21_15 AM-1',(221,1115,764,1138)),
 'scan-detection-surface':('01_21_18 AM-3',(279,434,733,447)),
 'scan-instruction-surface':('01_21_18 AM-3',(174,1237,695,1261)),
 'scan-controls-surface':('01_21_18 AM-3',(216,1408,330,1754)),
}
manifest=[]
for name,(suffix,bounds) in regions.items():
    path=next(SOURCE.glob(f'*{suffix}.png'))
    im=Image.open(path).crop(bounds)
    for directory in [ROOT/'assets/source',ROOT/'public/nutrisole']:im.save(directory/f'{name}.png')
    manifest.append({'id':name,'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'boundsLTRB':bounds,'operations':['crop only','lossless PNG encode'],'content':'Clean source paper or control-surface texture without any text, data, icon or hardware pixels. App stretches the original strip inside real components; exact whole-surface lighting cannot be recovered from the occluded raster.'})
# Restore the observed paper lighting from clean rows. Interpolation fills only
# background areas hidden by the source's text/photo; it never retains any UI pixels.
path=next(SOURCE.glob('*01_21_15 AM-1.png'))
source=np.asarray(Image.open(path).convert('RGB'),dtype=float)
bands=[(60,136,804,169),(60,258,804,280),(60,454,804,476),(60,610,780,631),(80,1599,617,1631),(80,1643,617,1677),(110,1756,617,1764)]
row_positions=[];rows=[]
for left,top,right,bottom in bands:
    row=source[top:bottom,left:right].mean(axis=0)
    rows.append(np.stack([np.interp(np.arange(38,824),np.arange(left,right),row[:,channel]) for channel in range(3)],axis=-1))
    row_positions.append((top+bottom-1)/2)
sampled=np.stack(rows)
reconstructed=np.empty((1748,786,3))
for x in range(786):
    for channel in range(3):reconstructed[:,x,channel]=np.interp(np.arange(38,1786),row_positions,sampled[:,x,channel])
paper=Image.fromarray(np.rint(reconstructed).clip(0,255).astype('uint8'))
for directory in [ROOT/'assets/source',ROOT/'public/nutrisole']:paper.save(directory/'paper-onboarding-calibrated.png')
manifest.append({'id':'paper-onboarding-calibrated','source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cleanSourceBandsLTRB':bands,'operations':['sample clean paper rows','interpolate original RGB lighting between sampled rows','lossless PNG encode'],'content':'Background only; no text, icons, photographs, controls or device pixels. Reconstructed occluded paper lighting is an estimate, not a claim of exact source pixels.'})
(ROOT/'assets/source/surfaces.provenance.json').write_text(json.dumps(manifest,indent=2))
names=[a['id'] for a in manifest]
(ROOT/'src/nutrisole/surfaceAssets.ts').write_text('// Clean source surface crop names.\nexport const surfaceAssets = '+json.dumps(names)+' as const;\n')
p=ROOT/'src/nutrisole/assets.native.ts'
s=re.sub(r'  // BEGIN SOURCE SURFACES.*?  // END SOURCE SURFACES\n','',p.read_text(),flags=re.S)
entries=''.join(f"  '{name}': require('../../assets/source/{name}.png'),\n" for name in names)
p.write_text(s.replace('};','  // BEGIN SOURCE SURFACES\n'+entries+'  // END SOURCE SURFACES\n};'))
print(f'Extracted {len(regions)} clean source surface strips and reconstructed the paper lighting.')
