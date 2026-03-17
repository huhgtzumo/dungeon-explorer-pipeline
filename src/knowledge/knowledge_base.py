"""Knowledge Base system for exploration element storage and retrieval.

Stores reusable exploration elements across 15 categories (building_types,
building_backstories, exploration_zones, route_paths, encounters, found_items,
traps_hazards, narrative_clues, time_settings, weather_conditions,
ambient_triggers, tension_curves, ending_types, exploration_motives,
explorer_equipment) for dungeon/urbex exploration script generation.
Supports weighted random combination for script generation.

Storage: data/knowledge/
"""

from __future__ import annotations

import fcntl
import json
import os
import random
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.config import PROJECT_ROOT, now_str as _now_str

KB_ROOT = PROJECT_ROOT / "data" / "knowledge"
KB_INDEX_PATH = KB_ROOT / "kb_index.json"

CATEGORIES = (
    # 場景層 (Scene Layer)
    "building_types",
    "building_backstories",
    "exploration_zones",
    "route_paths",
    # 事件層 (Event Layer)
    "encounters",
    "found_items",
    "traps_hazards",
    "narrative_clues",
    # 氛圍層 (Atmosphere Layer)
    "time_settings",
    "weather_conditions",
    "ambient_triggers",
    # 結構層 (Structure Layer)
    "tension_curves",
    "ending_types",
    "exploration_motives",
    "explorer_equipment",
)

CATEGORY_LABELS = {
    "building_types": "建築類型",
    "building_backstories": "廢棄原因",
    "exploration_zones": "探索區域",
    "route_paths": "動線路徑",
    "encounters": "遭遇事件",
    "found_items": "發現物品",
    "traps_hazards": "陷阱危機",
    "narrative_clues": "敘事線索",
    "time_settings": "時間設定",
    "weather_conditions": "天氣狀況",
    "ambient_triggers": "氛圍觸發",
    "tension_curves": "張力曲線",
    "ending_types": "結局類型",
    "exploration_motives": "探索動機",
    "explorer_equipment": "探索者裝備",
}

SUBCATEGORIES = {
    "building_types": ("醫療設施", "軍事設施", "教育設施", "工業設施", "宗教設施", "居住設施", "地下設施", "公共設施", "其他"),
    "exploration_zones": ("走廊通道", "功能房間", "地下空間", "特殊區域", "頂層空間", "其他"),
    "encounters": ("視覺異常", "聽覺異常", "物理異常", "環境異常", "心理異常", "其他"),
    "found_items": ("文件記錄", "個人物品", "工具設備", "神秘物件", "其他"),
    "traps_hazards": ("結構危險", "環境危險", "機關陷阱", "其他"),
}


