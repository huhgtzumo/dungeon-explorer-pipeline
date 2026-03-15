"""用 Claude 深度分析爆款短劇模式"""

from __future__ import annotations

import json
import logging

from ..utils import llm_client
from ..utils.config import PROJECT_ROOT
from ..utils.index_db import generate_id, add_analysis

logger = logging.getLogger(__name__)


def _smart_truncate(text: str, max_chars: int = 30000) -> str:
    """Smart truncation: if text exceeds max_chars, take first half + last half.
    For short texts, return as-is (full text)."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n... (中間省略) ...\n\n" + text[-half:]


ANALYSIS_SYSTEM = """你是一個頂級短劇市場分析師和劇本結構專家。
你精通三幕結構、英雄旅程、情感曲線設計、節奏控制等敘事技巧。
你的分析要深入到「為什麼這些劇會爆」的底層邏輯，而不只是表面歸納。"""

ANALYSIS_PROMPT = """深度分析以下爆款短劇資料，找出它們成功的底層模式：

{scripts_data}

請進行多維度深度分析，回傳 JSON：
{{
  "summary": "500 字深度總結：為什麼這些劇會爆？共同的成功密碼是什麼？",

  "narrative_structure": {{
    "opening_hook": "分析開場前 30 秒的鉤子設計模式（如何在最短時間抓住觀眾）",
    "rising_action": "上升動作的共同模式（衝突如何層層遞進）",
    "climax": "高潮設計的共同特徵（情緒頂點如何打造）",
    "resolution": "結局模式（開放式/反轉/大團圓/留懸念）",
    "mini_climaxes": ["每 1-2 分鐘出現的小高潮/衝突點模式1", "模式2", "..."],
    "act_structure": "整體幕結構分析（幾幕？每幕佔比？轉折點在哪？）"
  }},

  "pacing": {{
    "overall_tempo": "整體節奏特徵（快節奏/慢燃/前慢後快 等）",
    "tension_curve": "張力曲線描述（如：開場高張力→短暫舒緩→持續攀升→爆發）",
    "scene_rhythm": "場景切換節奏（平均每場幾秒？密集還是留白？）",
    "cliffhanger_pattern": "懸念/鉤子在什麼時間點出現？間隔多少？",
    "emotional_beats": "情緒節拍設計（笑點、淚點、爽點的分布規律）"
  }},

  "plot_twists": [
    {{
      "type": "反轉類型（身份揭露/背叛/誤會/逆襲/隱藏實力 等）",
      "timing": "通常出現在什麼位置（佔比幾%的地方）",
      "setup": "反轉前的鋪墊手法",
      "impact": "反轉的情緒衝擊力分析"
    }}
  ],

  "common_themes": ["主題1", "主題2", "..."],

  "hook_patterns": [
    {{
      "pattern": "鉤子模式描述",
      "example": "典型例子",
      "effectiveness": "為什麼有效"
    }}
  ],

  "emotional_arcs": [
    {{
      "arc_type": "情感曲線類型名稱",
      "description": "詳細描述情感走向",
      "key_moments": ["關鍵情感轉折1", "轉折2"]
    }}
  ],

  "character_archetypes": [
    {{
      "archetype": "角色原型",
      "traits": "核心特質",
      "audience_appeal": "為什麼觀眾喜歡這類角色"
    }}
  ],

  "dialogue_patterns": [
    "爆款對白模式1（如：金句型、反差型、情緒爆發型）",
    "模式2"
  ],

  "story_structures": ["結構模式1", "模式2"],

  "recommended_elements": [
    "基於以上分析，創作新劇本時必須包含的元素1",
    "元素2"
  ],

  "benchmark": {{
    "avg_scene_count": "平均場景數",
    "avg_duration_sec": "平均時長（秒）",
    "avg_dialogue_ratio": "對白佔比（估計）",
    "optimal_twist_count": "建議反轉次數",
    "optimal_hook_interval": "建議懸念間隔（秒）"
  }}
}}

