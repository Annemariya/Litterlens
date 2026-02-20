import cv2
import datetime
import os
import glob
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from ultralytics import YOLO
from models import Base, User, Location, Camera
from sqlalchemy.orm import Session
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# --- ADD THIS TO MAIN.PY ---
from fastapi.staticfiles import StaticFiles  # Ensure this is imported at top
from dotenv import load_dotenv

# This is the magic line that makes images visible:


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount templates
templates = Jinja2Templates(directory="templates")
app.mount("/detected_snapshots", StaticFiles(directory="detected_snapshots"), name="snapshots")
# Load your YOLO Model
#model = YOLO("best.pt") # Ensure your best.pt is in the folder

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg2://postgres:lladmin@localhost:5432/litterlens_db"

# --- DATABASE SETUP ---
engine = create_engine(DATABASE_URL)

# 1. Define the Login Data Model (Fixes 'UserLogin' warning)
class UserLogin(BaseModel):
    username: str
    password: str
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- CREATE BASE (For your Models) ---
try:
    print("⏳ Attempting to connect to Database on Port 8000...")
    Base.metadata.create_all(bind=engine)
    print("✅ SUCCESS: Connected to Database on Port 8000!")
except Exception as e:
    print(f"❌ DATABASE ERROR: Could not connect to Port 8000.\nDetails: {e}")
# 2. Define the Database Helper (Fixes 'get_db' warning)
def get_db():
    try:
        db = SessionLocal()  # Make sure SessionLocal is defined or imported
        yield db
    finally:
        db.close()
# List of Camera URLs (Replace these with the actual IPs from your Phone Apps)
# Example: "http://192.168.1.5:8080/video"
CAMERAS = [
    {"id": 1, "url": "http://172.30.19.16:8080/video", "name": "camera1"},
    {"id": 2, "url": "http://172.30.11.196:8080/video", "name": "camera2"},
    {"id": 3, "url": "http://172.30.19.16:8080/video", "name": "camera3"},
    {"id": 4, "url": "http://172.30.19.16:8080/video", "name": "camera4"}, 
    {"id": 5, "url": "http://172.30.19.16:8080/video", "name": "camera5"},
    {"id": 6, "url": "http://172.30.19.16:8080/video", "name": "camera6"},
    {"id": 7, "url": "http://172.30.19.16:8080/video", "name": "camera7"},
    {"id": 8, "url": "http://172.30.11.196:8080/video", "name": "camera8"},
    {"id": 9, "url": "http://172.30.11.196:8080/video", "name": "camera9"},
    {"id": 10, "url": "http://172.30.11.196:8080/video", "name": "camera10"},
    {"id": 11, "url": "http://172.30.11.196:8080/video", "name": "camera11"},
    {"id": 12, "url": "http://172.30.11.196:8080/video", "name": "camera12"},
]

# Scheduler for 4:00 PM tasks
scheduler = BackgroundScheduler()

def get_frame_with_overlay(camera_url):
    """
    Reads a frame, rotates it to fix orientation, adds the 'Clock' overlay, 
    and returns it.
    """
    cap = cv2.VideoCapture(camera_url)
    success, frame = cap.read()
    cap.release()
    
    if success:
        # --- ROTATION FIX ---
        # Rotates the image 90 degrees clockwise. 
        # If it is still wrong, try cv2.ROTATE_90_COUNTERCLOCKWISE
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        # --------------------

        # Add Clock/Date Overlay
        now = datetime.datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Draw black rectangle background for text (Adjust coordinates if needed)
        # Since we rotated, the frame dimensions changed, so we ensure the box fits
        cv2.rectangle(frame, (10, 10), (350, 60), (0, 0, 0), -1)
        
        # Put white text
        cv2.putText(frame, time_str, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (255, 255, 255), 2, cv2.LINE_AA)
        return frame
    return None

