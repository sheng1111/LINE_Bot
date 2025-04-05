# LINE 投資機器人

這是一個基於 LINE Messaging API 的投資機器人，提供即時股票資訊查詢、分析與投資建議。

## 功能特點

### 1. 股票查詢與分析

- 即時股價查詢：輸入「查詢 2330」可查詢台積電即時股價
- 股票基本面分析：輸入「分析 2330」可獲取台積電基本面分析
- 同類股比較：輸入「比較 2330 2303」可比較台積電和聯電的表現
- 除權息分析：輸入「除權息 2330」可查詢台積電的除權息資訊

### 2. ETF 分析

- ETF 成分股分析：輸入「ETF 分析 0050」可查詢元大台灣 50 的成分股分析
- 重疊度分析：每月 7 日和 14 日自動推送熱門 ETF 的重疊成分股分析

### 3. 台指期資訊

- 即時期貨行情：輸入「台指期」可查詢台指期即時行情

### 4. AI 投資顧問

- 投資諮詢：直接輸入您的投資問題，例如「台積電現在適合買嗎？」
- 一般諮詢：也可以詢問非投資相關的問題，機器人會盡力回答

## 部署方式

### Render 部署

1. 在 Render 創建新的 Web Service
2. 連接 GitHub 倉庫
3. 設定環境變數：
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_CHANNEL_SECRET
   - GEMINI_API_KEY
   - DATABASE_URL
4. 設定 Build Command: `pip install -r requirements.txt`
5. 設定 Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### 防止機器睡眠

使用 Render 的 Cron Jobs 功能，設定每小時執行一次健康檢查：

```bash
curl -X GET https://your-app-name.onrender.com/health
```

## 環境變數設定

```env
LINE_CHANNEL_ACCESS_TOKEN=你的LINE Channel Access Token
LINE_CHANNEL_SECRET=你的LINE Channel Secret
GEMINI_API_KEY=你的Gemini API Key
DATABASE_URL=你的資料庫連接字串
```

## 開發環境設定

1. 克隆倉庫
2. 安裝依賴：`pip install -r requirements.txt`
3. 設定環境變數
4. 運行測試：`python test_functions.py`

## 使用方式

1. 加入 LINE 好友
2. 發送以下指令：
   - 查詢股票：`查詢 2330`
   - 分析股票：`分析 2330`
   - ETF 分析：`ETF分析 0050`
   - 除權息查詢：`除權息 2330`
   - 同類股比較：`比較 2330 2303`
   - 台指期查詢：`台指期`
   - 投資諮詢：直接輸入您的投資問題
   - 一般諮詢：直接輸入您的問題

## 技術架構

- FastAPI：後端框架
- LINE Messaging API：訊息處理
- Gemini API：AI 對話
- PostgreSQL：資料庫
- APScheduler：定時任務

## 貢獻指南

歡迎提交 Pull Request 或提出 Issue。

## 授權

MIT License
