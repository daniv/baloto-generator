"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.miloto import router as miloto_router
from backend.app.config.app_settings import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_settings.title,
        version=settings.app_settings.version,
        description=settings.app_settings.description,
    )

    app.include_router(miloto_router)
    return app


app = create_app()



