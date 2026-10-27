from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.database import engine, Base
from api.routes import router as api_router
from api.batch_routes import batch_router

# Initialize database schema tables on startup
Base.metadata.create_all(bind=engine)

# Seed initial honeytoken canaries & demo institutes if table is empty
from models.database import SessionLocal
from security.honeytokens import seed_honeytokens
from models.models import Institute
from data.seed_demo_data import generate_seed_data

with SessionLocal() as db_session:
    seed_honeytokens(db_session, count=10)
    # If freshly deployed on Render without seed data, auto-seed demo institutes & students
    if db_session.query(Institute).count() == 0:
        print("Auto-seeding default demo institutions and synthetic students for cloud deployment...")
        db_session.close()
        generate_seed_data()

app = FastAPI(
    title="APAAR Student Data Verification Platform (SIH26263)",
    description="Backend API for APAAR ID-Based Student Data Management and Verification Platform for AICTE-Approved Institutions.",
    version="1.0.0"
)

# Enable CORS for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)
app.include_router(batch_router)

@app.get("/", summary="Health Check")
def health_check():
    return {
        "status": "online",
        "platform": "SIH26263 APAAR Verification Platform",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

