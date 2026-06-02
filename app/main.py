from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings
from app.core.errors import register_exception_handlers

app = FastAPI(title=settings.app_name, version="0.1.0")
register_exception_handlers(app)
app.include_router(router, prefix=settings.api_prefix)
