# 夜間優化任務

## 專案位置
/Users/zm-mini/Projects/short-drama-pipeline

## 任務：系統性排查所有代碼並優化結構

### Phase 1: 代碼審計
1. 讀取所有 Python 源碼（src/ 目錄下所有 .py）和前端代碼（src/web/static/）
2. 列出所有問題：Bug / 性能 / 結構 / 品質

### Phase 2: 數據庫設計優化
- 檢查 index_db.py 和 knowledge_base.py 的 JSON 存儲
- 優化數據存取效率和一致性
- 確保文件鎖正確

### Phase 3: 性能優化
- 找出性能瓶頸（JSON 讀寫、API 調用）
- 優化前端渲染效率

### Phase 4: 結構重構
- 消除重複代碼
- 統一錯誤處理
- 前後端 key 名稱一致
- 清理未使用的 legacy API endpoints

### Phase 5: 前端修復
- 所有 tab/view 切換正常
- API 調用有錯誤處理
- CSS 一致性

### Phase 6: 測試驗證
- 啟動 Web UI 驗證所有頁面
- 測試 API endpoints

## 規則
- 每修一個問題就 git commit
- commit message 中文
- 不動核心業務邏輯（prompt 不改）
- 發現 bug 直接修

## 完成後
執行：openclaw message send --channel discord --target 1481714286568018151 -m '✅ 夜間優化任務完成！詳情查看 git log。'
然後輸出一份完整的優化報告。
