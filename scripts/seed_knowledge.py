"""Seed knowledge base with genres and styles using LLM.

Usage:
    python -m scripts.seed_knowledge
"""

from __future__ import annotations

import json
import logging
import sys

from src.utils import llm_client
from src.knowledge.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED_SYSTEM = "你是一個短劇創作專家。請用純 JSON 格式回覆，不要包含 markdown code block。"

GENRES_PROMPT = """請生成 30 個短劇劇本類型，每個類型包含名稱、英文名、描述和範例。
涵蓋主流和新興的短劇類型，如都市、古裝、懸疑、科幻、校園、軍旅、仙俠、末日、職場、農村、醫療等。

回傳 JSON 格式：
{
  "genres": [
    {
      "name": "類型名稱",
      "name_en": "Genre name in English",
      "description": "這個類型的核心特徵、常見設定和受眾吸引力",
      "examples": ["代表作品或典型劇情1", "代表作品或典型劇情2"]
    }
  ]
}

要求：
- 每個類型的描述要具體，不少於 30 字
- 必須剛好 30 個類型
- 涵蓋不同題材方向"""

STYLES_PROMPT = """請生成 30 個短劇風格，每個風格包含名稱、英文名、描述和範例。
涵蓋主流和新興的短劇風格，如甜寵、虐戀、爽文、暗黑、搞笑、治癒、懸疑燒腦、熱血、沙雕、反轉等。

回傳 JSON 格式：
{
  "styles": [
    {
      "name": "風格名稱",
      "name_en": "Style name in English",
      "description": "這個風格的調性、情緒特徵和觀眾期待",
      "examples": ["代表作品或典型表現1", "代表作品或典型表現2"]
    }
  ]
}

要求：
- 每個風格的描述要具體，不少於 30 字
- 必須剛好 30 個風格
- 涵蓋不同情緒和調性方向"""


def seed_category(kb: KnowledgeBase, category: str, prompt: str, key: str) -> int:
    """Generate and seed entries for a category. Returns count of entries added."""
    logger.info("Generating %s seed data via LLM...", category)
    resp = llm_client.chat_json(prompt, system=SEED_SYSTEM, temperature=0.7)

    try:
        data = json.loads(resp)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response for %s: %s", category, resp[:300])
        return 0

    items = data.get(key, [])
    logger.info("Received %d %s items from LLM", len(items), category)

    added = 0
    for item in items:
        name = item.get("name", "")
        if not name:
            continue

        # Skip if similar entry already exists
        existing = kb.find_similar(category, name)
        if existing:
            logger.info("  Skip (exists): %s", name)
            continue

        examples = []
        for ex in item.get("examples", []):
            examples.append({
                "drama_title": "種子數據",
                "video_id": "",
                "excerpt": ex if isinstance(ex, str) else str(ex),
                "context": "",
            })

        kb.add_entry(category, {
            "name": name,
            "name_en": item.get("name_en", ""),
            "description": item.get("description", ""),
            "tags": [category],
            "examples": examples,
            "effectiveness_score": 5,
        })
        added += 1
        logger.info("  Added: %s", name)

    return added


def main():
    kb = KnowledgeBase()

    logger.info("=== Seeding genres ===")
    genre_count = seed_category(kb, "genres", GENRES_PROMPT, "genres")
    logger.info("Genres added: %d", genre_count)

    logger.info("=== Seeding styles ===")
    style_count = seed_category(kb, "styles", STYLES_PROMPT, "styles")
    logger.info("Styles added: %d", style_count)

    logger.info("=== Done! Total: %d genres + %d styles ===", genre_count, style_count)


if __name__ == "__main__":
    main()
