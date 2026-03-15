"""Gemini 生圖 client

目前狀態：
- API 方式：需要付費 tier（Free tier quota = 0）
- 網頁版：用 nano banana（免費），需要瀏覽器自動化

TODO: 付費後啟用 API 方式
TODO: 實作 nano banana 網頁版自動化（Playwright）
"""

from __future__ import annotations

from pathlib import Path

from ..utils.config import load_config, PROJECT_ROOT


def generate_image_api(prompt: str, output_path: str | Path) -> Path:
    """用 Gemini API 生圖（需要付費 tier）

    TODO: 付費後實作
    """
    raise NotImplementedError(
        "Gemini API 生圖需要付費 tier。"
        "目前請用網頁版 nano banana（免費）。"
        "或在 Google AI Studio 手動生圖。"
    )


def generate_image_web(prompt: str, output_path: str | Path) -> Path:
    """用 Gemini 網頁版 nano banana 生圖（免費）

    TODO: 實作 Playwright 自動化
    流程：
    1. 開 Chrome (port 18800)
    2. 前往 https://aistudio.google.com/prompts/new_chat
    3. 選 Image Generation → Nano Banana（免費版）
    4. 輸入 prompt → 等生成
    5. 下載圖片到 output_path
    """
    raise NotImplementedError(
        "nano banana 網頁版自動化尚未實作。"
        "需要 Playwright + Chrome CDP 自動化。"
    )


def generate_image(prompt: str, output_path: str | Path) -> Path:
    """統一入口：根據設定選 API 或網頁版"""
    config = load_config()
    provider = config["image_gen"]["provider"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if provider == "gemini_api":
        return generate_image_api(prompt, output_path)
    else:
        return generate_image_web(prompt, output_path)


def batch_generate(
    frames: list[dict],
    drama_id: str,
) -> list[dict]:
    """批次生成分鏡圖

    Args:
        frames: list of {frame_number, image_prompt, ...}
        drama_id: 用來組織輸出路徑

    Returns:
        list of {frame_number, image_path, status}
    """
    output_dir = PROJECT_ROOT / "data" / "images" / drama_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for frame in frames:
        num = frame.get("frame_number", 0)
        prompt = frame.get("image_prompt", "")
        out_path = output_dir / f"frame_{num:03d}.png"

        try:
            path = generate_image(prompt, out_path)
            results.append({"frame_number": num, "image_path": str(path), "status": "ok"})
        except NotImplementedError as e:
            results.append({"frame_number": num, "image_path": None, "status": "not_implemented", "error": str(e)})
        except Exception as e:
            results.append({"frame_number": num, "image_path": None, "status": "error", "error": str(e)})

    return results
