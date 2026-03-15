"""分鏡拆解 — 把劇本場景轉成生圖/生視頻的指令

核心邏輯：角色卡 + 場景描述 → 每張分鏡圖的完整 prompt
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict

from .character_card import CharacterManager, CharacterCard
from ..utils import llm_client

logger = logging.getLogger(__name__)


@dataclass
class StoryboardFrame:
    """一個分鏡畫面"""
    frame_number: int
    scene_number: int
    duration_sec: float
    image_prompt: str  # 生圖用的完整 prompt
    video_prompt: str  # 生視頻用的動作描述
    subtitle_zh: str
    subtitle_en: str
    camera_angle: str
    lighting: str
    characters: list[str]


SYSTEM = """你是一個短劇分鏡師。把場景拆成具體的生圖指令。
每個指令要包含：場景、角色外觀（必須跟角色卡一致）、動作、鏡頭、光線。
生成的 prompt 用英文，給 AI 生圖模型用。"""

STORYBOARD_PROMPT = """把以下劇本場景拆成分鏡圖指令。

## 角色卡（所有分鏡必須嚴格按照角色卡描述）
{character_cards}

## 全局風格
{style_prefix}

## 場景
{scene_data}

每個場景拆成 1-2 個分鏡畫面。回傳 JSON array：
[
  {{
    "frame_number": 1,
    "scene_number": 場景編號,
    "duration_sec": 秒數,
    "image_prompt": "完整英文生圖 prompt（包含風格前綴 + 場景 + 角色外觀 + 動作 + 鏡頭 + 光線）",
    "video_prompt": "英文動作描述（給 image-to-video 模型，描述畫面中的動態）",
    "subtitle_zh": "中文字幕",
    "subtitle_en": "English subtitle",
    "camera_angle": "鏡頭角度",
    "lighting": "光線",
    "characters": ["角色名"]
  }}
]"""


def generate_storyboard(
    script: dict,
    char_manager: CharacterManager,
    style_prefix: str = "",
) -> list[StoryboardFrame]:
    """把完整劇本轉成分鏡序列

    Args:
        script: generate_script() 的回傳值
        char_manager: 已載入角色卡的 CharacterManager
        style_prefix: 全局風格前綴
    """
    from ..utils.config import load_config
    config = load_config()

    if not style_prefix:
        style_prefix = config["image_gen"]["style_prefix"]

    # 組裝角色卡描述
    cards_text = ""
    for card in char_manager.all_cards():
        cards_text += f"\n- {card.name}: {card.to_prompt_desc('en')}"

    # 組裝場景資料
    scenes_text = json.dumps(script.get("scenes", []), ensure_ascii=False, indent=2)

    prompt = STORYBOARD_PROMPT.format(
        character_cards=cards_text,
        style_prefix=style_prefix,
        scene_data=scenes_text,
    )

    resp = llm_client.chat_json(prompt, system=SYSTEM)

    try:
        frames_data = json.loads(resp)
    except json.JSONDecodeError:
        logger.error("分鏡生成失敗：LLM 回傳的不是有效 JSON: %s", resp[:200])
        return []

    if not isinstance(frames_data, list):
        logger.error("分鏡生成失敗：LLM 回傳的不是 JSON array: %s", type(frames_data))
        return []

    frames = []
    for fd in frames_data:
        frames.append(StoryboardFrame(
            frame_number=fd.get("frame_number", 0),
            scene_number=fd.get("scene_number", 0),
            duration_sec=fd.get("duration_sec", 6),
            image_prompt=fd.get("image_prompt", ""),
            video_prompt=fd.get("video_prompt", ""),
            subtitle_zh=fd.get("subtitle_zh", ""),
            subtitle_en=fd.get("subtitle_en", ""),
            camera_angle=fd.get("camera_angle", "medium shot"),
            lighting=fd.get("lighting", "natural"),
            characters=fd.get("characters", []),
        ))

    return frames


def setup_characters(script: dict, drama_id: str) -> CharacterManager:
    """從劇本建立角色卡管理器"""
    manager = CharacterManager(drama_id)

    for char_data in script.get("characters", []):
        card = CharacterCard(
            name=char_data.get("name", "未知"),
            gender=char_data.get("gender", "unknown"),
            age_range=char_data.get("age_range", "25-30"),
            hair=char_data.get("hair", "black hair"),
            skin_tone=char_data.get("skin_tone", "fair"),
            outfit=char_data.get("outfit", "casual clothes"),
            body_type=char_data.get("body_type", "average"),
            personality=char_data.get("personality", ""),
        )
        manager.add(card)

    manager.save()
    return manager


def save_storyboard(frames: list[StoryboardFrame], drama_id: str):
    """存分鏡到 JSON"""
    from ..utils.config import PROJECT_ROOT
    out_dir = PROJECT_ROOT / "data" / "storyboards" / drama_id
    out_dir.mkdir(parents=True, exist_ok=True)

    data = [asdict(f) for f in frames]
    path = out_dir / "storyboard.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
