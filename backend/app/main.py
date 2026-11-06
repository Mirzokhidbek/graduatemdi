"""UzTerm AI REST API.

Ishga tushirish (repo ildizidan):
    PYTHONPATH=backend uvicorn app.main:app --reload --port 8000

Terminlar bazasi ilova yaratilganda bir marta yuklanadi va tekshiriladi;
baza noto'g'ri bo'lsa, ilova ishga tushmaydi.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.annotation.workspace import Workspace
from app.api.annotation_routes import router as annotation_router
from app.api.routes import router
from app.core.config import Settings
from app.database.term_store import load_terms
from app.models.runtime import load_predictor
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.services.detectors import DetectorRegistry

logger = logging.getLogger("uzterm")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    entries = load_terms(settings.terms_path)

    app = FastAPI(title="UzTerm AI", version="0.1.0", description="Oʻzbek tilshunoslik terminlarini aniqlash")
    app.state.settings = settings
    app.state.entries = entries
    app.state.matcher = DictionaryMatcher(entries)
    model = load_predictor(settings.model_path, settings.data_dir / "raw") if settings.model_path else None
    app.state.workspace = Workspace(settings.data_dir, app.state.matcher, model)
    app.state.detectors = DetectorRegistry(
        app.state.matcher, entries, settings.models_dir, settings.data_dir / "raw", settings.data_dir.parent / "reports"
    )
    app.include_router(router)
    app.include_router(annotation_router)

    # Production: `npm run build` natijasi (frontend/dist) shu serverning o'zidan beriladi — bitta port.
    dist = settings.frontend_dist
    if dist is not None and (dist / "index.html").is_file():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Ichki tafsilotlar (stack trace) foydalanuvchiga qaytarilmaydi.
        logger.exception("Kutilmagan xato: %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Serverda ichki xato yuz berdi."})

    return app


app = create_app()
