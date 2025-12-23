from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/presets", tags=["presets"])


@router.post("/", response_model=models.Preset)
def create_preset(payload: models.PresetBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    preset = models.Preset.from_orm(payload)
    session.add(preset)
    session.commit()
    session.refresh(preset)
    return preset


@router.get("/", response_model=List[models.Preset])
def list_presets(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    return session.exec(select(models.Preset)).all()


@router.delete("/{preset_id}")
def delete_preset(preset_id: int, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    preset = session.get(models.Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    session.delete(preset)
    session.commit()
    return {"status": "deleted"}
