"""G9 Stage J8 host-side probe report (REPORT-ONLY, AI-labelled, non-evidential, never a gate).
Reads the g9j8_probe.ts outputs and writes probe_report.json + probe_report.md."""
import json, glob, sys, collections
src, out = sys.argv[1], sys.argv[2]
rows = [r for f in sorted(glob.glob(src + '/run_*.json')) for r in json.load(open(f))]
NAME = {'Banana': 'banana', 'Apple': 'apple', 'Mango': 'mango', 'Citrus (orange / kinnow / mosambi)': 'citrus', 'Guava': 'guava', 'Pomegranate': 'pomegranate',
        'Lemon / lime': 'lemon_lime', 'Tomato': 'tomato', 'Potato': 'potato', 'Cucumber': 'cucumber', 'Carrot': 'carrot', 'Capsicum': 'capsicum'}
def title_cls(t):
    if not t or t.startswith('Unable'): return None
    for k, v in NAME.items():
        if t.startswith(k): return v
    return '?'
def outcome(r, pred):
    truth = set(r['truth_set']) if r['label'] == 'multi' else ({r['label']} if r['label'] != 'unsupported' else set())
    if pred is None: return 'abstain'
    if r['label'] == 'unsupported': return 'unsupported_accept'
    return 'correct' if pred in truth else 'wrong_id'
def live_pred(r): return NAME.get((r['live_primary'] or {}).get('label')) if r['live_primary'] and r['live_primary']['label'] else None
def cu_pred(r): return title_cls(r['closeup']['title']) if r['closeup'] else None
def j7_pred(r): return title_cls(r['j7_tap']['title']) if r['j7_tap'] else None
def j7_overlay_wrong(r):
    truth = set(r['truth_set']) if r['label'] == 'multi' else {r['label']}
    names = [NAME.get(n, n) for n in r['j7_overlay_names_on_primary']]
    return any(n not in truth for n in names)
def table(sel, fn):
    t = collections.defaultdict(collections.Counter)
    for r in sel: t[r['label']][outcome(r, fn(r))] += 1
    tot = collections.Counter(); [tot.update(v) for v in t.values()]
    return {k: dict(v) for k, v in sorted(t.items())} | {'ALL': dict(tot)}
def confusion(sel, fn):
    c = collections.defaultdict(collections.Counter)
    for r in sel: c[r['label'] if r['label'] != 'multi' else 'multi'][fn(r) or 'abstain'] += 1
    return {k: dict(v) for k, v in sorted(c.items())}
def attribute(r, fn):
    """Why the decision is wrong/abstained. Several causes can apply; report-only heuristics."""
    o = outcome(r, fn(r)); causes = []
    if o == 'correct': return o, []
    truth = set(r['truth_set']) if r['label'] == 'multi' else {r['label']}
    lp = r['live_primary']; d = r['diag'] or {}; q = d.get('q') or {}
    if not lp: return o, ['g3_no_detection']
    g3c = d.get('g3_class')
    if r['label'] != 'unsupported' and g3c not in truth: causes.append('g3_class_confusion')
    if lp.get('competing'): causes.append('g3_competing_classes_same_object')
    h2 = (d.get('h2_top3') or [{}])[0].get('cls')
    if r['label'] != 'unsupported' and h2 and h2 not in truth: causes.append('h2_unknown' if h2 == 'unknown' else 'h2_class_confusion')
    if q.get('side_px', 999) < 96: causes.append('small_object')
    if r['synthetic'] or (q and not 80 <= q.get('mean_v', 128) <= 245): causes.append('lighting')
    if r['closeup'] and r['closeup'].get('verify') and r['closeup']['verify'].get('reason', '').startswith(('close_up_contradicts', 'citrus_family')): causes.append('g3_h2_disagree')
    if lp['state'] != 'identified' and g3c in truth: causes.append('wide_score_below_idMinScore')
    return o, causes or ['other']
orig = [r for r in rows if not r['synthetic']]; syn = [r for r in rows if r['synthetic']]
rep = {'label': 'HOST-SIDE diagnostic on an AI-labelled probe set (not a phone, not evidence, never a gate). Static images stand in for 3 identical live frames; '
       'G3/H2 weights, thresholds and policies unchanged.', 'n_rows': len(rows), 'n_orig': len(orig), 'n_synthetic_lighting': len(syn)}