def scheduled_waste_detection():
    print("⏰ Trigger: Scanning for waste...")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    for cam in CAMERAS:
        # Note: Make sure 'get_frame_with_overlay' matches your actual function name
        frame = get_frame_with_overlay(cam['url']) 
        
        if frame is not None:
            # 1. Run YOLO
            results = model(frame)
            result = results[0]
            
            # 2. Extract Detected Object Names
            detected_names = []
            for box in result.boxes:
                class_id = int(box.cls[0])
                name = result.names[class_id]
                detected_names.append(name)
            
            # Create a string like "Plastic, Bottle"
            waste_str = ", ".join(detected_names) if detected_names else "No Waste Detected"
            
            # 3. Save the Image
            filename_base = f"cam{cam['id']}_{timestamp}"
            img_path = os.path.join("detected_snapshots", f"{filename_base}.jpg")
            os.makedirs("detected_snapshots", exist_ok=True)
            
            res_plotted = result.plot()
            cv2.imwrite(img_path, res_plotted)
            
            # 4. Save the Text File (THIS IS NEW)
            txt_path = os.path.join("detected_snapshots", f"{filename_base}.txt")
            with open(txt_path, "w") as f:
                f.write(waste_str)

            print(f"✅ Saved {img_path} (Found: {waste_str})")
# Start the scheduler (Run every day at 16:00 / 4 PM)
# For testing, you can change 'hour=16' to current hour and 'minute' to next minute
scheduler.add_job(scheduled_waste_detection, 'cron', hour=15, minute=41)
scheduler.start()

# --- Generator for Live Streaming ---
def generate_frames(camera_url):
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000000"
    cap = cv2.VideoCapture(camera_url)
    
    if not cap.isOpened():
        print(f"❌ Error: Could not open video stream at {camera_url}")
        return

    while True:
        success, frame = cap.read()
        
        if not success:
            print("⚠️ Frame lost. Retrying...")
            cap.release()
            cap = cv2.VideoCapture(camera_url) 
            continue

        try:
            # 1. Rotate and Resize
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            frame = cv2.resize(frame, (640, 480))

            # 3. UPDATED Text Overlay (Includes Date and Time)
            now = datetime.datetime.now()
            # This format gives you: 2026-02-14 15:30:45
            time_str = now.strftime("%Y-%m-%d %H:%M:%S") 
            
            # Put text on the frame
            cv2.putText(frame, time_str, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, (0, 0, 255), 2)

            # 4. Compress
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            print(f"Error processing frame: {e}")
            break
            
    cap.release()

def calculate_risk_level(waste_count):
    if waste_count >= 10:
        return "High Risk", "red"    # Critical
    elif waste_count >= 5:
        return "Medium Risk", "orange" # Warning
    else:
        return "Low Risk", "green"   # Safe

# --- FAKE DATA SEEDING (Run this once to setup X, Y, Z) ---
# --- REPLACE YOUR OLD seed_data FUNCTION WITH THIS ---
def seed_data(db: Session):
    # Check if the admin user already exists
    admin_user = db.query(User).filter(User.employee_id == "ADMIN001").first()
    
    if not admin_user:
        # Only add if the user is NOT found
        new_admin = User(
            employee_id="ADMIN001",
            password="admin_secret_pass",
            full_name="Super Supervisor",
            age=35,
            sex="Male",
            phone_number="0000000000",
            job_role="Supervisor",
            zone=1,
            role="admin"
        )
        db.add(new_admin)
        db.commit()
        print("✅ Admin user created successfully.")
    else:
        print("ℹ️ Admin user already exists. Skipping seed.")


# --- REPLACE YOUR OLD LOGIN ROUTE WITH THIS ---
# --- UPDATED LOGIN ROUTE ---
# --- REPLACEMENT LOGIN FUNCTION (Uses Redirects) ---
@app.post("/login")
async def login(
    request: Request,
    employee_id: str = Form(...),
    password: str = Form(...),
    zone_check: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Find User in DB
    user = db.query(User).filter(User.employee_id == employee_id).first()

    # 2. Check Password
    if not user or user.password != password:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid ID or Password"
        })

    # 3. SECURITY CHECK: Ensure Staff is in the correct Zone
    if user.role != "admin":
        if str(user.zone) != zone_check:
            return templates.TemplateResponse("login.html", {
                "request": request, 
                "error": f"Access Denied! You are assigned to Zone {user.zone}."
            })

    # 4. REDIRECT (This fixes the blank screen!)
    # status_code=303 tells the browser "This was a form submission, now Go Here"
    if user.role == "admin":
        return RedirectResponse(url="/dashboard", status_code=303)
    else:
        # Redirect to the dashboard for their specific zone (e.g., /dashboard/1)
        #return RedirectResponse(url=f"/dashboard/{user.zone}", status_code=303)
        return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# --- 2. HANDLE THE REGISTRATION (POST) ---
