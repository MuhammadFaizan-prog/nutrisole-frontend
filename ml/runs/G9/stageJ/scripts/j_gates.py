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
