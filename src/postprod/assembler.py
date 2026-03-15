"""FFmpeg 視頻拼接 — 把多個視頻片段串成一部完整短劇"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..utils.config import load_config, PROJECT_ROOT


def concat_clips(
    clip_paths: list[str | Path],
    output_path: str | Path,
    transition: str = "none",
) -> Path:
    """把多個視頻片段拼接成一個

    Args:
        clip_paths: 視頻片段路徑列表（按順序）
        output_path: 輸出路徑
        transition: 轉場效果 (none | fade | crossfade)
    """
    config = load_config()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if transition == "none":
        return _concat_simple(clip_paths, output_path)
    elif transition == "fade":
        return _concat_with_fade(clip_paths, output_path)
    else:
        return _concat_simple(clip_paths, output_path)


def _concat_simple(clip_paths: list[str | Path], output_path: Path) -> Path:
    """簡單拼接（無轉場）"""
    config = load_config()
    resolution = config["postprod"]["resolution"]
    fps = config["postprod"]["fps"]
    codec = config["postprod"]["codec"]

    # 建立 concat list 檔案
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for clip in clip_paths:
            f.write(f"file '{Path(clip).resolve()}'\n")
        list_path = f.name

    normalized = []
    try:
        # 先統一所有片段的格式
        for i, clip in enumerate(clip_paths):
            norm_path = output_path.parent / f"_norm_{i:03d}.mp4"
            cmd = [
                "ffmpeg", "-y", "-i", str(clip),
                "-vf", f"scale={resolution},setsar=1",
                "-r", str(fps),
                "-c:v", codec,
                "-c:a", "aac",
                "-ar", "44100",
                norm_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            normalized.append(norm_path)

        # 重建 concat list
        with open(list_path, "w") as f:
            for norm in normalized:
                f.write(f"file '{norm.resolve()}'\n")

        # 拼接
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        return output_path

    finally:
        # 清理臨時檔案（即使出錯也要清理）
        for norm in normalized:
            norm.unlink(missing_ok=True)
        Path(list_path).unlink(missing_ok=True)


def _get_clip_duration(clip_path: str | Path) -> float:
    """用 ffprobe 取得影片長度（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(clip_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
        return 6.0  # 預設 6 秒


def _concat_with_fade(clip_paths: list[str | Path], output_path: Path) -> Path:
    """帶淡入淡出轉場的拼接"""
    config = load_config()
    resolution = config["postprod"]["resolution"]
    fps = config["postprod"]["fps"]
    codec = config["postprod"]["codec"]
    fade_duration = 0.5  # 轉場 0.5 秒

    if len(clip_paths) < 2:
        return _concat_simple(clip_paths, output_path)

    # 先取得每個片段的長度以計算 offset
    durations = [_get_clip_duration(p) for p in clip_paths]

    # 用 filter_complex 做 crossfade
    inputs = []
    for clip in clip_paths:
        inputs.extend(["-i", str(clip)])

    # 建構 filter chain
    n = len(clip_paths)
    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v]scale={resolution},setsar=1,fps={fps}[v{i}];")

    # 兩兩做 crossfade — offset 需為數值（前一段結束時間 - fade_duration）
    prev = "v0"
    cumulative_offset = durations[0] - fade_duration
    for i in range(1, n):
        out = f"cf{i}" if i < n - 1 else "vout"
        filter_parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={fade_duration}:offset={cumulative_offset:.3f}[{out}];"
        )
        prev = out
        if i < n - 1:
            cumulative_offset += durations[i] - fade_duration

    filter_str = "".join(filter_parts).rstrip(";")

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[vout]",
        "-c:v", codec,
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # crossfade 失敗就用簡單拼接
        return _concat_simple(clip_paths, output_path)

    return output_path