重要：
- 每個欄位都要有實質內容，不要只寫「很好」「有效」這種空話
- 結合具體的劇情例子來說明模式
- 分析要深入到「觀眾心理」層面——為什麼這個設計能引發情緒反應
- 如果資料中有字幕/劇本內容，要仔細分析劇情結構，不要只看標題"""


def analyze_trending(scripts: list[dict]) -> dict:
    """分析多部爆款短劇的共同模式

    Args:
        scripts: list of {video_id, title, description, views, channel, duration, ...}

    Returns:
        分析結果 dict
    """
    # 只取前 10 部，避免 prompt 太長
    top_scripts = sorted(scripts, key=lambda x: x.get("views", 0), reverse=True)[:10]

    scripts_text = ""
    for i, s in enumerate(top_scripts, 1):
        scripts_text += f"\n--- 短劇 {i} ---\n"
        scripts_text += f"標題: {s.get('title', 'N/A')}\n"
        scripts_text += f"頻道: {s.get('channel', 'N/A')}\n"
        scripts_text += f"播放量: {s.get('views', 'N/A')}\n"
        scripts_text += f"時長: {s.get('duration', 'N/A')} 秒\n"
        # Use subtitle text if available, fall back to description
        sub = s.get("subtitle", {})
        content = (sub.get("text", "") if isinstance(sub, dict) else "") or s.get("text", "") or s.get("description", "")
        if content:
            scripts_text += f"字幕/內容:\n{content}\n"
        else:
            scripts_text += "字幕/內容: (無)\n"

    prompt = ANALYSIS_PROMPT.format(scripts_data=scripts_text)
    resp = llm_client.chat_json(prompt, system=ANALYSIS_SYSTEM)

    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        return {"raw_analysis": resp, "error": "JSON parse failed"}


def analyze_and_save(
    videos: list[dict],
    name: str = "",
    source_crawl_ids: list[str] | None = None,
    source_video_ids: list[str] | None = None,
) -> tuple[str, dict]:
    """Analyze videos and save result to data/analyses/{id}.json + update index.

    Returns:
        (analysis_id, analysis_result)
    """
    analysis_id = generate_id("analysis")
    analysis = analyze_trending(videos)

    # Save to file
    analyses_dir = PROJECT_ROOT / "data" / "analyses"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    out_path = analyses_dir / f"{analysis_id}.json"
    analysis["analysis_id"] = analysis_id
    analysis["source_crawl_ids"] = source_crawl_ids or []
    analysis["source_video_ids"] = [v.get("video_id", "") for v in videos]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # Update index
    rel_path = str(out_path.relative_to(PROJECT_ROOT))
    add_analysis(
        analysis_id,
        name or f"分析 ({len(videos)} 部)",
        source_crawl_ids or [],
        source_video_ids or [v.get("video_id", "") for v in videos],
        rel_path,
    )

    return analysis_id, analysis


# ──────────────── Single Drama Deep Analysis (for Knowledge Base) ────────────────

SINGLE_ANALYSIS_SYSTEM = """你是一個頂級短劇結構分析師。
你的任務是對單部短劇進行極其詳細的結構拆解，識別出所有可複用的創作元素。
每個識別出的元素必須附帶該劇中的具體範例摘錄（從字幕/內容中截取）。
輸出純 JSON。"""

SINGLE_ANALYSIS_PROMPT = """對以下短劇進行深度結構拆解，識別所有可複用的創作元素：

## 短劇資料
- 標題: {title}
- 頻道: {channel}
- 播放量: {views}
- 時長: {duration} 秒
- 字幕/內容:
{content}

