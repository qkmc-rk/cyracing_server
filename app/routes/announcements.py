from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Announcement
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[AnnouncementResponse])
def list_announcements(db: Session = Depends(get_db)):
    """获取全部公告（置顶在前，按发布时间倒序）"""
    return (
        db.query(Announcement)
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
        .all()
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(announcement_id: int, db: Session = Depends(get_db)):
    """获取单条公告详情"""
    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")
    return announcement


@router.post("/", response_model=AnnouncementResponse)
def create_announcement(
    body: AnnouncementCreate,
    db: Session = Depends(get_db),
):
    """创建新公告"""
    announcement = Announcement(**body.model_dump())
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    body: AnnouncementUpdate,
    db: Session = Depends(get_db),
):
    """更新公告（部分字段可选）"""
    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(announcement, key, value)

    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: int, db: Session = Depends(get_db)):
    """删除公告"""
    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    db.delete(announcement)
    db.commit()
    return {"detail": "公告已删除"}
