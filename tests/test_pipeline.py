"""測試前 4 層 Pipeline

用法:
    python -m pytest tests/test_pipeline.py -v
    python -m pytest tests/test_pipeline.py -v -k crawl     # 只測爬蟲
    python -m pytest tests/test_pipeline.py -v -k analyze    # 只測分析
    python -m pytest tests/test_pipeline.py -v -k generate   # 只測劇本生成
    python -m pytest tests/test_pipeline.py -v -k storyboard # 只測分鏡

注意：
  - 爬蟲層用 yt-dlp（不需 API key）
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


# ── Stage 1: 爬蟲 ──

class TestCrawl:
    """測試爬蟲搜尋（用 yt-dlp fallback，不需 API key）"""

    def test_ytdlp_search(self):
        """yt-dlp 搜尋應能找到結果"""
        from src.crawler.youtube_search import _search_with_ytdlp

        results = _search_with_ytdlp(
            query="短劇 完整版",
            max_results=5,
            min_views=0,  # 降低門檻確保有結果
        )
        assert isinstance(results, list)
        assert len(results) > 0, "yt-dlp 搜尋應至少找到 1 個結果"

        # 驗證結構
        r = results[0]
        assert "video_id" in r
        assert "title" in r
        assert "views" in r
        print(f"\n  找到 {len(results)} 部短劇，第一部: {r['title']} ({r['views']} views)")

    def test_batch_search(self):
        """batch_search 去重搜尋"""
        from src.crawler.youtube_search import batch_search

        results = batch_search(
            queries=["短劇 完整版"],
            max_results=3,
            min_views=0,
        )
        assert isinstance(results, list)
        # 檢查 video_id 不重複
        ids = [r["video_id"] for r in results]
        assert len(ids) == len(set(ids)), "batch_search 應去重"

    def test_save_results(self, tmp_path):
        """save_results 存 JSON"""
        from src.crawler.youtube_search import save_results

        test_data = [{"video_id": "test123", "title": "測試", "views": 999}]

        import src.crawler.youtube_search as yt_mod
        orig_root = yt_mod.PROJECT_ROOT

        # 暫時改 PROJECT_ROOT 到 tmp
        import src.utils.config as config_mod
        old_root = config_mod.PROJECT_ROOT
        try:
            config_mod.PROJECT_ROOT = tmp_path
            yt_mod.PROJECT_ROOT = tmp_path
            (tmp_path / "data" / "scripts").mkdir(parents=True, exist_ok=True)

            path = save_results(test_data)
            assert path.exists()
            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded == test_data
        finally:
            config_mod.PROJECT_ROOT = old_root
            yt_mod.PROJECT_ROOT = orig_root


# ── Stage 2: 分析 ──

class TestAnalyze:
    """測試爆款分析（需要 Claude proxy）"""

    def test_analyze_trending(self, has_proxy_key):
        if not has_proxy_key:
            pytest.skip("需要 PROXY_API_KEY")

        from src.crawler.trending_analyzer import analyze_trending

        mock_data = [
            {
                "video_id": "abc123",
                "title": "霸道總裁愛上我 完整版",
                "views": 5000000,
                "text": "女主角在雨中跌倒，被帥氣的男主角扶起。兩人四目相對，男主角說：「你是我見過最笨的女人。」"
            },
            {
                "video_id": "def456",
                "title": "重生千金復仇記",
                "views": 3000000,
                "text": "女主角重生回到十年前，她決定要報復所有欺負過她的人。"
            },
        ]

        result = analyze_trending(mock_data)
        assert isinstance(result, dict)
        # Should have analysis fields (or raw_analysis if JSON parse fails)
        has_fields = any(k in result for k in ["common_themes", "summary", "raw_analysis"])
        assert has_fields, f"分析結果缺少預期欄位: {list(result.keys())}"
        print(f"\n  分析結果 keys: {list(result.keys())}")


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


# ── Full Pipeline (前 4 層) ──

class TestFullPipeline:
    """完整跑前 4 層"""

    def test_full_run(self, has_proxy_key):
        """一次跑完前 4 層（整合測試）"""
        if not has_proxy_key:
            pytest.skip("需要 PROXY_API_KEY")

        from src.crawler.youtube_search import batch_search, save_results
        from src.crawler.trending_analyzer import analyze_trending
        from src.scriptwriter.generator import generate_script
        from src.scriptwriter.storyboard import setup_characters, generate_storyboard, save_storyboard

        # 1. 爬蟲
        print("\n  [1/4] 爬蟲搜尋...")
        results = batch_search(queries=["短劇 完整版"], max_results=3, min_views=0)
        assert len(results) > 0, "爬蟲應找到結果"
        save_results(results)
        print(f"  找到 {len(results)} 部")

        # 2. 分析
        print("  [2/4] 爆款分析...")
        analysis = analyze_trending(results)
        assert isinstance(analysis, dict)
        print(f"  分析完成: {list(analysis.keys())[:5]}")

        # 3. 生成劇本
        print("  [3/4] 劇本生成...")
        script = generate_script(trending_analysis=analysis)
        assert "title" in script or "raw" in script
        print(f"  劇本: {script.get('title', '(parse failed)')}")

        if "error" in script:
            pytest.skip("劇本 JSON parse 失敗，跳過分鏡")

        # 4. 分鏡
        print("  [4/4] 分鏡拆解...")
        drama_id = "test_full"
        char_manager = setup_characters(script, drama_id)
        frames = generate_storyboard(script, char_manager)
        assert isinstance(frames, list)
        if frames:
            save_storyboard(frames, drama_id)
        print(f"  分鏡完成: {len(frames)} 個畫面")
        print("\n  ✅ 前 4 層 Pipeline 全部通過！")
