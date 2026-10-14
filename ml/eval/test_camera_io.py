"""Stage I tests: camera integration reference (camera_io) + H2 audit regression locks (class maps, ONNX contract, label mapping)."""
import json, math, os, re, sys, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval import camera_io as C
from ml.eval.verify import H2_CLASSES
from ml.eval.h2_labels import folder_to_class, H2_CLASSES as L_CLASSES
R = "/workspace/work/nutrisole"

def test_tap_identity_portrait_cover():
    # 1280x720 sensor buffer rotated 90 to a 1080x1920-pt portrait view: view centre -> frame centre
    assert C.tap_to_frame((540, 960), 1080, 1920, 1280, 720, 90) == (0.5, 0.5)
    # top-left of the visible preview (portrait) is bottom-left... in sensor coordinates after undoing the clockwise rotation
    x, y = C.tap_to_frame((0, 0), 1080, 1920, 1280, 720, 90); assert abs(x - 0.0) < 1e-9 and abs(y - 1.0) < 1e-9

def test_tap_letterbox_bar_is_none_and_mirror():
    assert C.tap_to_frame((10, 5), 1000, 1000, 1600, 900, 0, mode="letterbox") is None
    a = C.tap_to_frame((250, 500), 1000, 1000, 1600, 900, 0, mode="letterbox"); b = C.tap_to_frame((250, 500), 1000, 1000, 1600, 900, 0, True, "letterbox")
    assert abs(a[0] + b[0] - 1) < 1e-12 and a[1] == b[1]

def test_rotations_round_trip():
    for d in (0, 90, 180, 270):
        p = C.rotate_point(C.rotate_point((0.2, 0.7), d), (360 - d) % 360); assert abs(p[0] - 0.2) < 1e-12 and abs(p[1] - 0.7) < 1e-12

def test_frame_to_still_16x9_in_4x3():
    # 1920x1080 video is the full sensor width and the central 75% of a 4:3 sensor's height
    b = C.frame_to_still_box([0, 0, 1920, 1080], 1920, 1080, 4000, 3000)
    assert [round(v, 6) for v in b] == [0.0, 375.0, 4000.0, 2625.0]
    b = C.frame_to_still_box([960, 540, 960, 540], 1920, 1080, 4000, 3000); assert [round(v, 6) for v in b] == [2000.0, 1500.0, 2000.0, 1500.0]

def test_identity_crop_stageH_matches_closeup_crop_rect():
    from ml.eval.closeup import crop_rect
    for box in ([10.3, 20.7, 200.2, 260.9], [0, 0, 50, 50], [900, 600, 1000, 720]):
        a = C.identity_crop(box, 1000, 720); b = crop_rect(box, 1000, 720, 0.08); assert (a["x"], a["y"], a["w"], a["h"]) == (b["x"], b["y"], b["w"], b["h"])

def test_identity_crop_square_inside_and_square():
    for box in ([5, 5, 60, 300], [900, 600, 1000, 720], [0, 0, 1000, 720]):
        c = C.identity_crop(box, 1000, 720, "square"); assert c["w"] == c["h"] and c["x"] >= 0 and c["y"] >= 0 and c["x"] + c["w"] <= 1000 and c["y"] + c["h"] <= 720

def test_h2_input_shape_and_close_to_cv2_path():
    import cv2
    rng = np.random.default_rng(0); img = rng.integers(0, 256, (300, 200, 3), np.uint8)
    x = C.h2_input(img); assert x.shape == (1, 3, 224, 224) and x.dtype == np.float32
    # constant image -> constant normalised value per channel
    k = C.h2_input(np.full((50, 80, 3), 128, np.uint8), "square"); assert np.allclose(k[0, 0], (128 / 255 - 0.485) / 0.229, atol=1e-5)
    # upscaling path equals cv2 INTER_LINEAR (half-pixel centres) up to float error
    sm = rng.integers(0, 256, (40, 60, 3), np.uint8); a = C.resize_bilinear(sm, 90, 70); b = cv2.resize(sm.astype(np.float32), (90, 70), interpolation=cv2.INTER_LINEAR)
    assert np.abs(a - b).max() < 1e-3

def test_model_io_contract():
    ok = dict(inputs=[dict(name="images", shape=["n", 3, 224, 224], type="tensor(float)")], outputs=[dict(name="probs", shape=["n", 13], type="tensor(float)")])
    assert C.check_model_io("h2", ok) == []
    bad = dict(inputs=[dict(name="images", shape=[1, 224, 224, 3])], outputs=[dict(name="probs", shape=[1, 12])])
    assert len(C.check_model_io("h2", bad)) >= 2

