"""Resource API endpoints"""
import logging

from fastapi import APIRouter, HTTPException

from app.models import (
    WordResources,
    WordDictionaryData,
    WordForms,
    ErrorResponse,
)
from app.services import MDDService, DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()
health_router = APIRouter()


def _convert_word_data(word_data) -> WordDictionaryData:
    """Convert internal WordData to API response model"""
    return WordDictionaryData(
        phonetic_uk=word_data.phonetic_uk,
        phonetic_us=word_data.phonetic_us,
        meaning=word_data.meaning,
        forms=WordForms(
            gqs=word_data.gqs,
            gqfc=word_data.gqfc,
            xzfc=word_data.xzfc,
            fs=word_data.fs,
        ),
        examples=word_data.examples,
    )


@health_router.get("/")
async def root():
    """Root endpoint - service status"""
    return {
        "service": "MDD 资源查询 API",
        "status": "running",
        "mdd_loaded": MDDService.is_loaded(),
        "db_initialized": DatabaseService.is_initialized(),
    }


@health_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mdd_loaded": MDDService.is_loaded(),
        "db_initialized": DatabaseService.is_initialized(),
    }


@router.get(
    "/{word}",
    response_model=WordResources,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_word_resources(word: str):
    """
    Get pronunciation resources and dictionary data for a word

    - **word**: English word to query

    Returns:
    - us: American pronunciation {icon, audio}
    - uk: British pronunciation {icon, audio}
    - dictionary: Dictionary data {phonetic_uk, phonetic_us, meaning, forms, examples}
    """
    original_word = word.strip()
    if not original_word:
        raise HTTPException(status_code=400, detail="Word parameter cannot be empty")

    # MDD 资源使用小写查询
    word_lower = original_word.lower()

    # Initialize result
    us_pronunciation = None
    uk_pronunciation = None
    dictionary_data = None

    # Query MDD resources (if available)
    if MDDService.is_loaded():
        try:
            resources = MDDService.get_resources_for_word(word_lower)
            us_pronunciation = resources.get("us")
            uk_pronunciation = resources.get("uk")
        except Exception as e:
            logger.error(f"Error getting MDD resources for '{word_lower}': {e}")
    else:
        logger.warning("MDD files not loaded, pronunciation resources unavailable")

    # Query database (if available) - 使用原始输入，让 DatabaseService 处理大小写
    if DatabaseService.is_initialized():
        try:
            word_data = DatabaseService.get_word_data(original_word)
            if word_data:
                dictionary_data = _convert_word_data(word_data)
        except Exception as e:
            logger.error(f"Error getting dictionary data for '{original_word}': {e}")
    else:
        logger.warning("Database not initialized, dictionary data unavailable")

    # Check if we have any data
    if not us_pronunciation and not uk_pronunciation and not dictionary_data:
        logger.info(f"No resources found for word: {original_word}")

    return WordResources(
        word=word_lower,
        us=us_pronunciation,
        uk=uk_pronunciation,
        dictionary=dictionary_data,
    )


@router.get("/search/{pattern}")
async def search_resources(pattern: str, limit: int = 20):
    """
    Search for matching resource keys

    - **pattern**: Search pattern
    - **limit**: Result limit (default 20)
    """
    if not MDDService.is_loaded():
        raise HTTPException(
            status_code=500,
            detail="MDD files not loaded"
        )

    matches = MDDService.find_matching_keys(pattern)[:limit]
    return {
        "pattern": pattern,
        "matches": [{"mdd_file": m[0], "key": m[1]} for m in matches],
        "count": len(matches)
    }
