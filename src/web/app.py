"""探索者計劃 Pipeline — Web Dashboard (v2: database-style workflow)

啟動方式: python -m src.web.app
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..utils.config import load_config, PROJECT_ROOT
from ..utils import index_db

logger = logging.getLogger(__name__)

# ──────────────────────────── Rate Limiter ──────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ──────────────────────────── Pydantic Models ──────────────────────────────
class GenerateRequest(BaseModel):
    source_analysis_id: str = ""
    human_requirements: str = Field(default="", max_length=5000)
    genre: str = Field(default="廢墟探索", max_length=200)
    style: str = Field(default="dramatic", max_length=200)


class StoryboardRequest(BaseModel):
    source_script_id: str = ""


class GenerateImagesRequest(BaseModel):
    storyboard_id: str = ""
    style_prefix: str = Field(default="", max_length=500)


class GenerateVideosRequest(BaseModel):
    image_set_id: str = ""
    duration_sec: int = Field(default=5, ge=1, le=30)
    mode: str = Field(default="std", max_length=50)


class GenerateKBRequest(BaseModel):
    genre: str = Field(default="", max_length=200)
    style: str = Field(default="", max_length=200)
    episode_count: int = Field(default=1, ge=1, le=100)
    duration_sec: int = Field(default=60, ge=10, le=600)
    human_requirements: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list)
    selected_elements: Optional[dict] = None

# ──────────────────────────── Thread Pool for CPU/IO-bound tasks ──────────────
_executor = ThreadPoolExecutor(max_workers=4)


def _run_in_thread(fn, *args):
    """Run a blocking function in a background thread so it doesn't block the event loop."""
    import threading
    t = threading.Thread(target=fn, args=args, daemon=True)
    t.start()


app = FastAPI(title="探索者計劃 Explorer Plan Dashboard", version="2.0.0")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        {"error": "請求過於頻繁，請稍後再試", "detail": str(exc)},
        status_code=429,
    )


# Static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory task store
_tasks: dict[str, dict] = {}
_MAX_TASKS = 200  # Keep at most this many tasks to prevent memory leak
_TASK_TTL_HOURS = 24  # Tasks older than this will be cleaned up

# Cached KnowledgeBase instance (lazy init)
_kb_instance = None


def _get_kb():
    """Return a cached KnowledgeBase instance."""
    global _kb_instance
    if _kb_instance is None:
        from ..knowledge.knowledge_base import KnowledgeBase
        _kb_instance = KnowledgeBase()
    return _kb_instance


def _safe_read_json(fpath: Path, default=None):
    """Read and parse a JSON file, returning default on any error."""
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read JSON file %s: %s", fpath, e)
        return default


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _cleanup_tasks() -> None:
    """Remove finished tasks older than _TASK_TTL_HOURS, and cap at _MAX_TASKS."""
    now = datetime.now()
    # TTL-based cleanup: remove any finished task older than 24 hours
    expired = []
    for tid, t in _tasks.items():
        if t["status"] not in ("done", "error"):
            continue
        finished_at = t.get("finished_at")
        if finished_at:
            try:
                finished_dt = datetime.strptime(finished_at, "%Y-%m-%d %H:%M:%S")
                if now - finished_dt > timedelta(hours=_TASK_TTL_HOURS):
                    expired.append(tid)
            except ValueError:
                expired.append(tid)  # malformed timestamp, remove
    for tid in expired:
        del _tasks[tid]

    # Also cap total count
    if len(_tasks) <= _MAX_TASKS:
        return
    finished = [
        (tid, t) for tid, t in _tasks.items()
        if t["status"] in ("done", "error")
    ]
    finished.sort(key=lambda x: x[1].get("finished_at") or "")
    to_remove = len(_tasks) - _MAX_TASKS
    for tid, _ in finished[:to_remove]:
        del _tasks[tid]


# ──────────────────────────── Pages ────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# ──────────────────────────── Index API ────────────────────────────

@app.get("/api/index")
async def get_index():
    """回傳完整 index.json"""
    return index_db.read_index()


@app.get("/api/index/{collection}")
async def get_collection(collection: str):
    """回傳某個 collection 的所有條目"""
    return {"data": index_db.list_entries(collection)}


# ──────────────────────────── Script API ────────────────────────────

@app.get("/api/scripts")
async def list_scripts():
    return {"data": index_db.list_entries("scripts")}


@app.get("/api/scripts/{script_id}")
async def get_script_detail(script_id: str):
    entry = index_db.get_entry("scripts", script_id)
    if not entry:
        return JSONResponse({"error": "劇本不存在"}, status_code=404)
    fpath = PROJECT_ROOT / entry["file"]
    if not fpath.exists():
        return {"data": None}
    return {"data": _safe_read_json(fpath), "meta": entry}


@app.post("/api/trigger/generate")
@limiter.limit("20/hour")
async def trigger_generate(request: Request):
    """觸發劇本生成：body={source_analysis_id, human_requirements, genre, style}"""
    try:
        raw_body = await request.body()
        if len(raw_body) > 50_000:  # 50KB body limit
            return JSONResponse({"error": "請求內容過大"}, status_code=413)
        body = json.loads(raw_body)
    except (json.JSONDecodeError, Exception):
        body = {}

    try:
        validated = GenerateRequest(**body)
    except Exception as e:
        return JSONResponse({"error": f"參數驗證失敗: {e}"}, status_code=422)

    task_id = _create_task("generate")
    _run_in_thread(
        _run_generate, task_id, validated.source_analysis_id,
        validated.human_requirements, validated.genre, validated.style
    )
    return {"task_id": task_id, "status": "started"}


