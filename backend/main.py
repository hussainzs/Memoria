import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="Memoria API",
    description="Backend API for Memoria",
    version="0.1.0"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health_check():
    """Basic health check endpoint"""
    return {"status": "ok"}

# Routes will be included here as the project grows
# from src.api import router
# app.include_router(router)

if __name__ == "__main__":
    # Start uvicorn server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Disable in production
    )
