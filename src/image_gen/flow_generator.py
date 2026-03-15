"""Flow Nano Banana 2 — Playwright 自動化生圖

透過 CDP 連接已開啟的 Chrome（port 18800），
自動操作 Google Flow 網頁版生成 9:16 豎版分鏡圖。
"""

from __future__ import annotations

import logging
import time
import re
import base64
import httpx
from pathlib import Path

from ..utils.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

FLOW_URL = "https://labs.google/fx/zh/tools/flow"
CDP_ENDPOINT = "http://localhost:18800"
GENERATED_IMAGES_DIR = PROJECT_ROOT / "data" / "generated_images"


def generate_single_image(
    prompt: str,
    output_path: Path,
    max_retries: int = 2,
) -> Path:
    """用 Flow Nano Banana 2 生成一張圖片。

    Args:
        prompt: 生圖 prompt
        output_path: 輸出圖片路徑
        max_retries: 最大重試次數

    Returns:
        output_path on success

    Raises:
        RuntimeError if generation fails after retries
    """
    from playwright.sync_api import sync_playwright

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info("重試第 %d 次...", attempt)
                time.sleep(3)

            with sync_playwright() as pw:
                browser = pw.chromium.connect_over_cdp(CDP_ENDPOINT)
                # 用已有的 context（有 Google 登入態），不要開 new_context（會是無痕沒登入）
                context = browser.contexts[0]
                page = context.new_page()

                try:
                    result = _do_generate(page, prompt, output_path)
                    return result
                finally:
                    page.close()

        except Exception as e:
            last_error = e
            logger.warning("生圖失敗 (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)

    raise RuntimeError(f"Flow 生圖失敗（重試 {max_retries} 次後）: {last_error}")


def _do_generate(page, prompt: str, output_path: Path) -> Path:
    """在 Flow 頁面上執行一次完整的生圖流程。

    Flow 頁面已預設 Nano Banana 2 crop_9_16 x1，
    不需要手動選比例和數量。
    """

    logger.info("開啟 Flow 頁面...")
    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)

    # ── 如果需要先點「新建项目」進入編輯模式 ──
    _ensure_project_mode(page)

    # ── 輸入 prompt ──
    logger.info("輸入 prompt...")
    _input_prompt(page, prompt)

    # ── 點擊生成 ──
    logger.info("點擊生成按鈕...")
    _click_generate(page)

    # ── 等待生成完成 ──
    logger.info("等待生成完成...")
    _wait_for_generation(page, timeout=120)

    # ── 下載圖片 ──
    logger.info("下載圖片...")
    _download_image(page, output_path)

    logger.info("圖片已儲存: %s", output_path)
    return output_path


def _ensure_project_mode(page):
    """如果頁面顯示「新建项目」按鈕，點擊進入編輯模式。"""
    new_project_selectors = [
        'button:has-text("新建项目")',
        'button:has-text("新建項目")',
        'button:has-text("New project")',
        'button:has-text("开始创作")',
        'button:has-text("開始創作")',
    ]
    for sel in new_project_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(2)
                logger.info("已點擊進入項目模式")
                return
        except Exception:
            continue
    logger.info("已在項目模式中，無需點擊")


def _input_prompt(page, prompt: str):
    """輸入 prompt 文字。

    Flow 使用 contenteditable div（role="textbox"），不是 textarea。
    """
    # Flow 的輸入框是 contenteditable div
    input_selectors = [
        '[role="textbox"]',
        '[contenteditable="true"]',
        'textarea',
    ]

    for sel in input_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=5000):
                el.click()
                time.sleep(0.3)
                # contenteditable 用 fill 可能不行，改用 keyboard
                el.fill("")
                time.sleep(0.2)
                try:
                    el.fill(prompt)
                except Exception:
                    # fill 不支援 contenteditable 時，用鍵盤輸入
                    page.keyboard.insert_text(prompt)
                time.sleep(0.5)
                logger.info("已輸入 prompt (%d 字元)", len(prompt))
                return
        except Exception:
            continue

    raise RuntimeError("找不到 prompt 輸入框")


def _click_generate(page):
    """點擊生成按鈕。

    Flow 的生成按鈕文字為「创建」（簡體中文），
    頁面上可能有多個匹配的按鈕，用 .last 取最後一個（底部的那個）。
    """
    generate_selectors = [
        ('button:has-text("创建")', "last"),
        ('button:has-text("創建")', "last"),
        ('button:has-text("Create")', "last"),
        ('button:has-text("Generate")', "first"),
        ('button:has-text("生成")', "first"),
    ]

    for sel, which in generate_selectors:
        try:
            locator = page.locator(sel)
            if locator.count() > 0:
                el = locator.last if which == "last" else locator.first
                if el.is_visible(timeout=3000) and el.is_enabled():
                    el.click()
                    time.sleep(1)
                    logger.info("已點擊生成按鈕 (%s)", sel)
                    return
        except Exception:
            continue

    # Fallback: try Enter key on the input
    try:
        page.keyboard.press("Enter")
        time.sleep(1)
        logger.info("已按 Enter 送出")
        return
    except Exception:
        pass

    raise RuntimeError("找不到生成按鈕")


