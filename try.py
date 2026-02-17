"""import io
import datetime
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session 
from geoalchemy2 import Geometry
from ultralytics import YOLO
from PIL import Image

# --- CONFIGURATION ---
# Format: postgresql://username:password@localhost:port/database_name
# CHANGE 'password' to your actual postgres password 
DATABASE_URL = "postgresql://postgres:lladmin@localhost:8000/litterlens_db"

# --- DATABASE SETUP ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class WasteRecord(Base):
    __tablename__ = "waste_detections"
    id = Column(Integer, primary_key=True, index=True)
    waste_type = Column(String)
    location = Column(Geometry('POINT', srid=4326))

Base.metadata.create_all(bind=engine)
# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# --- AI SETUP ---
app = FastAPI()
# Using the "Stunt Double" model for now
model = YOLO("best.pt") 


# --- THE API ENDPOINT ---
@app.post("/detect")
async def detect_waste(
    file: UploadFile = File(...), 
    latitude: float = Form(...), 
    longitude: float = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        # 1. Read Image & Convert to RGB (Removes transparency issues) 
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")      

        # 2. Run AI on the valid image object   
        results = model(image)
    
        
        detections = []
        
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                conf = float(box.conf[0])
                
                # Only save if confidence is decent (> 40%)          
                if conf > 0.4:
                    point_wkt = f"POINT({longitude} {latitude})"
                    new_record = WasteRecord(
                        waste_type=class_name,
                        confidence=conf,
                        location=point_wkt
                    )
                    db.add(new_record)
                    detections.append(class_name)

        db.commit()

        return {
            "status": "success", 
            "location": {"lat": latitude, "lng": longitude},
            "detected": detections
        }

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))"""

class WasteRecord(Base):
    __tablename__ = "waste_detections_v2"
    id = Column(Integer, primary_key=True, index=True)
    waste_type = Column(String, index=True)
    confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    location = Column(Geometry(geometry_type='POINT', srid=4326))


