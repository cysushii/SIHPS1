from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.database import engine, Base
from api.routes import router as api_router

# Initialize database schema tables cleanly on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Student Data Verification Platform (SIH26263)",
    description="APAAR ID-Based Student Data Verification & Approval Platform for AICTE-Approved Institutions.",
    version="2.0.0"
)

# Enable CORS for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes
app.include_router(api_router)

@app.get("/", summary="Health Check")
def health_check():
    return {
        "status": "online",
        "service": "SIH26263 Student Data Verification Platform",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
