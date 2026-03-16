"""廢墟探索短劇 Pipeline — 主入口

用法：
    python -m src.main --mode kb-generate  # 從知識庫生成探索劇本（主要模式）
    python -m src.main --mode kb-analyze   # 分析影片並入庫
    python -m src.main --mode kb-stats     # 顯示知識庫統計
    python -m src.main --mode storyboard   # 分鏡拆解
    python -m src.main --mode assemble     # 後製（拼接 + 字幕）
    python -m src.main --mode publish      # 上傳 YouTube
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .utils.config import load_config, PROJECT_ROOT

console = Console()


def stage_storyboard(config: dict, script: dict | None = None) -> list[dict]:
    """Stage 4.5: 分鏡拆解"""
    from .scriptwriter.storyboard import generate_storyboard, setup_characters, save_storyboard
    from dataclasses import asdict

    console.print(Panel("🎬 Stage 4.5: 分鏡拆解", style="bold cyan"))

    # 載入劇本
    if not script:
        scripts_dir = PROJECT_ROOT / "data" / "scripts"
        latest = sorted(scripts_dir.iterdir())[-1] if scripts_dir.exists() else None
        if latest and (latest / "script.json").exists():
            with open(latest / "script.json", "r", encoding="utf-8") as f:
                script = json.load(f)
        else:
            console.print("  [red]找不到劇本，請先跑 script 階段[/red]")
            return []

    drama_id = script.get("drama_id", "unknown")

    # 建立角色卡
    console.print("  建立角色卡...")
    char_manager = setup_characters(script, drama_id)
    console.print(f"  角色: {', '.join(c.name for c in char_manager.all_cards())}")

    # 生成分鏡
    console.print("  拆解分鏡...")
    frames = generate_storyboard(script, char_manager)
    console.print(f"  [green]✓ 分鏡完成: {len(frames)} 個畫面[/green]")

    # 儲存
    save_storyboard(frames, drama_id)
    return [asdict(f) for f in frames]


def stage_image(config: dict, frames: list[dict] | None = None, drama_id: str = "") -> list[dict]:
    """Stage 5: 生圖（目前尚未實作自動化）"""
    from .image_gen.gemini_client import batch_generate

    console.print(Panel("🖼️ Stage 5: 生成分鏡圖", style="bold cyan"))
    console.print("  [yellow]⚠ 生圖功能尚未完全自動化（免費方案限制）[/yellow]")
    console.print("  [yellow]  請手動在 Google AI Studio 用 nano banana 生圖[/yellow]")

    if frames:
        results = batch_generate(frames, drama_id or "unknown")
        return results
    return []


def stage_video(config: dict, frames: list[dict] | None = None, drama_id: str = "") -> list[dict]:
    """Stage 6: 生視頻（目前尚未實作自動化）"""
    from .video_gen.veo_client import batch_generate

    console.print(Panel("🎥 Stage 6: 生成視頻", style="bold cyan"))
    console.print("  [yellow]⚠ 視頻生成尚未完全自動化（免費方案限制）[/yellow]")
    console.print("  [yellow]  請手動在 Flow (labs.google/flow) 生成視頻[/yellow]")

    if frames:
        results = batch_generate(frames, drama_id or "unknown")
        return results
    return []


def stage_assemble(config: dict, drama_id: str = "") -> Path | None:
    """Stage 7: 後製（拼接 + 字幕）"""
    from .postprod.assembler import concat_clips
    from .postprod.subtitle_burner import burn_subtitles

    console.print(Panel("🎞️ Stage 7: 後製", style="bold cyan"))

    # 找視頻片段
    video_dir = PROJECT_ROOT / "data" / "videos" / drama_id if drama_id else None
    if not video_dir or not video_dir.exists():
        # 找最新的
        videos_root = PROJECT_ROOT / "data" / "videos"
        if videos_root.exists():
            dirs = sorted(videos_root.iterdir())
            video_dir = dirs[-1] if dirs else None

    if not video_dir or not video_dir.exists():
        console.print("  [red]找不到視頻片段[/red]")
        return None

    clips = sorted(video_dir.glob("clip_*.mp4"))
    if not clips:
        console.print("  [red]沒有視頻片段可以拼接[/red]")
        return None

    # 拼接
    output_dir = PROJECT_ROOT / "data" / "output" / (drama_id or "latest")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw.mp4"

    console.print(f"  拼接 {len(clips)} 個片段...")
    concat_clips(clips, raw_path, transition="fade")

    # 燒字幕
    storyboard_dir = PROJECT_ROOT / "data" / "storyboards" / (drama_id or "")
    subtitles = []
    if storyboard_dir.exists():
        sb_path = storyboard_dir / "storyboard.json"
        if sb_path.exists():
            with open(sb_path, "r", encoding="utf-8") as f:
                frames = json.load(f)
            cumulative = 0
            for frame in frames:
                dur = frame.get("duration_sec", 6)
                subtitles.append({
                    "start": cumulative,
                    "end": cumulative + dur,
                    "text_zh": frame.get("subtitle_zh", ""),
                    "text_en": frame.get("subtitle_en", ""),
                })
                cumulative += dur

    final_path = output_dir / "final.mp4"
    if subtitles:
        console.print("  燒字幕...")
        burn_subtitles(raw_path, subtitles, final_path)
    else:
        import shutil
        shutil.copy2(raw_path, final_path)

    console.print(f"  [green]✓ 後製完成: {final_path}[/green]")
    return final_path


def stage_publish(config: dict, video_path: str | Path | None = None, script: dict | None = None) -> dict | None:
    """Stage 8: 上傳 YouTube"""
    from .publisher.youtube_uploader import upload_video

    console.print(Panel("📤 Stage 8: 上傳 YouTube", style="bold cyan"))

    # 找最終視頻
    if not video_path:
        output_root = PROJECT_ROOT / "data" / "output"
        if output_root.exists():
            finals = sorted(output_root.rglob("final.mp4"))
            video_path = finals[-1] if finals else None

    if not video_path or not Path(video_path).exists():
        console.print("  [red]找不到最終視頻[/red]")
        return None

    title = script.get("title", "短劇") if script else "短劇"
    description = script.get("logline", "") if script else ""

    console.print(f"  上傳: {title}")
    result = upload_video(video_path, title=title, description=description)
    console.print(f"  [green]✓ 上傳完成: {result.get('url')}[/green]")
    return result




def stage_kb_generate(config: dict, episode_count: int = 30,
                      genre: str = "都市甜寵") -> dict:
    """KB mode: 從知識庫生成劇本"""
    from .knowledge.knowledge_base import KnowledgeBase
    from .scriptwriter.generator import generate_from_knowledge_base, generate_episode_script

    console.print(Panel("從知識庫生成劇本", style="bold cyan"))

    kb = KnowledgeBase()
    stats = kb.get_stats()
    console.print(f"  知識庫: {stats['total']} 條目")

    if stats["total"] == 0:
        console.print("  [red]知識庫為空，請先跑 kb-analyze[/red]")
        return {}

    kb_config = {
        "genre": genre,
        "episode_count": episode_count,
    }

    console.print(f"  生成 {episode_count} 集大綱 (類型: {genre})...")
    outline = generate_from_knowledge_base(kb, kb_config)
    console.print(f"  [green]大綱完成: {outline.get('series_title', '?')}[/green]")

    # Save and generate episodes (same as stage_series)
    series_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    outline["series_id"] = series_id
    outline["source_type"] = "knowledge_base"
    series_dir = PROJECT_ROOT / "data" / "series" / series_id
    series_dir.mkdir(parents=True, exist_ok=True)
    with open(series_dir / "outline.json", "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)

    episodes_dir = series_dir / "episodes"
    episodes_dir.mkdir(exist_ok=True)
    prev_synopsis = "（第一集，無前情）"

    for ep in outline.get("episodes", []):
        ep_num = ep["episode_number"]
        console.print(f"  [{ep_num}/{len(outline['episodes'])}] 生成第 {ep_num} 集...")
        episode_script = generate_episode_script(outline, ep_num, prev_synopsis)
        if episode_script.get("error"):
            console.print(f"  [red]第 {ep_num} 集失敗[/red]")
            continue
        episode_script["series_id"] = series_id
        with open(episodes_dir / f"ep{ep_num:03d}.json", "w", encoding="utf-8") as f:
            json.dump(episode_script, f, ensure_ascii=False, indent=2)
        prev_synopsis = ep.get("synopsis", "")
        console.print(f"  [green]第 {ep_num} 集完成[/green]")

    console.print(f"\n  [bold green]全部完成！{outline.get('series_title', '')}[/bold green]")
    return outline


def stage_kb_stats() -> None:
    """KB mode: 顯示知識庫統計"""
    from .knowledge.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    stats = kb.get_stats()

    console.print(Panel("知識庫統計", style="bold cyan"))
    console.print(f"  總條目: [bold]{stats['total']}[/bold]")
    console.print(f"  已分析劇目: [bold]{stats.get('dramas', 0)}[/bold]")
    for cat, info in stats.get("categories", {}).items():
        line = f"  {cat}: {info['count']}"
        if "subcategories" in info:
            subs = ", ".join(f"{k}({v})" for k, v in info["subcategories"].items())
            line += f" [{subs}]"
        console.print(line)


def run_pipeline(mode: str = "kb-generate", episode_count: int = 30, genre: str = "都市甜寵"):
    """執行 Pipeline"""
    config = load_config()

    console.print(Panel(
        f"🏚️ 廢墟探索 Pipeline — {mode} mode",
        style="bold magenta",
    ))

    if mode == "kb-generate":
        stage_kb_generate(config, episode_count=episode_count, genre=genre)
    elif mode == "kb-stats":
        stage_kb_stats()
    elif mode == "storyboard":
        stage_storyboard(config)
    elif mode == "assemble":
        stage_assemble(config)
    elif mode == "publish":
        stage_publish(config)
    else:
        console.print(f"[red]未知模式: {mode}[/red]")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="廢墟探索短劇 Pipeline")
    parser.add_argument("--mode", default="kb-generate",
                        choices=["kb-generate", "kb-stats",
                                 "storyboard", "assemble", "publish"])
    parser.add_argument("--drama-id", default="", help="指定 drama ID（用於 assemble/publish）")
    parser.add_argument("--episodes", type=int, default=30, help="集數")
    parser.add_argument("--genre", default="都市甜寵", help="類型")
    args = parser.parse_args()

    run_pipeline(args.mode, episode_count=args.episodes, genre=args.genre)


if __name__ == "__main__":
    main()
