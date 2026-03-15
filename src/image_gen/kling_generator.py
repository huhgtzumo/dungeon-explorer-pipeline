"""Kling AI 生圖 generator (Step 5 wrapper)

此模組是 kling_client 的輕量封裝，提供以下功能：
- generate_image_url(): 生成一張圖片並回傳 URL（不下載到本地）
- generate_image(): 生成並下載圖片到本地路徑
- batch_generate(): 批次生成分鏡圖（與 kling_client 相同）

model 預設使用 kling-v1（Kolors V1.0），aspect_ratio 預設 9:16（豎版行動裝置）。
每張圖消耗 1 個 API 單位。
JWT 認證、非同步輪詢等邏輯均在 kling_client 中實現。
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
import jwt

from ..utils.config import load_config, PROJECT_ROOT

logger = logging.getLogger(__name__)

BASE_URL = "https://api-singapore.klingai.com"
GENERATED_IMAGES_DIR = PROJECT_ROOT / "data" / "generated_images"


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


def generate_image_url(
    prompt: str,
    negative_prompt: str = "",
    aspect_ratio: str = "9:16",
    model: str = "kling-v1",
    poll_interval: int = 5,
    max_wait: int = 300,
) -> str:
    """用 Kling API 生成一張圖片，回傳圖片 URL（不下載）。

    Args:
        prompt: 生圖 prompt
        negative_prompt: 負向 prompt
        aspect_ratio: 長寬比，預設 9:16（豎版）
        model: 模型名稱，預設 kling-v1-5
        poll_interval: 輪詢間隔（秒）
        max_wait: 最大等待時間（秒）

    Returns:
        圖片 URL 字串

    Raises:
        RuntimeError if generation fails or times out
    """
    headers = _api_headers()

    req_body = {
        "model_name": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "n": 1,
        "aspect_ratio": aspect_ratio,
    }

    logger.info("提交 Kling 生圖任務 (model=%s, ratio=%s)...", model, aspect_ratio)
    resp = httpx.post(
        f"{BASE_URL}/v1/images/generations",
        headers=headers,
        json=req_body,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"Kling API 錯誤: {result.get('message', result)}")

    task_id = result["data"]["task_id"]
    logger.info("Kling 生圖任務已提交: task_id=%s", task_id)

    # 輪詢等待結果
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(poll_interval)

        headers = _api_headers()  # 每次重新簽發（避免過期）
        poll_resp = httpx.get(
            f"{BASE_URL}/v1/images/generations/{task_id}",
            headers=headers,
            timeout=30,
        )
        poll_resp.raise_for_status()
        poll_result = poll_resp.json()

        if poll_result.get("code") != 0:
            raise RuntimeError(f"Kling API 輪詢錯誤: {poll_result.get('message', poll_result)}")

        status = poll_result["data"]["task_status"]
        logger.info("Kling 任務狀態: %s (%.0fs)", status, time.time() - start)

        if status == "succeed":
            images = poll_result["data"]["task_result"]["images"]
            if not images:
                raise RuntimeError("Kling 返回成功但無圖片")
            image_url = images[0]["url"]
            logger.info("生圖完成，URL: %s", image_url[:80])
            return image_url

        if status == "failed":
            error_msg = poll_result["data"].get("task_status_msg", "未知錯誤")
            raise RuntimeError(f"Kling 生圖失敗: {error_msg}")

    raise RuntimeError(f"Kling 生圖超時（{max_wait}s）")


def generate_image(
    prompt: str,
    output_path: str | Path,
    negative_prompt: str = "",
    aspect_ratio: str = "9:16",
    model: str = "kling-v1",
    poll_interval: int = 5,
    max_wait: int = 300,
) -> Path:
    """用 Kling API 生成一張圖片並下載到本地。

    Args:
        prompt: 生圖 prompt
        output_path: 輸出圖片路徑
        negative_prompt: 負向 prompt
        aspect_ratio: 長寬比，預設 9:16（豎版）
        model: 模型名稱，預設 kling-v1-5
        poll_interval: 輪詢間隔（秒）
        max_wait: 最大等待時間（秒）

    Returns:
        output_path on success

    Raises:
        RuntimeError if generation fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_url = generate_image_url(
        prompt=prompt,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
        model=model,
        poll_interval=poll_interval,
        max_wait=max_wait,
    )

    logger.info("下載圖片: %s", image_url[:80])
    img_resp = httpx.get(image_url, timeout=60, follow_redirects=True)
    img_resp.raise_for_status()
    output_path.write_bytes(img_resp.content)
    logger.info("圖片已儲存: %s (%d bytes)", output_path, len(img_resp.content))
    return output_path


def batch_generate(
    frames: list[dict],
    drama_id: str,
    style_prefix: str = "",
    on_progress=None,
) -> list[dict]:
    """批次生成分鏡圖，回傳包含 image_url 的結果列表。

    Args:
        frames: list of {frame_number, image_prompt, negative_prompt?, ...}
        drama_id: 用來組織輸出路徑（也當 image_set_id）
        style_prefix: 風格前綴（加在每個 prompt 前面）
        on_progress: callback(current, total, message)

    Returns:
        list of {frame_number, image_url, image_path, status, error?}
    """
    import json
    output_dir = GENERATED_IMAGES_DIR / drama_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(frames)

    for i, frame in enumerate(frames):
        num = frame.get("frame_number", i + 1)
        raw_prompt = frame.get("image_prompt", "")
        negative_prompt = frame.get("negative_prompt", "")
        prompt = f"{style_prefix}, {raw_prompt}" if style_prefix else raw_prompt
        out_path = output_dir / f"frame_{num:03d}.png"

        if on_progress:
            on_progress(i, total, f"生成分鏡 #{num}...")

        try:
            image_url = generate_image_url(
                prompt=prompt,
                negative_prompt=negative_prompt,
            )
            # Download to local file
            img_resp = httpx.get(image_url, timeout=60, follow_redirects=True)
            img_resp.raise_for_status()
            out_path.write_bytes(img_resp.content)

            results.append({
                "frame_number": num,
                "image_url": image_url,
                "image_path": str(out_path.relative_to(PROJECT_ROOT)),
                "image_prompt": raw_prompt,
                "status": "ok",
            })
            logger.info("[%d/%d] 分鏡 #%d 生成成功: %s", i + 1, total, num, image_url[:60])
        except Exception as e:
            results.append({
                "frame_number": num,
                "image_url": None,
                "image_path": None,
                "image_prompt": raw_prompt,
                "status": "error",
                "error": str(e),
            })
            logger.error("[%d/%d] 分鏡 #%d 生成失敗: %s", i + 1, total, num, e)

        # Rate limit between generations
        if i < total - 1:
            time.sleep(2)

    if on_progress:
        on_progress(total, total, "完成")

    # Save metadata
    meta = {
        "image_set_id": drama_id,
        "total_frames": total,
        "success_count": sum(1 for r in results if r["status"] == "ok"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "style_prefix": style_prefix,
        "frames": results,
    }
    meta_path = output_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return results
