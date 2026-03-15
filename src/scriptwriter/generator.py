"""劇本生成 — 三步驟：大架構 → 拆集 → 逐集劇本

流程：
1. generate_series_outline() — 生成一部完整大劇的故事大綱 + 拆成 30-50 集
2. generate_episode_script() — 根據大綱，逐集生成詳細劇本
3. 每集劇本再接分鏡（storyboard.py）
"""

from __future__ import annotations

import json

from ..utils import llm_client


# ──────────────── Step 1: 大架構 + 拆集 ────────────────

OUTLINE_SYSTEM = """你是一個爆款短劇總編劇。你擅長：
- 設計一個完整的長篇故事大綱（約 1 小時總時長）
- 拆分成 30-50 集短劇，每集 60 秒
- 每集有獨立的小高潮，同時推進主線劇情
- 結尾留鉤子讓觀眾想看下一集"""

OUTLINE_PROMPT = """根據以下爆款分析和風格要求，設計一部完整的短劇大綱。

## 爆款分析
{trending_analysis}

## 要求
- 類型: {genre}
- 總集數: {episode_count} 集
- 每集時長: 60 秒
- 風格: {style}
- 語言: 中文（角色名和關鍵詞附英文）
{human_requirements_section}

請回傳 JSON：
{{
  "series_title": "劇名",
  "series_title_en": "英文劇名",
  "genre": "類型",
  "logline": "一句話總劇情",
  "total_episodes": 數字,
  "characters": [
    {{
      "name": "角色名",
      "name_en": "英文名",
      "gender": "male/female",
      "age_range": "25-30",
      "hair": "髮型描述（中英）",
      "skin_tone": "膚色",
      "outfit": "服裝描述（中英）",
      "body_type": "體型",
      "personality": "性格描述",
      "role": "protagonist/antagonist/supporting",
      "arc": "角色成長弧線"
    }}
  ],
  "story_arcs": [
    {{
      "arc_name": "主線名稱",
      "description": "主線描述",
      "episodes": [1, 2, 3]
    }}
  ],
  "episodes": [
    {{
      "episode_number": 1,
      "title": "集名",
      "title_en": "Episode title",
      "synopsis": "本集劇情摘要（3-5句）",
      "key_conflict": "核心衝突",
      "cliffhanger": "結尾鉤子",
      "characters_present": ["角色名"],
      "emotion_arc": "情緒走向（如：平靜→震驚→憤怒）",
      "location": "主要場景"
    }}
  ]
}}"""


def generate_series_outline(
    trending_analysis: dict | str = "",
    genre: str = "都市甜寵",
    style: str = "dramatic",
    episode_count: int = 30,
    human_requirements: str = "",
) -> dict:
    """Step 1: 生成完整大劇的故事大綱 + 拆集"""
    if isinstance(trending_analysis, dict):
        trending_analysis = json.dumps(trending_analysis, ensure_ascii=False, indent=2)

    hr_section = ""
    if human_requirements:
        hr_section = f"\n## 用戶特殊要求（必須滿足）\n{human_requirements}\n"

    prompt = OUTLINE_PROMPT.format(
        trending_analysis=trending_analysis or "（無分析資料，自由發揮）",
        genre=genre,
        style=style,
        episode_count=episode_count,
        human_requirements_section=hr_section,
    )
    resp = llm_client.chat_json(prompt, system=OUTLINE_SYSTEM)

    if not resp or not resp.strip():
        raise ValueError("Claude 回傳空白回應，無法生成大綱")

    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        raise ValueError(f"Claude 回傳非 JSON 格式: {resp[:300]}")


# ──────────────── Step 2: 逐集劇本 ────────────────

EPISODE_SYSTEM = """你是一個短劇編劇。根據大綱和角色設定，生成一集完整的 60 秒短劇劇本。
- 開頭 3 秒內抓住觀眾（強鉤子）
- 節奏快，每 5-8 秒一個情節點
- 角色外觀描述要與角色卡完全一致
- 結尾有本集的鉤子或反轉"""

