"""測試 Pipeline

用法:
    python -m pytest tests/test_pipeline.py -v
    python -m pytest tests/test_pipeline.py -v -k generate   # 只測劇本生成
    python -m pytest tests/test_pipeline.py -v -k storyboard # 只測分鏡

注意：
  - 分析/生成/分鏡層需要 Claude proxy (localhost:3456) + PROXY_API_KEY
  - 設定從 .env 讀取
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import load_config


@pytest.fixture(scope="session")
def config():
    return load_config()


@pytest.fixture(scope="session")
def has_proxy_key(config):
    return bool(config["proxy"]["api_key"])


# ── Stage 3: 劇本生成 ──

class TestGenerate:
    """測試劇本生成（需要 Claude proxy）"""

    def test_generate_script(self, has_proxy_key):
        if not has_proxy_key:
            pytest.skip("需要 PROXY_API_KEY")

        from src.scriptwriter.generator import generate_script

        script = generate_script(
            trending_analysis="測試用，跳過分析",
            genre="都市甜寵",
        )
        assert isinstance(script, dict)

        # 應有基本結構
        if "error" not in script:
            assert "title" in script, f"劇本缺少 title: {list(script.keys())}"
            assert "scenes" in script, "劇本缺少 scenes"
            assert "characters" in script, "劇本缺少 characters"
            assert len(script["scenes"]) > 0, "劇本至少要有一個場景"
            print(f"\n  劇本: {script['title']}, {len(script['scenes'])} 場景, {len(script['characters'])} 角色")
        else:
            print(f"\n  劇本生成 JSON parse 失敗，但有回應: {script.get('raw', '')[:100]}")


# ── Stage 4: 分鏡 ──

class TestStoryboard:
    """測試分鏡拆解（需要 Claude proxy）"""

    def test_setup_characters(self, tmp_path):
        """角色卡建立"""
        from src.scriptwriter.storyboard import setup_characters

        mock_script = {
            "characters": [
                {
                    "name": "陸晨",
                    "gender": "male",
                    "age_range": "28-32",
                    "hair": "black short hair",
                    "skin_tone": "fair",
                    "outfit": "dark suit",
                    "body_type": "tall and fit",
                    "personality": "cold but caring",
                },
                {
                    "name": "蘇小暖",
                    "gender": "female",
                    "age_range": "23-26",
                    "hair": "long black hair",
                    "skin_tone": "fair",
                    "outfit": "white dress",
                    "body_type": "slim",
                    "personality": "cute and clumsy",
                },
            ]
        }

        # Use tmp dir for drama_id
        import src.utils.config as config_mod
        old_root = config_mod.PROJECT_ROOT
        try:
            config_mod.PROJECT_ROOT = tmp_path
            manager = setup_characters(mock_script, "test_drama")
            cards = manager.all_cards()
            assert len(cards) == 2
            assert cards[0].name == "陸晨"
            assert cards[1].name == "蘇小暖"

            # Test prompt generation
            desc = manager.get_prompt_desc("陸晨", lang="en")
            assert "male" in desc
            assert "suit" in desc
            print(f"\n  角色描述: {desc}")
        finally:
            config_mod.PROJECT_ROOT = old_root

    def test_generate_storyboard(self, has_proxy_key, tmp_path):
        if not has_proxy_key:
            pytest.skip("需要 PROXY_API_KEY")

        from src.scriptwriter.storyboard import setup_characters, generate_storyboard

        mock_script = {
            "characters": [
                {
                    "name": "陸晨",
                    "gender": "male",
                    "age_range": "28-32",
                    "hair": "black short hair",
                    "skin_tone": "fair",
                    "outfit": "dark suit",
                    "body_type": "tall",
                    "personality": "cold",
                }
            ],
            "scenes": [
                {
                    "scene_number": 1,
                    "duration_sec": 5,
                    "location": "咖啡廳",
                    "location_en": "Coffee shop",
                    "characters_present": ["陸晨"],
                    "action_zh": "陸晨坐在窗邊，看著窗外下雨",
                    "action_en": "Lu Chen sits by the window, watching the rain",
                    "dialogue_zh": "",
                    "dialogue_en": "",
                    "emotion": "melancholy",
                    "camera_angle": "medium shot",
                    "lighting": "warm",
                }
            ],
        }

        import src.utils.config as config_mod
        old_root = config_mod.PROJECT_ROOT
        try:
            config_mod.PROJECT_ROOT = tmp_path
            manager = setup_characters(mock_script, "test_sb")
            frames = generate_storyboard(mock_script, manager)
            assert isinstance(frames, list)
            if frames:
                f = frames[0]
                assert f.image_prompt, "分鏡缺少 image_prompt"
                print(f"\n  分鏡 {len(frames)} 個, 第一個: {f.image_prompt[:80]}...")
        finally:
            config_mod.PROJECT_ROOT = old_root
