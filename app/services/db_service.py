"""SQLite database service for dictionary data"""
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WordData:
    """Internal data class for word dictionary data"""
    phonetic_uk: Optional[str] = None
    phonetic_us: Optional[str] = None
    meaning: Optional[str] = None
    # 分词形式
    gqs: Optional[str] = None  # 过去式
    gqfc: Optional[str] = None  # 过去分词
    xzfc: Optional[str] = None  # 现在分词
    fs: Optional[str] = None  # 复数
    examples: Optional[str] = None


class DatabaseService:
    """Service for querying SQLite dictionary databases"""

    _words_conn: Optional[sqlite3.Connection] = None
    _sentence_conn: Optional[sqlite3.Connection] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> bool:
        """Initialize database connections"""
        try:
            db_dir = Path(settings.db_dir)

            # Connect to words.db
            words_db_path = db_dir / "words.db"
            if words_db_path.exists():
                cls._words_conn = sqlite3.connect(str(words_db_path))
                cls._words_conn.row_factory = sqlite3.Row
                logger.info(f"Connected to words.db at {words_db_path}")
            else:
                logger.warning(f"words.db not found at {words_db_path}")

            # Connect to words_sentence.db
            sentence_db_path = db_dir / "words_sentence.db"
            if sentence_db_path.exists():
                cls._sentence_conn = sqlite3.connect(str(sentence_db_path))
                cls._sentence_conn.row_factory = sqlite3.Row
                logger.info(f"Connected to words_sentence.db at {sentence_db_path}")
            else:
                logger.warning(f"words_sentence.db not found at {sentence_db_path}")

            cls._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            cls._initialized = False
            return False

    @classmethod
    def close(cls):
        """Close database connections"""
        if cls._words_conn:
            cls._words_conn.close()
            cls._words_conn = None
        if cls._sentence_conn:
            cls._sentence_conn.close()
            cls._sentence_conn = None
        cls._initialized = False
        logger.info("Database connections closed")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if databases are initialized"""
        return cls._initialized

    @classmethod
    def _parse_additional(cls, additional: Optional[str]) -> dict:
        """
        Parse additional field to extract word forms
        Examples:
        - "过去式 abandoned 过去分词 abandoned 现在分词 abandoning"
        - "复数 abalones"
        """
        if not additional:
            return {}

        result = {}
        patterns = {
            "gqs": r"过去式\s+(\S+)",
            "gqfc": r"过去分词\s+(\S+)",
            "xzfc": r"现在分词\s+(\S+)",
            "fs": r"复数\s+(\S+)",
        }

        for field_name, pattern in patterns.items():
            match = re.search(pattern, additional)
            if match:
                result[field_name] = match.group(1)

        return result

    @classmethod
    def _query_words_db(cls, word: str) -> Optional[dict]:
        """Query words.db for word data

        先尝试小写，如果没找到再尝试原始输入（可能是大写缩写如 ACAS）
        """
        if not cls._words_conn:
            return None

        try:
            # 表名是 'word'，不是 'words'
            # 先尝试小写
            cursor = cls._words_conn.execute(
                "SELECT * FROM word WHERE word = ?", (word.lower(),)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            # 如果没找到，尝试原始大小写（用于缩写词如 ACAS）
            cursor = cls._words_conn.execute(
                "SELECT * FROM word WHERE word = ?", (word,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"Error querying words.db for '{word}': {e}")

        return None

    @classmethod
    def _query_sentence_db(cls, word: str) -> Optional[dict]:
        """Query words_sentence.db for word data

        先尝试首字母大写，如果没找到再尝试小写
        """
        if not cls._sentence_conn:
            return None

        try:
            # 列名需要大写: Word, GQS, GQFC, XZFC, FS, meaning, lx
            # 先尝试首字母大写
            cursor = cls._sentence_conn.execute(
                "SELECT * FROM words WHERE Word = ?", (word,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            # 如果没找到，尝试小写
            cursor = cls._sentence_conn.execute(
                "SELECT * FROM words WHERE Word = ?", (word.lower(),)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"Error querying words_sentence.db for '{word}': {e}")

        return None

    @classmethod
    def get_word_data(cls, word: str) -> Optional[WordData]:
        """
        Get word data from both databases and merge results

        Strategy:
        1. words.db 先尝试小写，再尝试原始输入（用于缩写词如 ACAS）
        2. words_sentence.db 先尝试首字母大写，再尝试小写
        3. 任意一个库查到都要返回
        4. 如果两个库都查到，优先使用 words_sentence 的数据（meaning, forms, examples）
        5. words.db 始终提供音标数据
        """
        word = word.strip()
        if not word:
            return None

        # words.db: 内部会先尝试小写，再尝试原始输入
        words_data = cls._query_words_db(word)

        # words_sentence.db: 内部会先尝试首字母大写，再尝试小写
        word_capitalized = word.lower().capitalize()
        sentence_data = cls._query_sentence_db(word_capitalized)

        # If neither database has the word, return None
        if not words_data and not sentence_data:
            return None

        result = WordData()

        # From words.db: always get phonetics if available
        # 列名: prounce_uk, prounce_us, trans, additional
        if words_data:
            result.phonetic_uk = words_data.get("prounce_uk")
            result.phonetic_us = words_data.get("prounce_us")

        # If sentence db has data, prefer it for meaning, forms, and examples
        # 列名: Word, GQS, GQFC, XZFC, FS, meaning, lx
        if sentence_data:
            # Use meaning field for translation
            result.meaning = sentence_data.get("meaning")

            # Get structured word forms from sentence db (大写列名)
            result.gqs = sentence_data.get("GQS")  # 过去式
            result.gqfc = sentence_data.get("GQFC")  # 过去分词
            result.xzfc = sentence_data.get("XZFC")  # 现在分词
            result.fs = sentence_data.get("FS")  # 复数

            # Get examples (lx 字段)
            result.examples = sentence_data.get("lx")
        elif words_data:
            # Only words.db available - use trans and parse additional
            result.meaning = words_data.get("trans")

            # Parse additional field for word forms
            additional = words_data.get("additional")
            if additional:
                parsed_forms = cls._parse_additional(additional)
                result.gqs = parsed_forms.get("gqs")
                result.gqfc = parsed_forms.get("gqfc")
                result.xzfc = parsed_forms.get("xzfc")
                result.fs = parsed_forms.get("fs")

        return result
