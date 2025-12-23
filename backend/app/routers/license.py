from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..config import get_settings
from ..deps import get_session

router = APIRouter(prefix="/license", tags=["license"])


@router.get("/state", response_model=models.LicenseState)
def get_state(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    state = session.exec(select(models.LicenseState)).first()
    if not state:
        raise HTTPException(status_code=404, detail="No license state")
    return state


@router.post("/activate", response_model=models.LicenseState)
def activate(install_id: str, install_secret: str, tier: str = "Basic", session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    settings = get_settings()
    expires = datetime.utcnow() + timedelta(hours=1)
    hashed = install_secret + "-hash"
    state = models.LicenseState(install_id=install_id, install_secret_hash=hashed, activated_tier=tier, lease_expires_at=expires)
    session.add(state)
    session.commit()
    session.refresh(state)
    return state


@router.post("/renew", response_model=models.LicenseState)
def renew(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    state = session.exec(select(models.LicenseState)).first()
    if not state:
        raise HTTPException(status_code=404, detail="No license state")
    state.lease_expires_at = datetime.utcnow() + timedelta(hours=1)
    state.last_check_at = datetime.utcnow()
    session.add(state)
    session.commit()
    session.refresh(state)
    return state