EPISODE_PROMPT = """根據以下大綱資訊，生成第 {episode_number} 集的完整劇本。

## 劇名
{series_title}

## 角色設定
{characters}

## 本集大綱
- 集名: {episode_title}
- 劇情摘要: {synopsis}
- 核心衝突: {key_conflict}
- 結尾鉤子: {cliffhanger}
- 出場角色: {characters_present}
- 情緒走向: {emotion_arc}
- 主要場景: {location}

## 前一集摘要（劇情銜接用）
{previous_synopsis}

請回傳 JSON：
{{
  "episode_number": {episode_number},
  "title": "集名",
  "title_en": "英文集名",
  "duration_sec": 60,
  "scenes": [
    {{
      "scene_number": 1,
      "duration_sec": 6,
      "location": "場景地點",
      "location_en": "Location in English",
      "characters_present": ["角色名"],
      "action_zh": "動作描述（中文）",
      "action_en": "Action description (English)",
      "dialogue_zh": "台詞（中文）",
      "dialogue_en": "Dialogue (English)",
      "emotion": "情緒",
      "camera_angle": "鏡頭角度（close-up/medium/wide/over-shoulder）",
      "lighting": "光線（warm/cold/dramatic/natural）"
    }}
  ],
  "subtitle_zh": ["完整中文字幕（按場景）"],
  "subtitle_en": ["完整英文字幕（按場景）"]
}}"""


def generate_episode_script(
    series_outline: dict,
    episode_number: int,
    previous_synopsis: str = "（第一集，無前情）",
) -> dict:
    """Step 2: 根據大綱生成單集詳細劇本"""
    # 找到對應集的大綱
    episode_info = None
    for ep in series_outline.get("episodes", []):
        if ep.get("episode_number") == episode_number:
            episode_info = ep
            break

    if not episode_info:
        return {"error": f"找不到第 {episode_number} 集的大綱"}

    # 組裝角色資訊
    characters_text = json.dumps(
        series_outline.get("characters", []),
        ensure_ascii=False, indent=2
    )

    prompt = EPISODE_PROMPT.format(
        episode_number=episode_number,
        series_title=series_outline.get("series_title", ""),
        characters=characters_text,
        episode_title=episode_info.get("title", ""),
        synopsis=episode_info.get("synopsis", ""),
        key_conflict=episode_info.get("key_conflict", ""),
        cliffhanger=episode_info.get("cliffhanger", ""),
        characters_present=", ".join(episode_info.get("characters_present", [])),
        emotion_arc=episode_info.get("emotion_arc", ""),
        location=episode_info.get("location", ""),
        previous_synopsis=previous_synopsis,
    )
    resp = llm_client.chat_json(prompt, system=EPISODE_SYSTEM)

    if not resp or not resp.strip():
        raise ValueError(f"Claude 回傳空白回應，無法生成第 {episode_number} 集劇本")

    try:
        result = json.loads(resp)
        # 把角色卡也附上，方便後續分鏡用
        result["characters"] = series_outline.get("characters", [])
        return result
    except json.JSONDecodeError:
        raise ValueError(f"Claude 回傳非 JSON 格式（第 {episode_number} 集）: {resp[:300]}")


# ──────────────── Legacy: 單集模式（向後兼容） ────────────────

def generate_script(
    trending_analysis: dict | str = "",
    genre: str = "都市甜寵",
    style: str = "dramatic",
    human_requirements: str = "",
) -> dict:
    """向後兼容：生成單集 60 秒劇本（不走大綱模式）"""
    outline = generate_series_outline(
        trending_analysis=trending_analysis,
        genre=genre,
        style=style,
        episode_count=1,
        human_requirements=human_requirements,
    )
    if outline.get("error"):
        return outline

    episode = generate_episode_script(outline, episode_number=1)
    # 合併大綱資訊到劇本
    episode["series_title"] = outline.get("series_title", "")
    episode["genre"] = outline.get("genre", "")
    episode["logline"] = outline.get("logline", "")
    return episode


# ──────────────── Knowledge-Base-Driven Generation ────────────────

KB_OUTLINE_SYSTEM = """你是一個爆款短劇總編劇。你擅長：
- 基於已被驗證有效的創作元素（架構、鉤子、人設、爽點、節奏、對白、視覺場景、結尾鉤子、張力行為）組合出新故事
- 每個選中的元素都有真實爆款劇的範例片段作為參考
- 你要融合這些元素，創造出全新的、有機整合的故事
- 不是簡單拼湊，而是讓元素之間產生化學反應"""

