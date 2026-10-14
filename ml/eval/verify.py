"""G9 Stage H close-up identity verification + Stage H close-up decision. EXACT mirror: native/src/cv/pipeline/verify.ts
(parity: native/tests/cvVerify.test.ts replays ml/eval/fixtures/verify_parity.json).

Order (brief): wide G3 identification -> user taps -> INDEPENDENT identity verification on the full-res crop (H2 close-up classifier
with explicit unknown/reject; optional H1 veto = G3 re-run on the crop) -> occlusion / visibility check -> Stage G quality gate ->
(grading model). Uncertain or contradictory identity -> "Unable to identify"; it is never passed to the grader. The user-assisted
fallback (confirm a suggested category) unlocks the category reference price only, never a grade, and is not identity accuracy."""
from __future__ import annotations

H2_CLASSES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum", "unknown"]
UNKNOWN = 12
CITRUS_PAIR = {3, 6}
DEFAULT_VERIFY = dict(policy="P-a", tau=0.6, margin=0.2, maxUnknown=0.3, h1VetoScore=0.5, suggestMinP=0.15)
FROZEN_VERIFY = dict(policy="P-a", tau=0.4, margin=0.0, maxUnknown=0.5, h1VetoScore=0.5, suggestMinP=0.15)  # Stage H frozen pick on TUNE only (H2 v2; selection INFEASIBLE -> fallback rule; see G9_stageH.md)


def h2_decision(probs, p=None):
    P = {**DEFAULT_VERIFY, **(p or {})}
    sup = list(probs[:UNKNOWN]); order = sorted(range(UNKNOWN), key=lambda i: -sup[i]); top, second = order[0], order[1]
    pu = float(probs[UNKNOWN]); pt = float(sup[top]); ps = float(sup[second])
    sugg = [i for i in order[:2] if sup[i] >= P["suggestMinP"]]
    if pu >= P["maxUnknown"] or pu > pt: return dict(accept=False, reason="close_up_unknown", top=top, suggestions=sugg)
    if pt < P["tau"]: return dict(accept=False, reason="close_up_uncertain", top=top, suggestions=sugg)
    if pt - ps < P["margin"]: return dict(accept=False, reason="close_up_ambiguous", top=top, suggestions=sugg)
    return dict(accept=True, classId=top, p=round(pt, 6), suggestions=sugg)


def verify_identity(wide, h1, h2_probs, p=None):
    """wide: {status, classId?} from id_policy; h1: None or {classId, score, hasWide} (G3 on the crop: best box at the crop centre, and
    whether any box of the wide class was found); h2_probs: 13 probabilities. Returns {status: verified|unable, ...}."""
    P = {**DEFAULT_VERIFY, **(p or {})}
    if P["policy"] == "H0":
        return dict(status="verified", classId=wide["classId"], evidence="wide_only") if wide.get("status") == "identified" else dict(status="unable", reason="not_identified_wide", suggestions=[])
    d = h2_decision(h2_probs, P)
    if P["policy"] == "P-c":  # H1 only (comparison arm; cannot be picked)
        if wide.get("status") != "identified": return dict(status="unable", reason="not_identified_wide", suggestions=d["suggestions"])
        if h1 and h1["classId"] == wide["classId"] and h1["score"] >= P["h1VetoScore"]: return dict(status="verified", classId=wide["classId"], evidence="wide+h1")
        return dict(status="unable", reason="h1_not_confirmed", suggestions=d["suggestions"])
    if P["policy"] == "H2-only":  # H2 alone, no wide agreement needed (comparison arm)
        return dict(status="verified", classId=d["classId"], evidence="h2") if d["accept"] else dict(status="unable", reason=d["reason"], suggestions=d["suggestions"])
    if wide.get("status") != "identified": return dict(status="unable", reason="not_identified_wide", suggestions=d["suggestions"])
    if not d["accept"]: return dict(status="unable", reason=d["reason"], suggestions=d["suggestions"])
    if d["classId"] != wide["classId"]:
        r = "citrus_family_contradiction" if {d["classId"], wide["classId"]} == CITRUS_PAIR else "close_up_contradicts_wide"
        return dict(status="unable", reason=r, suggestions=[i for i in [wide["classId"], d["classId"]]])
    if P["policy"] == "P-b" and h1 and h1["classId"] != wide["classId"] and h1["score"] >= P["h1VetoScore"] and not h1.get("hasWide", False):
        return dict(status="unable", reason="h1_contradicts", suggestions=[wide["classId"], h1["classId"]])
    return dict(status="verified", classId=wide["classId"], evidence="wide+h2" + ("+h1" if P["policy"] == "P-b" else ""))


def user_confirm(v, chosen):
    """User-assisted fallback. chosen: a class id the user picked from v['suggestions'], or None ('something else')."""
    if v["status"] == "verified": return v
    if chosen is None or chosen not in v.get("suggestions", []) or chosen == UNKNOWN: return dict(status="unable", reason="user_declined", suggestions=[])
    return dict(status="user_confirmed", classId=chosen, evidence="user")


def part_agreement(half_probs, class_id, min_p=0.3):
    """Fraction of half-crops (left/right/top/bottom) whose H2 top class is class_id with p >= min_p and not unknown."""
    if not half_probs: return 1.0
    ok = 0
    for pr in half_probs:
        top = max(range(len(pr)), key=lambda i: pr[i])
        ok += top == class_id and pr[top] >= min_p
    return round(ok / len(half_probs), 6)


def stageh_decision(verify, occ_reasons, gate_status, gate_reasons, grade_display_enabled=False):
    """Final close-up outcome. Identity first, then occlusion, then the Stage G gate. In Stage H grade_display_enabled is False:
    even a passing gate yields 'quality_check_unavailable' (no A/B/C shown), and the price is the category line only when verified."""
    if verify["status"] not in ("verified", "user_confirmed"):
        return dict(outcome="unable_to_identify", identity=None, gradeShown=None, priceKind=None, reasons=[verify.get("reason", "unable")])
    ident = dict(classId=verify["classId"], source=verify["status"])
    if verify["status"] == "user_confirmed":
        return dict(outcome="category_confirmed_by_user", identity=ident, gradeShown=None, priceKind="category_reference", reasons=["user_confirmed_category"])
    if occ_reasons: return dict(outcome="not_graded", identity=ident, gradeShown=None, priceKind="category_reference", reasons=list(occ_reasons))
    if gate_status != "graded": return dict(outcome="not_graded", identity=ident, gradeShown=None, priceKind="category_reference", reasons=list(gate_reasons))
    if not grade_display_enabled:
        return dict(outcome="quality_check_unavailable", identity=ident, gradeShown=None, priceKind="category_reference", reasons=["grades_not_enabled"])
    return dict(outcome="graded", identity=ident, gradeShown="internal_only", priceKind="category_reference", reasons=[])
