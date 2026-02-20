from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

# Standard SQLAlchemy Base definition
Base = declarative_base()

# 1. USER TABLE (Staff & Admin)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Login Credentials
    employee_id = Column(String, unique=True, index=True)
    password = Column(String)
    
    # Personal Details
    full_name = Column(String)
    age = Column(Integer)
    sex = Column(String)
    phone_number = Column(String)
    email = Column(String, nullable=True)
    
    # Work Details
    job_role = Column(String)
    zone = Column(Integer)  # Stores 1, 2, or 3
    
    # Security & Status (FIXED)
    role = Column(String, default="staff")
    status = Column(String, default="Active") # Fixes the 'status' keyword error

# 2. LOCATION TABLE (Restored)
class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

# 3. CAMERA TABLE (Restored)
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    url = Column(String)
    location_id = Column(Integer) # Links to zone number (1, 2, or 3)