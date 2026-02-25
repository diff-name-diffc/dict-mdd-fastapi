"""API v1 router aggregation"""
from fastapi import APIRouter

from app.api.v1.endpoints import resources

api_router = APIRouter()
api_router.include_router(resources.router, prefix="/resources", tags=["Resources"])
api_router.include_router(resources.health_router, tags=["Health"])
