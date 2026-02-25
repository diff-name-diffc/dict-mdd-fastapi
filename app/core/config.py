"""Application configuration"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "MDD 资源查询 API"
    app_version: str = "0.1.0"
    debug: bool = False

    # MDD files
    mdd_dir: Path = Path(__file__).parent.parent.parent.parent / "resource"
    mdd_files: list[str] = ["Sound_us_uk.mdd", "sound.mdd"]

    # CORS
    cors_origins: list[str] = ["*"]

    class Config:
        env_prefix = "MDD_"
        env_file = ".env"


settings = Settings()