@app.post("/detect")
async def detect_waste(
    file: UploadFile = File(...), 
    latitude: float = Form(...), 
    longitude: float = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        results = model(image)
        
        detections = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                conf = float(box.conf[0])
                
                print(f"Debug: Found {class_name} ({conf})")

                # Adjusted confidence threshold
                if conf > 0.25:
                    point_wkt = f"POINT({longitude} {latitude})"
                    new_record = WasteRecord(
                        waste_type=class_name,
                        confidence=conf,
                        location=point_wkt
                    )
                    db.add(new_record)
                    detections.append(class_name)

        db.commit()

        return {
            "status": "success", 
            "location": {"lat": latitude, "lng": longitude},
            "detected": detections
        }

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

    #neeeewwwwwwwwwwwwwwwwwwwwwwww

    import io
import datetime
# 1. Imports
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from geoalchemy2 import Geometry
from ultralytics import YOLO
from PIL import Image

# 2. Database Config
# REPLACE 'password' with your real PostgreSQL password
DATABASE_URL = "postgresql://postgres:lladmin@localhost:8000/litterlens_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Table Definition
# 3. Table Definition (Updated)
class WasteRecord(Base):
    __tablename__ = "waste_detections_v3"  # <--- CHANGED to v3 to force new table
    id = Column(Integer, primary_key=True, index=True)
    waste_type = Column(String, index=True)
    confidence = Column(Float)
    severity = Column(String)              # <--- NEW COLUMN
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    location = Column(Geometry(geometry_type='POINT', srid=4326))

Base.metadata.create_all(bind=engine)

# 4. Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. App & Model
app = FastAPI()

# Add CORS to allow the browser to send data to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Model
try:
    print("Attempting to load warp_latest.pt...")
    model = YOLO("best.pt")
    print("✅ Custom model loaded!")
except:
    print("⚠️ Custom model not found. Loading standard yolov8n.pt...")
    model = YOLO("yolov8n.pt")

# 6. UPDATED HOMEPAGE WITH DETECTION FORM & DISPLAY AREA
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <head>
            <title>LitterLens AI</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background-color: #f4f4f9; color: #333; }
                .container { max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
                h1 { color: #2c3e50; }
                input { width: 100%; margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { background-color: #4CAF50; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }
                button:hover { background-color: #45a049; }
                #result { margin-top: 20px; padding: 15px; border-radius: 5px; font-weight: bold; display: none; }
                .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌍 LitterLens Detector</h1>
                <p>Upload an image to detect waste.</p>
                
                <form id="uploadForm">
                    <label><b>1. Select Image:</b></label>
                    <input type="file" id="fileInput" required>
                    
                    <label><b>2. Enter Location:</b></label>
                    <input type="number" id="lat" step="any" placeholder="Latitude (e.g. 12.97)" required value="12.97">
                    <input type="number" id="lng" step="any" placeholder="Longitude (e.g. 77.59)" required value="77.59">
                    
                    <button type="button" onclick="detectWaste()">🔍 Detect Waste</button>
                </form>

                <div id="result"></div>
            </div>

            <script>
                async function detectWaste() {
                    const fileInput = document.getElementById('fileInput');
                    const lat = document.getElementById('lat').value;
                    const lng = document.getElementById('lng').value;
                    const resultDiv = document.getElementById('result');

                    if(fileInput.files.length === 0) {
                        alert("Please select a file!");
                        return;
                    }

                    const formData = new FormData();
                    formData.append("file", fileInput.files[0]);
                    formData.append("latitude", lat);
                    formData.append("longitude", lng);

                    resultDiv.style.display = "block";
                    resultDiv.className = ""; 
                    resultDiv.innerHTML = "⏳ Analyzing...";

                    try {
                        const response = await fetch('/detect', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();

                        if (response.ok) {
                            resultDiv.innerHTML = `
                            <b>Severity: ${data.severity}</b> (${data.count} items)<br>
                            ✅ Detected: ${data.detected.join(", ")}`;
                            } else {
                                resultDiv.innerHTML = "⚠️ No waste detected (Try lower confidence?)";
                            }
                        } else {
                            resultDiv.className = "error";
                            resultDiv.innerHTML = "❌ Error: " + data.detail;
                        }
                    } catch (error) {
                        resultDiv.className = "error";
                        resultDiv.innerHTML = "❌ Connection Failed";
                        console.error(error);
                    }
                }
            </script>
        </body>
    </html>
    """

# 7. API Endpoint
@app.post("/detect")
async def detect_waste(
    file: UploadFile = File(...), 
    latitude: float = Form(...), 
    longitude: float = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        # 1. Process Image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # 2. Run AI
        results = model(image)
        
        # 3. Collect Valid Detections (Don't save yet!)
        valid_objects = []
        detected_names = []

        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf > 0.25:  # Confidence threshold
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    
                    # Store tuple of (name, confidence) for later
                    valid_objects.append((class_name, conf))
                    detected_names.append(class_name)

        # 4. Determine Severity based on Count
        count = len(valid_objects)
        
        if count == 0:
            severity = "None"
        elif count <= 5:
            severity = "Low"      # 1-5 items
        elif count <= 10:
            severity = "Medium"   # 6-10 items
        else:
            severity = "High"     # 10+ items

        # 5. Save to Database with Severity
        point_wkt = f"POINT({longitude} {latitude})"
        
        for name, conf in valid_objects:
            new_record = WasteRecord(
                waste_type=name,
                confidence=conf,
                severity=severity,  # <--- Saving the calculated severity
                location=point_wkt
            )
            db.add(new_record)

        db.commit()

        # 6. Return Result
        return {
            "status": "success", 
            "location": {"lat": latitude, "lng": longitude},
            "detected": detected_names,
            "count": count,
            "severity": severity
        }

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))