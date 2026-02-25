import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.mdd_service import MDDService
from models.schemas import WordResources, ErrorResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动时预加载 MDD 文件"""
    logger.info("Starting MDD API service...")

    # 预加载 MDD 文件
    success = MDDService.load_mdd_files()
    if success:
        logger.info("MDD files loaded successfully")
    else:
        logger.warning("Failed to load MDD files - service may not work properly")

    yield

    logger.info("Shutting down MDD API service...")


# 创建 FastAPI 应用
app = FastAPI(
    title="MDD 资源查询 API",
    description="查询 MDD 发音库中的音频和图片资源",
    version="0.1.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """根路径 - 服务状态"""
    return {
        "service": "MDD 资源查询 API",
        "status": "running",
        "mdd_loaded": MDDService.is_loaded()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "mdd_loaded": MDDService.is_loaded()
    }


@app.get(
    "/resources/{word}",
    response_model=WordResources,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["Resources"]
)
async def get_word_resources(word: str):
    """
    获取单词的发音资源，按口音分组

    - **word**: 要查询的英文单词

    返回:
    - us: 美式发音 {icon, audio}
    - uk: 英式发音 {icon, audio}
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

        # 如果没有找到任何资源
        if not resources["us"] and not resources["uk"]:
            logger.info(f"No resources found for word: {word}")

        return resources

    except Exception as e:
        logger.error(f"Error processing request for word '{word}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get(
    "/search/{pattern}",
    response_model=dict,
    tags=["Resources"]
)
async def search_resources(pattern: str, limit: int = 20):
    """
    搜索匹配的资源键名

    - **pattern**: 搜索模式
    - **limit**: 返回结果数量限制 (默认 20)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
