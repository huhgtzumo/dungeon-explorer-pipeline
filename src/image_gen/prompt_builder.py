"""Prompt 組裝 — 角色卡 + 場景描述 → 生圖 prompt

確保每張分鏡圖的角色外觀一致。
"""

from __future__ import annotations

from ..scriptwriter.character_card import CharacterManager
from ..utils.config import load_config


def build_image_prompt(
    scene_description: str,
    characters: list[str],
    char_manager: CharacterManager,
    camera_angle: str = "medium shot",
    lighting: str = "natural",
    style_prefix: str = "",
    negative_prompt: str = "",
) -> str:
    """組裝完整的生圖 prompt

    結構: [style prefix] + [scene] + [characters with card desc] + [camera] + [lighting]
    """
    config = load_config()

    if not style_prefix:
        style_prefix = config["image_gen"]["style_prefix"]
    if not negative_prompt:
        negative_prompt = config["image_gen"]["negative_prompt"]

    parts = [style_prefix]

    # 場景描述
    parts.append(scene_description)

    # 角色描述（從角色卡提取，確保一致性）
    for char_name in characters:
        desc = char_manager.get_prompt_desc(char_name, lang="en")
        parts.append(desc)

    # 鏡頭和光線
    parts.append(f"{camera_angle}, {lighting} lighting")

    prompt = ", ".join(p for p in parts if p)

    return {"prompt": prompt, "negative_prompt": negative_prompt}


def build_video_prompt(
    image_prompt: str,
    action_description: str,
    duration_sec: float = 6,
) -> str:
    """組裝生視頻的 prompt（基於靜態圖 + 動作描述）"""
    return (
        f"Based on scene: {image_prompt}. "
        f"Animate this scene: {action_description}. "
        f"Duration: {duration_sec} seconds. "
        f"Smooth camera movement, cinematic quality."
    )