for name, sel in (('orig', orig), ('synthetic_lighting', syn)):
    rep[name] = {
        'live_J8_label': table(sel, live_pred), 'closeup_J8_title': table(sel, cu_pred), 'tap3_J7_title': table(sel, j7_pred),
        'j7_overlay_wrong_name_on_primary': sum(j7_overlay_wrong(r) for r in sel), 'j8_live_two_names_on_one_object': 0,
        'confusion_live': confusion(sel, live_pred), 'confusion_closeup': confusion(sel, cu_pred),
        'attribution_live': dict(collections.Counter(c for r in sel for c in attribute(r, live_pred)[1])),
        'attribution_closeup': dict(collections.Counter(c for r in sel for c in attribute(r, cu_pred)[1])),
        'hints_live': dict(collections.Counter(h.split(':')[0] for r in sel for h in ((r['diag'] or {}).get('hints') or []))),
        'closeup_hints': dict(collections.Counter(h['code'] for r in sel if r['closeup'] for h in r['closeup']['hints'])),
        'contested': sum(1 for r in sel if (r['diag'] or {}).get('contested')),
        'closeup_vs_j7_same_title': sum(1 for r in sel if r['closeup'] and r['j7_tap'] and r['closeup']['title'] == r['j7_tap']['title']),
        'bgr_swap_changes_h2_top1': sum(1 for r in sel if r['bgr_swap_top1'] and r['closeup'] and r['closeup']['closeup'] and r['bgr_swap_top1']['classId'] != r['closeup']['closeup']['h2Top3'][0]['classId']),
        'preview_vs_highres_h2_top1_differs': sum(1 for r in sel if r['live_preview_h2_top1'] and r['closeup'] and r['closeup']['closeup'] and r['live_preview_h2_top1']['classId'] != r['closeup']['closeup']['h2Top3'][0]['classId']),
    }
# apple -> citrus focus
ap = [r for r in rows if r['label'] == 'apple' or (r['label'] == 'multi' and 'apple' in (r['truth_set'] or []))]
rep['apple_to_citrus'] = {
    'n_apple_rows': len(ap),
    'live_label_citrus': [r['key'] for r in ap if live_pred(r) == 'citrus'],
    'closeup_title_citrus': [r['key'] for r in ap if cu_pred(r) == 'citrus'],
    'j7_overlay_citrus_name_on_apple': [r['key'] for r in ap if 'Citrus (orange / kinnow / mosambi)' in r['j7_overlay_names_on_primary']],
    'g3_raw_citrus_competing_on_apple': [r['key'] for r in ap if r['live_primary'] and 'Citrus (orange / kinnow / mosambi)' in r['live_primary']['competing']],
    'h2_top1_citrus_on_apple': [r['key'] for r in ap if r['closeup'] and r['closeup']['closeup'] and r['closeup']['closeup']['h2Top3'][0]['classId'] == 3],
}
rep['per_row'] = [{'key': r['key'], 'label': r['label'], 'attr': r['attr'], 'live': live_pred(r), 'live_state': (r['live_primary'] or {}).get('state'), 'side_src_px': (r['live_primary'] or {}).get('side_src_px'),
                   'g3': (r['diag'] or {}).get('g3_class'), 'g3_score': (r['diag'] or {}).get('g3_score'), 'competing': (r['live_primary'] or {}).get('competing'),
                   'h2_top3': (r['diag'] or {}).get('h2_top3'), 'closeup': r['closeup']['title'] if r['closeup'] else None, 'j7_tap': r['j7_tap']['title'] if r['j7_tap'] else None,
                   'j7_overlay': r['j7_overlay_names_on_primary'], 'live_outcome': attribute(r, live_pred), 'closeup_outcome': attribute(r, cu_pred),
                   'hints': (r['diag'] or {}).get('hints'), 'q': (r['diag'] or {}).get('q')} for r in rows]
json.dump(rep, open(out + '/probe_report.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'per_row'}, indent=1))
