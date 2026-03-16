"""探索影片結構分析 — 用 Claude 分析原始字幕，提取探索腳本結構"""

from __future__ import annotations

import json

from ..utils import llm_client


SYSTEM = "你是一個專業的廢墟探索/都市探險(Urban Exploration)影片分析師，擅長分析探索影片的敘事結構、氛圍營造和張力設計。"

ANALYZE_PROMPT = """分析以下廢墟探索影片字幕，提取探索結構：

標題: {title}
字幕內容:
{subtitle_text}

請分析並回傳 JSON：
{{
  "title": "影片名",
  "building_type": "建築類型（廢棄醫院/工廠/學校/豪宅/地下室等）",
  "summary": "100 字探索摘要",
  "explorer_style": "探索者風格（冷靜分析型/驚恐反應型/幽默吐槽型等）",
  "zones_explored": [
    {{
      "zone_name": "區域名稱",
      "description": "區域描述",
      "atmosphere": "氛圍描述（陰暗/壓迫/詭異等）",
      "duration_hint": "預估秒數"
    }}
  ],
  "encounters": [
    {{
      "type": "遭遇類型（異響/人影/文件/血跡/動物/陷阱等）",
      "location": "發生位置",
      "tension_level": "張力等級 1-10",
      "description": "遭遇描述"
    }}
  ],
  "hooks": ["開場鉤子描述"],
  "tension_peaks": ["張力高峰描述"],
  "tension_curve": "張力曲線描述（如：緩升→多次peak→急降→懸念收場）",
  "atmosphere_techniques": ["氛圍手法1", "氛圍手法2"],
  "ending_type": "結局類型（帶線索離開/被嚇跑/發現秘密/迷路等）"
}}"""


def analyze_script(title: str, subtitle_text: str) -> dict:
    """分析一部探索影片的字幕，提取結構化探索腳本資訊"""
    prompt = ANALYZE_PROMPT.format(title=title, subtitle_text=subtitle_text[:6000])
    resp = llm_client.chat_json(prompt, system=SYSTEM)

    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        return {"raw": resp, "error": "JSON parse failed"}


def batch_analyze(scripts: list[dict]) -> list[dict]:
    """批次分析多部探索影片"""
    results = []
    for s in scripts:
        result = analyze_script(
            title=s.get("title", "未知"),
            subtitle_text=s.get("description", ""),
        )
        result["video_id"] = s.get("video_id")
        results.append(result)
    return results