def _generate_kb_id(category: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = uuid.uuid4().hex[:6]
    return f"kb_{category}_{ts}_{rand}"


def _ensure_dirs() -> None:
    """Create knowledge base directory structure if missing."""
    KB_ROOT.mkdir(parents=True, exist_ok=True)
    for cat in CATEGORIES:
        (KB_ROOT / cat).mkdir(exist_ok=True)
    (KB_ROOT / "videos").mkdir(exist_ok=True)


def _read_kb_index() -> list[dict]:
    """Read kb_index.json with shared lock."""
    _ensure_dirs()
    if not KB_INDEX_PATH.exists():
        return []
    with open(KB_INDEX_PATH, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return data


def _write_kb_index(entries: list[dict]) -> None:
    """Write kb_index.json atomically: write to temp file then rename."""
    _ensure_dirs()
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=KB_INDEX_PATH.parent, suffix=".tmp", prefix=".kb_index_"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, KB_INDEX_PATH)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _atomic_update_index(updater) -> Any:
    """Atomic read-modify-write on kb_index.json. Returns updater's return value."""
    _ensure_dirs()
    lock_path = KB_INDEX_PATH.with_suffix(".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            entries = _read_kb_index()
            result = updater(entries)
            _write_kb_index(entries)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)
    return result


class KnowledgeBase:
    """Read/write interface for the exploration knowledge base at data/knowledge/."""

    def __init__(self) -> None:
        _ensure_dirs()

    # ── Add / Update ──

    def add_entry(self, category: str, data: dict) -> dict:
        """Add a new knowledge base entry. Returns the saved entry."""
        if category not in CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of {CATEGORIES}")

        entry_id = data.get("id") or _generate_kb_id(category)
        now = _now_str()
        entry = {
            "id": entry_id,
            "category": category,
            "subcategory": data.get("subcategory", ""),
            "name": data.get("name", ""),
            "name_en": data.get("name_en", ""),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "examples": data.get("examples", []),
            "effectiveness_score": data.get("effectiveness_score", 5),
            "usage_count": data.get("usage_count", 0),
            "created_at": now,
            "updated_at": now,
        }

        # Save entry file
        entry_path = KB_ROOT / category / f"{entry_id}.json"
        entry_path.write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Update index
        index_meta = {
            "id": entry_id,
            "category": category,
            "subcategory": entry["subcategory"],
            "name": entry["name"],
            "tags": entry["tags"],
            "effectiveness_score": entry["effectiveness_score"],
            "created_at": now,
        }

        def _add(entries: list):
            entries.append(index_meta)

        _atomic_update_index(_add)
        return entry

    def update_entry_examples(self, entry_id: str, category: str,
                              new_examples: list[dict]) -> dict | None:
        """Append examples to an existing entry (for dedup: merge instead of create new)."""
        entry_path = KB_ROOT / category / f"{entry_id}.json"
        if not entry_path.exists():
            return None

        with open(entry_path, "r+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                entry = json.load(f)
                existing_excerpts = {
                    ex.get("excerpt", "") for ex in entry.get("examples", [])
                }
                for ex in new_examples:
                    if ex.get("excerpt", "") not in existing_excerpts:
                        entry["examples"].append(ex)
                entry["updated_at"] = _now_str()
                f.seek(0)
                f.truncate()
                json.dump(entry, f, ensure_ascii=False, indent=2)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return entry

    def save_drama(self, video_id: str, data: dict) -> None:
        """Save a fully analyzed exploration video record."""
        _ensure_dirs()
        path = KB_ROOT / "videos" / f"{video_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def has_drama(self, video_id: str) -> bool:
        """Check if a video has already been analyzed and stored."""
        path = KB_ROOT / "videos" / f"{video_id}.json"
        return path.exists()

    # ── Query ──

    def get_entries(self, category: str, subcategory: str | None = None,
                    tags: list[str] | None = None) -> list[dict]:
        """List entries in a category, optionally filtered by subcategory and tags."""
        cat_dir = KB_ROOT / category
        if not cat_dir.exists():
            return []
        results = []
        for fpath in cat_dir.glob("*.json"):
            try:
                entry = json.loads(fpath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if subcategory and entry.get("subcategory") != subcategory:
                continue
            if tags:
                entry_tags = set(entry.get("tags", []))
                if not entry_tags.intersection(tags):
                    continue
            results.append(entry)
        return results

    def get_entry(self, category: str, entry_id: str) -> dict | None:
        """Get a single entry by ID."""
        path = KB_ROOT / category / f"{entry_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def get_entries_by_ids(self, category: str, ids: list[str]) -> list[dict]:
        """Get multiple entries by their IDs."""
        results = []
        for entry_id in ids:
            entry = self.get_entry(category, entry_id)
            if entry:
                results.append(entry)
        return results

    def search(self, keyword: str) -> list[dict]:
        """Search all entries by keyword (name, description, tags)."""
        keyword_lower = keyword.lower()
        results = []
        for cat in CATEGORIES:
            cat_dir = KB_ROOT / cat
            if not cat_dir.exists():
                continue
            for fpath in cat_dir.glob("*.json"):
                try:
                    entry = json.loads(fpath.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                searchable = " ".join([
                    entry.get("name", ""),
                    entry.get("name_en", ""),
                    entry.get("description", ""),
                    " ".join(entry.get("tags", [])),
                    entry.get("subcategory", ""),
                ]).lower()
                if keyword_lower in searchable:
                    results.append(entry)
        return results

    def get_stats(self) -> dict:
        """Return counts per category and subcategory."""
        stats: dict[str, Any] = {"total": 0, "categories": {}}
        for cat in CATEGORIES:
            cat_dir = KB_ROOT / cat
            entries = list(cat_dir.glob("*.json")) if cat_dir.exists() else []
            count = len(entries)
            stats["total"] += count
            cat_stats: dict[str, Any] = {"count": count, "label": CATEGORY_LABELS.get(cat, cat)}
            # Subcategory breakdown for categories that have subcategories
            if cat in SUBCATEGORIES and entries:
                sub_counts: dict[str, int] = {}
                for fpath in entries:
                    try:
                        e = json.loads(fpath.read_text(encoding="utf-8"))
                        sub = e.get("subcategory", "other")
                        sub_counts[sub] = sub_counts.get(sub, 0) + 1
                    except (json.JSONDecodeError, OSError):
                        pass
                cat_stats["subcategories"] = sub_counts
            stats["categories"][cat] = cat_stats
        # Analyzed video count
        videos_dir = KB_ROOT / "videos"
        stats["videos"] = len(list(videos_dir.glob("*.json"))) if videos_dir.exists() else 0
        return stats

    def get_random_combination(self, config: dict | None = None) -> dict:
        """Pick random elements from each category for exploration script generation.

        config can contain:
            tags: list[str] -- filter entries by tags
            duration_sec: int -- video duration; scales element counts
            {category}_count: int -- override pick count per category

        Selection is weighted by effectiveness_score.
        """
        config = config or {}
        filter_tags = config.get("tags")
        duration_sec = config.get("duration_sec", 60)

        def _pick(category: str, count: int) -> list[dict]:
            entries = self.get_entries(category, tags=filter_tags)
            if not entries:
                return []
            # Weighted random by effectiveness_score
            weights = [max(e.get("effectiveness_score", 5), 1) for e in entries]
            pick_count = min(count, len(entries))
            selected: list[dict] = []
            pool = list(zip(entries, weights))
            for _ in range(pick_count):
                if not pool:
                    break
                items, ws = zip(*pool)
                chosen = random.choices(list(items), weights=list(ws), k=1)[0]
                selected.append(chosen)
                pool = [(e, w) for e, w in pool if e["id"] != chosen["id"]]
            return selected

        # Scale element counts by duration
        if duration_sec <= 90:
            # Short (60s): tight and compact
            zones = random.randint(2, 3)
            encounters = random.randint(2, 3)
            items = random.randint(1, 2)
            traps = 1
            clues = random.randint(1, 2)
            ambients = random.randint(1, 2)
            equipment = random.randint(2, 3)
        elif duration_sec <= 210:
            # Medium (180s): multi-zone exploration
            zones = random.randint(4, 6)
            encounters = random.randint(4, 6)
            items = random.randint(2, 4)
            traps = random.randint(1, 3)
            clues = random.randint(2, 4)
            ambients = random.randint(2, 4)
            equipment = random.randint(3, 4)
        else:
            # Long (300s+): full arc with rich detail
            zones = random.randint(6, 8)
            encounters = random.randint(6, 8)
            items = random.randint(3, 5)
            traps = random.randint(2, 4)
            clues = random.randint(3, 5)
            ambients = random.randint(3, 5)
            equipment = random.randint(3, 5)

        defaults = {
            "building_types": 1,
            "building_backstories": 1,
            "exploration_zones": zones,
            "route_paths": 1,
            "encounters": encounters,
            "found_items": items,
            "traps_hazards": traps,
            "narrative_clues": clues,
            "time_settings": 1,
            "weather_conditions": 1,
            "ambient_triggers": ambients,
            "tension_curves": 1,
            "ending_types": 1,
            "exploration_motives": 1,
            "explorer_equipment": equipment,
        }

        return {
            cat: _pick(cat, config.get(f"{cat}_count", default))
            for cat, default in defaults.items()
        }

    def find_similar(self, category: str, name: str) -> dict | None:
        """Find an existing entry with the same or very similar name."""
        name_lower = name.lower().strip()
        for entry in self.get_entries(category):
            if entry.get("name", "").lower().strip() == name_lower:
                return entry
            if entry.get("name_en", "").lower().strip() == name_lower:
                return entry
        return None
