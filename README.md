# 🏚️ 探索者計劃 — 廢墟探索影片自動化 Pipeline

從知識庫生成廢墟探索影片並上傳 YouTube。

## 架構概覽

```
生成層          指令層          圖片層          視頻層
知識庫 ──→ 探索腳本生成 ──→ 分鏡拆解 ──→ 場景圖生成 ──→ 探索影片生成
Claude         Claude        角色卡+場景    Flux/fal.ai    Kling AI

後製層          發布層
FFmpeg拼接 ──→ YouTube上傳
+字幕燒錄       自動發布
```

## Pipeline 流程（6 步）

| 步驟 | 功能 | 技術 | 狀態 |
|------|------|------|------|
| 1. 探索腳本生成 | 從知識庫生成探索劇本 | Claude API (proxy) | ✅ 可用 |
| 2. 場景分鏡 | 分鏡拆解 + 角色卡 + Prompt 組裝 | Claude API (proxy) | ✅ 可用 |
| 3. 場景圖生成 | 生成分鏡圖 | Flux Schnell (fal.ai) | ✅ 可用 |
| 4. 探索影片生成 | 分鏡圖生成視頻 | Kling AI API | ✅ 可用 |
| 5. 後製合成 | 拼接視頻 + 燒字幕 | FFmpeg | ⏳ 開發中 |
| 6. 發布上傳 | 上傳 YouTube | YouTube Upload API | ⏳ 開發中 |

## 產出規格

- 每部 ~60 秒（8-10 段 × 6-8 秒）
- 分辨率：1080×1920（豎屏）
- 字幕：中文 + 英文雙語
- 目標：一天 4 部

## 快速開始

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 API keys

# 3. 從知識庫生成劇本
python -m src.main --mode kb-generate

# 或單獨執行某一步
python -m src.main --mode kb-stats    # 顯示知識庫統計
python -m src.main --mode storyboard  # 分鏡拆解
python -m src.main --mode assemble    # 後製合成
python -m src.main --mode publish     # 上傳 YouTube

# 啟動 Web Dashboard
python -m src.web.app
```

## 技術棧

- Python 3.11+
- Claude API（走 proxy localhost:3456）
- Flux Schnell / fal.ai（生圖）
- Kling AI（生視頻）
- FFmpeg
- FastAPI（Web Dashboard）
