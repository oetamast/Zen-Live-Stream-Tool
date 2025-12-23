from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/", response_model=models.Schedule)
def create_schedule(payload: models.ScheduleBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    job = session.get(models.Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if payload.end_at is None and not job.loop_enabled:
        raise HTTPException(status_code=400, detail="Open-ended schedules require loop enabled")
    schedule = models.Schedule.from_orm(payload)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.get("/", response_model=List[models.Schedule])
def list_schedules(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    return session.exec(select(models.Schedule)).all()
