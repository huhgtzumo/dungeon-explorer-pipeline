"""字幕燒錄 — 把中英雙語字幕燒進視頻"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..utils.config import load_config


def burn_subtitles(
    video_path: str | Path,
    subtitles: list[dict],
    output_path: str | Path,
    languages: list[str] | None = None,
) -> Path:
    """把字幕燒進視頻

    Args:
        video_path: 輸入視頻
        subtitles: list of {start, end, text_zh, text_en}
        output_path: 輸出路徑
        languages: ["zh", "en"] 或其子集
    """
    config = load_config()
    sub_config = config["postprod"]["subtitle"]
    languages = languages or sub_config.get("languages", ["zh", "en"])

    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成 ASS 字幕檔
    ass_path = _generate_ass(subtitles, sub_config, languages)

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"ass={ass_path}",
            "-c:v", config["postprod"]["codec"],
            "-c:a", "copy",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    finally:
        Path(ass_path).unlink(missing_ok=True)


def _generate_ass(
    subtitles: list[dict],
    sub_config: dict,
    languages: list[str],
) -> str:
    """生成 ASS 字幕檔"""
    font_size = sub_config.get("font_size", 42)
    font_color = sub_config.get("font_color", "white")
    outline_width = sub_config.get("outline_width", 2)

    # ASS 顏色格式是 &HBBGGRR
    color_map = {
        "white": "&H00FFFFFF",
        "yellow": "&H0000FFFF",
        "black": "&H00000000",
    }
    primary_color = color_map.get(font_color, "&H00FFFFFF")
    outline_color = color_map.get(sub_config.get("outline_color", "black"), "&H00000000")

    header = f"""[Script Info]
Title: Short Drama Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ZH,Noto Sans CJK TC,{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{outline_width},1,2,30,30,80,1
Style: EN,Arial,{int(font_size * 0.7)},{primary_color},&H000000FF,{outline_color},&H80000000,0,0,0,0,100,100,0,0,1,{outline_width},1,2,30,30,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for sub in subtitles:
        start = _sec_to_ass_time(sub.get("start", 0))
        end = _sec_to_ass_time(sub.get("end", 0))

        if "zh" in languages and sub.get("text_zh"):
            events.append(
                f"Dialogue: 0,{start},{end},ZH,,0,0,0,,{sub['text_zh']}"
            )
        if "en" in languages and sub.get("text_en"):
            events.append(
                f"Dialogue: 0,{start},{end},EN,,0,0,0,,{sub['text_en']}"
            )

    content = header + "\n".join(events)

    # 寫入暫存檔
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ass", delete=False, encoding="utf-8") as f:
        f.write(content)
        return f.name


def _sec_to_ass_time(seconds: float) -> str:
    """秒數轉 ASS 時間格式 H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
