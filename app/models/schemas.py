"""API response schemas"""
from typing import Optional
from pydantic import BaseModel


class ResourceItem(BaseModel):
    """Single resource item with base64 data"""
    filename: str
    base64_data: str
    content_type: str


class PronunciationResource(BaseModel):
    """Pronunciation resource for a single accent (icon + audio)"""
    icon: Optional[ResourceItem] = None
    audio: Optional[ResourceItem] = None


class WordResources(BaseModel):
    """Word resources response - grouped by accent"""
    word: str
    us: Optional[PronunciationResource] = None
    uk: Optional[PronunciationResource] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str = ""
