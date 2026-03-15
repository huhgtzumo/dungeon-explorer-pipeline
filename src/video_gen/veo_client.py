"""Veo 3.1 / Flow 視頻生成 client

目前狀態：
- Veo API：需要付費 tier
- Flow 網頁版 (labs.google/flow)：一天 3 次免費額度

TODO: 付費後啟用 Veo API
TODO: 實作 Flow 網頁版自動化
"""

from __future__ import annotations

from pathlib import Path

from ..utils.config import load_config, PROJECT_ROOT


def generate_video_api(
    image_path: str | Path,
    prompt: str,
    duration_sec: float = 8,
    output_path: str | Path = "",
) -> Path:
    """用 Veo 3.1 API 從圖片生成視頻（需要付費）

    TODO: 付費後實作
    Veo 3.1 支援 image-to-video，最長 8 秒/段
    """
    raise NotImplementedError(
        "Veo API 需要付費 tier。"
        "目前請用 Flow 網頁版（一天 3 次免費額度）。"
    )


def generate_video_flow(
    image_path: str | Path,
    prompt: str,
    duration_sec: float = 8,
    output_path: str | Path = "",
) -> Path:
    """用 Flow 網頁版生成視頻（免費，一天 3 次）

    TODO: 實作 Playwright 自動化
    流程：
    1. 開 Chrome (port 18800)
    2. 前往 https://labs.google/flow
    3. 上傳圖片 + 輸入 prompt
    4. 等生成（可能要幾分鐘）
    5. 下載視頻到 output_path
    """
    raise NotImplementedError(
        "Flow 網頁版自動化尚未實作。"
        "需要 Playwright + Chrome CDP 自動化。"
    )


def generate_video(
    image_path: str | Path,
    prompt: str,
    duration_sec: float = 8,
    output_path: str | Path = "",
) -> Path:
    """統一入口"""
    config = load_config()
    provider = config["video_gen"]["provider"]

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if provider == "veo_api":
        return generate_video_api(image_path, prompt, duration_sec, output_path)
    else:
        return generate_video_flow(image_path, prompt, duration_sec, output_path)


def batch_generate(
    frames: list[dict],
    drama_id: str,
) -> list[dict]:
    """批次生成視頻片段

    Args:
        frames: list of {frame_number, image_path, video_prompt, duration_sec}
        drama_id: drama ID

    Returns:
        list of {frame_number, video_path, status}
    """
    output_dir = PROJECT_ROOT / "data" / "videos" / drama_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for frame in frames:
        num = frame.get("frame_number", 0)
        image_path = frame.get("image_path", "")
        prompt = frame.get("video_prompt", "")
        duration = frame.get("duration_sec", 8)
        out_path = output_dir / f"clip_{num:03d}.mp4"

        try:
            path = generate_video(image_path, prompt, duration, out_path)
            results.append({"frame_number": num, "video_path": str(path), "status": "ok"})
        except NotImplementedError as e:
            results.append({"frame_number": num, "video_path": None, "status": "not_implemented", "error": str(e)})
        except Exception as e:
            results.append({"frame_number": num, "video_path": None, "status": "error", "error": str(e)})

    return results
