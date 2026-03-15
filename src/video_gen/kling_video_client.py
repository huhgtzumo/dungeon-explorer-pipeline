"""Kling AI 視頻生成 client（image-to-video）

使用 Kling API 從圖片生成視頻片段。
JWT token 認證，異步輪詢等待結果。
"""

from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path

import httpx
import jwt

from ..utils.config import load_config, PROJECT_ROOT

logger = logging.getLogger(__name__)

BASE_URL = "https://api-singapore.klingai.com"
GENERATED_VIDEOS_DIR = PROJECT_ROOT / "data" / "generated_videos"


def _get_jwt_token() -> str:
    """簽發 Kling API JWT token。"""
    config = load_config()
    access_key = config.get("kling_access_key", "")
    secret_key = config.get("kling_secret_key", "")
    if not access_key or not secret_key:
        raise ValueError("KLING_ACCESS_KEY 或 KLING_SECRET_KEY 未設定")

    now = int(time.time())
    headers = {
        "alg": "HS256",
        "typ": "JWT",
        "kid": access_key,
    }
    payload = {
        "iss": access_key,
        "exp": now + 1800,
        "nbf": now - 5,
        "iat": now,
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256", headers=headers)
    return token


def _api_headers() -> dict:
    """返回帶 Bearer token 的 headers。"""
    token = _get_jwt_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _image_to_base64(image_path: str | Path) -> str:
    """讀取圖片檔案並轉為 base64 字串。"""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"圖片不存在: {image_path}")
    data = image_path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def generate_video(
    image_path: str | Path,
    prompt: str = "",
    duration_sec: int = 5,
    output_path: str | Path = "",
    mode: str = "std",
    model: str = "kling-v1",
    poll_interval: int = 10,
    max_wait: int = 600,
) -> Path:
    """用 Kling API 從圖片生成視頻。

    Args:
        image_path: 來源圖片路徑
        prompt: 動態描述 prompt
        duration_sec: 視頻時長（5 或 10 秒）
        output_path: 輸出視頻路徑
        mode: "std"（標準）或 "pro"（高品質）
        model: 模型名稱
        poll_interval: 輪詢間隔（秒）
        max_wait: 最大等待時間（秒）

    Returns:
        output_path on success

    Raises:
        RuntimeError if generation fails
    """
    image_path = Path(image_path)
    output_path = Path(output_path) if output_path else image_path.with_suffix(".mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = _api_headers()

    # 將圖片轉為 base64
    image_b64 = _image_to_base64(image_path)

    # 1. 提交視頻生成任務
    req_body = {
        "model": model,
        "image": image_b64,
        "prompt": prompt,
        "duration": str(duration_sec),
        "cfg_scale": 0.5,
        "mode": mode,
    }

    logger.info("提交 Kling 視頻生成任務 (duration=%ds, mode=%s)...", duration_sec, mode)
    resp = httpx.post(
        f"{BASE_URL}/v1/videos/image2video",
        headers=headers,
        json=req_body,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"Kling API 錯誤: {result.get('message', result)}")

    task_id = result["data"]["task_id"]
    logger.info("Kling 視頻任務已提交: task_id=%s", task_id)

    # 2. 輪詢等待結果
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(poll_interval)

        headers = _api_headers()  # 每次重新簽發
        poll_resp = httpx.get(
            f"{BASE_URL}/v1/videos/image2video/{task_id}",
            headers=headers,
            timeout=30,
        )
        poll_resp.raise_for_status()
        poll_result = poll_resp.json()

        if poll_result.get("code") != 0:
            raise RuntimeError(f"Kling API 輪詢錯誤: {poll_result.get('message', poll_result)}")

        status = poll_result["data"]["task_status"]
        elapsed = time.time() - start
        logger.info("Kling 視頻任務狀態: %s (%.0fs)", status, elapsed)

        if status == "succeed":
            videos = poll_result["data"]["task_result"]["videos"]
            if not videos:
                raise RuntimeError("Kling 返回成功但無視頻")
            video_url = videos[0]["url"]
            logger.info("下載視頻: %s", video_url[:80])
            vid_resp = httpx.get(video_url, timeout=120, follow_redirects=True)
            vid_resp.raise_for_status()
            output_path.write_bytes(vid_resp.content)
            logger.info("視頻已儲存: %s (%d bytes)", output_path, len(vid_resp.content))
            return output_path

        if status == "failed":
            error_msg = poll_result["data"].get("task_status_msg", "未知錯誤")
            raise RuntimeError(f"Kling 視頻生成失敗: {error_msg}")

    raise RuntimeError(f"Kling 視頻生成超時（{max_wait}s）")


def batch_generate(
    frames: list[dict],
    drama_id: str,
    duration_sec: int = 5,
    mode: str = "std",
    on_progress=None,
) -> list[dict]:
    """批次從分鏡圖生成視頻片段。

    Args:
        frames: list of {frame_number, image_path, video_prompt, duration_sec?}
        drama_id: drama ID，用來組織輸出路徑
        duration_sec: 預設每段時長
        mode: "std" 或 "pro"
        on_progress: callback(current, total, message)

    Returns:
        list of {frame_number, video_path, status, error?}
    """
    output_dir = GENERATED_VIDEOS_DIR / drama_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(frames)

    for i, frame in enumerate(frames):
        num = frame.get("frame_number", i + 1)
        image_path = frame.get("image_path", "")
        prompt = frame.get("video_prompt", "")
        dur = frame.get("duration_sec", duration_sec)
        out_path = output_dir / f"clip_{num:03d}.mp4"

        if on_progress:
            on_progress(i, total, f"生成視頻片段 #{num}...")

        # 處理相對路徑
        if image_path and not Path(image_path).is_absolute():
            image_path = PROJECT_ROOT / image_path

        try:
            generate_video(
                image_path=image_path,
                prompt=prompt,
                duration_sec=dur,
                output_path=out_path,
                mode=mode,
            )
            results.append({
                "frame_number": num,
                "video_path": str(out_path.relative_to(PROJECT_ROOT)),
                "video_prompt": prompt,
                "duration_sec": dur,
                "status": "ok",
            })
            logger.info("[%d/%d] 視頻片段 #%d 生成成功", i + 1, total, num)
        except Exception as e:
            results.append({
                "frame_number": num,
                "video_path": None,
                "video_prompt": prompt,
                "status": "error",
                "error": str(e),
            })
            logger.error("[%d/%d] 視頻片段 #%d 生成失敗: %s", i + 1, total, num, e)

        # Rate limit between generations
        if i < total - 1:
            time.sleep(3)

    if on_progress:
        on_progress(total, total, "完成")

    # Save metadata
    meta = {
        "video_set_id": drama_id,
        "total_clips": total,
        "success_count": sum(1 for r in results if r["status"] == "ok"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "duration_sec": duration_sec,
        "mode": mode,
        "clips": results,
    }
    meta_path = output_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return results
