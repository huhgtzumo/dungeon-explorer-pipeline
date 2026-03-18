"""Kling AI 圖生視頻 generator (Step 6 wrapper)

此模組是 kling_video_client 的輕量封裝，提供以下功能：
- generate_video_url(): 從圖片 URL 或本地路徑生成視頻，回傳視頻 URL
- generate_video(): 生成並下載視頻到本地路徑
- batch_generate(): 批次從分鏡圖生成視頻片段（支援前後幀銜接）

model 預設使用 kling-v1（最便宜），duration 預設 "10"（10 秒），mode 預設 "std"（標準品質）。
每段 10s 標準視頻消耗 2 個 API 單位（kling-v1）。
支援 image_tail 參數實現一鏡到底的連貫效果。
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


def generate_video_url(
    image_url: str = "",
    image_path: str | Path = "",
    image_tail_url: str = "",
    image_tail_path: str | Path = "",
    prompt: str = "",
    negative_prompt: str = "",
    duration: str = "10",
    mode: str = "std",
    model: str = "kling-v1",
    cfg_scale: float = 0.5,
    poll_interval: int = 10,
    max_wait: int = 600,
) -> str:
    """用 Kling API 從圖片生成視頻，回傳視頻 URL（不下載）。

    Args:
        image_url: 首幀圖片 URL（與 image_path 二選一）
        image_path: 首幀圖片本地路徑（與 image_url 二選一）
        image_tail_url: 尾幀圖片 URL（可選，用於銜接下一段）
        image_tail_path: 尾幀圖片本地路徑（可選）
        prompt: 動態描述 prompt
        negative_prompt: 負向 prompt
        duration: 視頻時長字串 "5" 或 "10"
        mode: "std"（標準）或 "pro"（高品質）
        model: 模型名稱，預設 kling-v1（最便宜）
        cfg_scale: CFG 比例，預設 0.5
        poll_interval: 輪詢間隔（秒）
        max_wait: 最大等待時間（秒）

    Returns:
        視頻 URL 字串

    Raises:
        RuntimeError if generation fails or times out
        ValueError if neither image_url nor image_path provided
    """
    headers = _api_headers()

    req_body: dict = {
        "model_name": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "cfg_scale": cfg_scale,
        "mode": mode,
        "duration": str(duration),
    }

    # 首幀圖片
    if image_url:
        req_body["image_url"] = image_url
    elif image_path:
        image_path = Path(image_path)
        if not image_path.is_absolute():
            image_path = PROJECT_ROOT / image_path
        if not image_path.exists():
            raise FileNotFoundError(f"圖片不存在: {image_path}")
        data = image_path.read_bytes()
        req_body["image"] = base64.b64encode(data).decode("utf-8")
    else:
        raise ValueError("必須提供 image_url 或 image_path 其中之一")

    # 尾幀圖片（可選，用於一鏡到底銜接）
    if image_tail_url:
        req_body["image_tail_url"] = image_tail_url
    elif image_tail_path:
        image_tail_path = Path(image_tail_path)
        if not image_tail_path.is_absolute():
            image_tail_path = PROJECT_ROOT / image_tail_path
        if not image_tail_path.exists():
            raise FileNotFoundError(f"尾幀圖片不存在: {image_tail_path}")
        tail_data = image_tail_path.read_bytes()
        req_body["image_tail"] = base64.b64encode(tail_data).decode("utf-8")

    has_tail = bool(image_tail_url or image_tail_path)
    logger.info("提交 Kling 視頻生成任務 (duration=%s, mode=%s, model=%s, tail=%s)...", duration, mode, model, has_tail)
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

    # 輪詢等待結果
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
            logger.info("生視頻完成，URL: %s", video_url[:80])
            return video_url

        if status == "failed":
            error_msg = poll_result["data"].get("task_status_msg", "未知錯誤")
            raise RuntimeError(f"Kling 視頻生成失敗: {error_msg}")

    raise RuntimeError(f"Kling 視頻生成超時（{max_wait}s）")


def generate_video(
    image_url: str = "",
    image_path: str | Path = "",
    image_tail_url: str = "",
    image_tail_path: str | Path = "",
    prompt: str = "",
    negative_prompt: str = "",
    duration: str = "10",
    output_path: str | Path = "",
    mode: str = "std",
    model: str = "kling-v1",
    poll_interval: int = 10,
    max_wait: int = 600,
) -> Path:
    """用 Kling API 從圖片生成視頻並下載到本地。

    Args:
        image_url: 來源圖片 URL（與 image_path 二選一）
        image_path: 來源圖片本地路徑（與 image_url 二選一）
        prompt: 動態描述 prompt
        negative_prompt: 負向 prompt
        duration: 視頻時長字串 "5" 或 "10"
        output_path: 輸出視頻路徑
        mode: "std"（標準）或 "pro"（高品質）
        model: 模型名稱，預設 kling-v1-5
        poll_interval: 輪詢間隔（秒）
        max_wait: 最大等待時間（秒）

    Returns:
        output_path on success

    Raises:
        RuntimeError if generation fails
    """
    if image_path:
        image_path = Path(image_path)
        if not image_path.is_absolute():
            image_path = PROJECT_ROOT / image_path
        out = Path(output_path) if output_path else image_path.with_suffix(".mp4")
    else:
        out = Path(output_path) if output_path else Path(f"video_{int(time.time())}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    video_url = generate_video_url(
        image_url=image_url,
        image_path=image_path or "",
        image_tail_url=image_tail_url,
        image_tail_path=image_tail_path or "",
        prompt=prompt,
        negative_prompt=negative_prompt,
        duration=duration,
        mode=mode,
        model=model,
        poll_interval=poll_interval,
        max_wait=max_wait,
    )

    logger.info("下載視頻: %s", video_url[:80])
    vid_resp = httpx.get(video_url, timeout=120, follow_redirects=True)
    vid_resp.raise_for_status()
    out.write_bytes(vid_resp.content)
    logger.info("視頻已儲存: %s (%d bytes)", out, len(vid_resp.content))
    return out


def generate_text2video(
    prompt: str,
    negative_prompt: str = "",
    duration: str = "5",
    output_path: str | Path = "",
    mode: str = "std",
    model: str = "kling-v1",
    cfg_scale: float = 0.5,
    aspect_ratio: str = "9:16",
    poll_interval: int = 10,
    max_wait: int = 600,
) -> Path:
    """用 Kling API 從文字 prompt 生成視頻（text-to-video）。

    Args:
        prompt: 視頻描述 prompt
        negative_prompt: 負向 prompt
        duration: 視頻時長字串 "5" 或 "10"
        output_path: 輸出視頻路徑
        mode: "std"（標準）或 "pro"（高品質）
        model: 模型名稱
        cfg_scale: CFG 比例
        aspect_ratio: 畫面比例，預設 9:16（豎屏）
        poll_interval: 輪詢間隔（秒）
        max_wait: 最大等待時間（秒）

    Returns:
        output_path on success
    """
    headers = _api_headers()

    req_body = {
        "model_name": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "cfg_scale": cfg_scale,
        "mode": mode,
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
    }

    out = Path(output_path) if output_path else GENERATED_VIDEOS_DIR / f"text2video_{int(time.time())}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    logger.info("提交 Kling text2video 任務 (prompt=%s, duration=%s, mode=%s)...", prompt[:50], duration, mode)
    resp = httpx.post(
        f"{BASE_URL}/v1/videos/text2video",
        headers=headers,
        json=req_body,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"Kling API 錯誤: {result.get('message', result)}")

    task_id = result["data"]["task_id"]
    logger.info("Kling text2video 任務已提交: task_id=%s", task_id)

    # 輪詢等待結果
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(poll_interval)

        headers = _api_headers()
        poll_resp = httpx.get(
            f"{BASE_URL}/v1/videos/text2video/{task_id}",
            headers=headers,
            timeout=30,
        )
        poll_resp.raise_for_status()
        poll_result = poll_resp.json()

        if poll_result.get("code") != 0:
            raise RuntimeError(f"Kling API 輪詢錯誤: {poll_result.get('message', poll_result)}")

        status = poll_result["data"]["task_status"]
        elapsed = time.time() - start
        logger.info("Kling text2video 狀態: %s (%.0fs)", status, elapsed)

        if status == "succeed":
            videos = poll_result["data"]["task_result"]["videos"]
            if not videos:
                raise RuntimeError("Kling 返回成功但無視頻")
            video_url = videos[0]["url"]
            logger.info("下載視頻: %s", video_url[:80])
            vid_resp = httpx.get(video_url, timeout=120, follow_redirects=True)
            vid_resp.raise_for_status()
            out.write_bytes(vid_resp.content)
            logger.info("text2video 視頻已儲存: %s (%d bytes)", out, len(vid_resp.content))
            return out

        if status == "failed":
            error_msg = poll_result["data"].get("task_status_msg", "未知錯誤")
            raise RuntimeError(f"Kling text2video 失敗: {error_msg}")

    raise RuntimeError(f"Kling text2video 超時（{max_wait}s）")


def batch_generate(
    frames: list[dict],
    drama_id: str,
    duration_sec: int = 10,
    mode: str = "std",
    on_progress=None,
) -> list[dict]:
    """批次從分鏡圖生成視頻片段，支援前後幀銜接（一鏡到底效果）。

    每段視頻的首幀是當前分鏡圖，尾幀是下一張分鏡圖，
    這樣拼接後畫面連貫，像攝影機一直在走。
    最後一段沒有尾幀（自然結束）。

    Args:
        frames: list of {frame_number, image_url?, image_path?, video_prompt?, duration_sec?}
        drama_id: drama ID，用來組織輸出路徑
        duration_sec: 預設每段時長（秒）
        mode: "std" 或 "pro"
        on_progress: callback(current, total, message)

    Returns:
        list of {frame_number, video_url, video_path, status, error?}
    """
    output_dir = GENERATED_VIDEOS_DIR / drama_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(frames)

    for i, frame in enumerate(frames):
        num = frame.get("frame_number", i + 1)
        image_url = frame.get("image_url", "")
        image_path = frame.get("image_path", "")
        prompt = frame.get("video_prompt", frame.get("image_prompt", ""))
        negative_prompt = frame.get("negative_prompt", "")
        dur = str(frame.get("duration_sec", duration_sec))
        out_path = output_dir / f"clip_{num:03d}.mp4"

        # 取下一幀作為尾幀（一鏡到底銜接）
        tail_url = ""
        tail_path = ""
        if i < total - 1:
            next_frame = frames[i + 1]
            tail_url = next_frame.get("image_url", "")
            tail_path = next_frame.get("image_path", "")

        has_tail = bool(tail_url or tail_path)
        if on_progress:
            tail_info = " → 銜接下一幀" if has_tail else " (最後一段)"
            on_progress(i, total, f"生成視頻片段 #{num}{tail_info}...")

        try:
            video_url = generate_video_url(
                image_url=image_url,
                image_path=image_path,
                image_tail_url=tail_url,
                image_tail_path=tail_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration=dur,
                mode=mode,
            )
            # Download to local file
            vid_resp = httpx.get(video_url, timeout=120, follow_redirects=True)
            vid_resp.raise_for_status()
            out_path.write_bytes(vid_resp.content)

            results.append({
                "frame_number": num,
                "video_url": video_url,
                "video_path": str(out_path.relative_to(PROJECT_ROOT)),
                "video_prompt": prompt,
                "duration_sec": int(dur),
                "has_tail_frame": has_tail,
                "status": "ok",
            })
            logger.info("[%d/%d] 視頻片段 #%d 生成成功 (tail=%s): %s", i + 1, total, num, has_tail, video_url[:60])
        except Exception as e:
            results.append({
                "frame_number": num,
                "video_url": None,
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
        "chained_frames": True,
        "clips": results,
    }
    meta_path = output_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return results
