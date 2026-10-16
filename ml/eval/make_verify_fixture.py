"""Generate ml/eval/fixtures/verify_parity.json: Python outputs of the Stage H identity / occlusion / decision / display functions that
native/tests/cvVerify.test.ts must reproduce exactly. Deterministic (seed 7)."""
import json, random, sys
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.verify import h2_decision, verify_identity, user_confirm, part_agreement, stageh_decision, DEFAULT_VERIFY, FROZEN_VERIFY
from ml.eval.occlusion import occlusion_reasons, DEFAULT_OCC, FROZEN_OCC
rng = random.Random(7)
def probs(peak=None, unk=None):
    v = [rng.random() ** 3 for _ in range(13)]
    if peak is not None: v[peak] += rng.uniform(0, 8)
    if unk is not None: v[12] += unk
    s = sum(v); return [round(x / s, 6) for x in v]
cases = dict(h2=[], verify=[], confirm=[], part=[], occ=[], decision=[])
for i in range(60):
    p = probs(rng.choice([None, rng.randrange(12)]), rng.choice([None, 0, 2.0])); P = rng.choice([DEFAULT_VERIFY, FROZEN_VERIFY, dict(DEFAULT_VERIFY, tau=0.8, margin=0.4)])
    cases["h2"].append(dict(probs=p, p=P, out=h2_decision(p, P)))
for i in range(120):
    w = rng.randrange(12); p = probs(rng.choice([w, w, rng.randrange(12), None]), rng.choice([None, None, 1.5]))
    wide = rng.choice([dict(status="identified", classId=w), dict(status="identified", classId=w), dict(status="unable", reason="low confidence")])
    h1 = rng.choice([None, dict(classId=w, score=round(rng.random(), 3), hasWide=True), dict(classId=rng.randrange(12), score=round(rng.random(), 3), hasWide=rng.random() < 0.3)])
    P = dict(rng.choice([DEFAULT_VERIFY, FROZEN_VERIFY]), policy=rng.choice(["H0", "P-a", "P-b", "P-c", "H2-only"]))
    v = verify_identity(wide, h1, p, P); cases["verify"].append(dict(wide=wide, h1=h1, probs=p, p=P, out=v))
    ch = rng.choice([None, 12] + v.get("suggestions", []) + [rng.randrange(12)])
    cases["confirm"].append(dict(v=v, chosen=ch, out=user_confirm(v, ch)))
for i in range(30):
    hp = [probs(rng.choice([None, 3, 7])) for _ in range(rng.choice([0, 4]))]; c = rng.randrange(12); mp = rng.choice([0.3, 0.5])
    cases["part"].append(dict(halves=hp, classId=c, minP=mp, out=part_agreement(hp, c, mp)))
for i in range(60):
    cu = dict(solidity=round(rng.random(), 4), ellipseIoU=round(rng.random(), 4), straightFrac=round(rng.random(), 4), borderFrac=round(rng.random(), 4),
              segAgree=round(rng.random(), 4), flatFrac=round(rng.random(), 4), colourSplit=round(rng.random() * 60, 3))
    if rng.random() < 0.6: cu["partAgree"] = rng.choice([0, 0.25, 0.5, 0.75, 1.0])
    P = rng.choice([DEFAULT_OCC, FROZEN_OCC])
    cases["occ"].append(dict(cues=cu, p=P, out=occlusion_reasons(cu, P)))
for v in [dict(status="unable", reason="close_up_unknown", suggestions=[]), dict(status="verified", classId=1, evidence="wide+h2"), dict(status="user_confirmed", classId=3, evidence="user")]:
    for occ in ([], ["outline_incomplete"]):
        for gs, gr in (("graded", []), ("pending", ["confirming"]), ("not_graded", ["blurry"])):
            for en in (False, True):
                cases["decision"].append(dict(v=v, occ=occ, gs=gs, gr=gr, en=en, out=stageh_decision(v, occ, gs, gr, en)))
json.dump(dict(frozen_verify=FROZEN_VERIFY, frozen_occ=FROZEN_OCC, **cases), open("/workspace/work/nutrisole/ml/eval/fixtures/verify_parity.json", "w"))
print({k: len(v) for k, v in cases.items()})