def test_h2_onnx_contract_if_present():
    p = "/workspace/work/g9h/h2/h2_mnv3s.onnx"
    if not os.path.exists(p): return
    import onnx
    g = onnx.load(p).graph; assert g.node[-1].op_type == "Softmax"
    meta = dict(inputs=[dict(name=i.name, shape=[d.dim_param or d.dim_value for d in i.type.tensor_type.shape.dim], type="float32") for i in g.input],
                outputs=[dict(name=o.name, shape=[d.dim_param or d.dim_value for d in o.type.tensor_type.shape.dim], type="float32") for o in g.output])
    assert C.check_model_io("h2", meta) == []

def test_class_maps_agree_everywhere():
    k = open(f"{R}/ml/runs/G9/stageH/kaggle/k_h2v2/run.py").read().splitlines()
    kc = json.loads(next(l for l in k if l.startswith("C = [")).split("=", 1)[1].replace("'", '"'))
    ts = open(f"{R}/native/src/cv/pipeline/verify.ts").read(); tc = json.loads(re.search(r"H2_CLASSES = (\[[^\]]+\])", ts).group(1).replace("'", '"'))
    g = open(f"{R}/ml/runs/G9/stageG/scripts/g_models.py").read(); gc = json.loads(re.search(r'^N = (\[.*\])', g, re.M).group(1))
    assert kc == H2_CLASSES == tc == L_CLASSES and gc == H2_CLASSES[:12]

def test_folder_mapping_does_not_relabel_lookalikes():
    assert folder_to_class("Mangostan 1") == "unknown" and folder_to_class("Potato Sweet 1") == "unknown"
    assert folder_to_class("Kumsquats 1") is None and folder_to_class("Grapefruit Pink 1") is None
    assert folder_to_class("Mango Red 1") == "mango" and folder_to_class("Apple Granny Smith 1") == "apple" and folder_to_class("Tomato Cherry Red 1") == "tomato"
    assert folder_to_class("Pepper Red 1") == "capsicum" and folder_to_class("Pepino 1") == "unknown" and folder_to_class("Pineapple 1") == "unknown"
    assert folder_to_class("Carrot 1") == "carrot" and folder_to_class("Orange 1") == "citrus" and folder_to_class("Banana Lady Finger 1") == "banana"
    # the Stage H prefix rule DID relabel these (documented regression, kernel left unchanged)
    old = lambda n: next((c for pre, c in [("Mango", "mango"), ("Potato", "potato")] if n.startswith(pre)), None)
    assert old("Mangostan 1") == "mango" and old("Potato Sweet 1") == "potato"

def test_targeted_occlusion_cues_only_add_rejections():
    from ml.eval.occlusion import targeted_reasons, targeted_cues, DEFAULT_TARGETED
    t = dict(sideTouch=0.99, skinFrac=0.9, specFrac=0.9, hullGap=5.0); assert targeted_reasons(t) == [] and targeted_reasons(t, DEFAULT_TARGETED) == []
    assert targeted_reasons(t, dict(maxSideTouch=0.5)) == ["cut_by_box"]
    m = np.zeros((96, 96), bool); m[20:76, 20:76] = True; img = np.full((96, 96, 3), 90, np.uint8)
    c = targeted_cues(img, m); assert set(c) == {"sideTouch", "skinFrac", "specFrac", "hullGap"} and c["sideTouch"] == 0.0
    m2 = np.zeros((96, 96), bool); m2[20:96, 10:86] = True; assert targeted_cues(img, m2)["sideTouch"] > 0.7  # item cut by the bottom of the box

def test_camera_fixture_replays():
    p = f"{R}/ml/eval/fixtures/camera_parity.json"
    if not os.path.exists(p): return
    F = json.load(open(p))
    for c in F["taps"]:
        r = C.tap_to_frame(tuple(c["tap"]), *c["view"], *c["frame"], c["rotation"], c["mirrored"], c["mode"])
        assert (r is None and c["out"] is None) or (r is not None and all(abs(a - b) < 1e-9 for a, b in zip(r, c["out"])))
    for c in F["plans"]:
        r = C.still_crop_plan(tuple(c["tap"]), c["view"], c["frame"], c["still"], c["boxes"], c["rotation"], c["mirrored"], c["mode"], c["cropMode"])
        assert (r is None) == (c["out"] is None) and (r is None or r["crop"] == c["out"]["crop"])