# --- REPLACE YOUR OLD REGISTER ROUTE WITH THIS ---
@app.post("/register")
async def register_user(
    request: Request,
    full_name: str = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(None),
    employee_id: str = Form(...),
    job_role: str = Form(...),
    zone: int = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Validate Zone (Must be 1, 2, or 3)
    if zone not in [1, 2, 3]:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Invalid Zone!"})

    # 2. Validate Passwords
    if password != confirm_password:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Passwords do not match!"})

    # 3. Check if Employee ID exists
    if db.query(User).filter(User.employee_id == employee_id).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Employee ID taken!"})

    # 4. Create User (Default role is 'staff')
    new_user = User(
        full_name=full_name, age=age, sex=sex, phone_number=phone_number,
        email=email, employee_id=employee_id, job_role=job_role,
        zone=zone, password=password, role="staff"
    )
    
    db.add(new_user)
    db.commit()
    
    return templates.TemplateResponse("login.html", {"request": request, "message": "Registered! Please Login."})

# --- ADD THIS NEW ROUTE FOR ADMIN ---
# --- UPDATE THIS ROUTE IN MAIN.PY ---
@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Create a fake user object so the HTML doesn't crash
    dummy_admin = User(
        full_name="Admin Preview", 
        employee_id="ADMIN001", 
        role="admin", 
        zone=1
    )
    
    return templates.TemplateResponse("admin-dash.html", {
        "request": request, 
        "user": dummy_admin  # <--- PASS THIS DATA
    })
@app.post("/api/update_snapshot_time")
async def update_time(time_data: dict):
    new_time = time_data.get("time") # Expecting "HH:MM"
    if new_time:
        hour, minute = new_time.split(":")
        
        # Remove the old job and add the new one
        scheduler.remove_all_jobs()
        scheduler.add_job(scheduled_waste_detection, 'cron', hour=int(hour), minute=int(minute))
        
        print(f"⏰ Snapshot time updated to: {new_time}")
        return {"message": f"Snapshot time updated to {new_time}"}
    return {"error": "Invalid time format"}

# --- UNIVERSAL DASHBOARD ROUTE ---
@app.get("/dashboard", response_class=HTMLResponse)
async def simple_dashboard(request: Request, db: Session = Depends(get_db)):
    
    # Just get everything for now
    cameras = db.query(Camera).all()
    #location_name = "LitterLens Main Dashboard"

    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "cameras": cameras, 
        #"location_name": location_name
    })

# --- API TO GET LIVE RISK STATUS ---
@app.get("/api/risk_status/{camera_id}")
def get_risk(camera_id: int):
    # In real life, fetch this from your latest detection
    # For now, let's simulate it randomly or check the last snapshot txt file
    import random
    count = random.randint(0, 15) # Simulated detection count
    status, color = calculate_risk_level(count)
    return {"status": status, "color": color, "count": count}

# NEW CODE (What you need)
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    # Make sure "landing.html" exists in your templates folder!
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/index", response_class=HTMLResponse)
async def view_index(request: Request):
    # Instead of db.query, we use the CAMERAS list from the top of your main.py
    from main import CAMERAS 
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "cameras": CAMERAS  # This sends the list directly to the HTML
    })