請回傳以下 JSON 格式（每個元素必須帶上「範例摘錄」——從上方字幕/內容中截取相關片段）：
{{
  "drama_summary": "這部劇的一句話總結",

  "structure": {{
    "type": "架構類型名稱（如：三幕式反轉、五幕漸進式、雙線交錯、環形結構等）",
    "type_en": "Structure type in English",
    "description": "詳細描述這個架構如何運作",
    "act_breakdown": "每幕的內容和佔比",
    "excerpt": "體現這個架構的關鍵段落摘錄"
  }},

  "hooks": [
    {{
      "type": "鉤子類型（如：懸念開場、衝突開場、倒敘開場、反差開場等）",
      "type_en": "Hook type in English",
      "description": "這個鉤子如何運作、為什麼有效",
      "timing": "出現在什麼位置（開場/中段/結尾）",
      "excerpt": "相關的字幕/內容摘錄"
    }}
  ],

  "elements": {{
    "characters": [
      {{
        "type": "人設類型（如：隱忍女主、霸道總裁、腹黑反派等）",
        "type_en": "Character type in English",
        "description": "這個人設的核心特質和吸引力",
        "excerpt": "體現這個人設的對白/行為摘錄"
      }}
    ],
    "character_combos": [
      {{
        "type": "人設組合（如：霸總×灰姑娘、腹黑閨蜜×天真女主、冷面軍官×嬌蠻千金）",
        "type_en": "Character combo in English",
        "description": "這個人設組合的化學反應和衝突張力",
        "excerpt": "相關摘錄"
      }}
    ],
    "settings": [
      {{
        "type": "場景類型（如：豪門宴會、醫院病房、法庭對峙等）",
        "type_en": "Setting type in English",
        "description": "這個場景為什麼有戲劇張力",
        "excerpt": "相關摘錄"
      }}
    ],
    "relationships": [
      {{
        "type": "關係類型（如：假夫妻真動心、閨蜜背叛、師徒反目等）",
        "type_en": "Relationship type in English",
        "description": "這個關係類型的衝突核心",
        "excerpt": "相關摘錄"
      }}
    ]
  }},

  "payoffs": [
    {{
      "type": "爽點類型（如：打臉復仇、身份揭露、逆襲翻盤、真相大白、深情告白等）",
      "type_en": "Payoff type in English",
      "description": "這個爽點為什麼讓觀眾滿足",
      "emotional_impact": "觸發的核心情緒（爽快/感動/震驚/解氣）",
      "excerpt": "相關摘錄"
    }}
  ],

  "pacing": {{
    "tempo": "整體節奏描述（快節奏/慢燃/前慢後快等）",
    "tension_curve": "張力曲線描述（如：開場高張力→短暫舒緩→持續攀升→爆發）",
    "key_beats": ["節拍1", "節拍2", "節拍3"],
    "excerpt": "體現節奏特點的段落摘錄"
  }},

  "dialogues": [
    {{
      "type": "對白類型（如：威脅型、反擊型、撒糖型、揭露型、金句型）",
      "type_en": "Dialogue type in English",
      "description": "這類對白的套路和特徵",
      "emotional_function": "在劇情中的情緒功能（製造壓迫/爽感/甜蜜/震撼）",
      "excerpt": "實際對白摘錄"
    }}
  ],

  "visual_scenes": [
    {{
      "type": "視覺場景類型（如：婚禮被搶、會議室對峙、雨中告白、豪車接人等）",
      "type_en": "Visual scene type in English",
      "description": "這個視覺場景的戲劇效果",
      "dramatic_tension": "畫面張力來源",
      "excerpt": "相關摘錄"
    }}
  ],

  "ending_hooks": [
    {{
      "type": "結尾鉤子類型（如：懸念型、反轉型、情感衝擊型、身份揭露型）",
      "type_en": "Ending hook type in English",
      "description": "這個結尾鉤子如何留住觀眾",
      "timing": "在集末的具體位置（最後幾秒/最後一句台詞/畫面定格）",
      "excerpt": "相關摘錄"
    }}
  ],

  "tension_actions": [
    {{
      "type": "張力行為類型（如：打巴掌、潑水、壁咚、摔杯子、撕文件、扔戒指等）",
      "type_en": "Tension action type in English",
      "description": "這個行為的戲劇功能和視覺衝擊",
      "visual_impact": "視覺衝擊力描述",
      "excerpt": "相關摘錄"
    }}
  ],

  "genres": [
    {{
      "type": "劇本類型（如：都市、古裝、懸疑、科幻、校園、軍旅、仙俠等）",
      "type_en": "Genre type in English",
      "description": "這個類型的核心特徵和受眾吸引力"
    }}
  ],

  "styles": [
    {{
      "type": "風格（如：甜寵、虐戀、爽文、暗黑、搞笑、治癒等）",
      "type_en": "Style type in English",
      "description": "這個風格的調性和情緒特徵"
    }}
  ],

  "tags": ["tag1", "tag2", "tag3"]
}}

