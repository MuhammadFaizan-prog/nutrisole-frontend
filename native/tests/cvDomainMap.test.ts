// G9 Stage J6: canonical CV class <-> nutrition/pricing domain map (src/cv/domainMap.ts).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CV_DOMAIN, DOMAIN_IDS, checkDomainMap, cvClassOf, domainIdForClassIndex, domainIdForCvClass, cvClassForDomain, priceAppClassForCvClass } from '../src/cv/domainMap.ts';
import { V1_CLASSES } from '../src/cv/models/labels.ts';
import { H2_CLASSES } from '../src/cv/pipeline/verify.ts';
import { nutritionFor, nutritionForCv, SHOWCASE } from '../src/cv/data/nutrition.ts';
import { lahoreProducePrice, lahoreProducePriceForCv, SHOWCASE_APP_CLASS, SHOWCASE_CLASSES } from '../src/cv/prices/lookup.ts';
import { FDC_SHOWCASE } from '../src/cv/data/nutritionFdc.ts';
import type { PriceSource } from '../src/cv/prices/reference.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const rd = (rel: string): string => readFileSync(resolve(HERE, rel), 'utf8');
const F = JSON.parse(rd('../../ml/prices/fixtures/reference_parity.json'));
const SRC: PriceSource[] = F.sources;
const TODAY = '2026-10-12';

test('table is valid and model output indexes are untouched', () => {
  assert.deepEqual(checkDomainMap(), []);
  assert.deepEqual(V1_CLASSES.map((c) => c.id), [...Array(12).keys()]);
  assert.equal(H2_CLASSES.length, 13); assert.equal(H2_CLASSES[12], 'unknown');
  for (const c of V1_CLASSES) { assert.equal(cvClassOf('g3', c.id), c.classId); assert.equal(cvClassOf('h2', c.id), c.classId); }
  assert.equal(cvClassOf('h2', 12), null); assert.equal(cvClassOf('g3', 12), null); assert.equal(cvClassOf('g3', -1), null); assert.equal(cvClassOf('g3', 1.5), null);
});

test('citrus (id 3) -> citrus_orange; lemon_lime (id 6) never becomes orange; unknown -> null', () => {
  assert.equal(domainIdForClassIndex('g3', 3), 'citrus_orange'); assert.equal(domainIdForClassIndex('h2', 3), 'citrus_orange');
  assert.equal(domainIdForClassIndex('g3', 6), null); assert.equal(domainIdForCvClass('lemon_lime'), null);
  assert.equal(domainIdForClassIndex('h2', 12), null); assert.equal(domainIdForCvClass('citrus_orange'), null); // domain id is not a CV class
  assert.equal(domainIdForCvClass(null), null); assert.equal(domainIdForCvClass('persimmon'), null);
  for (const d of DOMAIN_IDS) assert.equal(domainIdForCvClass(cvClassForDomain(d)), d);
});

test('matches the CSV class map, the FDC records, the showcase lists and the Stage J annotation map', () => {
  const csv = rd('../../ml/data/class_map.csv').split('\n').filter((l: string) => l.startsWith('nutrisole,'));
  assert.equal(csv.length, 12);
  for (const l of csv) { const p = l.split(','); assert.equal(cvClassOf('g3', Number(p[4])), p[3]); }
  assert.deepEqual([...DOMAIN_IDS].sort(), Object.keys(FDC_SHOWCASE).sort());
  assert.deepEqual([...DOMAIN_IDS].sort(), [...SHOWCASE].sort()); assert.deepEqual([...DOMAIN_IDS].sort(), [...SHOWCASE_CLASSES].sort());
  assert.deepEqual(SHOWCASE_APP_CLASS, { apple: 'apple', banana: 'banana', citrus_orange: 'citrus', tomato: 'tomato', carrot: 'carrot' });
  const ja = rd('../../ml/runs/G9/stageJ/scripts/j_agree.py');
  const m = ja.match(/^CLASS13 = (\{.*\})$/m); assert.ok(m);
  const class13 = JSON.parse(m![1]) as Record<string, string>;
  for (const [d, cv] of Object.entries(class13)) assert.equal(domainIdForCvClass(cv), d);
});

test('price app_class equals the CV class for all 12 (ml/prices lexicon keys)', () => {
  const lex = rd('../../ml/prices/lexicon.py');
  const used = new Set([...lex.matchAll(/,\s*"([a-z_]+)",\s*"(?:kg|dozen|piece)"\)/g)].map((x) => x[1]));
  for (const c of used) assert.equal(priceAppClassForCvClass(c), c, c);
  for (const c of Object.keys(CV_DOMAIN)) assert.equal(priceAppClassForCvClass(c), c);
  assert.equal(priceAppClassForCvClass('unknown'), null);
});

test('CV-consuming nutrition and price lookups go through the map', () => {
  assert.equal(nutritionFor('citrus'), null); // the raw domain lookup is unchanged
  const r = nutritionForCv('citrus')!; assert.ok(r); assert.equal(r.produceType, 'citrus_orange'); assert.equal(r.source.fdcId, 169097);
  assert.equal(nutritionForCv('lemon_lime'), null); assert.equal(nutritionForCv(null), null);
  assert.equal(r.basis, 'per 100 g raw edible portion');
  assert.deepEqual(lahoreProducePriceForCv('citrus', SRC, TODAY), lahoreProducePrice('citrus_orange', SRC, TODAY));
  const ll = lahoreProducePriceForCv('lemon_lime', SRC, TODAY); assert.equal(ll.status, 'unavailable');
  assert.equal(lahoreProducePriceForCv('apple', [], TODAY).status, 'unavailable'); // no supplied source -> no price, never invented
});

test('no scattered citrus/citrus_orange string replaces in app source', () => {
  const root = resolve(HERE, '../src/'); const hits: string[] = [];
  const walk = (d: string) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else if (/\.tsx?$/.test(f)) {
    const s = readFileSync(p, 'utf8'); if (/replace\([^)]*citrus|citrus_orange['"]?\s*:\s*['"]citrus['"]/.test(s)) hits.push(p); } } };
  walk(root);
  assert.deepEqual(hits.filter((p) => !p.endsWith('domainMap.ts')), []);
});
