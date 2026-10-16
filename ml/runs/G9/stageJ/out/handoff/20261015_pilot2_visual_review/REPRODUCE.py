"""Recheck recorded Pilot 2 AI review evidence; never annotate, train or create human evidence.

Run from any directory with Python + Pillow + ImageHash. Optional original ZIPs are
read-only. --output must name a new file. Visual judgments themselves are not tests.
"""
from pathlib import Path
from collections import Counter
from itertools import combinations
import argparse
import csv
import hashlib
import json
import sys

BASE = Path(__file__).resolve().parent
ROOT = next(p for p in BASE.parents if (p / 'package.json').is_file() and (p / 'ml/runs/G9/stageJ').is_dir())
sys.path.insert(0, str(ROOT / 'ml/runs/G9/stageJ/scripts'))
import j_annotation as V
import j_agree as J
import j_handoff as H


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def table(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, strict=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack1', type=Path)
    parser.add_argument('--pack2', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if bool(args.pack1) != bool(args.pack2):
        parser.error('supply both --pack1 and --pack2')
    expected = set(J.load_key('pilot2'))
    key = J.load_key('pilot2')
    saved = [r for p in sorted((BASE / 'review_batches').glob('*.json')) for r in read(p)]
    source = {r['item_id']: r for r in saved}
    assert len(saved) == len(source) == len(expected) == 335 and set(source) == expected
    ai_path = BASE / 'AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335.csv'
    ai = V.validate_ai(ai_path, expected, batch='pilot2')
    details = table(BASE / 'G9J_pilot2_AI_per_image_review.csv')
    detail = {r['item_id']: r for r in details}
    assert len(details) == len(detail) == 335 and set(detail) == expected
    report = read(BASE / 'audit/G9J_pilot2_integrity_report.json')
    integrity = {r['item_id']: r for r in report['rows']}
    assert report['status'] == 'PASS' and set(integrity) == expected
    subtypes = {'lemon_or_lime','mango','guava','pomegranate','potato','cucumber','capsicum_bell_pepper',
                'chili','onion','grapefruit_or_pomelo','peach_plum_apricot','persimmon','kiwi',
                'radish_or_beetroot','sweet_potato','other'}
    for r in ai['rows']:
        iid = r['item_id']; s = source[iid]; d = detail[iid]; im = integrity[iid]
        assert r['annotator'] == V.AI_MARKER and r['copy'] == 'annotator1' and r['seconds'] == '0'
        assert r['labelled_at'] == s['reviewed_at'] == d['reviewed_at']
        for name in ('label', 'note', 'other_produce_name', 'occluded_or_printed_what'):
            assert r[name] == s[name] == d[name], (iid, name)
        if r['label'] == 'other_produce':
            assert r['other_produce_name'] in subtypes
        else:
            assert r['other_produce_name'] == ''
        assert r['occluded_or_printed_what'] in {'', *V.LABELS[:6]}
        for name, tag in zip(V.TAGS, 'CBMX'):
            assert V.boolean(r[name]) == int(tag in s['tags']), (iid, name)
        assert d['tags'] == s['tags'] and d['confidence'] == s['confidence']
        assert d['review_flags'] == s['review_flags'] and d['visual_evidence'] == s['visual_evidence']
        assert d['source_context_used'] == str(s['source_context_used']).lower()
        assert d['provenance'] == V.AI_MARKER and d['human_verified'] == 'false'
        assert r['order_index'] == d['order_index'] == str(im['annotator1_order'])
        assert d['package_sha256'] == im['annotator1_sha256'] == im['annotator2_sha256']
        assert d['package_width'] == str(im['width']) and d['package_height'] == str(im['height'])
        assert d['source_page_url'] == key[iid]['page_url'] and key[iid]['split'] == 'J-eval'
        assert im['status'] == 'PASS'
    assert {int(r['order_index']) for r in ai['rows']} == set(range(1,336))
    queue = table(BASE / 'nutrisole_G9J_pilot2_AI_review_queue.csv')
    qids = [r['item_id'] for r in queue]
    assert len(qids) == len(set(qids)) == 233
    assert set(qids) == {r['item_id'] for r in details if r['label'] == 'uncertain' or r['confidence'] != 'high' or r['review_flags']}
    assert all(r == detail[r['item_id']] for r in queue)
    assert queue == sorted(queue, key=lambda r: ({'HIGH':0,'MEDIUM':1,'LOW':2}[r['priority']],r['item_id']))
    meta = read(BASE / 'G9J_pilot2_visual_review_metadata.json')
    assert ai['counts'] == {k:v for k,v in meta['label_counts'].items() if v}
    assert meta['annotation_csv_sha256'] == ai['sha256'] and meta['annotation_label_fingerprint'] == ai['label_fingerprint']
    assert dict(Counter(r['priority'] for r in queue)) == meta['queue_priority_counts']
    assert sum('native' in r['visual_evidence'] for r in saved) == meta['native_package_detail_views'] == 100
    assert sum(r['source_context_used'] for r in saved) == meta['source_context_used'] == 8
    assert meta['human_verified_images'] == 0 and meta['kappa'] is None and meta['source_originals_viewed'] == 0
    ready = read(BASE / 'audit/G9J_pilot2_H3_readiness.json')
    assert ready['status'] == 'BLOCKED' and ready['training_authorized'] is False and ready['ai_rows_used_for_human_gates'] == 0
    frozen = read(BASE / 'audit/G9J_frozen_inputs.json')
    assert frozen['git_lf_sha256'] == read(BASE.parent / '20261015/G9J_frozen_inputs.json')['git_lf_sha256']
    assert all(V.frozen_digest(ROOT/p) == h for p,h in frozen['git_lf_sha256'].items())
    gaps = read(BASE / 'audit/G9J2_preserved_inputs.json')['byte_sha256']
    assert all(V.digest(ROOT/p) == h for p,h in gaps.items())
    for n in (1,2):
        smoke = read(BASE / f'audit/G9J_pilot2_offline_tool_annotator{n}.json')
        assert smoke['provenance'] == 'AUTOMATION_TEST_NOT_HUMAN' and smoke['passed'] and smoke['rows'] == 335
        assert smoke['offline'] and smoke['import_roundtrip'] and smoke['export_schema']
        assert not smoke['page_errors'] and not smoke['external_requests']
    duplicate = read(BASE / 'audit/G9J_pilot2_duplicate_candidates.json')
    pairs = []
    for a,b in combinations(report['rows'],2):
        dist = (int(a['package_phash'],16)^int(b['package_phash'],16)).bit_count()
        if a['annotator1_sha256'] == b['annotator1_sha256'] or dist <= 10:
            pairs.append(dict(ids=[a['item_id'],b['item_id']],hamming=dist,exact_bytes=a['annotator1_sha256']==b['annotator1_sha256'],status='CANDIDATE_NOT_PROOF'))
    assert pairs == duplicate['within_pilot2']
    split = read(BASE / 'audit/G9J_pilot2_dataset_split_audit.json')
    parts = read(ROOT / 'ml/runs/G9/stageJ/out/j_partitions.json')['items']
    merged = {k:dict(v) for k,v in parts.items()}
    for k,v in read(ROOT / 'ml/runs/G9/stageJ/out/gaps/j2_candidates.json').items():
        assert k not in merged
        merged[k] = dict(v,artist=v.get('author',''),group=k)
    for v in merged.values():
        if v['source'].startswith('commons'):
            v['source'] = 'commons'
    fresh_split = H.audit_splits(merged)
    assert fresh_split['conflicts'] == split['conflicts'] and fresh_split['quarantine_keys'] == split['quarantine_keys']
    zip_checked = False
    if args.pack1:
        packs = [H.inspect_pack(p) for p in (args.pack1,args.pack2)]
        for n,p in enumerate(packs):
            assert p['sha256'] == report['packages'][n]['sha256']
            assert p['pack_id'] == 'G9J-pilot2' and p['copy'] == f'annotator{n+1}'
            assert p['count'] == 335 and set(p['ids']) == expected and len(p['ids']) == len(set(p['ids']))
            assert p['crc_ok'] and not p['corrupt_images'] and not p['duplicate_ids']
            assert p['order_matches_fallback'] and p['fallback_unlabelled']
            assert p['export_columns'] == V.COLUMNS and not p['offline_external_resources']
            for i,iid in enumerate(p['ids'],1):
                assert i == integrity[iid][f'annotator{n+1}_order']
                assert p['images'][iid]['sha256'] == integrity[iid][f'annotator{n+1}_sha256']
        assert packs[0]['ids'] != packs[1]['ids'] and packs[0]['images'] == packs[1]['images']
        zip_checked = True
    checksum_count = 0
    manifest = BASE / 'SHA256SUMS.txt'
    if manifest.exists():
        for line in manifest.read_text(encoding='utf-8').splitlines():
            expected_hash, name = line.split('  ',1)
            p = (BASE / name).resolve()
            assert p.is_relative_to(BASE) and V.digest(p) == expected_hash, name
            checksum_count += 1
    result = dict(status='PASS',provenance=V.AI_MARKER,rows=335,columns=15,stable_ids='PASS',
                  original_display_indices='PASS',packaged_image_hashes='PASS',saved_notes_tags_and_subtypes='PASS',
                  queue_rows=233,high_priority=77,csv_sha256=ai['sha256'],known_ai_registry_path=str(ai_path.relative_to(ROOT)),
                  frozen_inputs_preserved=len(frozen['git_lf_sha256']),j2_gap_artifacts_preserved=len(gaps),
                  supplied_zip_recheck=zip_checked,checksums_checked=checksum_count,stored_metadata_cross_split_conflicts=len(split['conflicts']),
                  earlier_reference_hashes_revalidated=False,holdout_content_opened=False,
                  human_verified_images=0,kappa=None,H3='BLOCKED',training_started=False,
                  limitation='Consistency and integrity checks do not measure subjective label accuracy or establish human verification.')
    if args.output:
        H.write_json(args.output,result)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
