from pydantic import BaseModel
from typing import Optional


class ResourceItem(BaseModel):
    """单个资源项"""
    filename: str
    base64_data: str
    content_type: str


class PronunciationResource(BaseModel):
    """单个口音的发音资源（图标 + 音频）"""
    icon: Optional[ResourceItem] = None
    audio: Optional[ResourceItem] = None


class WordResources(BaseModel):
    """单词资源响应 - 按口音分组，方便前端解析"""
    word: str
    us: Optional[PronunciationResource] = None
    uk: Optional[PronunciationResource] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: str = ""