KB_OUTLINE_PROMPT = """基於以下從知識庫中抽取的創作元素，設計一部全新的短劇大綱。

## 架構模板（參考但不照搬）
{structures_text}

## 開場鉤子參考
{hooks_text}

## 角色/場景/關係元素
{elements_text}

## 爽點設計參考
{payoffs_text}

## 節奏模板參考
{pacing_text}

## 對白模式參考
{dialogues_text}

## 視覺場景參考
{visual_scenes_text}

## 結尾鉤子參考
{ending_hooks_text}

## 張力行為參考
{tension_actions_text}

## 要求
- 類型: {genre}
- 總集數: {episode_count} 集
- 每集時長: {duration_sec} 秒
- 風格: {style}
- 語言: 中文（角色名和關鍵詞附英文）
{human_requirements_section}

## 重要指導
- 上方標記「必須使用」的元素是用戶指定的，必須融入劇本
- 上方標記「（知識庫中無XX資料，請自由發揮）」的分類，由你自由創造
- 不要照抄範例，而是學習其手法後創造全新的內容
- 確保所有選中的元素有機融合，不是硬拼
- 根據時長（{duration_sec}秒）合理分配劇情密度：60秒要精練，180秒可多層衝突，300秒可有完整起承轉合
- 每集結尾都要有結尾鉤子

請回傳 JSON（格式與標準大綱一致）：
{{
  "series_title": "劇名",
  "series_title_en": "英文劇名",
  "genre": "類型",
  "logline": "一句話總劇情",
  "total_episodes": 數字,
  "kb_elements_used": {{
    "structure": "使用的架構名稱",
    "hooks": ["使用的鉤子1", "鉤子2"],
    "elements": ["使用的元素1", "元素2"],
    "payoffs": ["使用的爽點1", "爽點2"],
    "pacing": "使用的節奏模板",
    "dialogues": ["使用的對白模式1"],
    "visual_scenes": ["使用的視覺場景1"],
    "ending_hooks": ["使用的結尾鉤子1"],
    "tension_actions": ["使用的張力行為1"]
  }},
  "characters": [
    {{
      "name": "角色名",
      "name_en": "英文名",
      "gender": "male/female",
      "age_range": "25-30",
      "hair": "髮型描述（中英）",
      "skin_tone": "膚色",
      "outfit": "服裝描述（中英）",
      "body_type": "體型",
      "personality": "性格描述",
      "role": "protagonist/antagonist/supporting",
      "arc": "角色成長弧線"
    }}
  ],
  "story_arcs": [
    {{
      "arc_name": "主線名稱",
      "description": "主線描述",
      "episodes": [1, 2, 3]
    }}
  ],
  "episodes": [
    {{
      "episode_number": 1,
      "title": "集名",
      "title_en": "Episode title",
      "synopsis": "本集劇情摘要（3-5句）",
      "key_conflict": "核心衝突",
      "cliffhanger": "結尾鉤子",
      "characters_present": ["角色名"],
      "emotion_arc": "情緒走向",
      "location": "主要場景"
    }}
  ]
}}"""


def _format_kb_entries(entries: list[dict], label: str) -> str:
    """Format KB entries into readable text for prompt injection."""
    if not entries:
        return f"（知識庫中無{label}資料，請自由發揮）"
    parts = []
    for i, e in enumerate(entries, 1):
        part = f"\n### {label} {i}: {e.get('name', '')} ({e.get('name_en', '')})\n"
        part += f"描述: {e.get('description', '')}\n"
        for ex in e.get("examples", [])[:2]:
            part += f"  範例（來自《{ex.get('drama_title', '')}》）: {ex.get('excerpt', '')}\n"
            if ex.get("context"):
                part += f"  上下文: {ex.get('context', '')}\n"
        parts.append(part)
    return "\n".join(parts)


