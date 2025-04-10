# LINE Bot 股票資訊助手

一個基於 LINE 平台的智能投資助手，提供即時股票查詢、技術分析、ETF 分析等功能。

## 功能特點

1. 即時股票查詢
   - 查詢股票即時報價
   - 顯示基本資訊（股價、漲跌、成交量等）

2. 技術分析
   - MA（移動平均線）分析
   - KD 指標分析
   - RSI 指標分析

3. ETF 相關功能
   - ETF 基本資訊查詢
   - ETF 成分股分析
   - ETF 重疊度分析

4. 到價提醒
   - 設定股票價格提醒（每月限 2 檔）
   - 即時通知價格達標

5. 市場資訊
   - 即時市場新聞
   - 大盤走勢分析
   - 市場排行榜

6. AI 智能問答
   - 投資相關諮詢
   - 個股分析建議
   - 投資策略建議

## 使用指南

### 基本指令

1. 股票查詢
   ```
   查詢 2330
   ```

2. 技術分析
   ```
   分析 2330
   ```

3. ETF 查詢
   ```
   ETF 0050
   ```

4. ETF 重疊分析
   ```
   重疊 0050 0056
   ```

5. 設定價格提醒
   ```
   提醒 2330 600
   ```

### 安裝步驟

1. 克隆專案
   ```bash
   git clone https://github.com/sheng1111/LINE_Bot.git
   cd LINE_Bot
   ```

2. 建立虛擬環境
   ```bash
   python -m venv .venv
   
   # Windows 啟動虛擬環境
   .venv\Scripts\activate
   
   # Linux/Mac 啟動虛擬環境
   source .venv/bin/activate
   ```

3. 安裝依賴
   ```bash
   pip install -r requirements.txt
   ```

4. 設定環境變數
   在專案根目錄建立 .env 檔案，並設定以下參數：
   ```
   # LINE Bot 設定
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
   LINE_CHANNEL_SECRET=your_line_channel_secret_here

   # MongoDB 設定
   MONGODB_URI=your_mongodb_uri_here
   MONGODB_DB_NAME=your_database_name_here

   # Gemini API 設定
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL_NAME=gemini-2.0-flash
   GEMINI_TEMPERATURE=0.9
   GEMINI_TOP_P=0.8
   GEMINI_TOP_K=40

   # ETF 分析推送日期
   ETF_ANALYSIS_DAYS=7,14
   ```

5. LINE Bot 設定
   1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
   2. 建立新的 Provider 和 Channel
   3. 在 Messaging API 設定頁面：
      - 取得 Channel Secret 和 Channel Access Token
      - 設定 Webhook URL：`https://你的網域/callback`
      - 開啟 "Use webhook"
   
   部署方式有兩種：

   A. 使用 Render 部署
   - 部署到 Render 後，設定 Webhook URL 為：
     `https://你的render網域/callback`

   B. 本地開發測試
   - 安裝 ngrok：`pip install pyngrok`
   - 啟動 ngrok：
     ```bash
     ngrok http 8000
     ```
   - 複製 ngrok 提供的 HTTPS URL，設定為 Webhook URL：
     `https://xxxx.ngrok.io/callback`

6. 啟動服務
   ```bash
   # 使用 FastAPI + uvicorn
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

## 專案結構

```
LINE_Bot/
├── app.py                 # 主應用程式入口
├── .env.example          # 環境變數範例
├── .gitignore            # Git 忽略檔案配置
├── LICENSE               # MIT 授權條款
├── README.md            # 專案說明文件
├── requirements.txt      # 相依套件清單
│
├── config/              # 配置檔案目錄
│   └── settings.py      # 系統設定檔
│
├── services/            # 服務模組目錄
│   ├── __init__.py
│   ├── database.py      # 資料庫服務
│   ├── daily_recommender.py  # 每日推薦服務
│   ├── dividend_analyzer.py  # 股息分析服務
│   ├── etf_service.py       # ETF 相關服務
│   ├── gemini_client.py     # Gemini AI 客戶端
│   ├── market_service.py    # 市場資訊服務
│   ├── stock_analyzer.py    # 股票分析服務
│   ├── stock_comparator.py  # 股票比較服務
│   ├── stock_service.py     # 股票基本服務
│   └── twse_api.py         # 證交所 API 服務
│
├── utils/              # 工具函數目錄
│   ├── __init__.py
│   ├── cache.py       # 快取工具
│   └── logger.py      # 日誌工具
│
├── tests/             # 測試目錄
│   ├── __init__.py
│   ├── run_tests.py          # 測試執行器
│   ├── test_etf_service.py   # ETF 服務測試
│   ├── test_gemini_client.py # AI 服務測試
│   ├── test_market_service.py # 市場服務測試
│   └── test_stock_service.py  # 股票服務測試
│
└── logs/              # 日誌檔案目錄
    └── app.log       # 應用程式日誌
```

## 系統架構

- FastAPI 後端框架
- LINE Messaging API v3
- MongoDB 資料庫
- Google Gemini AI
- asyncio 非同步處理
- APScheduler 定時任務

## 使用的 API

1. LINE Messaging API v3
   - Webhook 處理
   - 訊息回覆
   - 載入動畫顯示

2. 台灣證券交易所 API
   - 股票即時資訊
   - 大盤指數
   - 市場新聞
   - 基本資料查詢

3. Google Gemini AI API
   - 自然語言處理
   - 投資建議生成
   - 市場分析
   - 意圖識別

4. MongoDB API
   - 使用者資料儲存
   - 查詢記錄
   - 到價提醒設定
   - ETF 成分股資料

## 主要功能模組

1. 股票服務 (StockService)
   - 即時股價查詢
   - 技術指標計算
   - 股票基本資訊

2. ETF 服務 (ETFService)
   - ETF 成分股分析
   - 重疊度計算
   - 持股變化追蹤

3. 市場服務 (MarketService)
   - 台指期資訊
   - 市場新聞
   - 大盤走勢

4. AI 服務 (GeminiClient)
   - 智能問答
   - 投資建議
   - 市場分析

## 定時任務

- ETF 重疊分析：每月 7、14 日自動推送
- 股價到價提醒：即時監控
- 系統狀態檢查：定期執行

## 資料來源

- 台灣證券交易所
- 證券櫃檯買賣中心
- Yahoo Finance
- Google Gemini AI

## 注意事項

1. 價格提醒功能每月限制 2 檔股票
2. 所有資訊僅供參考，投資請自負盈虧
3. API 呼叫有流量限制，請適度使用
4. 環境變數請妥善保管，勿外流

## 授權條款

本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 文件。

## 貢獻指南

歡迎提交 Issue 和 Pull Request 來改善專案。在提交之前，請確保：

1. 程式碼遵循 PEP 8 規範
2. 新功能已經過測試
3. 文件已更新

## 更新日誌

### v1.0.0 (2025-03)
- 初始版本發布
- 實現基本功能
- 整合 AI 智能問答

### v1.1.0 (2025-04)
- 重構所有功能
- 升級至 LINE Messaging API v3
- 整合 Google Gemini AI
- 優化 ETF 分析功能
