"""Resource API endpoints"""
import logging

from fastapi import APIRouter, HTTPException

from app.models import WordResources, ErrorResponse
from app.services import MDDService

logger = logging.getLogger(__name__)

router = APIRouter()
health_router = APIRouter()


@health_router.get("/")
async def root():
    """Root endpoint - service status"""
    return {
        "service": "MDD 资源查询 API",
        "status": "running",
        "mdd_loaded": MDDService.is_loaded()
    }


@health_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mdd_loaded": MDDService.is_loaded()
    }


@router.get(
    "/{word}",
    response_model=WordResources,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_word_resources(word: str):
    """
    Get pronunciation resources for a word, grouped by accent

    - **word**: English word to query

    Returns:
    - us: American pronunciation {icon, audio}
    - uk: British pronunciation {icon, audio}
    """
    if not MDDService.is_loaded():
        raise HTTPException(
            status_code=500,
            detail="MDD files not loaded. Please check server logs."
        )

    word = word.strip().lower()
    if not word:
        raise HTTPException(status_code=400, detail="Word parameter cannot be empty")

    try:
        resources = MDDService.get_resources_for_word(word)

        if not resources["us"] and not resources["uk"]:
            logger.info(f"No resources found for word: {word}")

        return resources

    except Exception as e:
        logger.error(f"Error processing request for word '{word}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
