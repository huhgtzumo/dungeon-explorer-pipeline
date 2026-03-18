"""分鏡拆解 -- 把探索腳本場景轉成生圖/生視頻的指令

核心邏輯：場景描述 + 氛圍 → 每張分鏡圖的完整 prompt
統一風格前綴：dark [building_type], first person POV, flashlight beam, [zone], horror atmosphere, cinematic, hyper realistic, 9:16 vertical
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict

from .character_card import CharacterManager, CharacterCard
from ..utils import llm_client

logger = logging.getLogger(__name__)


# Default exploration style prefix
EXPLORATION_STYLE_PREFIX = (
    "photorealistic raw photograph, NOT illustration, NOT digital art, NOT painting, NOT 3D render, "
    "captured on old Sony Handycam CCD camcorder from 2003, 480p low resolution, "
    "first person POV, handheld shaky camera, single flashlight beam cutting through darkness, "
    "abandoned building interior, real concrete walls real dust real debris, "
    "CCD sensor bloom on highlights, interlaced video artifact, "
    "chromatic aberration, barrel lens distortion, "
    "dirty scratched lens, "
    "natural shadows and real light physics, "
    "9:16 vertical"
)


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
    camera_movement: str  # 鏡頭運動（推進、轉頭、低頭看、抬頭看等）
    lighting: str
    tension_level: int  # 緊張度等級 1-5
    zone: str  # 探索區域


SYSTEM = """你是一個第一人稱恐怖探索影片的分鏡師。把探索腳本拆成具體的生圖指令。
每個指令要包含：探索區域、環境細節、手電筒光線效果、氛圍、鏡頭運動。
生成的 prompt 用英文，給 AI 生圖模型用。
所有畫面都是第一人稱 POV（手持手電筒視角）。"""

STORYBOARD_PROMPT = """把以下探索腳本場景拆成分鏡圖指令。

## 全局風格前綴（每個 image_prompt 必須以此開頭）
{style_prefix}

## 建築類型
{building_type}

## 場景
{scene_data}

每個場景拆成 1-2 個分鏡畫面。回傳 JSON array：
[
  {{
    "frame_number": 1,
    "scene_number": 場景編號,
    "duration_sec": 秒數,
    "image_prompt": "完整英文生圖 prompt（必須以全局風格前綴開頭 + 具體區域 + 環境細節 + 手電筒光線 + 氛圍 + 鏡頭角度）",
    "video_prompt": "英文動作描述（給 image-to-video 模型：手電筒光束移動、灰塵飄落、門緩慢開啟等動態描述）",
    "subtitle_zh": "中文字幕（旁白）",
    "subtitle_en": "English subtitle (narration)",
    "camera_movement": "鏡頭運動（push_forward/turn_left/turn_right/look_down/look_up/step_back/quick_pan/slow_tilt/handheld_shake）",
    "lighting": "光線（flashlight_beam/dim_ambient/flickering/pitch_dark/crack_of_light/emergency_red）",
    "tension_level": 1-5 緊張度等級,
    "zone": "探索區域名稱"
  }}
]

重要：
- image_prompt 必須以風格前綴開頭，然後加上具體的場景描述
- 所有畫面都是第一人稱 POV，手持手電筒照亮前方
- tension_level 要反映場景的緊張程度（1=平靜探索, 3=不安, 5=極度恐懼）
- camera_movement 要配合劇情節奏（探索時慢推、驚嚇時快搖、發現線索時低頭看）
- video_prompt 要描述具體的動態：光束掃過房間、門緩慢關上、影子閃過等

⚠️ 前後幀連貫性（極重要 — 這些幀會被用作視頻生成的首幀/尾幀對）：
- 相鄰兩幀必須構成合理的視覺過渡 — Frame N 的畫面終點 ≈ Frame N+1 的畫面起點
- 例如：Frame 3 看到走廊盡頭有一扇門 → Frame 4 站在那扇門前/推開門
- 保持光線、色調、環境的連續性 — 不能前一幀暗黃色調後一幀突然變冷藍
- 探索者是在「走」的，相鄰幀的空間位置必須是物理上連續的移動
- image_prompt 中要包含足夠的環境線索，讓相鄰幀看起來是同一棟建築的不同位置
- 如果兩幀之間有轉彎/開門/下樓，要在 image_prompt 中體現過渡狀態"""


def generate_storyboard(
    script: dict,
    char_manager: CharacterManager | None = None,
    style_prefix: str = "",
) -> list[StoryboardFrame]:
    """把完整探索腳本轉成分鏡序列

    Args:
        script: generate_episode_script() 的回傳值
        char_manager: 角色卡管理器（探索模式下可能為 None）
        style_prefix: 全局風格前綴
    """
    from ..utils.config import load_config
    config = load_config()

    if not style_prefix:
        style_prefix = EXPLORATION_STYLE_PREFIX

    # Get building type from script
    building_type = (
        script.get("genre", "") or
        script.get("building_type", "") or
        "abandoned building"
    )

    # 組裝場景資料
    scenes_text = json.dumps(script.get("scenes", []), ensure_ascii=False, indent=2)

    prompt = STORYBOARD_PROMPT.format(
        style_prefix=style_prefix,
        building_type=building_type,
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
            camera_movement=fd.get("camera_movement", "push_forward"),
            lighting=fd.get("lighting", "flashlight_beam"),
            tension_level=fd.get("tension_level", 3),
            zone=fd.get("zone", ""),
        ))

    return frames


def setup_characters(script: dict, drama_id: str) -> CharacterManager:
    """從腳本建立角色卡管理器（探索模式下創建探索者卡）"""
    manager = CharacterManager(drama_id)

    # In exploration mode, we may have an explorer profile instead of characters
    explorer = script.get("explorer", script.get("explorer_profile", {}))
    if explorer:
        card = CharacterCard(
            name=explorer.get("name", "Explorer"),
            gender=explorer.get("gender", "unknown"),
            age_range="25-35",
            hair="hidden under helmet",
            skin_tone="fair",
            outfit=explorer.get("equipment", "tactical gear, headlamp, backpack"),
            body_type="athletic",
            personality=explorer.get("personality", "cautious explorer"),
        )
        manager.add(card)
    else:
        # Fallback: create from characters list if available
        for char_data in script.get("characters", []):
            card = CharacterCard(
                name=char_data.get("name", "Unknown"),
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
