# 🎬 YouTube 短劇自動化 Pipeline

全自動短劇生產線：從搜集爆款短劇到生成新短劇並上傳 YouTube。

## 架構概覽

```
爬蟲層          分析層          生成層          指令層
YouTube API ──→ 字幕提取 ──→ 劇本分析 ──→ 新劇本生成 ──→ 分鏡拆解
                yt-dlp         Claude         Claude        角色卡+場景
                Whisper

圖片層          視頻層          後製層          發布層
Gemini ──→ Veo 3.1/Flow ──→ FFmpeg拼接 ──→ YouTube上傳
生分鏡圖      圖生視頻        +字幕燒錄       自動發布
```

## Pipeline 流程

| 層 | 功能 | 技術 | 狀態 |
|---|------|------|------|
| 1. 爬蟲層 | 搜尋爆款短劇、提取字幕 | YouTube Data API + yt-dlp + Whisper | ✅ 可用 |
| 2. 分析層 | 分析劇本結構、歸納爆款模式 | Claude API (proxy) | ✅ 可用 |
| 3. 生成層 | 生成新劇本 | Claude API (proxy) | ✅ 可用 |
| 4. 指令層 | 分鏡拆解 + 角色卡 + Prompt 組裝 | Claude API (proxy) | ✅ 可用 |
| 5. 圖片層 | 生成分鏡圖 | Gemini API / 網頁版 nano banana | ⏳ 免費方案 |
| 6. 視頻層 | 分鏡圖生成視頻 | Veo 3.1 API / Flow 網頁版 | ⏳ 免費方案 |
| 7. 後製層 | 拼接視頻 + 燒字幕 | FFmpeg | ✅ 可用 |
| 8. 發布層 | 上傳 YouTube | YouTube Upload API | ✅ 可用 |

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

# 3. 執行完整 pipeline
python -m src.main --mode full

# 或單獨執行某一層
python -m src.main --mode crawl      # 只跑爬蟲
python -m src.main --mode script     # 只跑劇本生成
python -m src.main --mode storyboard # 只跑分鏡
python -m src.main --mode assemble   # 只跑後製
python -m src.main --mode publish    # 只跑上傳
```

## 設計參考

- [火宝短剧 (huobao-drama)](https://github.com/chatfire-AI/huobao-drama) — 角色卡系統、全局風格一致性
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — Pipeline 架構、多 LLM 整合

## 技術棧

- Python 3.11+
- Claude API（走 proxy localhost:3456）
- Gemini（生圖）/ Veo 3.1（生視頻）
- YouTube Data API + yt-dlp + Whisper
- FFmpeg
