from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/jobs", tags=["jobs"])


def validate_job(job: models.Job, session: Session) -> List[str]:
    reasons: List[str] = []
    destination = session.get(models.Destination, job.destination_id)
    if not destination:
        reasons.append("Destination missing")
    video_asset = session.get(models.Asset, job.video_asset_id)
    if not video_asset or video_asset.status != "active":
        reasons.append("Video asset missing")
    if job.crossfade_enabled and not job.loop_enabled:
        reasons.append("Crossfade requires loop")
    if job.audio_mode != "none" and job.tier_required == "Basic":
        reasons.append("Audio replacement requires Premium")
    if job.scenes_enabled and job.tier_required != "Ultimate":
        reasons.append("Scenes require Ultimate")
    return reasons


@router.post("/", response_model=models.Job)
def create_job(payload: models.JobBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    job = models.Job.from_orm(payload)
    reasons = validate_job(job, session)
    job.status = "invalid" if reasons else "valid"
    job.invalid_reasons = ", ".join(reasons) if reasons else None
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.get("/", response_model=List[models.Job])
def list_jobs(filter_status: Optional[str] = None, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    query = select(models.Job)
    if filter_status:
        query = query.where(models.Job.status == filter_status)
    return session.exec(query).all()


@router.get("/backups", response_model=List[models.JobBackup])
def list_backups(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    stmt = select(models.JobBackup).order_by(models.JobBackup.created_at.desc())
    return session.exec(stmt).all()


@router.patch("/{job_id}", response_model=models.Job)
def update_job(job_id: int, payload: models.JobBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    job = session.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    reasons = validate_job(job, session)
    job.status = "invalid" if reasons else "valid"
    job.invalid_reasons = ", ".join(reasons) if reasons else None
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.post("/{job_id}/run", response_model=models.Session)
def run_now(job_id: int, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    job = session.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    new_session = models.Session(job_id=job.id, trigger="run_now", planned_start_at=datetime.utcnow())
    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    return new_session


@router.post("/{job_id}/restore", response_model=models.Job)
def restore_job(job_id: int, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    backup = session.exec(
        select(models.JobBackup).where(models.JobBackup.job_id == job_id).order_by(models.JobBackup.created_at.desc())
    ).first()
    if not backup:
        raise HTTPException(status_code=404, detail="No backup found for job")
    job = session.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    restored = models.Job.model_validate_json(backup.backup_json)
    for key, value in restored.model_dump(exclude={"id"}).items():
        setattr(job, key, value)
    job.status = "draft"
    job.invalid_reasons = None
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