@app.get("/video_feed/{cam_id}")
async def video_feed(cam_id: int):
    # Find the camera in your hardcoded list
    camera = next((c for c in CAMERAS if c["id"] == cam_id), None)
    
    if camera:
        return StreamingResponse(
            generate_frames(camera["url"]), 
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    return JSONResponse({"error": "Camera not found"}, status_code=404)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# --- NEW ROUTE 1: The HTML Page ---
@app.get("/snapshots_page", response_class=HTMLResponse)
async def snapshots_page(request: Request):
    return templates.TemplateResponse("snapshots.html", {"request": request})

# --- NEW ROUTE 2: The API that finds files ---
@app.get("/api/history")
async def get_history():
    data = []
    # Find all .jpg files
    files = glob.glob("detected_snapshots/*.jpg")
    # Sort by newest first
    files.sort(key=os.path.getmtime, reverse=True)
    
    for file_path in files:
        filename = os.path.basename(file_path) 
        
        # Read the matching .txt file
        txt_path = file_path.replace(".jpg", ".txt")
        waste_names = "Unknown"
        if os.path.exists(txt_path):
            with open(txt_path, "r") as f:
                waste_names = f.read()
        
        # Format the filename into readable data
        parts = filename.split("_") # e.g. cam1_2025-01-28_16-00-00.jpg
        if len(parts) >= 3:
            cam_id = parts[0].replace("cam", "")
            date_time = f"{parts[1]} {parts[2].replace('.jpg', '').replace('-', ':')}"
        else:
            cam_id = "?"
            date_time = "Unknown"

        data.append({
            "image_url": f"/detected_snapshots/{filename}",
            "cam_id": cam_id,
            "timestamp": date_time,
            "waste_detected": waste_names
        })
    return JSONResponse(content=data)

@app.get("/staff_mngmt", response_class=HTMLResponse)
def get_staff_management(request: Request, db: Session = Depends(get_db)):
    # This fetches all users from the 'users' table in Supabase
    staff_list = db.query(User).all() 
    
    return templates.TemplateResponse("staff_mngmt.html", {
        "request": request, 
        "staff_list": staff_list
    })

# ROUTE 1: Display the Edit Page
@app.get("/edit_staff/{staff_id}", response_class=HTMLResponse)
async def get_edit_page(request: Request, staff_id: int, db: Session = Depends(get_db)):
    # Find the staff member in the database by their unique ID
    member = db.query(User).filter(User.id == staff_id).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Staff member not found")
        
    return templates.TemplateResponse("edit_staff.html", {
        "request": request,
        "member": member
    })

@app.post("/update_staff/{staff_id}")
async def update_staff(
    staff_id: int,
    full_name: str = Form(...),
    employee_id: str = Form(...),
    password: str = Form(None), # Password optional in edit
    age: int = Form(...),
    sex: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(None),
    job_role: str = Form(...),
    zone: int = Form(...),
    role: str = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    member = db.query(User).filter(User.id == staff_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Update all fields
    member.full_name = full_name
    member.employee_id = employee_id
    member.age = age
    member.sex = sex
    member.phone_number = phone_number
    member.email = email
    member.job_role = job_role
    member.zone = zone
    member.role = role
    member.status = status
    
    # Only update password if a new one is provided
    if password:
        member.password = password

    db.commit()
    return RedirectResponse(url="/staff_mngmt", status_code=303)

@app.post("/delete_staff/{staff_id}")
async def delete_staff_from_db(staff_id: int, db: Session = Depends(get_db)):
    # Find the user in the database
    member = db.query(User).filter(User.id == staff_id).first()
    
    if member:
        db.delete(member)
        db.commit() # Saves the deletion to PostgreSQL
        
    # Redirect back to the staff list
    return RedirectResponse(url="/staff_mngmt", status_code=303)

@app.get("/analytics/{staff_id}", response_class=HTMLResponse)
async def get_staff_analytics(request: Request, staff_id: int, db: Session = Depends(get_db)):
    # 1. Fetch the staff member
    member = db.query(User).filter(User.id == staff_id).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Staff not found")

    # 2. Placeholder for analytics data (Integrate your actual logs here later)
    stats = {
        "completion_rate": 85,
        "avg_response_time": "12m",
        "tasks_completed": 42,
        "false_positives": 3
    }

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "member": member,
        "stats": stats
    })

# --- ADD THIS AT THE VERY END OF main.py ---

@app.on_event("startup")
def startup_event():
    print("🌱 Checking Database for Zones...")
    db = SessionLocal()
    
    # This calls the function you already wrote to create Zones 1, 2, 3
    seed_data(db) 
    
    db.close()
    print("✅ Database Ready!")