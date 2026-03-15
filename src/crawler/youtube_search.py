"""YouTube Data API 搜尋爆款短劇（含 yt-dlp fallback）"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

from ..utils.config import load_config, PROJECT_ROOT

DEFAULT_MAX_DURATION_SEC = 0  # 0 = no limit (user can set via UI)
from ..utils.index_db import generate_id, add_crawl

logger = logging.getLogger(__name__)

# yt-dlp 可能不在標準 PATH，搜尋常見安裝位置
_YTDLP_PATH: str | None = None


def _find_ytdlp() -> str:
    global _YTDLP_PATH
    if _YTDLP_PATH:
        return _YTDLP_PATH
    found = shutil.which("yt-dlp")
    if not found:
        candidates = [
            Path.home() / "Library/Python/3.9/bin/yt-dlp",
            Path.home() / "Library/Python/3.11/bin/yt-dlp",
            Path.home() / "Library/Python/3.12/bin/yt-dlp",
            Path("/opt/homebrew/bin/yt-dlp"),
            Path("/usr/local/bin/yt-dlp"),
        ]
        for c in candidates:
            if c.exists():
                found = str(c)
                break
    if not found:
        raise FileNotFoundError("yt-dlp not found")
    _YTDLP_PATH = found
    logger.info("yt-dlp found at: %s", found)
    return found


def _parse_iso_duration(iso: str) -> int:
    """Parse ISO 8601 duration (e.g. PT1H2M30S) to seconds."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def search_trending_dramas(
    query: str = "短劇 完整版",
    max_results: int = 20,
    min_views: int | None = None,
    max_duration: int = 0,
) -> list[dict]:
    """搜尋 YouTube 上的爆款短劇，自動 fallback 到 yt-dlp"""
    config = load_config()
    if min_views is None:
        min_views = config.get("crawler", {}).get("min_views", 10000)
    api_key = config.get("youtube_api_key", "")

    if api_key:
        try:
            return _search_with_api(query, max_results, min_views, api_key, max_duration)
        except Exception as e:
            logger.warning("YouTube API 搜尋失敗，fallback 到 yt-dlp: %s", e)

    return _search_with_ytdlp(query, max_results, min_views, max_duration)


def _search_with_api(
    query: str, max_results: int, min_views: int, api_key: str,
    max_duration: int = 0,
) -> list[dict]:
    """用 YouTube Data API 搜尋"""
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=api_key)

    search_resp = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        order="viewCount",
        maxResults=min(max_results, 50),
        relevanceLanguage="zh",
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        return []

    videos_resp = youtube.videos().list(
        id=",".join(video_ids),
        part="snippet,statistics,contentDetails",
    ).execute()

    results = []
    for item in videos_resp.get("items", []):
        views = int(item["statistics"].get("viewCount", 0))
        if views < min_views:
            continue

        duration_iso = item["contentDetails"]["duration"]
        duration_sec = _parse_iso_duration(duration_iso)
        if max_duration > 0 and duration_sec > max_duration:
            continue

        results.append({
            "video_id": item["id"],
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "views": views,
            "duration": duration_iso,
            "duration_sec": duration_sec,
            "published_at": item["snippet"]["publishedAt"],
            "description": item["snippet"]["description"][:500],
        })

    results.sort(key=lambda x: x["views"], reverse=True)
    return results


def _search_with_ytdlp(
    query: str, max_results: int, min_views: int,
    max_duration: int = 0,
) -> list[dict]:
    """用 yt-dlp 搜尋（不需要 API key）"""
    search_url = f"ytsearch{min(max_results, 20)}:{query}"

    cmd = [
        _find_ytdlp(),
        "--dump-json",
        "--no-download",
        "--no-playlist",
    ]
    if max_duration > 0:
        cmd += ["--match-filter", f"duration<={max_duration}"]
    cmd.append(search_url)

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180
        )
        if proc.returncode != 0:
            logger.error("yt-dlp 搜尋失敗: %s", proc.stderr[:200])
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("yt-dlp 執行失敗: %s", e)
        return []

    results = []
    for line in proc.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        view_count = item.get("view_count") or 0
        if view_count < min_views:
            continue

        vid = item.get("id", "")
        dur = item.get("duration") or 0
        results.append({
            "video_id": vid,
            "url": item.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
            "title": item.get("title", ""),
            "channel": item.get("channel", item.get("uploader", "")),
            "views": view_count,
            "duration": f"PT{dur}S",
            "duration_sec": dur,
            "published_at": item.get("upload_date", ""),
            "description": (item.get("description") or "")[:500],
        })

    results.sort(key=lambda x: x["views"], reverse=True)
    return results


def _load_existing_video_ids() -> set[str]:
    """Load all video_ids from existing crawl results in data/crawls/."""
    crawls_dir = PROJECT_ROOT / "data" / "crawls"
    existing = set()
    if not crawls_dir.exists():
        return existing
    for fpath in crawls_dir.glob("*.json"):
        try:
            videos = json.loads(fpath.read_text(encoding="utf-8"))
            for v in videos:
                vid = v.get("video_id", "")
                if vid:
                    existing.add(vid)
        except (json.JSONDecodeError, OSError):
            continue
    return existing


def batch_search(queries: list[str] | None = None, **kwargs) -> list[dict]:
    """用多個關鍵字搜尋並去重"""
    config = load_config()
    queries = queries or config["crawler"]["search_queries"]
    if "min_views" not in kwargs:
        kwargs["min_views"] = config.get("crawler", {}).get("min_views", 10000)
    if "max_duration" not in kwargs:
        kwargs["max_duration"] = config.get("crawler", {}).get("max_duration", 0)

    seen_ids = set()
    all_results = []
    # Load existing video_ids from previous crawls for dedup
    existing_ids = _load_existing_video_ids()

    for q in queries:
        results = search_trending_dramas(query=q, **kwargs)
        for r in results:
            if r["video_id"] not in seen_ids:
                seen_ids.add(r["video_id"])
                # Mark as duplicate if already in previous crawl results
                if r["video_id"] in existing_ids:
                    r["is_duplicate"] = True
                all_results.append(r)

    all_results.sort(key=lambda x: x["views"], reverse=True)
    return all_results


def save_results(results: list[dict], filename: str = "trending.json"):
    """向後兼容：存搜尋結果到 data/scripts/"""
    out_path = PROJECT_ROOT / "data" / "scripts" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return out_path


def save_crawl(results: list[dict], keyword: str = "",
               tags: list[str] | None = None) -> str:
    """存搜尋結果到 data/crawls/{crawl_id}.json 並更新 index。

    Returns:
        crawl_id
    """
    crawl_id = generate_id("crawl")
    if tags is None:
        tags = [keyword] if keyword else []

    crawls_dir = PROJECT_ROOT / "data" / "crawls"
    crawls_dir.mkdir(parents=True, exist_ok=True)
    out_path = crawls_dir / f"{crawl_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Also save to legacy location for backward compat
    save_results(results)

    # Update index
    rel_path = str(out_path.relative_to(PROJECT_ROOT))
    add_crawl(crawl_id, keyword, tags, len(results), rel_path)

    return crawl_id
