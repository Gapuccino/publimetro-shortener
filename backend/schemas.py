from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class LinkCreate(BaseModel):
    url: str
    title: Optional[str] = None
    custom_code: Optional[str] = None


class LinkResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    title: Optional[str]
    created_at: datetime
    clicks: int
    short_url: str
    
    class Config:
        from_attributes = True


class LinkListResponse(BaseModel):
    links: list[LinkResponse]
    total: int


class AuthRequest(BaseModel):
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    role: Optional[str] = None


class StatsResponse(BaseModel):
    total_links: int
    total_clicks: int
    links_today: int
    clicks_today: int
