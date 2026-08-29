from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.history import router as history_router
from backend.app.api.reports import router as reports_router
from backend.app.api.scan import router as scan_router

# `models` is imported for its side effect: a model class has to be imported
# before create_all() to be registered on Base.metadata. The routers pull it
# in too, but relying on that means an import reorder quietly stops the
# tables from being created.
from backend.app.db import models  # noqa: F401  (registers ScanRecord on Base)
from backend.app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PhishGuard API")

# Permissive CORS: this is a local resume project, not a hardened public
# API. The Chrome extension's popup/background worker and (from Milestone
# 8) the React dashboard both call this API directly from the browser on a
# different origin, so CORS has to be open for either to work at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)
app.include_router(history_router)
app.include_router(reports_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
