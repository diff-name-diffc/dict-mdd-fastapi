import subprocess
import base64
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# MDD 文件路径
MDD_DIR = Path(__file__).parent.parent.parent
MDD_FILES = [
    "Sound_us_uk.mdd",
    "sound.mdd",
]


class MDDService:
    """MDD 资源查询服务"""

    # 存储所有资源的字典索引 {key_lower: (mdd_filename, original_key, data)}
    _resource_index: Dict[str, Tuple[str, bytes, bytes]] = {}
    # 存储图标资源 {accent: (filename, content_type, data)}
    _icons: Dict[str, Tuple[str, str, bytes]] = {}
    _loaded = False

    @classmethod
    def load_mdd_files(cls) -> bool:
        """预加载所有 MDD 文件并构建索引"""
        if cls._loaded:
            return True

        try:
            from readmdict import MDD

            for filename in MDD_FILES:
                filepath = MDD_DIR / filename
                if filepath.exists():
                    logger.info(f"Loading MDD file: {filepath}")
                    mdd = MDD(str(filepath))

                    # 构建资源索引
                    count = 0
                    for key, data in mdd.items():
                        key_str = key.decode('utf-8', errors='ignore') if isinstance(key, bytes) else key
                        key_lower = key_str.lower()
                        cls._resource_index[key_lower] = (filename, key_str, data)
                        count += 1

                    logger.info(f"Loaded {filename} with {count} entries")
                else:
                    logger.warning(f"MDD file not found: {filepath}")

            # 缓存图标资源
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
        """缓存播放图标资源"""
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
        """检查 MDD 文件是否已加载"""
        return cls._loaded

    @classmethod
    def find_matching_keys(cls, word: str) -> List[Tuple[str, str, bytes]]:
        """
        在索引中查找匹配的资源
        返回: [(mdd_filename, key, data), ...]
        """
        if not cls._loaded:
            return []

        matches = []
        word_lower = word.lower()

        # 构建精确匹配的键
        # 格式: \hello.spx (美式) 或 \hello_Uk.spx (英式)
        search_keys = [
            f"\\{word_lower}.spx",      # 美式
            f"\\{word_lower}_uk.spx",   # 英式
        ]

        for search_key in search_keys:
            if search_key in cls._resource_index:
                mdd_name, original_key, data = cls._resource_index[search_key]
                matches.append((mdd_name, original_key, data))

        return matches

    @classmethod
    def convert_spx_to_mp3(cls, spx_bytes: bytes) -> Optional[bytes]:
        """使用 ffmpeg 将 SPX 音频转换为 MP3"""
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
        获取单词的所有资源，按口音分组
        返回格式: {word, us: {icon, audio}, uk: {icon, audio}}
        """
        result = {
            "word": word,
            "us": None,
            "uk": None
        }

        if not cls._loaded:
            return result

        # 查找匹配的音频资源
        matches = cls.find_matching_keys(word)

        for mdd_name, key, raw_data in matches:
            # 提取文件名 (去掉前导反斜杠)
            clean_key = key.lstrip('\\')
            filename = Path(clean_key).name

            # 判断口音类型: 英式有 _Uk 后缀，美式没有
            accent = "uk" if "_uk" in filename.lower() else "us"

            # 转换音频格式
            if filename.lower().endswith('.spx'):
                mp3_data = cls.convert_spx_to_mp3(raw_data)
                if mp3_data:
                    mp3_filename = filename.replace('.spx', '.mp3')

                    # 构建该口音的资源
                    pron_resource = {
                        "icon": None,
                        "audio": {
                            "filename": mp3_filename,
                            "base64_data": base64.b64encode(mp3_data).decode('utf-8'),
                            "content_type": "audio/mpeg"
                        }
                    }

                    # 添加对应图标
                    if accent in cls._icons:
                        icon_filename, icon_type, icon_data = cls._icons[accent]
                        pron_resource["icon"] = {
                            "filename": icon_filename,
                            "base64_data": base64.b64encode(icon_data).decode('utf-8'),
                            "content_type": icon_type
                        }

                    result[accent] = pron_resource

        return result
