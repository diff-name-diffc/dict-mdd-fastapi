"""FastAPI application entry point"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.services import MDDService, DatabaseService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle - preload MDD files and initialize databases on startup"""
    logger.info("Starting MDD API service...")

    # Load MDD files
    mdd_success = MDDService.load_mdd_files()
    if mdd_success:
        logger.info("MDD files loaded successfully")
    else:
        logger.warning("Failed to load MDD files - pronunciation resources may not work")

    # Initialize database connections
    db_success = DatabaseService.initialize()
    if db_success:
        logger.info("Database connections initialized successfully")
    else:
        logger.warning("Failed to initialize databases - dictionary data may not work")

    yield

    # Cleanup
    logger.info("Shutting down MDD API service...")
    DatabaseService.close()


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title=settings.app_name,
        description="查询 MDD 发音库中的音频和图片资源",
        version=settings.app_version,
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
