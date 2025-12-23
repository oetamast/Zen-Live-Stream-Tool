from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models
from ..auth import require_password_reset
from ..deps import get_session
from ..storage import default_asset_path

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/", response_model=models.Asset)
def create_asset(asset: models.AssetBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    db_asset = models.Asset.from_orm(asset)
    if not db_asset.path:
        db_asset.path = default_asset_path(db_asset.type, db_asset.filename)
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset


@router.get("/", response_model=List[models.Asset])
def list_assets(session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    assets = session.exec(select(models.Asset)).all()
    return assets


@router.get("/{asset_id}", response_model=models.Asset)
def get_asset(asset_id: int, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=models.Asset)
def update_asset(asset_id: int, payload: models.AssetBase, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(asset, key, value)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, session: Session = Depends(get_session), admin=Depends(require_password_reset)):
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.status = "deleted"
    session.add(asset)
    session.commit()
    return {"status": "deleted"}
