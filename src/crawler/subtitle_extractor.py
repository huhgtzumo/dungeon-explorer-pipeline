"""YouTube 字幕提取：youtube-transcript-api → yt-dlp → Whisper"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..utils.config import load_config, PROJECT_ROOT


def _find_ytdlp() -> str:
    """Find yt-dlp binary, searching common install locations."""
    found = shutil.which("yt-dlp")
    if found:
        return found
    candidates = [
        Path.home() / "Library/Python/3.9/bin/yt-dlp",
        Path.home() / "Library/Python/3.11/bin/yt-dlp",
        Path.home() / "Library/Python/3.12/bin/yt-dlp",
        Path("/opt/homebrew/bin/yt-dlp"),
        Path("/usr/local/bin/yt-dlp"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "yt-dlp"  # fallback, hope it's in PATH

# Module-level Whisper model cache to avoid reloading on every call
_whisper_model = None
_whisper_model_name = None

# 字幕語言優先順序：中文 > 英文
_LANG_PRIORITY = ['zh-Hant', 'zh-Hans', 'zh', 'zh-TW', 'zh-CN', 'en']


def extract_subtitle(video_id: str, method: str = "auto") -> dict:
    """提取 YouTube 視頻字幕

    Args:
        video_id: YouTube video ID
        method: auto | youtube | whisper
            auto = transcript-api → yt-dlp → (不自動 Whisper，標記 pending)
            youtube = 只用 transcript-api + yt-dlp
            whisper = 只用 Whisper

    Returns:
        {video_id, text, segments: [{start, end, text}], method_used, language}
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    if method == "whisper":
        return _whisper_transcribe(url, video_id)

    # 方法 1: youtube-transcript-api（最可靠，不需要 PO token）
    result = _try_transcript_api(video_id)
    if result:
        return result

    # 方法 2: yt-dlp（需要 PO token，可能失敗）
    result = _try_youtube_subtitle(url, video_id)
    if result:
        return result

    # auto 模式下不自動跑 Whisper（太慢），標記為 none 讓前端顯示 pending
    return {"video_id": video_id, "text": "", "segments": [], "method_used": "none"}


def _try_transcript_api(video_id: str) -> dict | None:
    """用 youtube-transcript-api 提取字幕（最可靠的方式）"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None

    api = YouTubeTranscriptApi()

    try:
        # 先嘗試中文，再英文
        transcript = api.fetch(video_id=video_id, languages=_LANG_PRIORITY)

        segments = []
        full_text = []
        lang = "unknown"

        for snippet in transcript.snippets:
            text = snippet.text.strip()
            if text:
                segments.append({
                    "start": snippet.start,
                    "end": snippet.start + snippet.duration,
                    "text": text,
                })
                full_text.append(text)

        if not segments:
            return None

        # 嘗試取得語言資訊
        try:
            transcript_list = api.list(video_id=video_id)
            for t in transcript_list:
                if t.language_code in _LANG_PRIORITY:
                    lang = t.language_code
                    break
        except Exception:
            pass

        return {
            "video_id": video_id,
            "text": "\n".join(full_text),
            "segments": segments,
            "method_used": "transcript_api",
            "language": lang,
        }
    except Exception:
        return None


def _try_youtube_subtitle(url: str, video_id: str) -> dict | None:
    """用 yt-dlp 下載 YouTube 內建字幕（fallback，需要 PO token）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "sub"
        cmd = [
            _find_ytdlp(),
            "--skip-download",
            "--write-auto-sub",
            "--write-subs",
            "--sub-lang", "zh,zh-Hans,zh-Hant,zh-TW,en",
            "--sub-format", "json3",
            "-o", str(out_path),
            url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

        # 找生成的字幕檔
        sub_files = list(Path(tmpdir).glob("*.json3"))
        if not sub_files:
            return None

        with open(sub_files[0], "r", encoding="utf-8") as f:
            sub_data = json.load(f)

        segments = []
        full_text = []
        for event in sub_data.get("events", []):
            if "segs" not in event:
                continue
            text = "".join(s.get("utf8", "") for s in event["segs"]).strip()
            if text:
                start_ms = event.get("tStartMs", 0)
                dur_ms = event.get("dDurationMs", 0)
                segments.append({
                    "start": start_ms / 1000,
                    "end": (start_ms + dur_ms) / 1000,
                    "text": text,
                })
                full_text.append(text)

        if not segments:
            return None

        return {
            "video_id": video_id,
            "text": "\n".join(full_text),
            "segments": segments,
            "method_used": "youtube",
        }


def _whisper_transcribe(url: str, video_id: str) -> dict:
    """下載音頻後用 Whisper 轉錄"""
    config = load_config()
    whisper_model = config.get("whisper_model", "base")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.mp3"

        # 下載音頻 — ensure ffmpeg is in PATH
        import shutil as _shutil
        env = dict(os.environ)
        ffmpeg_path = _shutil.which("ffmpeg")
        if ffmpeg_path:
            ffmpeg_dir = str(Path(ffmpeg_path).parent)
            if ffmpeg_dir not in env.get("PATH", ""):
                env["PATH"] = ffmpeg_dir + ":" + env.get("PATH", "")
        cmd = [
            _find_ytdlp(),
            "-x", "--audio-format", "mp3",
            "-o", str(audio_path),
            url,
        ]
        subprocess.run(cmd, capture_output=True, timeout=300, env=env, check=True)

        # 找實際下載的檔案（yt-dlp 可能加後綴）
        audio_files = list(Path(tmpdir).glob("audio*"))
        if not audio_files:
            return {"video_id": video_id, "text": "", "segments": [], "method_used": "whisper_failed"}

        actual_audio = audio_files[0]

        # Whisper 轉錄（快取模型避免重複載入）
        import whisper

        global _whisper_model, _whisper_model_name
        if _whisper_model is None or _whisper_model_name != whisper_model:
            _whisper_model = whisper.load_model(whisper_model)
            _whisper_model_name = whisper_model
        result = _whisper_model.transcribe(str(actual_audio), language="zh")

        segments = [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"].strip(),
            }
            for s in result.get("segments", [])
        ]

        return {
            "video_id": video_id,
            "text": result.get("text", ""),
            "segments": segments,
            "method_used": "whisper",
        }


def batch_extract(video_ids: list[str], method: str = "auto") -> list[dict]:
    """批次提取多個視頻的字幕"""
    results = []
    for vid in video_ids:
        try:
            result = extract_subtitle(vid, method=method)
            results.append(result)
        except Exception as e:
            results.append({
                "video_id": vid,
                "text": "",
                "segments": [],
                "method_used": "error",
                "error": str(e),
            })
    return results
