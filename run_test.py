#!/usr/bin/env python3
"""端到端測試：Step 3 腳本 → Step 4 分鏡 → Step 5 Kling 生圖"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from src.utils.config import load_config, PROJECT_ROOT
from src.scriptwriter.generator import generate_script
from src.scriptwriter.storyboard import generate_storyboard, save_storyboard, setup_characters
from src.image_gen.kling_generator import batch_generate

def main():
    print("=" * 60)
    print("探索者計劃 — 端到端測試 (Step 3→4→5)")
    print("=" * 60)

    drama_id = "test_run_001"

    # ── Step 3: 生成腳本 ──
    print("\n🎬 Step 3: 生成探索腳本（單集 60 秒）...")
    script = generate_script(
        genre="廢棄精神病院",
        style="found-footage horror",
        human_requirements="夜間探索，手電筒是唯一光源，要有一個關鍵發現（病歷檔案），結尾門自動關上",
    )

    if script.get("error"):
        print(f"❌ 腳本生成失敗: {script['error']}")
        return

    # Save script
    script_dir = PROJECT_ROOT / "data" / "scripts" / drama_id
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / "script.json"
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    scene_count = len(script.get("scenes", []))
    print(f"✅ 腳本生成完成！{scene_count} 個場景")
    print(f"   標題: {script.get('title', 'N/A')}")
    print(f"   存檔: {script_path}")

    # ── Step 4: 分鏡拆解 ──
    print("\n🎞️ Step 4: 分鏡拆解...")
    frames = generate_storyboard(script)

    if not frames:
        print("❌ 分鏡生成失敗")
        return

    sb_path = save_storyboard(frames, drama_id)
    print(f"✅ 分鏡完成！{len(frames)} 個畫面")
    print(f"   存檔: {sb_path}")

    # Print frame prompts for review
    for f in frames:
        print(f"   Frame #{f.frame_number}: {f.image_prompt[:80]}...")

    # ── Step 5: Flux 生圖 ──
    print(f"\n🖼️ Step 5: Kling 生圖（{len(frames)} 張）...")
    from dataclasses import asdict
    frames_data = [asdict(f) for f in frames]

    def on_progress(current, total, msg):
        print(f"   [{current}/{total}] {msg}")

    results = batch_generate(
        frames=frames_data,
        drama_id=drama_id,
        on_progress=on_progress,
    )

    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = sum(1 for r in results if r["status"] == "error")
    print(f"\n✅ 生圖完成！成功 {ok_count}/{len(results)}，失敗 {err_count}")

    img_dir = PROJECT_ROOT / "data" / "generated_images" / drama_id
    print(f"   圖片目錄: {img_dir}")

    # Print summary
    print("\n" + "=" * 60)
    print("📋 測試摘要")
    print(f"   腳本: {script.get('title', 'N/A')} ({scene_count} 場景)")
    print(f"   分鏡: {len(frames)} 個畫面")
    print(f"   生圖: {ok_count} 成功 / {err_count} 失敗")
    print(f"   費用: ~${ok_count * 0.0035:.4f} (Kling)")
    print("=" * 60)


if __name__ == "__main__":
    main()
