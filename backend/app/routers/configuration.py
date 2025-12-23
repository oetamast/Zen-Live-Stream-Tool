from typing import Dict, List

from fastapi import APIRouter, Body, Depends
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/export")
def export_config(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    payload: Dict[str, List[Dict]] = {
        "assets": [asset.model_dump() for asset in session.exec(select(models.Asset)).all()],
        "destinations": [dest.model_dump() for dest in session.exec(select(models.Destination)).all()],
        "presets": [preset.model_dump() for preset in session.exec(select(models.Preset)).all()],
        "jobs": [job.model_dump() for job in session.exec(select(models.Job)).all()],
        "schedules": [sched.model_dump() for sched in session.exec(select(models.Schedule)).all()],
    }
    return payload


@router.post("/import")
def import_config(
    data: Dict = Body(...), session: Session = Depends(get_session), admin=Depends(require_password_reset)
):
    def upsert(model_cls, items: List[Dict]):
        for raw in items:
            clean = dict(raw)
            clean.pop("id", None)
            obj = model_cls(**clean)
            session.add(obj)
    upsert(models.Asset, data.get("assets", []))
    upsert(models.Destination, data.get("destinations", []))
    upsert(models.Preset, data.get("presets", []))
    upsert(models.Job, data.get("jobs", []))
    upsert(models.Schedule, data.get("schedules", []))
    session.commit()
    return {"status": "imported"}

