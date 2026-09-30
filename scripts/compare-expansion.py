"""Build diagnostic comparisons from fresh browser viewport screenshots.

Screenshot pixels use CSS coordinates for content despite a larger outer canvas.
The crop is calibrated by inspecting the full viewport, not scaled to canvas size.
Protected device chrome is intentionally present; this is not a pixel-identity score.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import json

root = Path(__file__).resolve().parents[1]
captures = root / 'artifacts/expansion/browser'
refs = root / 'artifacts/screen-coverage/images'
ids = ['sign-in', 'create-account', 'verify-email', 'recover-account', 'reset-password', 'analysis-result', 'market-reference', 'capture-retry', 'food-selector', 'nutrition-details', 'glucose-overview', 'add-reading', 'reading-detail', 'health-connections', 'plan-generation', 'activity-plan', 'plan-rationale', 'foot-questionnaire', 'foot-guidance', 'assistant', 'privacy-data-rights', 'reminders', 'report-output', 'report-status', 'personal-history', 'catalog-queue', 'catalog-review', 'model-release', 'operations-audit', 'report-triage']
for name in ids:
    Image.open(captures / f'{name}.jpg').crop((578,241,971,1093)).save(captures / f'{name}-app.png')
for batch in range(5):
    sheet = Image.new('RGB', (1242, 942), '#e8e8e5')
    draw = ImageDraw.Draw(sheet)
    for k,name in enumerate(ids[batch*6:batch*6+6]):
        x,y = (k%3)*414,(k//3)*471
        draw.text((x+5,y+5),name,fill='black')
        draw.text((x+5,y+23),'Concept',fill='black')
        draw.text((x+209,y+23),'Fresh code',fill='black')
        for j,path in enumerate([refs/f'{name}.png',captures/f'{name}-app.png']):
            img=Image.open(path).convert('RGB').resize((196,425))
            sheet.paste(img,(x+5+j*204,y+42))
    sheet.save(captures / f'comparison-{batch+1}.jpg',quality=93)
print(json.dumps({'screens':len(ids),'cropCss':[578,241,971,1093],'sheets':5,'pixelIdentityCertified':False}))
