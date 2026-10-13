import sys,shutil
from ultralytics import YOLO
p=YOLO(sys.argv[1]).export(format="onnx",imgsz=480,device="cpu",dynamic=False,simplify=True)
shutil.copyfile(p,sys.argv[2]); print("EXPORTED",sys.argv[2])
