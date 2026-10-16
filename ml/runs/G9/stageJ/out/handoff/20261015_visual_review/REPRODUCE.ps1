param(
    [string]$Python = 'python',
    [string]$AuditOut = ''
)
# Run from the repository root. This checks recorded AI work; it never trains or creates human evidence.
$ErrorActionPreference = 'Stop'
$stage = 'ml/runs/G9/stageJ'
$review = "$stage/out/handoff/20261015_visual_review"
if (-not $AuditOut) {
    $AuditOut = "$stage/out/handoff/visual-review-recheck-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
}
$consistencyCheck = @'
import csv, json, sys
from pathlib import Path
sys.path.insert(0, 'ml/runs/G9/stageJ/scripts')
import j_annotation as V
import j_agree as J
base = Path('ml/runs/G9/stageJ/out/handoff/20261015_visual_review')
table = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))
saved = [r for p in sorted((base/'review_batches').glob('*.json')) for r in json.loads(p.read_text(encoding='utf-8'))]
source = {r['item_id']: r for r in saved}
expected = set(J.load_key('pilot'))
assert len(saved) == len(source) == 265 and set(source) == expected
ai = V.validate_ai(base/'AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv', expected)
details = table(base/'G9J_AI_per_image_review.csv')
detail = {r['item_id']: r for r in details}
assert len(details) == len(detail) == 265 and set(detail) == expected
integrity = {r['item_id']: r for r in table(base/'audit/G9J_pilot_integrity_report.csv')}
for r in ai['rows']:
    iid = r['item_id']; s = source[iid]; d = detail[iid]; im = integrity[iid]
    assert r['annotator'] == V.AI_MARKER and r['copy'] == 'annotator1' and r['seconds'] == '0'
    assert r['labelled_at'] == s['reviewed_at']
    for k in ('label', 'note', 'other_produce_name', 'occluded_or_printed_what'):
        assert r[k] == s[k] == d[k], (iid, k)
    for k, tag in zip(V.TAGS, 'CBMX'):
        assert V.boolean(r[k]) == int(tag in s['tags']), (iid, k)
    assert d['tags'] == s['tags'] and d['confidence'] == s['confidence'] and d['review_flags'] == s['review_flags']
    assert d['source_context_used'] == str(s['source_context_used']).lower()
    assert d['provenance'] == V.AI_MARKER and d['human_verified'] == 'false'
    assert r['order_index'] == d['order_index'] == im['annotator1_order']
    assert d['package_sha256'] == im['annotator1_sha256'] == im['annotator2_sha256']
    assert im['status'] == 'PASS'
queue = table(base/'nutrisole_G9J_AI_review_queue.csv')
qids = [r['item_id'] for r in queue]
assert len(qids) == len(set(qids)) == 157
assert set(qids) == {r['item_id'] for r in details if r['label'] == 'uncertain' or r['confidence'] != 'high' or r['review_flags']}
assert all(r == detail[r['item_id']] for r in queue)
meta = json.loads((base/'G9J_visual_review_metadata.json').read_text(encoding='utf-8'))
assert ai['counts'] == meta['label_counts'] and meta['human_verified_images'] == 0 and meta['kappa'] is None
assert json.loads((base/'audit/G9J_H3_readiness.json').read_text(encoding='utf-8'))['status'] == 'BLOCKED'
frozen = json.loads((base/'audit/G9J_frozen_inputs.json').read_text(encoding='utf-8'))
baseline = json.loads((base.parent/'20261015/G9J_frozen_inputs.json').read_text(encoding='utf-8'))
assert frozen['git_lf_sha256'] == baseline['git_lf_sha256']
assert all(V.frozen_digest(Path(p)) == h for p, h in frozen['git_lf_sha256'].items())
print(json.dumps(dict(rows=265, schema='PASS', stable_ids='PASS', order_and_image_hashes='PASS', saved_notes_and_tags='PASS', queue_rows=len(queue), provenance='AI_ASSISTED_NOT_HUMAN', human_verified=0, H3='BLOCKED', csv_sha256=ai['sha256']), indent=2))
'@
$consistencyCheck | & $Python -X utf8 -
if ($LASTEXITCODE -ne 0) { throw 'Visual-review consistency check failed' }
& $Python -X utf8 -m pytest "$stage/scripts/test_j_agree.py" "$stage/scripts/test_j_handoff.py" -q
if ($LASTEXITCODE -ne 0) { throw 'Stage J regression tests failed' }
& $Python -X utf8 "$stage/scripts/j_handoff.py" `
    --pack1 '../nutrisole_G9J_pilot_annotator1.zip' `
    --pack2 '../nutrisole_G9J_pilot_annotator2.zip' `
    --ai-csv "$review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv" `
    --review-queue "$review/nutrisole_G9J_AI_review_queue.csv" `
    --ai-readme "$review/nutrisole_G9J_AI_annotation_handoff_README.txt" `
    --out $AuditOut
if ($LASTEXITCODE -ne 0) { throw 'Audit failed' }
