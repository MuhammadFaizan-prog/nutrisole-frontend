"""Table-grid OCR for the Lahore Market Committee / PAMRA daily retail rate list JPEGs.

Layout (checked on the 2026-10-12 fruit and vegetable lists): one bordered table with two
side-by-side blocks of 3 columns each, right-to-left: [name | grade1 (اول) | grade2 (دوم)]
on the right block and the same on the left block. Grid lines are found with morphology;
numbers are read with Tesseract (eng, digit whitelist), names with Tesseract urd (tessdata_best,
Apache-2.0). A cell that does not read as an integer or '-' is returned as None (never guessed).
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile

import cv2
import numpy as np

TESSDATA = os.environ.get("NUTRISOLE_TESSDATA", "/workspace/work/cv/tessdata")


def _lines(mask: np.ndarray, axis: int, min_frac: float) -> list[int]:
    proj = mask.sum(axis=axis) / 255.0
    L = mask.shape[axis]
    idx = np.where(proj > min_frac * L)[0]
    out, grp = [], []
    for i in idx:
        if grp and i - grp[-1] > 3:
            out.append(int(np.mean(grp))); grp = []
        grp.append(i)
    if grp:
        out.append(int(np.mean(grp)))
    return out


def find_grid(img_bgr: np.ndarray):
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    H, W = g.shape
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (W // 4, 1)))
    ver = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, H // 6)))
    ys = _lines(hor, 1, 0.5)
    xs = _lines(ver, 0, 0.3)
    rows = np.where(ver.sum(axis=1) > 0)[0]  # vertical extent of the table body
    if len(rows):
        top, bot = rows.min(), rows.max()
        ys = [y for y in ys if top - 6 <= y <= bot + 6]
    return xs, ys


def _tess(img: np.ndarray, lang: str, psm: int, whitelist: str | None = None) -> tuple[str, float]:
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "c.png")
        cv2.imwrite(p, img)
        cmd = ["tesseract", p, os.path.join(d, "o"), "--tessdata-dir", TESSDATA, "-l", lang, "--psm", str(psm)]
        if whitelist:
            cmd += ["-c", f"tessedit_char_whitelist={whitelist}"]
        cmd += ["-c", "tessedit_create_tsv=1"]
        subprocess.run(cmd, check=True, capture_output=True)
        words, confs = [], []
        for line in open(os.path.join(d, "o.tsv"), encoding="utf-8").read().splitlines()[1:]:
            f = line.split("\t")
            if len(f) == 12 and f[11].strip():
                words.append(f[11].strip()); confs.append(float(f[10]))
        return " ".join(words), (min(confs) / 100.0 if confs else 0.0)


def _prep(cell: np.ndarray, scale: float = 2.0) -> np.ndarray:
    g = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.copyMakeBorder(b, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)


def read_number(cell: np.ndarray) -> tuple[int | None, float, str]:
    """Return (value, confidence, raw). '-' (no price) -> (None, conf, '-')."""
    b = _prep(cell)
    ink = (b < 128).mean()
    if ink < 0.004:
        return None, 1.0, ""
    txt, conf = _tess(b, "eng", 7, "0123456789-")
    t = txt.replace(" ", "")
    if re.fullmatch(r"\d{1,5}", t):
        return int(t), conf, t
    if re.fullmatch(r"-+", t) or (t == "" and ink < 0.02):
        return None, conf, "-"
    return None, 0.0, t  # unreadable: dropped by the caller, never guessed


def read_name(cell: np.ndarray) -> tuple[str, float]:
    txt, conf = _tess(_prep(cell, 1.5), "urd", 7)
    if len(re.sub(r"[^\u0600-\u06FF]", "", txt)) < 2:  # short single words often come back empty at psm 7
        txt, conf = _tess(_prep(cell, 2.5), "urd", 8)
    return txt, conf


def parse_table(img_bgr: np.ndarray) -> dict:
    xs, ys = find_grid(img_bgr)
    if len(xs) < 7 or len(ys) < 3:
        return dict(ok=False, error=f"grid not found (xs={len(xs)}, ys={len(ys)})", rows=[])
    if len(xs) != 7:
        return dict(ok=False, error=f"expected 7 vertical rules (two 3-column blocks), found {len(xs)}", rows=[])
    rows = []
    pad = 4
    for r in range(1, len(ys) - 1):  # row 0 is the header
        y0, y1 = ys[r] + pad, ys[r + 1] - pad
        if y1 - y0 < 15:
            continue
        for block, (cn, c1, c2) in (("right", (5, 4, 3)), ("left", (2, 1, 0))):
            cell = lambda c: img_bgr[y0:y1, xs[c] + pad: xs[c + 1] - pad]
            name, nconf = read_name(cell(cn))
            g1, g1c, g1r = read_number(cell(c1))
            g2, g2c, g2r = read_number(cell(c2))
            rows.append(dict(row=r, block=block, name_ocr=name, name_conf=round(nconf, 3), grade1=g1, grade1_raw=g1r,
                             grade2=g2, grade2_raw=g2r, num_conf=round(min(g1c, g2c), 3)))
    return dict(ok=True, n_rows=len(ys) - 2, xs=xs, ys=ys, rows=rows)
