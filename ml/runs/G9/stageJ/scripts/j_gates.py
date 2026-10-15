"""G9 Stage J: frozen decision helpers for the H3 evaluation gates (G9_stageJ_readiness.md section 4). Standard library only.
A gate is PASS / FAIL / UNCERTAIN. UNCERTAIN means the 95% Wilson interval still straddles the threshold region: collect more eval items
(the same frozen model, the same rules) before any pass/fail claim."""
from __future__ import annotations
import math

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

def at_least(k: int, n: int, thr: float, margin: float = 0.10) -> str:
    """Rate must be >= thr. PASS: point >= thr and lower bound >= thr - margin. FAIL: upper bound < thr. Else UNCERTAIN."""
    lo, hi = wilson(k, n)
    if n and k / n >= thr and lo >= thr - margin: return "PASS"
    if hi < thr: return "FAIL"
    return "UNCERTAIN"

def at_most(k: int, n: int, thr: float, upper_cap: float) -> str:
    """Rate must be <= thr. PASS: point <= thr and upper bound <= upper_cap. FAIL: lower bound > thr. Else UNCERTAIN."""
    lo, hi = wilson(k, n)
    if n and k / n <= thr and hi <= upper_cap: return "PASS"
    if lo > thr: return "FAIL"
    return "UNCERTAIN"

def zero_required(k: int) -> str: return "PASS" if k == 0 else "FAIL"


# Stage J5: what each provenance tier can do against the FROZEN gates (G9_stageJ_readiness.md, G9_stageJ3_H3_frozen_plan_v2.md).
# Nothing here loosens a gate: a tier that is not independent double annotation can satisfy none of R1-R4 / T1-T4, so it cannot unlock H3.
FROZEN_GATES = {
    "R1": "kappa(class) >= 0.85 and kappa(supported) >= 0.80 between two independent annotators on pilot and pilot2",
    "R2": ">= 20 clean supported per priority class, >= 100 total, >= 60 negatives among ADJUDICATED (verified) J-eval items",
    "R3": "100% of items labelled by BOTH annotators; every disagreement / uncertain / cut-bag mismatch adjudicated by a third human",
    "R4": "verified_manifest + .sha256 committed before any model sees a J-eval image",
    "T1": ">= 150 human-verified clean J-train images per priority class from >= 2 sources",
    "T2": ">= 150 verified real-photo negatives in J-train",
    "T3": ">= 10 verified clean J-dev items per priority class",
    "T4": "kappa(class) >= 0.85 on the training batches, adjudicated as R3",
    "T5": "licence + split separation + pHash <= 10 against all earlier sets; no J-eval / eval-only source in training",
    "GO": "user-written h3/USER_TRAINING_GO.json naming the plan and verified-manifest hashes",
}


def tier_gate_report(provenance: str) -> dict:
    """Per-gate verdict for a labelling record of this provenance tier, before any data-count is considered."""
    import j_agree as JA
    t = JA.PROVENANCE_TIERS.get(provenance, {})
    indep = bool(t.get("independent_double_annotation")); out = {}
    why_no = "needs two independent blind annotators (HUMAN_INDEPENDENT); this tier has one non-blind reviewer"
    for g in ("R1", "R3", "T4"):
        out[g] = dict(verdict="ELIGIBLE" if indep else "FAIL", rule=FROZEN_GATES[g], reason="" if indep else why_no + "; kappa is undefined (no second label set)" if g != "R3" else why_no)
    for g in ("R2", "T1", "T2", "T3"):
        out[g] = dict(verdict="ELIGIBLE" if t.get("verified_manifest") else "FAIL", rule=FROZEN_GATES[g],
                      reason="" if t.get("verified_manifest") else "counts only from verified (independent + adjudicated) manifests; this tier produces none")
    out["R4"] = dict(verdict="ELIGIBLE" if t.get("verified_manifest") else "FAIL", rule=FROZEN_GATES["R4"],
                     reason="" if t.get("verified_manifest") else "no verified manifest exists to freeze")
    out["T5"] = dict(verdict="NOT_PROVENANCE_DEPENDENT", rule=FROZEN_GATES["T5"], reason="checked separately on the data (keys, owners, pHash)")
    out["GO"] = dict(verdict="FAIL", rule=FROZEN_GATES["GO"], reason="only the user writes it, and only after R1-R4/T1-T5 pass")
    out["E1-E8"] = dict(verdict="NOT_RUN", rule="H3 evaluation gates", reason="no H3 run; eval needs human-verified J-eval labels first")
    unlock = indep and all(out[g]["verdict"] == "ELIGIBLE" for g in ("R1", "R2", "R3", "R4"))
    out["summary"] = dict(provenance=provenance, kappa_evidence=bool(t.get("kappa_evidence")), counts_as_double_annotation=indep,
                          can_unlock_h3_eval_gate=unlock, can_feed_training_gates=bool(t.get("counts_for_training_gates")),
                          frozen_gates_allow_single_reviewer_tier=False)
    return out