def generate_from_knowledge_base(
    kb,
    config: dict | None = None,
    selected_elements: dict | None = None,
) -> dict:
    """Generate a series outline using elements drawn from the knowledge base.

    Args:
        kb: KnowledgeBase instance
        config: dict with genre, style, episode_count, human_requirements, tags
        selected_elements: dict mapping category -> list of entry_ids
            If provided, uses these specific entries instead of random selection.

    Returns:
        Series outline dict (same format as generate_series_outline)
    """
    config = config or {}
    genre = config.get("genre", "")
    style = config.get("style", "")
    episode_count = config.get("episode_count", 1)
    human_requirements = config.get("human_requirements", "")

    duration_sec = config.get("duration_sec", 60)

    # Build combination: use selected_elements if provided, otherwise leave empty
    # Unselected categories are left empty — Claude decides freely
    user_selected_cats: set[str] = set()
    if selected_elements:
        combination = {}
        all_categories = [
            "structures", "hooks", "elements", "payoffs",
            "pacing", "dialogues", "visual_scenes", "ending_hooks", "tension_actions",
            "genres", "styles",
        ]
        for cat in all_categories:
            ids = selected_elements.get(cat, [])
            if ids:
                combination[cat] = kb.get_entries_by_ids(cat, ids)
                user_selected_cats.add(cat)
            else:
                combination[cat] = []  # leave empty, let Claude decide
    else:
        combination = kb.get_random_combination(config)

    def _format_with_label(cat: str, entries: list[dict], label: str) -> str:
        """Format entries; prefix with (必須使用) if user explicitly selected them."""
        if cat in user_selected_cats and entries:
            header = f"【必須使用 — 用戶指定，不可替換】"
            text = _format_kb_entries(entries, label)
            return f"{header}\n{text}"
        return _format_kb_entries(entries, label)

    structures_text = _format_with_label("structures", combination.get("structures", []), "架構")
    hooks_text = _format_with_label("hooks", combination.get("hooks", []), "鉤子")
    elements_text = _format_with_label("elements", combination.get("elements", []), "元素")
    payoffs_text = _format_with_label("payoffs", combination.get("payoffs", []), "爽點")
    pacing_text = _format_with_label("pacing", combination.get("pacing", []), "節奏")
    dialogues_text = _format_with_label("dialogues", combination.get("dialogues", []), "對白")
    visual_scenes_text = _format_with_label("visual_scenes", combination.get("visual_scenes", []), "視覺場景")
    ending_hooks_text = _format_with_label("ending_hooks", combination.get("ending_hooks", []), "結尾鉤子")
    tension_actions_text = _format_with_label("tension_actions", combination.get("tension_actions", []), "張力行為")

    # Use genre/style from KB entries if available, else fall back to config values
    genre_entries = combination.get("genres", [])
    style_entries = combination.get("styles", [])
    if genre_entries and not genre:
        genre = genre_entries[0].get("name", "自由發揮")
    if style_entries and not style:
        style = style_entries[0].get("name", "自由發揮")
    if not genre:
        genre = "自由發揮"
    if not style:
        style = "自由發揮"

    hr_section = ""
    if human_requirements:
        hr_section = f"\n## 用戶特殊要求（必須滿足）\n{human_requirements}\n"

    # Build must-use summary note
    if user_selected_cats:
        cat_labels = {
            "structures": "架構", "hooks": "鉤子", "elements": "元素", "payoffs": "爽點",
            "pacing": "節奏", "dialogues": "對白", "visual_scenes": "視覺場景",
            "ending_hooks": "結尾鉤子", "tension_actions": "張力行為",
            "genres": "劇本類型", "styles": "風格",
        }
        must_use_list = "、".join(cat_labels.get(c, c) for c in sorted(user_selected_cats))
        hr_section += (
            f"\n## 必須使用的知識庫元素（用戶指定）\n"
            f"以下類別已由用戶指定，必須融入劇本中：{must_use_list}。\n"
            f"未指定的類別由你自由發揮，不要勉強塞入。\n"
        )

    prompt = KB_OUTLINE_PROMPT.format(
        structures_text=structures_text,
        hooks_text=hooks_text,
        elements_text=elements_text,
        payoffs_text=payoffs_text,
        pacing_text=pacing_text,
        dialogues_text=dialogues_text,
        visual_scenes_text=visual_scenes_text,
        ending_hooks_text=ending_hooks_text,
        tension_actions_text=tension_actions_text,
        genre=genre,
        style=style,
        episode_count=episode_count,
        duration_sec=duration_sec,
        human_requirements_section=hr_section,
    )

    resp = llm_client.chat_json(prompt, system=KB_OUTLINE_SYSTEM)

    if not resp or not resp.strip():
        raise ValueError("Claude 回傳空白回應，無法生成知識庫大綱")

    try:
        outline = json.loads(resp)
        # Attach the KB elements used for traceability
        outline["_kb_combination"] = {
            cat: [e.get("id", "") for e in combination.get(cat, [])]
            for cat in ["structures", "hooks", "elements", "payoffs",
                        "pacing", "dialogues", "visual_scenes", "ending_hooks", "tension_actions",
                        "genres", "styles"]
        }
        outline["_kb_user_selected"] = list(user_selected_cats)
        return outline
    except json.JSONDecodeError:
        raise ValueError(f"Claude 回傳非 JSON 格式: {resp[:300]}")
