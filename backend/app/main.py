from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .auth import authenticate, require_password_reset, update_password
from .config import get_settings
from .database import lifespan
from .routers import assets, configuration, destinations, jobs, license, presets, schedules, sessions
from .storage import ensure_data_folders

settings = get_settings()
ensure_data_folders()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(assets.router)
app.include_router(destinations.router)
app.include_router(presets.router)
app.include_router(jobs.router)
app.include_router(schedules.router)
app.include_router(sessions.router)
app.include_router(license.router)
app.include_router(configuration.router)


@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.utcnow()}


@app.post("/auth/change-password")
def change_password(new_password: str, admin=Depends(authenticate)):
    update_password(new_password)
    return {"status": "updated"}


@app.get("/wizard", response_class=HTMLResponse)
def wizard():
    html = Path(__file__).parent / "static" / "wizard.html"
    if not html.exists():
        raise HTTPException(status_code=404, detail="Wizard missing")
    return HTMLResponse(html.read_text())
