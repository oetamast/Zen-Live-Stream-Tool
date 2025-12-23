from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=List[models.Session])
def list_sessions(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    return session.exec(select(models.Session)).all()
