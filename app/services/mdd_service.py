"""MDD resource service for querying pronunciation files"""
import base64
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class MDDService:
    """Service for querying MDD pronunciation resources"""

    # Resource index: {key_lower: (mdd_filename, original_key, data)}
    _resource_index: Dict[str, Tuple[str, str, bytes]] = {}
    # Cached icons: {accent: (filename, content_type, data)}
    _icons: Dict[str, Tuple[str, str, bytes]] = {}
    _loaded: bool = False

    @classmethod
    def load_mdd_files(cls) -> bool:
        """Preload all MDD files and build index"""
        if cls._loaded:
            return True

        try:
            from readmdict import MDD

            logger.info(f"MDD resource_dir: {settings.resource_dir}")
            logger.info(f"MDD db_dir: {settings.db_dir}")
            logger.info(f"MDD files to load: {settings.mdd_files}")

            for filename in settings.mdd_files:
                filepath = settings.resource_dir / filename
                if filepath.exists():
                    logger.info(f"Loading MDD file: {filepath}")
                    mdd = MDD(str(filepath))

                    count = 0
                    for key, data in mdd.items():
                        key_str = key.decode('utf-8', errors='ignore') if isinstance(key, bytes) else key
                        key_lower = key_str.lower()
                        cls._resource_index[key_lower] = (filename, key_str, data)
                        count += 1

                    logger.info(f"Loaded {filename} with {count} entries")
                else:
                    logger.warning(f"MDD file not found: {filepath}")

            cls._cache_icons()

            cls._loaded = bool(cls._resource_index)
            logger.info(f"Total resources indexed: {len(cls._resource_index)}")
            return cls._loaded

        except Exception as e:
            logger.error(f"Failed to load MDD files: {e}")
            import traceback
            traceback.print_exc()
            return False

    @classmethod
    def _cache_icons(cls):
        """Cache speaker icons"""
        icon_keys = {
            "us": "\\snd_us.png",
            "uk": "\\snd_uk.png"
        }

        for accent, key in icon_keys.items():
            if key in cls._resource_index:
                _, original_key, data = cls._resource_index[key]
                clean_key = original_key.lstrip('\\')
                filename = Path(clean_key).name
                cls._icons[accent] = (filename, 'image/png', data)

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if MDD files are loaded"""
        return cls._loaded

    @classmethod
    def find_matching_keys(cls, word: str) -> List[Tuple[str, str, bytes]]:
        """
        Find matching resources in index
        Returns: [(mdd_filename, key, data), ...]
        """
        if not cls._loaded:
            return []

        matches = []
        word_lower = word.lower()

        search_keys = [
            f"\\{word_lower}.spx",      # US
            f"\\{word_lower}_uk.spx",   # UK
        ]

        for search_key in search_keys:
            if search_key in cls._resource_index:
                mdd_name, original_key, data = cls._resource_index[search_key]
                matches.append((mdd_name, original_key, data))

        return matches

    @classmethod
    def convert_spx_to_mp3(cls, spx_bytes: bytes) -> Optional[bytes]:
        """Convert SPX audio to MP3 using ffmpeg"""
        try:
            proc = subprocess.Popen(
                ['ffmpeg', '-y', '-i', 'pipe:0', '-acodec', 'libmp3lame',
                 '-ab', '128k', '-f', 'mp3', 'pipe:1'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            mp3_bytes, stderr = proc.communicate(input=spx_bytes, timeout=30)

            if proc.returncode != 0:
                logger.error(f"ffmpeg error: {stderr.decode('utf-8', errors='ignore')}")
                return None

            return mp3_bytes

        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error("ffmpeg timeout")
            return None
        except FileNotFoundError:
            logger.error("ffmpeg not found. Please install ffmpeg.")
            return None
        except Exception as e:
            logger.error(f"Error converting SPX to MP3: {e}")
            return None

    @classmethod
    def get_resources_for_word(cls, word: str) -> Dict:
        """
        Get all resources for a word, grouped by accent
        Returns: {word, us: {icon, audio}, uk: {icon, audio}}
        """
        result = {
            "word": word,
            "us": None,
            "uk": None
        }

        if not cls._loaded:
            return result

        matches = cls.find_matching_keys(word)

        for mdd_name, key, raw_data in matches:
            clean_key = key.lstrip('\\')
            filename = Path(clean_key).name

            # Determine accent: UK has _uk suffix, US doesn't
            accent = "uk" if "_uk" in filename.lower() else "us"

            if filename.lower().endswith('.spx'):
                mp3_data = cls.convert_spx_to_mp3(raw_data)
                if mp3_data:
                    mp3_filename = filename.replace('.spx', '.mp3')

                    pron_resource = {
                        "icon": None,
                        "audio": {
                            "filename": mp3_filename,
                            "base64_data": base64.b64encode(mp3_data).decode('utf-8'),
                            "content_type": "audio/mpeg"
                        }
                    }

                    if accent in cls._icons:
                        icon_filename, icon_type, icon_data = cls._icons[accent]
                        pron_resource["icon"] = {
                            "filename": icon_filename,
                            "base64_data": base64.b64encode(icon_data).decode('utf-8'),
                            "content_type": icon_type
                        }

                    result[accent] = pron_resource

        return result
