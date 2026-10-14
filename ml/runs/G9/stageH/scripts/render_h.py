"""Stage H demo video: H0 (Stage G pipeline) vs H-final on (1) an occluded apple, (2) a wrong-ID case, (3) an unsupported item, (4) the
user-confirm fallback. Every caption is the real output of the harness (out/demo_cases.json, built by h_demo_cases.py). Licensed Commons
stills; credits frame. Output: out/video/g9h_demo_H0_vs_H.mp4. Usage: render_h.py"""
import json, os, subprocess, cv2, numpy as np
B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"; V = f"{B}/video"; os.makedirs(V, exist_ok=True); F = "/workspace/work/g9h/frames"; os.makedirs(F, exist_ok=True)
D = json.load(open(f"{B}/demo_cases.json")); W, H = 1280, 720; FPS = 15
FONT = cv2.FONT_HERSHEY_SIMPLEX
def text(im, s, xy, sc=0.7, col=(255, 255, 255), th=2, bg=None):
    (tw, tht), _ = cv2.getTextSize(s, FONT, sc, th)
    if bg is not None: cv2.rectangle(im, (xy[0] - 6, xy[1] - tht - 8), (xy[0] + tw + 6, xy[1] + 8), bg, -1)
    cv2.putText(im, s, xy, FONT, sc, col, th, cv2.LINE_AA)
def wrap(s, n=44):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return out + ([cur] if cur else [])
def fit(img, w, h):
    ih, iw = img.shape[:2]; s = min(w / iw, h / ih); r = cv2.resize(img, (int(iw * s), int(ih * s)), interpolation=cv2.INTER_AREA)
    c = np.full((h, w, 3), 30, np.uint8); y, x = (h - r.shape[0]) // 2, (w - r.shape[1]) // 2; c[y:y + r.shape[0], x:x + r.shape[1]] = r; return c
def panel(img, title, lines, colour, sub):
    p = np.full((H - 90, W // 2, 3), 22, np.uint8); text(p, title, (20, 40), 0.85, (255, 255, 255), 2)
    p[60:60 + 380, 20:W // 2 - 20] = fit(img, W // 2 - 40, 380)
    y = 480
    for i, l in enumerate(lines):
        for j, ww in enumerate(wrap(l, 46)):
            text(p, ww, (24, y), 0.68 if i == 0 else 0.58, colour if i == 0 else (230, 230, 230), 2 if i == 0 else 1); y += 30 if i == 0 else 26
    if sub: text(p, sub, (24, H - 110), 0.5, (170, 170, 170), 1)
    return p
def frame(case, t):
    im = np.full((H, W, 3), 12, np.uint8); text(im, case["title"], (24, 50), 0.95, (255, 255, 255), 2)
    text(im, case["subtitle"], (24, 80), 0.55, (190, 190, 190), 1)
    a = cv2.imread(case["img_h0"]); b = cv2.imread(case["img_h"])
    show = t > 1.2
    pa = panel(a, "H0  Stage G pipeline", case["h0"] if show else ["..."], (80, 80, 255) if case.get("h0_bad") else (120, 220, 120), case.get("h0_sub", ""))
    pb = panel(b, "H  final (verify + occlusion)", case["h"] if show else ["..."], (120, 220, 120), case.get("h_sub", ""))
    im[90:, :W // 2] = pa; im[90:, W // 2:] = pb; cv2.line(im, (W // 2, 90), (W // 2, H), (80, 80, 80), 2)
    return im
n = 0
def emit(img, secs):
    global n
    for _ in range(int(secs * FPS)): cv2.imwrite(f"{F}/f{n:05d}.png", img); n += 1
for f in os.listdir(F): os.remove(f"{F}/{f}")
t = np.full((H, W, 3), 12, np.uint8)
for i, l in enumerate(["NutriSole CV  G9 Stage H", "Close-up identity verification and occlusion safety", "H0 = Stage G pipeline   |   H = H0 + independent close-up identity check + occlusion check",
                       "DEV material only. Agent-labelled, exploratory. No A/B/C grade is shown in the app."]):
    text(t, l, (60, 220 + 60 * i), 1.1 if i == 0 else 0.7, (255, 255, 255) if i == 0 else (210, 210, 210), 2 if i == 0 else 1)
emit(t, 3)
for c in D["cases"]:
    for k in range(int(6.5 * FPS)): cv2.imwrite(f"{F}/f{n:05d}.png", frame(c, k / FPS)); n += 1
cr = np.full((H, W, 3), 12, np.uint8); text(cr, "Credits (Wikimedia Commons, per-file licences)", (40, 60), 0.8)
for i, l in enumerate(D["credits"][:14]): text(cr, l[:120], (40, 110 + 36 * i), 0.5, (220, 220, 220), 1)
text(cr, "Occluders are synthetic overlays (Stage H suite). Prices: official reference only, never this seller's price.", (40, H - 40), 0.5, (180, 180, 180), 1)
emit(cr, 4)
out = f"{V}/g9h_demo_H0_vs_H.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{F}/f%05d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", out], check=True)
print(out, n / FPS, "s")
