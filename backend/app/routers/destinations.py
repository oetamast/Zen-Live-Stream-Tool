from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.post("/", response_model=models.Destination)
def create_destination(payload: models.DestinationBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    destination = models.Destination.from_orm(payload)
    session.add(destination)
    session.commit()
    session.refresh(destination)
    return destination


@router.get("/", response_model=List[models.Destination])
def list_destinations(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    return session.exec(select(models.Destination)).all()


@router.delete("/{destination_id}")
def delete_destination(destination_id: int, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    destination = session.get(models.Destination, destination_id)
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    session.delete(destination)
    session.commit()
    return {"status": "deleted"}