def _wait_for_generation(page, timeout: int = 120):
    """等待圖片生成完成。

    Flow 生成的圖片 src 包含 lh3.googleusercontent.com。
    """
    start = time.time()
    # 記錄進入時已有的圖片數量，避免誤判頁面上已存在的圖
    initial_img_count = 0
    try:
        initial_img_count = page.locator('img[src*="lh3.googleusercontent"]').count()
    except Exception:
        pass

    while time.time() - start < timeout:
        try:
            imgs = page.locator('img[src*="lh3.googleusercontent"]')
            current_count = imgs.count()
            if current_count > initial_img_count:
                # 新圖片出現了
                new_img = imgs.nth(current_count - 1)
                if new_img.is_visible():
                    box = new_img.bounding_box()
                    if box and box["width"] > 50 and box["height"] > 50:
                        logger.info("偵測到新生成的圖片")
                        time.sleep(2)  # 等圖片完全載入
                        return
        except Exception:
            pass

        elapsed = int(time.time() - start)
        if elapsed % 15 == 0 and elapsed > 0:
            logger.info("等待生圖中... (%ds/%ds)", elapsed, timeout)

        time.sleep(3)

    raise RuntimeError(f"等待生圖超時（{timeout}s）")


def _download_image(page, output_path: Path):
    """從頁面下載生成的圖片。

    優先策略：從 lh3.googleusercontent URL 直接下載（Flow 生成的圖都用這個 CDN）。
    """

    # Strategy 1: 從 lh3.googleusercontent 圖片 URL 直接下載
    try:
        imgs = page.locator('img[src*="lh3.googleusercontent"]')
        if imgs.count() > 0:
            # 取最後一張（最新生成的）
            src = imgs.last.get_attribute("src")
            if src and src.startswith("http"):
                logger.info("從 Google CDN 下載圖片...")
                resp = httpx.get(src, timeout=30, follow_redirects=True)
                resp.raise_for_status()
                output_path.write_bytes(resp.content)
                logger.info("圖片下載完成 (%d bytes)", len(resp.content))
                return
    except Exception as e:
        logger.warning("Google CDN 下載失敗: %s", e)

    # Strategy 2: 找頁面上最大的圖片
    try:
        result = page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            let best = null;
            let bestArea = 0;
            for (const img of imgs) {
                const rect = img.getBoundingClientRect();
                const area = rect.width * rect.height;
                if (area > bestArea && img.src && rect.width > 50) {
                    bestArea = area;
                    best = img.src;
                }
            }
            return best;
        }""")
        if result:
            if result.startswith("data:image"):
                match = re.match(r"data:image/\w+;base64,(.+)", result)
                if match:
                    output_path.write_bytes(base64.b64decode(match.group(1)))
                    return
            elif result.startswith("blob:"):
                img_data = page.evaluate("""async (url) => {
                    const resp = await fetch(url);
                    const blob = await resp.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }""", result)
                if img_data and "base64," in img_data:
                    b64 = img_data.split("base64,")[1]
                    output_path.write_bytes(base64.b64decode(b64))
                    return
            elif result.startswith("http"):
                resp = httpx.get(result, timeout=30, follow_redirects=True)
                resp.raise_for_status()
                output_path.write_bytes(resp.content)
                return
    except Exception as e:
        logger.warning("備用下載策略失敗: %s", e)

    # Strategy 3: 截圖圖片元素
    try:
        img_el = page.locator('img[src*="lh3.googleusercontent"]').last
        if img_el.is_visible():
            img_el.screenshot(path=str(output_path))
            logger.info("使用截圖方式儲存圖片")
            return
    except Exception as e:
        logger.warning("截圖策略失敗: %s", e)

    raise RuntimeError("無法下載生成的圖片")


def batch_generate_flow(
    frames: list[dict],
    image_set_id: str,
    style_prefix: str = "",
    on_progress=None,
) -> list[dict]:
    """批次生成分鏡圖。

    Args:
        frames: list of {frame_number, image_prompt, ...}
        image_set_id: 用來組織輸出路徑
        style_prefix: 風格前綴（加在每個 prompt 前面）
        on_progress: callback(current, total, message)

    Returns:
        list of {frame_number, image_path, status, error?}
    """
    output_dir = GENERATED_IMAGES_DIR / image_set_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(frames)

    for i, frame in enumerate(frames):
        num = frame.get("frame_number", i + 1)
        raw_prompt = frame.get("image_prompt", "")

        # Add style prefix
        prompt = f"{style_prefix}, {raw_prompt}" if style_prefix else raw_prompt

        out_path = output_dir / f"frame_{num:03d}.png"

        if on_progress:
            on_progress(i, total, f"生成分鏡 #{num}...")

        try:
            generate_single_image(prompt, out_path)
            results.append({
                "frame_number": num,
                "image_path": str(out_path.relative_to(PROJECT_ROOT)),
                "image_prompt": raw_prompt,
                "status": "ok",
            })
            logger.info("[%d/%d] 分鏡 #%d 生成成功", i + 1, total, num)
        except Exception as e:
            results.append({
                "frame_number": num,
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
        "image_set_id": image_set_id,
        "total_frames": total,
        "success_count": sum(1 for r in results if r["status"] == "ok"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "style_prefix": style_prefix,
        "frames": results,
    }
    meta_path = output_dir / "meta.json"
    import json
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return results
