from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.history import router as history_router
from backend.app.api.reports import router as reports_router
from backend.app.api.scan import router as scan_router
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