重要：
- 每個元素的 excerpt 必須是從字幕/內容中截取的實際片段，不是你自己編的
- 如果字幕內容不足，excerpt 可以寫「（字幕資料不足，基於標題和描述推斷）」加上你的推斷
- 分析要深入到觀眾心理層面
- hooks 至少識別 2 個，elements 的每個子類至少 1 個，payoffs 至少 2 個
- dialogues 至少 2 個，visual_scenes 至少 1 個，ending_hooks 至少 1 個，tension_actions 至少 1 個"""


def is_video_in_knowledge_base(video_id: str) -> bool:
    """Check if a video has already been analyzed and stored in the knowledge base."""
    from ..knowledge.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    return kb.has_drama(video_id)


def analyze_single_drama(video_data: dict) -> dict:
    """Deep analysis of a single drama for knowledge base extraction.

    Args:
        video_data: dict with title, channel, views, duration, description/text, video_id

    Returns:
        Structured analysis result dict
    """
    # Check if already in knowledge base
    video_id = video_data.get("video_id", "")
    if video_id and is_video_in_knowledge_base(video_id):
        return {
            "error": "already_in_kb",
            "video_id": video_id,
            "title": video_data.get("title", ""),
            "message": f"視頻 {video_id} 已在知識庫中，跳過重複分析",
        }

    # Prefer subtitle text, then text, then description
    sub = video_data.get("subtitle", {})
    content = (sub.get("text", "") if isinstance(sub, dict) else "") or video_data.get("text", "") or video_data.get("description", "")
    if not content:
        content = "(無字幕/內容資料)"

    prompt = SINGLE_ANALYSIS_PROMPT.format(
        title=video_data.get("title", "N/A"),
        channel=video_data.get("channel", "N/A"),
        views=video_data.get("views", "N/A"),
        duration=video_data.get("duration", "N/A"),
        content=_smart_truncate(content, 30000),
    )

    resp = llm_client.chat_json(prompt, system=SINGLE_ANALYSIS_SYSTEM)
    try:
        result = json.loads(resp)
        result["video_id"] = video_data.get("video_id", "")
        result["title"] = video_data.get("title", "")
        return result
    except json.JSONDecodeError:
        logger.error("Single drama analysis JSON parse failed: %s", resp[:300])
        return {
            "raw_analysis": resp,
            "error": "JSON parse failed",
            "video_id": video_data.get("video_id", ""),
            "title": video_data.get("title", ""),
        }


def extract_to_knowledge_base(analysis_result: dict, video_data: dict) -> dict:
    """Extract analysis results into knowledge base entries.

    Decomposes a single drama analysis into individual KB entries:
    - structure -> structures/
    - hooks -> hooks/
    - characters/settings/relationships/character_combos -> elements/ (with subcategory)
    - payoffs -> payoffs/
    - pacing -> pacing/
    - dialogues -> dialogues/
    - visual_scenes -> visual_scenes/
    - ending_hooks -> ending_hooks/
    - tension_actions -> tension_actions/

    If similar entries already exist, appends examples instead of creating duplicates.
    If video_id already has a drama record, skip entirely (dedup).

    Returns:
        dict with counts of entries added/updated per category
    """
    from ..knowledge.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    video_id = video_data.get("video_id", "")
    drama_title = video_data.get("title", "")
    counts = {"added": 0, "updated": 0, "categories": {}}

    # Dedup: skip if already in knowledge base
    if video_id and kb.has_drama(video_id):
        logger.info("video_id %s 已在知識庫中，跳過入庫", video_id)
        return counts

    def _make_example(excerpt: str, context: str = "") -> dict:
        return {
            "drama_title": drama_title,
            "video_id": video_id,
            "excerpt": excerpt,
            "context": context,
        }

    def _add_or_update(category: str, name: str, data: dict, excerpt: str, context: str = ""):
        """Helper to add or update a KB entry."""
        if not name:
            return
        existing = kb.find_similar(category, name)
        if existing:
            kb.update_entry_examples(
                existing["id"], category,
                [_make_example(excerpt, context)]
            )
            counts["updated"] += 1
        else:
            kb.add_entry(category, data)
            counts["added"] += 1
        counts["categories"][category] = counts["categories"].get(category, 0) + 1

    # 1. Structure
    structure = analysis_result.get("structure")
    if structure and isinstance(structure, dict):
        name = structure.get("type", "")
        _add_or_update("structures", name, {
            "name": name,
            "name_en": structure.get("type_en", ""),
            "description": structure.get("description", ""),
            "tags": analysis_result.get("tags", []),
            "examples": [_make_example(structure.get("excerpt", ""), structure.get("act_breakdown", ""))],
            "effectiveness_score": 7,
        }, structure.get("excerpt", ""), structure.get("act_breakdown", ""))

    # 2. Hooks
    for hook in analysis_result.get("hooks", []):
        if not isinstance(hook, dict):
            continue
        name = hook.get("type", "")
        _add_or_update("hooks", name, {
            "name": name,
            "name_en": hook.get("type_en", ""),
            "description": hook.get("description", ""),
            "tags": [hook.get("timing", ""), *analysis_result.get("tags", [])],
            "examples": [_make_example(hook.get("excerpt", ""), hook.get("timing", ""))],
            "effectiveness_score": 7,
        }, hook.get("excerpt", ""), hook.get("timing", ""))

    # 3. Elements (characters, settings, relationships, character_combos)
    elements = analysis_result.get("elements", {})
    subcategory_map = {
        "characters": "人設",
        "settings": "場景",
        "relationships": "關係",
        "character_combos": "人設組合",
    }
    for key, subcategory in subcategory_map.items():
        for elem in elements.get(key, []):
            if not isinstance(elem, dict):
                continue
            name = elem.get("type", "")
            _add_or_update("elements", name, {
                "subcategory": subcategory,
                "name": name,
                "name_en": elem.get("type_en", ""),
                "description": elem.get("description", ""),
                "tags": [subcategory, *analysis_result.get("tags", [])],
                "examples": [_make_example(elem.get("excerpt", ""), elem.get("description", ""))],
                "effectiveness_score": 6,
            }, elem.get("excerpt", ""), elem.get("description", ""))

    # 4. Payoffs
    for payoff in analysis_result.get("payoffs", []):
        if not isinstance(payoff, dict):
            continue
        name = payoff.get("type", "")
        _add_or_update("payoffs", name, {
            "name": name,
            "name_en": payoff.get("type_en", ""),
            "description": payoff.get("description", ""),
            "tags": [payoff.get("emotional_impact", ""), *analysis_result.get("tags", [])],
            "examples": [_make_example(payoff.get("excerpt", ""), payoff.get("emotional_impact", ""))],
            "effectiveness_score": 7,
        }, payoff.get("excerpt", ""), payoff.get("emotional_impact", ""))

    # 5. Pacing
    pacing = analysis_result.get("pacing")
    if pacing and isinstance(pacing, dict) and pacing.get("tempo"):
        name = pacing.get("tempo", "")
        _add_or_update("pacing", name, {
            "name": name,
            "description": pacing.get("tension_curve", ""),
            "tags": analysis_result.get("tags", []),
            "examples": [_make_example(
                pacing.get("excerpt", pacing.get("tension_curve", "")),
                "; ".join(pacing.get("key_beats", []))
            )],
            "effectiveness_score": 6,
        }, pacing.get("excerpt", pacing.get("tension_curve", "")),
            "; ".join(pacing.get("key_beats", [])))

    # 6. Dialogues
    for dlg in analysis_result.get("dialogues", []):
        if not isinstance(dlg, dict):
            continue
        name = dlg.get("type", "")
        _add_or_update("dialogues", name, {
            "name": name,
            "name_en": dlg.get("type_en", ""),
            "description": dlg.get("description", ""),
            "tags": [dlg.get("emotional_function", ""), *analysis_result.get("tags", [])],
            "examples": [_make_example(dlg.get("excerpt", ""), dlg.get("emotional_function", ""))],
            "effectiveness_score": 7,
        }, dlg.get("excerpt", ""), dlg.get("emotional_function", ""))

    # 7. Visual Scenes
    for vs in analysis_result.get("visual_scenes", []):
        if not isinstance(vs, dict):
            continue
        name = vs.get("type", "")
        _add_or_update("visual_scenes", name, {
            "name": name,
            "name_en": vs.get("type_en", ""),
            "description": vs.get("description", ""),
            "tags": [vs.get("dramatic_tension", ""), *analysis_result.get("tags", [])],
            "examples": [_make_example(vs.get("excerpt", ""), vs.get("dramatic_tension", ""))],
            "effectiveness_score": 7,
        }, vs.get("excerpt", ""), vs.get("dramatic_tension", ""))

    # 8. Ending Hooks
    for eh in analysis_result.get("ending_hooks", []):
        if not isinstance(eh, dict):
            continue
        name = eh.get("type", "")
        _add_or_update("ending_hooks", name, {
            "name": name,
            "name_en": eh.get("type_en", ""),
            "description": eh.get("description", ""),
            "tags": [eh.get("timing", ""), *analysis_result.get("tags", [])],
            "examples": [_make_example(eh.get("excerpt", ""), eh.get("timing", ""))],
            "effectiveness_score": 7,
        }, eh.get("excerpt", ""), eh.get("timing", ""))

    # 9. Tension Actions
    for ta in analysis_result.get("tension_actions", []):
        if not isinstance(ta, dict):
            continue
        name = ta.get("type", "")
        _add_or_update("tension_actions", name, {
            "name": name,
            "name_en": ta.get("type_en", ""),
            "description": ta.get("description", ""),
            "tags": [ta.get("visual_impact", ""), *analysis_result.get("tags", [])],
            "examples": [_make_example(ta.get("excerpt", ""), ta.get("visual_impact", ""))],
            "effectiveness_score": 7,
        }, ta.get("excerpt", ""), ta.get("visual_impact", ""))

    # 10. Genres
    for genre in analysis_result.get("genres", []):
        if not isinstance(genre, dict):
            continue
        name = genre.get("type", "")
        _add_or_update("genres", name, {
            "name": name,
            "name_en": genre.get("type_en", ""),
            "description": genre.get("description", ""),
            "tags": analysis_result.get("tags", []),
            "examples": [_make_example(genre.get("description", ""), "")],
            "effectiveness_score": 6,
        }, genre.get("description", ""), "")

    # 11. Styles
    for style in analysis_result.get("styles", []):
        if not isinstance(style, dict):
            continue
        name = style.get("type", "")
        _add_or_update("styles", name, {
            "name": name,
            "name_en": style.get("type_en", ""),
            "description": style.get("description", ""),
            "tags": analysis_result.get("tags", []),
            "examples": [_make_example(style.get("description", ""), "")],
            "effectiveness_score": 6,
        }, style.get("description", ""), "")

    # Save full drama record
    kb.save_drama(video_id, {
        "video_id": video_id,
        "title": drama_title,
        "analysis": analysis_result,
        "video_data": {
            "channel": video_data.get("channel", ""),
            "views": video_data.get("views", 0),
            "duration": video_data.get("duration", 0),
        },
    })

    return counts
