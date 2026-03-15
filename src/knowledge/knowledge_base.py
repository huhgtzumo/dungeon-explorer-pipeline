"""Knowledge Base system for drama pattern storage and retrieval.

Stores reusable drama elements (structures, hooks, character archetypes, payoffs, pacing,
dialogues, visual_scenes, ending_hooks, tension_actions) extracted from analyzed dramas.
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
    "structures",
    "hooks",
    "elements",
    "payoffs",
    "pacing",
    "dialogues",
    "visual_scenes",
    "ending_hooks",
    "tension_actions",
    "genres",
    "styles",
)

CATEGORY_LABELS = {
    "structures": "架構模板",
    "hooks": "開場鉤子",
    "elements": "元素庫",
    "payoffs": "爽點庫",
    "pacing": "節奏模板",
    "dialogues": "對白模式",
    "visual_scenes": "視覺場景",
    "ending_hooks": "結尾鉤子",
    "tension_actions": "張力行為",
    "genres": "劇本類型",
    "styles": "風格",
}

SUBCATEGORIES = {
    "elements": ("人設", "場景", "關係", "人設組合", "道具", "職業", "背景設定"),
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
    (KB_ROOT / "dramas").mkdir(exist_ok=True)


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
    """Read/write interface for the drama knowledge base at data/knowledge/."""

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
        """Save a fully analyzed drama record."""
        _ensure_dirs()
        path = KB_ROOT / "dramas" / f"{video_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def has_drama(self, video_id: str) -> bool:
        """Check if a drama has already been analyzed and stored."""
        path = KB_ROOT / "dramas" / f"{video_id}.json"
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
            # Subcategory breakdown for elements
            if cat == "elements" and entries:
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
        # Drama count
        dramas_dir = KB_ROOT / "dramas"
        stats["dramas"] = len(list(dramas_dir.glob("*.json"))) if dramas_dir.exists() else 0
        return stats

    def get_random_combination(self, config: dict | None = None) -> dict:
        """Pick random elements from each category for script generation.

        config can contain:
            tags: list[str] — filter entries by tags
            structure_count: int (default 1)
            hook_count: int (default 2-3)
            element_count: int (default 3-5)
            payoff_count: int (default 2-3)
            pacing_count, dialogue_count, visual_scene_count,
            ending_hook_count, tension_action_count: int

        Selection is weighted by effectiveness_score.
        """
        config = config or {}
        filter_tags = config.get("tags")

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

        structure_count = config.get("structure_count", 1)
        hook_count = config.get("hook_count", random.randint(2, 3))
        element_count = config.get("element_count", random.randint(3, 5))
        payoff_count = config.get("payoff_count", random.randint(2, 3))
        pacing_count = config.get("pacing_count", 1)
        dialogue_count = config.get("dialogue_count", random.randint(1, 3))
        visual_scene_count = config.get("visual_scene_count", random.randint(1, 3))
        ending_hook_count = config.get("ending_hook_count", random.randint(1, 2))
        tension_action_count = config.get("tension_action_count", random.randint(1, 3))
        genre_count = config.get("genre_count", 1)
        style_count = config.get("style_count", 1)

        return {
            "structures": _pick("structures", structure_count),
            "hooks": _pick("hooks", hook_count),
            "elements": _pick("elements", element_count),
            "payoffs": _pick("payoffs", payoff_count),
            "pacing": _pick("pacing", pacing_count),
            "dialogues": _pick("dialogues", dialogue_count),
            "visual_scenes": _pick("visual_scenes", visual_scene_count),
            "ending_hooks": _pick("ending_hooks", ending_hook_count),
            "tension_actions": _pick("tension_actions", tension_action_count),
            "genres": _pick("genres", genre_count),
            "styles": _pick("styles", style_count),
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
