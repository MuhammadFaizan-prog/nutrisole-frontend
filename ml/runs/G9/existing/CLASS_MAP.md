# G9 existing models: class maps (fixed 2026-10-14 ~01:58 PKT, BEFORE any scoring)

Source of truth in code: `ml/eval/roboflow_adapter.py` (`CLASS_MAPS`, `EXPLICITLY_UNMAPPED`), tested by `ml/eval/test_roboflow_adapter.py`.
Rule: per box, argmax over the model's OWN classes; if that class is mapped it scores as the NutriSole class, otherwise the box is
ignored (logged as out-of-taxonomy). A box is never re-routed to a lower-scoring mapped class.

## snapml-4ubnx/veggies-and-fruits-balanced-0g1ss v1 (yolov5v6n, Roboflow 2.0 Fast, 416 fit-black-edges)
| source | NutriSole |
|---|---|
| Apple | apple |
| Banana | banana |
| Mango | mango |
| Orange | citrus |
| Lemon | lemon_lime |
| Pomegranate | pomegranate |
| Tomato | tomato |
| Potato | potato |
| Cucumber | cucumber |
| Carrot | carrot |
| Bell pepper | capsicum (OIV7 "Bell pepper" = whole bell pepper) |
| **Grapefruit** | **not counted** (brief) |
| Artichoke, Broccoli, Cabbage, Cantaloupe, Coconut, Common fig, Grape, Peach, Pear, Pineapple, Radish, Salad, Strawberry, Watermelon, Winter melon | ignored |

Coverage 11/12 (missing guava); showcase 5/5.

## calories/fruits-and-veg-2-x027v v2 (YOLOv8s, Ultralytics 8.0.196, 640 stretch). v2 is the only version with a trained model (v1 has none).
| source | NutriSole |
|---|---|
| apple | apple |
| banana | banana |
| mango | mango |
| orange | citrus |
| guava | guava |
| Tomato | tomato |
| Potato | potato |
| cucumber | cucumber |
| Capsicum | capsicum: 12/12 sampled training images (Roboflow search API, class Capsicum, offset 20) show whole green bell peppers |
| **Green Chili** | **unmapped** (brief: chilli is not capsicum) |
| **oren** | **unmapped** (brief). Note: 8/8 sampled "oren" training images show a whole orange; oren has 2,360 instances vs 270 for "orange", so the strict rule likely costs this model citrus recall |
| Bitter melon, Brinjal, Cabbage, Calabash, Cauliflower, Cherry, Garlic, Ginger, Kiwi, Lady finger, Onion, Sponge Gourd, avocado, dragon fruit, egg, peach, pear, pineapple, strawberry, sugar apple, watermelon | ignored |

Coverage 9/12 (missing pomegranate, lemon_lime, carrot); showcase 4/5 (no carrot). No lemon/lime class, so a lemon may score as citrus.

## Licences
- snapml model: Roboflow 2.0 / YOLOv5 family, GPL-3.0. Data CC BY 4.0.
- calories model: Ultralytics YOLOv8s, AGPL-3.0 (stated in the ONNX metadata). Data CC BY 4.0.
- Weights were fetched for local benchmarking only (api.roboflow.com/ort signed URL) and are NOT committed or redistributed.
