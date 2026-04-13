from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routes import router as api_router
from .core.logging_config import configure_logging
from .core.settings import get_settings
from .db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize application concerns that should run once at startup."""
    configure_logging()
    init_db()
    yield


settings = get_settings()

# Create the FastAPI app instance with configured metadata.
app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Include API routes
app.include_router(api_router)
