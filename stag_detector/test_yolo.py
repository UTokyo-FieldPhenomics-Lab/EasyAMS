from ultralytics import YOLO

# Load a COCO-pretrained YOLO11n model
model = YOLO("yolo11x.pt")

results = model(r"xxxx.jpg")
results[0].show()