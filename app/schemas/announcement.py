from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class AnnouncementCreate(BaseModel):
    """创建公告"""
    title: str
    content: Any  # 富文本 JSON（如 Quill Delta）
    summary: Optional[str] = None
    is_pinned: bool = False
    published_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    """更新公告（所有字段可选）"""
    title: Optional[str] = None
    content: Optional[Any] = None
    summary: Optional[str] = None
    is_pinned: Optional[bool] = None
    published_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    """公告返回"""
    announcement_id: int
    title: str
    content: Any
    summary: Optional[str] = None
    is_pinned: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
