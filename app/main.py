from fastapi import FastAPI

from .api.routes import router as api_router
from .core.logging_config import configure_logging
from .core.settings import get_settings

# Configure logging and settings once at startup.
configure_logging()
settings = get_settings()

# Create the FastAPI app instance with configured metadata.
app = FastAPI(title=settings.app_name)

# Include API routes
app.include_router(api_router)
