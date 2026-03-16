"""Metadata index system — data/index.json CRUD with file locking.

Acts as a lightweight DB index for all pipeline artifacts:
analyses, scripts, storyboards, knowledge_entries.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, now_str as _now_str

INDEX_PATH = PROJECT_ROOT / "data" / "index.json"

_EMPTY_INDEX: dict[str, list] = {
    "analyses": [],
    "scripts": [],
    "storyboards": [],
    "knowledge_entries": [],
}


def generate_id(prefix: str) -> str:
    """Generate ID like script_20260314_a1b2c3"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = uuid.uuid4().hex[:6]
    return f"{prefix}_{ts}_{rand}"


def _read_index_unlocked() -> dict:
    if not INDEX_PATH.exists():
        return {k: list(v) for k, v in _EMPTY_INDEX.items()}
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {k: list(v) for k, v in _EMPTY_INDEX.items()}


def read_index() -> dict:
    """Read index.json with shared lock."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not INDEX_PATH.exists():
        return {k: list(v) for k, v in _EMPTY_INDEX.items()}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {k: list(v) for k, v in _EMPTY_INDEX.items()}
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return data


def _write_index(data: dict) -> None:
    """Write index.json atomically: write to temp file then rename."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=INDEX_PATH.parent, suffix=".tmp", prefix=".index_"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, INDEX_PATH)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def add_entry(collection: str, entry: dict) -> dict:
    """Add an entry to a collection in the index (atomic read-modify-write)."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = INDEX_PATH.with_suffix(".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            idx = _read_index_unlocked()
            if collection not in idx:
                idx[collection] = []
            idx[collection].append(entry)
            _write_index(idx)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)
    return entry


def get_entry(collection: str, entry_id: str) -> dict | None:
    """Find an entry by id in a collection."""
    idx = read_index()
    for entry in idx.get(collection, []):
        if entry.get("id") == entry_id:
            return entry
    return None


def list_entries(collection: str) -> list[dict]:
    """List all entries in a collection."""
    return read_index().get(collection, [])


def update_entry(collection: str, entry_id: str, updates: dict) -> dict | None:
    """Update fields on an existing entry (atomic read-modify-write)."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = INDEX_PATH.with_suffix(".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            idx = _read_index_unlocked()
            for entry in idx.get(collection, []):
                if entry.get("id") == entry_id:
                    entry.update(updates)
                    _write_index(idx)
                    return entry
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)
    return None


# ── Convenience helpers ──

def add_script(script_id: str, title: str,
               source_analysis_id: str,
               human_requirements: str,
               script_type: str,
               file: str) -> dict:
    entry = {
        "id": script_id,
        "title": title,
        "source_analysis_id": source_analysis_id,
        "human_requirements": human_requirements,
        "type": script_type,
        "created_at": _now_str(),
        "file": file,
    }
    return add_entry("scripts", entry)


def add_storyboard(sb_id: str, source_script_id: str,
                   frame_count: int, file: str) -> dict:
    entry = {
        "id": sb_id,
        "source_script_id": source_script_id,
        "frame_count": frame_count,
        "created_at": _now_str(),
        "file": file,
    }
    return add_entry("storyboards", entry)


def add_knowledge_entry(kb_entry_id: str, category: str,
                        name: str, source_video_id: str = "") -> dict:
    entry = {
        "id": kb_entry_id,
        "category": category,
        "name": name,
        "source_video_id": source_video_id,
        "created_at": _now_str(),
    }
    return add_entry("knowledge_entries", entry)


# ── Storyboard Frame Media Helpers ──

def get_frames_by_storyboard(storyboard_id: str) -> list[dict]:
    """從 storyboard 檔案載入所有分鏡幀。

    Returns storyboard frames list, or [] if not found.
    """
    entry = get_entry("storyboards", storyboard_id)
    if not entry:
        return []
    fpath = PROJECT_ROOT / entry["file"]
    if not fpath.exists():
        return []
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def update_frame_image(storyboard_id: str, frame_number: int,
                       image_url: str, task_id: str = "") -> bool:
    """更新分鏡幀的圖片 URL 和 Kling task_id。

    Args:
        storyboard_id: 分鏡 ID
        frame_number: 幀編號（1-based）
        image_url: 圖片 URL
        task_id: Kling 任務 ID

    Returns:
        True if updated successfully, False otherwise
    """
    entry = get_entry("storyboards", storyboard_id)
    if not entry:
        return False
    fpath = PROJECT_ROOT / entry["file"]
    if not fpath.exists():
        return False
    try:
        frames = json.loads(fpath.read_text(encoding="utf-8"))
        updated = False
        for frame in frames:
            if frame.get("frame_number") == frame_number:
                frame["image_url"] = image_url
                if task_id:
                    frame["image_task_id"] = task_id
                updated = True
                break
        if updated:
            fpath.write_text(json.dumps(frames, ensure_ascii=False, indent=2), encoding="utf-8")
        return updated
    except (json.JSONDecodeError, OSError):
        return False


def update_frame_video(storyboard_id: str, frame_number: int,
                       video_url: str, task_id: str = "") -> bool:
    """更新分鏡幀的視頻 URL 和 Kling task_id。

    Args:
        storyboard_id: 分鏡 ID
        frame_number: 幀編號（1-based）
        video_url: 視頻 URL
        task_id: Kling 任務 ID

    Returns:
        True if updated successfully, False otherwise
    """
    entry = get_entry("storyboards", storyboard_id)
    if not entry:
        return False
    fpath = PROJECT_ROOT / entry["file"]
    if not fpath.exists():
        return False
    try:
        frames = json.loads(fpath.read_text(encoding="utf-8"))
        updated = False
        for frame in frames:
            if frame.get("frame_number") == frame_number:
                frame["video_url"] = video_url
                if task_id:
                    frame["video_task_id"] = task_id
                updated = True
                break
        if updated:
            fpath.write_text(json.dumps(frames, ensure_ascii=False, indent=2), encoding="utf-8")
        return updated
    except (json.JSONDecodeError, OSError):
        return False
