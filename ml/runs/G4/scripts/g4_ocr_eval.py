# G4.6: OCR accuracy of ml/prices on the hand-checked sample (4 lists, 148 rows). Writes ml/runs/G4/prices_ocr_eval.json + parsed JSON fixtures.
import sys, json, cv2, collections
sys.path.insert(0, '/workspace/work/nutrisole/ml')
from prices.rate_list import parse_list, norm_ur
gt = json.load(open('/workspace/work/nutrisole/ml/prices/fixtures/handcheck_gt.json'))
res = {}; tot = collections.Counter()
for key, L in gt['lists'].items():
    out = parse_list(cv2.imread(f"/workspace/work/cv/g4data/prices/{L['file']}"), L['kind'], L['date'], 'file://' + L['file'])
    json.dump(out, open(f"/workspace/work/nutrisole/ml/prices/fixtures/parsed_{key}.json", 'w'), ensure_ascii=False, indent=1)
    c = collections.Counter(); errs = []
    G = {k: v for k, v in L['rows'].items() if k != '(blank)'}
    seen = set()
    for r in out['rows']:
        g = G.get(r['item_ur'])
        if g is None: c['kept_not_in_gt'] += 1; continue
        seen.add(r['item_ur'])
        for i, col in enumerate(['grade1_rs', 'grade2_rs']):
            c['cells_kept'] += 1
            if r[col] == g[i]: c['cells_correct'] += 1
            else: errs.append((r['item_ur'], col, r[col], g[i]))
    c['rows_gt'] = len(G); c['rows_kept'] = len(out['rows']); c['rows_dropped'] = len(out['dropped_rows'])
    c['gt_rows_with_price'] = sum(1 for v in G.values() if v[0] is not None or v[1] is not None)
    c['priced_rows_recovered'] = sum(1 for k in seen if G[k][0] is not None or G[k][1] is not None)
    res[key] = dict(counts=c, errors=errs, dropped=[(d['name_ocr'], d['dropped'], d['grade1_rs'], d['grade2_rs']) for d in out['dropped_rows']])
    tot.update(c)
    print(key, dict(c), errs[:5])
cell_acc = tot['cells_correct'] / max(1, tot['cells_kept'])
summary = dict(total=dict(tot), kept_cell_accuracy=round(cell_acc, 4), priced_row_recall=round(tot['priced_rows_recovered'] / max(1, tot['gt_rows_with_price']), 4),
               note="Lexicon built from the 2026-10-12 lists, so 2026-10-12 is in-sample for name matching; 2026-10-10 is held out (same item set, different prices).")
json.dump(dict(summary=summary, per_list=res), open('/workspace/work/nutrisole/ml/runs/G4/prices_ocr_eval.json', 'w'), ensure_ascii=False, indent=1, default=dict)
print(summary)
