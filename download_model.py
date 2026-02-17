from ultralytics import YOLO

print("Downloading standard YOLO model...")
# This downloads 'yolov8n.pt' (a standard model that detects generic objects)
model = YOLO("yolov8n.pt") 
print("Success! 'yolov8n.pt' is now in your folder.")