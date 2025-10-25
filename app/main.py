from fastapi import FastAPI

from .api.routes import router as api_router

# Create the FastAPI app instance
app = FastAPI(title="Zeit Project API")

# Include API routes
app.include_router(api_router)
