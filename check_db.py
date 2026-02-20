from sqlalchemy import inspect
from main import engine

def verify_column():
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'status' in columns:
        print("✅ SUCCESS: The 'status' column exists in the database.")
    else:
        print("❌ ERROR: 'status' column not found. Run the ALTER TABLE SQL command.")

if __name__ == "__main__":
    verify_column()