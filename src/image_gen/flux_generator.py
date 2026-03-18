"""Flux 生圖 generator（透過 fal.ai API）

使用 Flux.1 [schnell] 模型生成分鏡圖。
- generate_image_url(): 生成一張圖片並回傳 URL
- generate_image(): 生成並下載圖片到本地
- batch_generate(): 批次生成分鏡圖
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import httpx

from ..utils.config import load_config, PROJECT_ROOT

logger = logging.getLogger(__name__)

GENERATED_IMAGES_DIR = PROJECT_ROOT / "data" / "generated_images"


def _get_fal_key() -> str:
    config = load_config()
    key = config.get("fal_api_key", "") or os.getenv("FAL_API_KEY", "")
    if not key:
        raise ValueError("FAL_API_KEY 未設定")
    return key


def generate_image_url(
    prompt: str,
    negative_prompt: str = "",
    image_size: str = "portrait_16_9",
    model: str = "fal-ai/flux/schnell",
    num_inference_steps: int = 4,
) -> str:
    """用 Flux (fal.ai) 生成一張圖片，回傳圖片 URL。

    Args:
        prompt: 生圖 prompt
        negative_prompt: 負向 prompt（Flux schnell 不支援，保留介面一致性）
        image_size: 圖片尺寸，預設 portrait_16_9（豎版 9:16）
        model: fal.ai 模型端點
        num_inference_steps: 推理步數（schnell 建議 1-4）

    Returns:
        圖片 URL
    """
    import fal_client

    api_key = _get_fal_key()
    os.environ["FAL_KEY"] = api_key

    arguments = {
        "prompt": prompt,
        "image_size": image_size,
        "num_inference_steps": num_inference_steps,
        "num_images": 1,
        "enable_safety_checker": False,
    }

    logger.info("提交 Flux 生圖任務 (model=%s)...", model)
    result = fal_client.subscribe(
        model,
        arguments=arguments,
        with_logs=False,
    )

    images = result.get("images", [])
    if not images:
        raise RuntimeError("Flux 生圖返回成功但無圖片")

    image_url = images[0]["url"]
    logger.info("Flux 生圖完成，URL: %s", image_url[:80])
    return image_url


def generate_image(
    prompt: str,
    output_path: str | Path,
    negative_prompt: str = "",
    image_size: str = "portrait_16_9",
) -> Path:
    """生成一張圖片並下載到本地。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_url = generate_image_url(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image_size=image_size,
    )

    logger.info("下載圖片: %s", image_url[:80])
    img_resp = httpx.get(image_url, timeout=60, follow_redirects=True)
    img_resp.raise_for_status()
    output_path.write_bytes(img_resp.content)
    logger.info("圖片已儲存: %s (%d bytes)", output_path, len(img_resp.content))
    return output_path


EXPLORER_STYLE_PREFIX = (
    "real photograph taken with old Sony Handycam, 480p low resolution, "
    "first person POV, handheld camera, single flashlight beam in darkness, "
    "abandoned building interior, film grain, motion blur, "
    "dirty lens, found footage, "
    "photorealistic, raw unedited footage, not illustration, not digital art, "
    "9:16 vertical"
)


def batch_generate(
    frames: list[dict],
    drama_id: str,
    style_prefix: str = "",
    on_progress=None,
) -> list[dict]:
    """批次生成分鏡圖。"""
    output_dir = GENERATED_IMAGES_DIR / drama_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(frames)

    # Always prepend explorer style prefix
    effective_prefix = EXPLORER_STYLE_PREFIX
    if style_prefix:
        effective_prefix = f"{EXPLORER_STYLE_PREFIX}, {style_prefix}"

    for i, frame in enumerate(frames):
        num = frame.get("frame_number", i + 1)
        raw_prompt = frame.get("image_prompt", "")
        negative_prompt = frame.get("negative_prompt", "")
        prompt = f"{effective_prefix}, {raw_prompt}" if raw_prompt else effective_prefix
        out_path = output_dir / f"frame_{num:03d}.png"

        if on_progress:
            on_progress(i, total, f"生成分鏡 #{num}...")

        try:
            image_url = generate_image_url(prompt=prompt)

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

        if i < total - 1:
            time.sleep(1)

    if on_progress:
        on_progress(total, total, "完成")

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
