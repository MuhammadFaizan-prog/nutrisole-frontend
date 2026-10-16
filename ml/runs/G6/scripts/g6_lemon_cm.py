# G6.1 lemon/lime vs citrus: confusion matrix of the G3 control on test_oiv7c (n=181) and test (n=557) at imgsz 480 (PyTorch CPU, conf 0.25 CM default, iou 0.7)
import json
from ultralytics import YOLO
m = YOLO("/workspace/work/nutrisole/ml/runs/G3/kaggle/nutrisole-g3-det-yolo11n-640/runs/det_yolo11n_640/weights/best.pt")
out = {}
for sp in ["test_oiv7c", "test"]:
    r = m.val(data="/workspace/work/cv/g4data/det_v4_eval.yaml", split=sp, imgsz=480, batch=8, device="cpu", conf=0.001, iou=0.7, plots=False, verbose=False, project="/workspace/work/cv/g6data/cm", name=sp, exist_ok=True)
    M = r.confusion_matrix.matrix.tolist(); N = list(r.names.values()) + ["background"]
    # rows = predicted, cols = true (ultralytics convention)
    out[sp] = dict(names=N, matrix_pred_x_true=M, note="ultralytics ConfusionMatrix (conf 0.25, iou 0.45 defaults), rows=pred cols=true")
json.dump(out, open("/workspace/work/nutrisole/ml/runs/G6/audit/g3_confusion_lemon_citrus.json", "w"))
for sp, d in out.items():
    N = d["names"]; M = d["matrix_pred_x_true"]; ci, li, bg = N.index("citrus"), N.index("lemon_lime"), len(N) - 1
    print(sp, "true lemon_lime -> pred lemon", M[li][li], "pred citrus", M[ci][li], "missed(bg)", M[bg][li], "| true citrus -> pred citrus", M[ci][ci], "pred lemon", M[li][ci], "missed", M[bg][ci])