def _run_generate(task_id: str, source_analysis_id: str,
                  human_requirements: str, genre: str, style: str):
    task = _tasks[task_id]
    try:
        task["logs"].append(f"[{_now()}] 開始劇本生成...")

        # Load analysis if specified
        analysis = {}
        if source_analysis_id:
            entry = index_db.get_entry("analyses", source_analysis_id)
            if entry:
                fpath = PROJECT_ROOT / entry["file"]
                if fpath.exists():
                    analysis = _safe_read_json(fpath, {})
                    task["logs"].append(f"[{_now()}] 使用分析: {source_analysis_id}")

        if human_requirements:
            task["logs"].append(f"[{_now()}] 用戶要求: {human_requirements[:100]}")

        from ..scriptwriter.generator import generate_script
        script = generate_script(
            trending_analysis=analysis,
            genre=genre,
            style=style,
            human_requirements=human_requirements,
        )

        # Validate response before saving
        if script.get("error"):
            raise ValueError(f"劇本生成失敗: {script.get('error')} — {script.get('raw', '')[:200]}")
        if not script.get("scenes") and not script.get("episodes"):
            raise ValueError("劇本生成結果為空（無場景資料），請重試")

        # Save
        script_id = index_db.generate_id("script")
        script["script_id"] = script_id
        script["source_analysis_id"] = source_analysis_id
        script["human_requirements"] = human_requirements

        script_dir = PROJECT_ROOT / "data" / "scripts" / script_id
        script_dir.mkdir(parents=True, exist_ok=True)
        script_file = script_dir / "script.json"
        script_file.write_text(
            json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Update index
        rel_path = str(script_file.relative_to(PROJECT_ROOT))
        index_db.add_script(
            script_id,
            script.get("title", script.get("series_title", "")),
            source_analysis_id,
            human_requirements,
            "single",
            rel_path,
        )

        task["result"] = {
            "script_id": script_id,
            "title": script.get("title", script.get("series_title", "")),
        }
        task["logs"].append(f"[{_now()}] 劇本生成完成: {task['result']['title']}")
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


# ──────────────────────────── Storyboard API ────────────────────────────

@app.get("/api/storyboards")
async def list_storyboards():
    storyboards = index_db.list_entries("storyboards")
    # Enrich with script title
    scripts = {s["id"]: s for s in index_db.list_entries("scripts")}
    for sb in storyboards:
        sid = sb.get("source_script_id", "")
        if sid in scripts:
            sb["script_title"] = scripts[sid].get("title") or scripts[sid].get("series_title", sid)
        else:
            sb["script_title"] = sid
    return {"data": storyboards}


@app.get("/api/storyboards/{sb_id}")
async def get_storyboard_detail(sb_id: str):
    entry = index_db.get_entry("storyboards", sb_id)
    if not entry:
        return JSONResponse({"error": "分鏡不存在"}, status_code=404)
    fpath = PROJECT_ROOT / entry["file"]
    if not fpath.exists():
        return {"data": []}
    return {"data": _safe_read_json(fpath), "meta": entry}


@app.post("/api/trigger/storyboard")
@limiter.limit("20/hour")
async def trigger_storyboard(request: Request):
    """觸發分鏡：body={source_script_id}"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        validated = StoryboardRequest(**body)
    except Exception as e:
        return JSONResponse({"error": f"參數驗證失敗: {e}"}, status_code=422)

    if not validated.source_script_id:
        return JSONResponse({"error": "請指定劇本 ID"}, status_code=400)

    task_id = _create_task("storyboard")
    _run_in_thread(_run_storyboard, task_id, validated.source_script_id)
    return {"task_id": task_id, "status": "started"}


def _run_storyboard(task_id: str, source_script_id: str):
    task = _tasks[task_id]
    try:
        task["logs"].append(f"[{_now()}] 開始分鏡拆解...")

        # Load script
        entry = index_db.get_entry("scripts", source_script_id)
        if not entry:
            raise FileNotFoundError(f"劇本不存在: {source_script_id}")
        fpath = PROJECT_ROOT / entry["file"]
        if not fpath.exists():
            raise FileNotFoundError(f"劇本檔案不存在: {fpath}")
        script = _safe_read_json(fpath)
        if script is None:
            raise ValueError(f"劇本檔案損壞: {fpath}")

        drama_id = source_script_id

        from ..scriptwriter.storyboard import generate_storyboard, setup_characters, save_storyboard
        char_manager = setup_characters(script, drama_id)
        frames = generate_storyboard(script, char_manager)
        save_storyboard(frames, drama_id)

        # Update index
        sb_id = index_db.generate_id("sb")
        sb_dir = PROJECT_ROOT / "data" / "storyboards" / drama_id
        sb_file = sb_dir / "storyboard.json"
        rel_path = str(sb_file.relative_to(PROJECT_ROOT))
        index_db.add_storyboard(sb_id, source_script_id, len(frames), rel_path)

        task["result"] = {
            "storyboard_id": sb_id,
            "source_script_id": source_script_id,
            "frame_count": len(frames),
        }
        task["logs"].append(f"[{_now()}] 分鏡完成: {len(frames)} 個畫面")
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


# ──────────────────────────── Image Generation API ────────────────────────────

GENERATED_IMAGES_DIR = PROJECT_ROOT / "data" / "generated_images"


@app.get("/api/image-sets")
async def list_image_sets():
    """列出所有已生成的圖片集。"""
    if not GENERATED_IMAGES_DIR.exists():
        return {"data": []}
    sets = []
    for d in sorted(GENERATED_IMAGES_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_file = d / "meta.json"
        if meta_file.exists():
            meta = _safe_read_json(meta_file, {})
            meta["id"] = d.name
            sets.append(meta)
        else:
            # Directory exists but no meta — count PNGs
            pngs = list(d.glob("*.png"))
            sets.append({
                "id": d.name,
                "image_set_id": d.name,
                "total_frames": len(pngs),
                "success_count": len(pngs),
                "error_count": 0,
            })
    return {"data": sets}


@app.get("/api/image-sets/{set_id}")
async def get_image_set_detail(set_id: str):
    """取得圖片集詳情。"""
    set_dir = GENERATED_IMAGES_DIR / set_id
    if not set_dir.exists():
        return JSONResponse({"error": "圖片集不存在"}, status_code=404)
    meta_file = set_dir / "meta.json"
    if meta_file.exists():
        meta = _safe_read_json(meta_file, {})
    else:
        pngs = sorted(set_dir.glob("*.png"))
        meta = {
            "image_set_id": set_id,
            "total_frames": len(pngs),
            "frames": [
                {"frame_number": i + 1, "image_path": str(p.relative_to(PROJECT_ROOT)), "status": "ok"}
                for i, p in enumerate(pngs)
            ],
        }
    return {"data": meta}


@app.get("/api/images/{set_id}/{filename}")
async def serve_image(set_id: str, filename: str):
    """提供已生成的圖片檔案。"""
    from fastapi.responses import FileResponse
    # Path traversal protection
    if ".." in filename or "/" in filename or ".." in set_id or "/" in set_id:
        return JSONResponse({"error": "無效的檔案名稱"}, status_code=400)
    img_path = (GENERATED_IMAGES_DIR / set_id / filename).resolve()
    if not img_path.is_relative_to(GENERATED_IMAGES_DIR.resolve()):
        return JSONResponse({"error": "無效的檔案路徑"}, status_code=400)
    if not img_path.exists() or not img_path.is_file():
        return JSONResponse({"error": "圖片不存在"}, status_code=404)
    return FileResponse(str(img_path), media_type="image/png")


@app.post("/api/trigger/generate-images")
@limiter.limit("20/hour")
async def trigger_generate_images(request: Request):
    """觸發分鏡圖生成：body={storyboard_id, style_prefix?}"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        validated = GenerateImagesRequest(**body)
    except Exception as e:
        return JSONResponse({"error": f"參數驗證失敗: {e}"}, status_code=422)

    storyboard_id = validated.storyboard_id
    style_prefix = validated.style_prefix

    if not storyboard_id:
        return JSONResponse({"error": "請指定分鏡 ID"}, status_code=400)

    # Verify storyboard exists
    entry = index_db.get_entry("storyboards", storyboard_id)
    if not entry:
        return JSONResponse({"error": "分鏡不存在"}, status_code=404)

    task_id = _create_task("generate-images", storyboard_id=storyboard_id)
    _run_in_thread(_run_generate_images, task_id, storyboard_id, style_prefix)
    return {"task_id": task_id, "status": "started"}


def _run_generate_images(task_id: str, storyboard_id: str, style_prefix: str):
    """Background task: generate images for a storyboard using Kling API."""
    task = _tasks[task_id]
    try:
        task["logs"].append(f"[{_now()}] 開始生成分鏡圖（Flux via fal.ai）...")

        # Load storyboard
        entry = index_db.get_entry("storyboards", storyboard_id)
        if not entry:
            raise FileNotFoundError(f"分鏡不存在: {storyboard_id}")
        fpath = PROJECT_ROOT / entry["file"]
        if not fpath.exists():
            raise FileNotFoundError(f"分鏡檔案不存在: {fpath}")
        frames = _safe_read_json(fpath, [])
        if not frames:
            raise ValueError("分鏡表為空")

        # Prepare frames with frame_number
        for i, f in enumerate(frames):
            if "frame_number" not in f:
                f["frame_number"] = i + 1

        image_set_id = f"imgset_{storyboard_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        total = len(frames)
        task["logs"].append(f"[{_now()}] 共 {total} 個分鏡需要生圖")

        def on_progress(current, total_count, message):
            _set_progress(task, current, total_count, message)
            task["logs"].append(f"[{_now()}] [{current}/{total_count}] {message}")

        from ..image_gen.flux_generator import batch_generate as flux_batch_generate
        results = flux_batch_generate(
            frames=frames,
            drama_id=image_set_id,
            style_prefix=style_prefix,
            on_progress=on_progress,
        )

        success_count = sum(1 for r in results if r["status"] == "ok")
        error_count = sum(1 for r in results if r["status"] == "error")

        task["result"] = {
            "image_set_id": image_set_id,
            "storyboard_id": storyboard_id,
            "total_frames": total,
            "success_count": success_count,
            "error_count": error_count,
        }
        task["logs"].append(
            f"[{_now()}] 生圖完成: {success_count} 成功, {error_count} 失敗"
        )
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


# ──────────────────────────── Video Generation API ────────────────────────────

GENERATED_VIDEOS_DIR = PROJECT_ROOT / "data" / "generated_videos"


@app.get("/api/video-sets")
async def list_video_sets():
    """列出所有已生成的視頻集。"""
    if not GENERATED_VIDEOS_DIR.exists():
        return {"data": []}
    sets = []
    for d in sorted(GENERATED_VIDEOS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_file = d / "meta.json"
        if meta_file.exists():
            meta = _safe_read_json(meta_file, {})
            meta["id"] = d.name
            sets.append(meta)
        else:
            mp4s = sorted(d.glob("*.mp4"))
            sets.append({
                "id": d.name,
                "video_set_id": d.name,
                "total_clips": len(mp4s),
            })
    return {"data": sets}


@app.get("/api/video-sets/{set_id}")
async def get_video_set(set_id: str):
    """取得指定視頻集的詳細資訊。"""
    set_dir = GENERATED_VIDEOS_DIR / set_id
    if not set_dir.exists():
        return JSONResponse({"error": "視頻集不存在"}, status_code=404)
    meta_file = set_dir / "meta.json"
    if meta_file.exists():
        meta = _safe_read_json(meta_file, {})
    else:
        mp4s = sorted(set_dir.glob("*.mp4"))
        meta = {
            "video_set_id": set_id,
            "total_clips": len(mp4s),
            "clips": [
                {"frame_number": i + 1, "video_path": str(p.relative_to(PROJECT_ROOT)), "status": "ok"}
                for i, p in enumerate(mp4s)
            ],
        }
    return {"data": meta}


@app.get("/api/videos/{set_id}/{filename}")
async def serve_video(set_id: str, filename: str):
    """提供已生成的視頻檔案。"""
    from fastapi.responses import FileResponse
    # Path traversal protection
    if ".." in filename or "/" in filename or ".." in set_id or "/" in set_id:
        return JSONResponse({"error": "無效的檔案名稱"}, status_code=400)
    vid_path = (GENERATED_VIDEOS_DIR / set_id / filename).resolve()
    if not vid_path.is_relative_to(GENERATED_VIDEOS_DIR.resolve()):
        return JSONResponse({"error": "無效的檔案路徑"}, status_code=400)
    if not vid_path.exists() or not vid_path.is_file():
        return JSONResponse({"error": "視頻不存在"}, status_code=404)
    return FileResponse(str(vid_path), media_type="video/mp4")


@app.post("/api/trigger/generate-videos")
@limiter.limit("10/hour")
async def trigger_generate_videos(request: Request):
    """觸發視頻生成：body={image_set_id, duration_sec?, mode?}"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        validated = GenerateVideosRequest(**body)
    except Exception as e:
        return JSONResponse({"error": f"參數驗證失敗: {e}"}, status_code=422)

    image_set_id = validated.image_set_id
    duration_sec = validated.duration_sec
    mode = validated.mode

    if not image_set_id:
        return JSONResponse({"error": "請指定圖片集 ID"}, status_code=400)

    # Verify image set exists
    img_set_dir = GENERATED_IMAGES_DIR / image_set_id
    if not img_set_dir.exists():
        return JSONResponse({"error": "圖片集不存在"}, status_code=404)

    task_id = _create_task("generate-videos", image_set_id=image_set_id)
    _run_in_thread(_run_generate_videos, task_id, image_set_id, duration_sec, mode)
    return {"task_id": task_id, "status": "started"}


def _run_generate_videos(task_id: str, image_set_id: str, duration_sec: int, mode: str):
    """Background task: generate videos from image set using Kling API."""
    task = _tasks[task_id]
    try:
        task["logs"].append(f"[{_now()}] 開始生成視頻（Kling API, duration={duration_sec}s, mode={mode}）...")

        # Load image set metadata
        img_set_dir = GENERATED_IMAGES_DIR / image_set_id
        meta_file = img_set_dir / "meta.json"
        if meta_file.exists():
            meta = _safe_read_json(meta_file, {})
            frames = meta.get("frames", [])
        else:
            pngs = sorted(img_set_dir.glob("*.png"))
            frames = [
                {"frame_number": i + 1, "image_path": str(p.relative_to(PROJECT_ROOT)), "status": "ok"}
                for i, p in enumerate(pngs)
            ]

        # Filter only successful frames
        frames = [f for f in frames if f.get("status") == "ok" and f.get("image_path")]
        if not frames:
            raise ValueError("無可用的分鏡圖")

        # Add video_prompt from image_prompt if missing
        for f in frames:
            if "video_prompt" not in f:
                f["video_prompt"] = f.get("image_prompt", "")

        video_set_id = f"vidset_{image_set_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        total = len(frames)
        task["logs"].append(f"[{_now()}] 共 {total} 個分鏡圖需要生成視頻")

        def on_progress(current, total_count, message):
            _set_progress(task, current, total_count, message)
            task["logs"].append(f"[{_now()}] [{current}/{total_count}] {message}")

        from ..video_gen.kling_video_client import batch_generate as kling_video_batch
        results = kling_video_batch(
            frames=frames,
            drama_id=video_set_id,
            duration_sec=duration_sec,
            mode=mode,
            on_progress=on_progress,
        )

        success_count = sum(1 for r in results if r["status"] == "ok")
        error_count = sum(1 for r in results if r["status"] == "error")

        task["result"] = {
            "video_set_id": video_set_id,
            "image_set_id": image_set_id,
            "total_clips": total,
            "success_count": success_count,
            "error_count": error_count,
        }
        task["logs"].append(
            f"[{_now()}] 視頻生成完成: {success_count} 成功, {error_count} 失敗"
        )
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


# ──────────────────────────── Knowledge Base API ────────────────────────────

@app.get("/api/knowledge/stats")
async def kb_stats():
    return _get_kb().get_stats()


@app.get("/api/knowledge/search")
async def kb_search(q: str = ""):
    if not q.strip():
        return {"data": []}
    return {"data": _get_kb().search(q.strip())}


@app.get("/api/knowledge/categories")
async def kb_categories():
    from ..knowledge.knowledge_base import CATEGORIES, CATEGORY_LABELS
    return {"data": [{"id": c, "label": CATEGORY_LABELS.get(c, c)} for c in CATEGORIES]}


@app.get("/api/knowledge/{category}/{entry_id}")
async def kb_get_entry(category: str, entry_id: str):
    """Return a single KB entry by category and ID."""
    from ..knowledge.knowledge_base import CATEGORIES
    if category not in CATEGORIES:
        return JSONResponse({"error": f"Invalid category"}, status_code=400)
    entry = _get_kb().get_entry(category, entry_id)
    if not entry:
        return JSONResponse({"error": "條目不存在"}, status_code=404)
    return {"data": entry}


@app.get("/api/knowledge/{category}")
async def kb_list_category(category: str, subcategory: str = ""):
    from ..knowledge.knowledge_base import CATEGORIES
    if category not in CATEGORIES:
        return JSONResponse({"error": f"Invalid category. Must be one of {CATEGORIES}"}, status_code=400)
    return {"data": _get_kb().get_entries(category, subcategory=subcategory or None)}


@app.post("/api/trigger/generate-kb")
@limiter.limit("20/hour")
async def trigger_generate_kb(request: Request):
    """Generate script from knowledge base.
    body={genre, style, episode_count, duration_sec, human_requirements, tags, selected_elements}
    selected_elements: dict mapping category name -> list of entry_id strings
    """
    try:
        raw_body = await request.body()
        if len(raw_body) > 50_000:  # 50KB body limit
            return JSONResponse({"error": "請求內容過大"}, status_code=413)
        body = json.loads(raw_body)
    except (json.JSONDecodeError, Exception):
        body = {}

    try:
        validated = GenerateKBRequest(**body)
    except Exception as e:
        return JSONResponse({"error": f"參數驗證失敗: {e}"}, status_code=422)

    task_id = _create_task("kb-generate")
    _run_in_thread(
        _run_generate_kb, task_id, validated.genre, validated.style,
        validated.episode_count, validated.duration_sec,
        validated.human_requirements, validated.tags, validated.selected_elements
    )
    return {"task_id": task_id, "status": "started"}


def _run_generate_kb(task_id: str, genre: str, style: str, episode_count: int,
                     duration_sec: int, human_requirements: str, tags: list[str],
                     selected_elements: Optional[dict] = None):
    task = _tasks[task_id]
    try:
        task["logs"].append(f"[{_now()}] 從知識庫生成劇本...")
        _set_progress(task, 0, 3, "抽取知識庫元素...")

        from ..scriptwriter.generator import generate_from_knowledge_base, generate_episode_script
        from ..knowledge.knowledge_base import CATEGORIES

        kb = _get_kb()
        stats = kb.get_stats()
        task["logs"].append(f"[{_now()}] 知識庫: {stats['total']} 條目")
        task["logs"].append(f"[{_now()}] 時長: {duration_sec} 秒/集")

        if stats["total"] == 0 and not selected_elements:
            raise ValueError("知識庫為空，請先分析一些劇目入庫")

        config = {
            "genre": genre,
            "style": style,
            "episode_count": episode_count,
            "duration_sec": duration_sec,
            "human_requirements": human_requirements,
            "tags": tags if tags else None,
        }

        if selected_elements:
            sel_count = sum(len(v) for v in selected_elements.values() if isinstance(v, list))
            sel_cats = [k for k, v in selected_elements.items() if isinstance(v, list) and v]
            task["logs"].append(f"[{_now()}] 使用用戶選擇的 {sel_count} 個知識庫元素（{', '.join(sel_cats)}）")
            # Log which categories are left for Claude to decide freely
            all_cats = list(CATEGORIES)
            free_cats = [c for c in all_cats if c not in sel_cats]
            if free_cats:
                task["logs"].append(f"[{_now()}] 其餘分類由 AI 自由發揮：{', '.join(free_cats)}")

        _set_progress(task, 1, 3, "Claude 生成大綱中...")
        outline = generate_from_knowledge_base(kb, config, selected_elements=selected_elements)

        if outline.get("error"):
            raise ValueError(f"生成失敗: {outline.get('error')}")

        task["logs"].append(
            f"[{_now()}] 大綱完成: {outline.get('series_title', '?')} "
            f"({len(outline.get('episodes', []))} 集)"
        )

        # Save outline
        script_id = index_db.generate_id("script")
        outline["script_id"] = script_id
        outline["source_type"] = "knowledge_base"

        script_dir = PROJECT_ROOT / "data" / "scripts" / script_id
        script_dir.mkdir(parents=True, exist_ok=True)
        outline_file = script_dir / "outline.json"
        outline_file.write_text(
            json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Generate first episode as preview
        _set_progress(task, 2, 3, "生成第 1 集劇本...")
        if outline.get("episodes"):
            ep1 = generate_episode_script(outline, 1)
            ep1["script_id"] = script_id
            ep1_file = script_dir / "script.json"
            ep1_file.write_text(
                json.dumps(ep1, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            # Update index
            rel_path = str(ep1_file.relative_to(PROJECT_ROOT))
            index_db.add_script(
                script_id,
                outline.get("series_title", ""),
                "knowledge_base",
                human_requirements,
                "kb-series",
                rel_path,
            )
            task["logs"].append(f"[{_now()}] 第 1 集劇本已生成")

        _set_progress(task, 3, 3, "完成")
        task["result"] = {
            "script_id": script_id,
            "title": outline.get("series_title", ""),
            "episodes": len(outline.get("episodes", [])),
            "kb_elements": outline.get("kb_elements_used", {}),
            "kb_combination": outline.get("_kb_combination", {}),
            "kb_user_selected": outline.get("_kb_user_selected", []),
        }
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


# ──────────────────────────── Traceability API ────────────────────────────

@app.get("/api/trace/{item_type}/{item_id}")
async def trace_lineage(item_type: str, item_id: str):
    """追溯完整上下游鏈"""
    idx = index_db.read_index()
    chain = {"target": {"type": item_type, "id": item_id}, "upstream": [], "downstream": []}

    if item_type == "storyboards":
        entry = index_db.get_entry("storyboards", item_id)
        if entry:
            src_script_id = entry.get("source_script_id", "")
            chain["upstream"].append({"type": "scripts", "id": src_script_id})
            script_entry = index_db.get_entry("scripts", src_script_id)
            if script_entry:
                src_analysis = script_entry.get("source_analysis_id", "")
                if src_analysis == "knowledge_base":
                    # KB-generated script: read _kb_combination from outline
                    script_dir = PROJECT_ROOT / "data" / "scripts" / src_script_id
                    outline_file = script_dir / "outline.json"
                    kb_combo = {}
                    kb_user_sel = []
                    outline_data = _safe_read_json(outline_file) if outline_file.exists() else None
                    if outline_data:
                        kb_combo = outline_data.get("_kb_combination", {})
                        kb_user_sel = outline_data.get("_kb_user_selected", [])
                    chain["upstream"].append({
                        "type": "knowledge_base",
                        "id": "knowledge_base",
                        "kb_combination": kb_combo,
                        "kb_user_selected": kb_user_sel,
                    })
                else:
                    chain["upstream"].append({"type": "analyses", "id": src_analysis})

    elif item_type == "scripts":
        entry = index_db.get_entry("scripts", item_id)
        if entry:
            src_analysis = entry.get("source_analysis_id", "")
            if src_analysis == "knowledge_base":
                # KB-generated script: read _kb_combination from outline
                script_dir = PROJECT_ROOT / "data" / "scripts" / item_id
                outline_file = script_dir / "outline.json"
                kb_combo = {}
                kb_user_sel = []
                outline_data = _safe_read_json(outline_file) if outline_file.exists() else None
                if outline_data:
                    kb_combo = outline_data.get("_kb_combination", {})
                    kb_user_sel = outline_data.get("_kb_user_selected", [])
                chain["upstream"].append({
                    "type": "knowledge_base",
                    "id": "knowledge_base",
                    "kb_combination": kb_combo,
                    "kb_user_selected": kb_user_sel,
                })
            else:
                chain["upstream"].append({"type": "analyses", "id": src_analysis})
                analysis_entry = index_db.get_entry("analyses", src_analysis)
                if analysis_entry:
                    for cid in analysis_entry.get("source_crawl_ids", []):
                        chain["upstream"].append({"type": "crawls", "id": cid})
            # downstream: storyboards
            for sb in idx.get("storyboards", []):
                if sb.get("source_script_id") == item_id:
                    chain["downstream"].append({"type": "storyboards", "id": sb["id"]})

    elif item_type == "analyses":
        entry = index_db.get_entry("analyses", item_id)
        if entry:
            for cid in entry.get("source_crawl_ids", []):
                chain["upstream"].append({"type": "crawls", "id": cid})
            # downstream: scripts
            for s in idx.get("scripts", []):
                if s.get("source_analysis_id") == item_id:
                    chain["downstream"].append({"type": "scripts", "id": s["id"]})

    elif item_type == "crawls":
        pass  # crawl tracing removed (src/crawler module deprecated)

    return chain


# ──────────────────────────── Storyboard Media API (Steps 5 & 6) ────────────────────────────

@app.post("/api/storyboard/{storyboard_id}/generate-images")
async def storyboard_generate_images(storyboard_id: str, request: Request):
    """Step 5: 為指定分鏡表的每個幀生成圖片（Kling AI）。
    body={style_prefix?}
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    style_prefix = body.get("style_prefix", "")

    entry = index_db.get_entry("storyboards", storyboard_id)
    if not entry:
        return JSONResponse({"error": "分鏡不存在"}, status_code=404)

    # Prevent duplicate runs
    task_key = f"kling_image_{storyboard_id}"
    existing = _tasks.get(task_key)
    if existing and existing.get("status") == "running":
        return JSONResponse({"error": "生圖任務已在執行中", "task_id": task_key}, status_code=409)

    _tasks[task_key] = {
        "id": task_key,
        "stage": "generate-images",
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "result": None,
        "error": None,
        "logs": [],
        "progress": {"current": 0, "total": 0, "percent": 0, "step": ""},
        "storyboard_id": storyboard_id,
    }
    _run_in_thread(_run_storyboard_generate_images, task_key, storyboard_id, style_prefix)
    return {"task_id": task_key, "status": "started"}


def _run_storyboard_generate_images(task_id: str, storyboard_id: str, style_prefix: str):
    """Background task: generate images for each frame in a storyboard using Kling AI."""
    task = _tasks[task_id]
    try:
        task["logs"].append(f"[{_now()}] 開始分鏡圖生成（Flux via fal.ai, 9:16）...")

        frames = index_db.get_frames_by_storyboard(storyboard_id)
        if not frames:
            raise ValueError(f"分鏡表為空或不存在: {storyboard_id}")

        # Ensure frame_number
        for i, f in enumerate(frames):
            if "frame_number" not in f:
                f["frame_number"] = i + 1

        total = len(frames)
        task["logs"].append(f"[{_now()}] 共 {total} 個分鏡需要生圖")
        _set_progress(task, 0, total, "準備中...")

        from ..image_gen.flux_generator import generate_image_url

        image_set_id = f"imgset_{storyboard_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = GENERATED_IMAGES_DIR / image_set_id
        output_dir.mkdir(parents=True, exist_ok=True)

        import httpx as _httpx
        results = []
        success_count = 0
        error_count = 0

        for i, frame in enumerate(frames):
            num = frame.get("frame_number", i + 1)
            raw_prompt = frame.get("image_prompt", "")
            prompt = f"{style_prefix}, {raw_prompt}" if style_prefix else raw_prompt
            out_path = output_dir / f"frame_{num:03d}.png"

            _set_progress(task, i, total, f"生成分鏡 #{num} ({i+1}/{total})...")
            task["logs"].append(f"[{_now()}] [{i+1}/{total}] 生成分鏡 #{num}...")

            try:
                image_url = generate_image_url(prompt=prompt)

                # Download to local
                img_resp = _httpx.get(image_url, timeout=60, follow_redirects=True)
                img_resp.raise_for_status()
                out_path.write_bytes(img_resp.content)

                # Update frame record in storyboard file
                index_db.update_frame_image(storyboard_id, num, image_url)

                results.append({
                    "frame_number": num,
                    "image_url": image_url,
                    "image_path": str(out_path.relative_to(PROJECT_ROOT)),
                    "status": "ok",
                })
                success_count += 1
                task["logs"].append(f"[{_now()}]   -> 成功: {image_url[:60]}")
            except Exception as e:
                results.append({
                    "frame_number": num,
                    "image_url": None,
                    "image_path": None,
                    "status": "error",
                    "error": str(e),
                })
                error_count += 1
                task["logs"].append(f"[{_now()}]   -> 失敗: {e}")

            # Rate limit
            if i < total - 1:
                import time as _time
                _time.sleep(2)

        # Save image set metadata
        meta = {
            "image_set_id": image_set_id,
            "storyboard_id": storyboard_id,
            "total_frames": total,
            "success_count": success_count,
            "error_count": error_count,
            "style_prefix": style_prefix,
            "frames": results,
        }
        meta_path = output_dir / "meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        _set_progress(task, total, total, "完成")
        task["result"] = {
            "image_set_id": image_set_id,
            "storyboard_id": storyboard_id,
            "total_frames": total,
            "success_count": success_count,
            "error_count": error_count,
        }
        task["logs"].append(f"[{_now()}] 生圖完成: {success_count} 成功, {error_count} 失敗")
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


@app.post("/api/storyboard/{storyboard_id}/generate-videos")
async def storyboard_generate_videos(storyboard_id: str, request: Request):
    """Step 6: 為指定分鏡表中有 image_url 的幀生成視頻（Kling AI image-to-video）。
    body={duration_sec?, mode?}
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    duration_sec = int(body.get("duration_sec", 5))
    mode = body.get("mode", "std")

    entry = index_db.get_entry("storyboards", storyboard_id)
    if not entry:
        return JSONResponse({"error": "分鏡不存在"}, status_code=404)

    # Prevent duplicate runs
    task_key = f"kling_video_{storyboard_id}"
    existing = _tasks.get(task_key)
    if existing and existing.get("status") == "running":
        return JSONResponse({"error": "視頻生成任務已在執行中", "task_id": task_key}, status_code=409)

    _tasks[task_key] = {
        "id": task_key,
        "stage": "generate-videos",
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "result": None,
        "error": None,
        "logs": [],
        "progress": {"current": 0, "total": 0, "percent": 0, "step": ""},
        "storyboard_id": storyboard_id,
    }
    _run_in_thread(_run_storyboard_generate_videos, task_key, storyboard_id, duration_sec, mode)
    return {"task_id": task_key, "status": "started"}


def _run_storyboard_generate_videos(task_id: str, storyboard_id: str, duration_sec: int, mode: str):
    """Background task: generate videos from frames that have image_url."""
    task = _tasks[task_id]
    try:
        task["logs"].append(
            f"[{_now()}] 開始分鏡視頻生成（Kling AI image-to-video, duration={duration_sec}s, mode={mode}）..."
        )

        frames = index_db.get_frames_by_storyboard(storyboard_id)
        if not frames:
            raise ValueError(f"分鏡表為空或不存在: {storyboard_id}")

        # Only process frames that have image_url
        eligible = [f for f in frames if f.get("image_url")]
        if not eligible:
            raise ValueError("分鏡表中沒有已生成圖片的幀，請先執行生圖（Step 5）")

        total = len(eligible)
        task["logs"].append(f"[{_now()}] 共 {total} 個分鏡圖需要生成視頻")
        _set_progress(task, 0, total, "準備中...")

        from ..video_gen.kling_video import generate_video_url

        video_set_id = f"vidset_{storyboard_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = GENERATED_VIDEOS_DIR / video_set_id
        output_dir.mkdir(parents=True, exist_ok=True)

        import httpx as _httpx
        results = []
        success_count = 0
        error_count = 0

        for i, frame in enumerate(eligible):
            num = frame.get("frame_number", i + 1)
            image_url = frame.get("image_url", "")
            prompt = frame.get("video_prompt", frame.get("image_prompt", ""))
            out_path = output_dir / f"clip_{num:03d}.mp4"

            _set_progress(task, i, total, f"生成視頻片段 #{num} ({i+1}/{total})...")
            task["logs"].append(f"[{_now()}] [{i+1}/{total}] 生成視頻片段 #{num}...")

            try:
                video_url = generate_video_url(
                    image_url=image_url,
                    prompt=prompt,
                    duration=str(duration_sec),
                    mode=mode,
                )

                # Download to local
                vid_resp = _httpx.get(video_url, timeout=120, follow_redirects=True)
                vid_resp.raise_for_status()
                out_path.write_bytes(vid_resp.content)

                # Update frame record in storyboard file
                index_db.update_frame_video(storyboard_id, num, video_url)

                results.append({
                    "frame_number": num,
                    "video_url": video_url,
                    "video_path": str(out_path.relative_to(PROJECT_ROOT)),
                    "duration_sec": duration_sec,
                    "status": "ok",
                })
                success_count += 1
                task["logs"].append(f"[{_now()}]   -> 成功: {video_url[:60]}")
            except Exception as e:
                results.append({
                    "frame_number": num,
                    "video_url": None,
                    "video_path": None,
                    "status": "error",
                    "error": str(e),
                })
                error_count += 1
                task["logs"].append(f"[{_now()}]   -> 失敗: {e}")

            # Rate limit
            if i < total - 1:
                import time as _time
                _time.sleep(3)

        # Save video set metadata
        meta = {
            "video_set_id": video_set_id,
            "storyboard_id": storyboard_id,
            "total_clips": total,
            "success_count": success_count,
            "error_count": error_count,
            "duration_sec": duration_sec,
            "mode": mode,
            "clips": results,
        }
        meta_path = output_dir / "meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        _set_progress(task, total, total, "完成")
        task["result"] = {
            "video_set_id": video_set_id,
            "storyboard_id": storyboard_id,
            "total_clips": total,
            "success_count": success_count,
            "error_count": error_count,
        }
        task["logs"].append(f"[{_now()}] 視頻生成完成: {success_count} 成功, {error_count} 失敗")
        task["status"] = "done"
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        task["logs"].append(f"[{_now()}] 錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        task["finished_at"] = _now()


@app.get("/api/storyboard/{storyboard_id}/media-status")
async def storyboard_media_status(storyboard_id: str):
    """查詢分鏡表的圖片/視頻生成狀態。"""
    entry = index_db.get_entry("storyboards", storyboard_id)
    if not entry:
        return JSONResponse({"error": "分鏡不存在"}, status_code=404)

    frames = index_db.get_frames_by_storyboard(storyboard_id)
    total = len(frames)
    images_done = sum(1 for f in frames if f.get("image_url"))
    videos_done = sum(1 for f in frames if f.get("video_url"))

    image_task_key = f"kling_image_{storyboard_id}"
    video_task_key = f"kling_video_{storyboard_id}"

    image_task = _tasks.get(image_task_key)
    video_task = _tasks.get(video_task_key)

    return {
        "storyboard_id": storyboard_id,
        "total_frames": total,
        "images_done": images_done,
        "videos_done": videos_done,
        "image_task": {
            "status": image_task["status"] if image_task else "none",
            "progress": image_task.get("progress") if image_task else None,
            "result": image_task.get("result") if image_task else None,
            "error": image_task.get("error") if image_task else None,
        } if image_task else {"status": "none"},
        "video_task": {
            "status": video_task["status"] if video_task else "none",
            "progress": video_task.get("progress") if video_task else None,
            "result": video_task.get("result") if video_task else None,
            "error": video_task.get("error") if video_task else None,
        } if video_task else {"status": "none"},
        "frames_summary": [
            {
                "frame_number": f.get("frame_number", i + 1),
                "has_image": bool(f.get("image_url")),
                "has_video": bool(f.get("video_url")),
                "image_url": f.get("image_url"),
                "video_url": f.get("video_url"),
            }
            for i, f in enumerate(frames)
        ],
    }


# ──────────────────────────── Task API ────────────────────────────

@app.get("/api/tasks")
async def list_tasks():
    return list(_tasks.values())


@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "任務不存在"}, status_code=404)
    return task


# ──────────────────────────── Config API ────────────────────────────

@app.get("/api/config")
async def get_config():
    config = load_config()
    safe = dict(config)
    if "proxy" in safe:
        safe["proxy"] = {**safe["proxy"], "api_key": "***" if safe["proxy"].get("api_key") else "(empty)"}
    for key in ["gemini_api_key"]:
        if key in safe:
            safe[key] = "***" if safe[key] else "(empty)"
    return safe


# ──────────────────────────── Helpers ────────────────────────────

def _has_running_task(stage: str) -> str | None:
    """Return task_id if there's already a running task of the same stage."""
    for tid, t in _tasks.items():
        if t["stage"] == stage and t["status"] == "running":
            return tid
    return None


def _create_task(stage: str, **extra) -> str:
    _cleanup_tasks()
    task_id = uuid.uuid4().hex[:8]
    task = {
        "id": task_id,
        "stage": stage,
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "result": None,
        "error": None,
        "logs": [],
        "progress": {"current": 0, "total": 0, "percent": 0, "step": ""},
        **extra,
    }
    _tasks[task_id] = task
    return task_id


def _set_progress(task: dict, current: int, total: int, step: str):
    pct = int(current / total * 100) if total > 0 else 0
    task["progress"] = {"current": current, "total": total, "percent": pct, "step": step}


# ──────────────────────────── Main ────────────────────────────

def main():
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8502,
        reload=True,
    )


if __name__ == "__main__":
    main()
