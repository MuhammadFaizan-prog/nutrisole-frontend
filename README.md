# qa-models-j7 (QA model assets only; orphan branch, never merge)

ONNX weights for the NutriSole Android QA APK (G9 Stage J7). `.github/workflows/android-qa-apk.yml` on `cv-gauntlet-device`
downloads `models/*.onnx` from this branch at build time, checks size + SHA-256 against `native/src/cv/device/models.ts`, and
bundles them as APK assets. Kept on this separate orphan branch so the weights are never part of the cv-gauntlet-device /
cv-gauntlet / main history. Not a product release; nothing is deployed.

| file | bytes | sha256 | origin | licence |
|---|---|---|---|---|
| models/det_yolo11n_640_raw.onnx | 10600677 | c6fcb32a5fb2f51ba34e88ce9106a52d6bbd12ae385ca8361b292d54e3d340c1 | G3 detector k11_480, Ultralytics YOLO11n fine-tune (best.pt 29cc5212...) | AGPL-3.0 (Ultralytics): distributing these weights, or an APK containing them, carries AGPL-3.0 obligations unless an Ultralytics Enterprise licence is held |
| models/h2_mnv3s.onnx | 6133032 | 20898d7cdfc1f0580cdf3f58d6d3d63528b9c04178d4603b49dee4ba1b89a22e | G9 Stage H v2 verifier, timm mobilenetv3_small_100 ImageNet-pretrained fine-tune | timm (Apache-2.0); ImageNet-pretrained backbone |
