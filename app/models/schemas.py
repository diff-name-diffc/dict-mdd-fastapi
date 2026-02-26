"""API response schemas"""
from typing import Optional
from pydantic import BaseModel, Field


class WordForms(BaseModel):
    """单词的分词形式"""
    gqs: Optional[str] = Field(None, description="过去式")
    gqfc: Optional[str] = Field(None, description="过去分词")
    xzfc: Optional[str] = Field(None, description="现在分词")
    fs: Optional[str] = Field(None, description="复数")


class WordDictionaryData(BaseModel):
    """单词的词典数据"""
    phonetic_uk: Optional[str] = Field(None, description="英式音标")
    phonetic_us: Optional[str] = Field(None, description="美式音标")
    meaning: Optional[str] = Field(None, description="词义/翻译")
    forms: WordForms = Field(default_factory=WordForms)
    examples: Optional[str] = Field(None, description="例句(原始字符串)")


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
    dictionary: Optional[WordDictionaryData] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str = ""
