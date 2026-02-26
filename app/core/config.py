"""Application configuration"""
from pathlib import Path
from pydantic import Extra
from pydantic_settings import BaseSettings

# Base directory (project root)
BASE_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "MDD 资源查询 API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Resource directories (MDD files and databases)
    # Dev: ./resources, Production: /home/jk/resources/english/us-uk
    resource_dir: Path = BASE_DIR / "resources"
    db_dir: Path = BASE_DIR / "resources"

    # MDD files to load
    mdd_files: list[str] = ["Sound_us_uk.mdd", "sound.mdd"]

    # CORS
    cors_origins: list[str] = ["*"]

    model_config = {
        "env_prefix": "MDD_",
        "env_file": ".env",
        "extra": Extra.ignore,
    }


settings = Settings()
