"""劇本結構分析 — 用 Claude 分析原始字幕，提取劇本結構"""

from __future__ import annotations

import json

from ..utils import llm_client


SYSTEM = "你是一個專業的短劇編劇顧問，擅長分析劇本結構。"

ANALYZE_PROMPT = """分析以下短劇字幕，提取劇本結構：

標題: {title}
字幕內容:
{subtitle_text}

請分析並回傳 JSON：
{{
  "title": "劇名",
  "genre": "類型（都市/古裝/懸疑/甜寵/復仇/...）",
  "summary": "100 字劇情摘要",
  "characters": [
    {{
      "name": "角色名",
      "gender": "男/女",
      "role": "主角/配角/反派",
      "description": "簡短描述",
      "age_range": "年齡範圍"
    }}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "location": "場景地點",
      "characters_present": ["角色名"],
      "action": "場景動作描述",
      "dialogue_summary": "對話摘要",
      "emotion": "場景情緒（緊張/甜蜜/悲傷/...）",
      "duration_hint": "預估秒數"
    }}
  ],
  "hooks": ["開場鉤子描述"],
  "turning_points": ["轉折點描述"],
  "emotional_arc": "情感曲線描述"
}}"""


def analyze_script(title: str, subtitle_text: str) -> dict:
    """分析一部短劇的字幕，提取結構化劇本資訊"""
    prompt = ANALYZE_PROMPT.format(title=title, subtitle_text=subtitle_text[:6000])
    resp = llm_client.chat_json(prompt, system=SYSTEM)

    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        return {"raw": resp, "error": "JSON parse failed"}


def batch_analyze(scripts: list[dict]) -> list[dict]:
    """批次分析多部短劇"""
    results = []
    for s in scripts:
        result = analyze_script(
            title=s.get("title", "未知"),
            subtitle_text=s.get("description", ""),
        )
        result["video_id"] = s.get("video_id")
        results.append(result)
    return results
