from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/license", tags=["license"])


def _hash_secret(secret: str) -> str:
    return f"sha256:{hashlib.sha256(secret.encode()).hexdigest()}"


def _record_activity(session: Session, install_id: str, action: str, message: Optional[str] = None) -> None:
    log = models.LicenseActivity(install_id=install_id, action=action, message=message)
    session.add(log)
    session.commit()


def _active_members(session: Session) -> List[models.MemberLicense]:
    now = datetime.utcnow()
    stmt = select(models.MemberLicense).where(models.MemberLicense.active == True)
    members = session.exec(stmt).all()
    return [m for m in members if not m.expires_at or m.expires_at > now]


def _downgrade_jobs_to_basic(session: Session, reason: str) -> None:
    jobs = session.exec(select(models.Job).where(models.Job.tier_required != "Basic")).all()
    for job in jobs:
        backup = models.JobBackup(job_id=job.id, previous_tier=job.tier_required, backup_json=job.model_dump_json())
        session.add(backup)
        job.tier_required = "Basic"
        job.audio_mode = "none"
        job.auto_recovery = False
        job.hot_swap_mode = "immediate"
        job.scenes_enabled = False
        job.swap_rules_json = None
        job.scene_overrides_json = None
        job.status = "invalid"
        job.invalid_reasons = (
            reason
            if not job.invalid_reasons
            else f"{job.invalid_reasons}; {reason}"
        )
        job.updated_at = datetime.utcnow()
        session.add(job)
    session.commit()


def _enforce_outage_policy(state: models.LicenseState, member: Optional[models.MemberLicense], session: Session) -> models.LicenseState:
    now = datetime.utcnow()
    if state.last_check_at is None:
        return state
    offline_for = now - state.last_check_at
    if offline_for > timedelta(minutes=30) and state.grace_started_at is None:
        state.grace_started_at = state.last_check_at + timedelta(minutes=30)
    if state.grace_started_at and now - state.grace_started_at > timedelta(hours=6):
        if state.activated_tier != "Basic":
            state.activated_tier = "Basic"
            state.grace_started_at = None
            session.add(state)
            _downgrade_jobs_to_basic(session, "License grace period expired")
            _record_activity(session, state.install_id, "downgraded", "Grace exhausted; restricted to Basic")
    session.commit()
    return state


@router.post("/issue", response_model=models.MemberLicense)
def issue_license(
    install_id: str,
    install_secret: str,
    tier: str = "Basic",
    notes: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    session: Session = Depends(get_session),
    admin=Depends(require_password_reset),
):
    existing = session.exec(select(models.MemberLicense).where(models.MemberLicense.install_id == install_id)).first()
    secret_hash = _hash_secret(install_secret)
    if existing:
        existing.install_secret_hash = secret_hash
        existing.tier = tier
        existing.notes = notes
        existing.expires_at = expires_at
        existing.last_check_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        _record_activity(session, install_id, "updated", f"Tier set to {tier}")
        return existing
    member = models.MemberLicense(
        install_id=install_id,
        install_secret_hash=secret_hash,
        tier=tier,
        notes=notes,
        expires_at=expires_at,
        last_check_at=datetime.utcnow(),
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    _record_activity(session, install_id, "issued", f"Tier {tier} created")
    return member


@router.get("/members", response_model=List[models.MemberLicense])
def list_members(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    return session.exec(select(models.MemberLicense)).all()


@router.get("/metrics")
def metrics(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    active_members = _active_members(session)
    counts: Dict[str, int] = {"total": len(active_members), "Basic": 0, "Premium": 0, "Ultimate": 0}
    for member in active_members:
        counts[member.tier] = counts.get(member.tier, 0) + 1
    return counts


@router.get("/activity", response_model=List[models.LicenseActivity])
def activity(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    stmt = select(models.LicenseActivity).order_by(models.LicenseActivity.created_at.desc())
    return session.exec(stmt).all()


@router.get("/state", response_model=models.LicenseState)
def get_state(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    state = session.exec(select(models.LicenseState)).first()
    if not state:
        raise HTTPException(status_code=404, detail="No license state")
    member = session.exec(select(models.MemberLicense).where(models.MemberLicense.install_id == state.install_id)).first()
    return _enforce_outage_policy(state, member, session)


@router.post("/activate", response_model=models.LicenseState)
def activate(
    install_id: str,
    install_secret: str,
    session: Session = Depends(get_session),
    admin=Depends(require_password_reset),
):
    member = session.exec(select(models.MemberLicense).where(models.MemberLicense.install_id == install_id)).first()
    if not member or not member.active:
        raise HTTPException(status_code=403, detail="License not issued or inactive")
    if member.expires_at and member.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=403, detail="License expired")
    if member.install_secret_hash != _hash_secret(install_secret):
        raise HTTPException(status_code=403, detail="Invalid secret")
    lease_expires = datetime.utcnow() + timedelta(hours=1)
    state = session.exec(select(models.LicenseState)).first()
    if state:
        state.install_id = install_id
        state.install_secret_hash = member.install_secret_hash
        state.activated_tier = member.tier
        state.lease_expires_at = lease_expires
        state.last_check_at = datetime.utcnow()
        state.grace_started_at = None
        state.member_license_id = member.id
    else:
        state = models.LicenseState(
            install_id=install_id,
            install_secret_hash=member.install_secret_hash,
            activated_tier=member.tier,
            lease_expires_at=lease_expires,
            last_check_at=datetime.utcnow(),
            member_license_id=member.id,
        )
    session.add(state)
    session.commit()
    session.refresh(state)
    _record_activity(session, install_id, "activated", f"Tier {member.tier} active")
    return state


@router.post("/renew", response_model=models.LicenseState)
def renew(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    state = session.exec(select(models.LicenseState)).first()
    if not state:
        raise HTTPException(status_code=404, detail="No license state")
    member = session.exec(select(models.MemberLicense).where(models.MemberLicense.install_id == state.install_id)).first()
    if member and member.expires_at and member.expires_at <= datetime.utcnow():
        state.activated_tier = "Basic"
        session.add(state)
        _downgrade_jobs_to_basic(session, "License expired; downgraded to Basic")
        _record_activity(session, state.install_id, "expired", "Premium/Ultimate features removed")
    else:
        state.lease_expires_at = datetime.utcnow() + timedelta(hours=1)
        state.last_check_at = datetime.utcnow()
        state.grace_started_at = None
        session.add(state)
        session.commit()
        session.refresh(state)
        _record_activity(session, state.install_id, "renewed", "Lease extended 1h")
    return _enforce_outage_policy(state, member, session)


@router.post("/outage/check", response_model=models.LicenseState)
def enforce_outage(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    state = session.exec(select(models.LicenseState)).first()
    if not state:
        raise HTTPException(status_code=404, detail="No license state")
    member = session.exec(select(models.MemberLicense).where(models.MemberLicense.install_id == state.install_id)).first()
    return _enforce_outage_policy(state, member, session)
