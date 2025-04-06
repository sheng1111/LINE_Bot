# 智能投資助手 LINE Bot

這是一個基於 LINE Messaging API 和 Google Gemini AI 開發的智能投資助手，能夠提供即時股票資訊、技術分析、ETF 分析等多項功能。

## 功能特點

### 1. 股票資訊查詢

- 即時股價與基本資訊查詢
- 技術指標分析（MA、KD、RSI、MACD）
- 籌碼面分析（法人買賣超、融資融券）
- 基本面分析（財務報表、本益比等）

### 2. ETF 相關功能

- ETF 成分股查詢
- ETF 重疊分析
- 定期推送 ETF 投資建議（每月 7、14 日）

### 3. 市場資訊

- 大盤指數即時資訊
- 市場成交量排行
- 產業類股表現
- 市場新聞彙整

### 4. 智能分析

- 自然語言查詢與回答
- 個股投資建議
- 技術面分析報告
- 客製化投資組合建議

### 5. 提醒功能

- 股價到價提醒
- 除權息提醒
- 技術指標突破提醒

## 安裝指南

1. 克隆專案：

```bash
git clone https://github.com/sheng1111/LINE_Bot.git
cd LINE_Bot
```

2. 安裝依賴：

```bash
pip install -r requirements.txt
```

3. 設定環境變數（創建 .env 文件）：

```env
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
GEMINI_API_KEY=你的_Gemini_API_Key
```

4. 啟動服務：

```bash
python app.py
```

## 使用說明

### 基本查詢指令

- 查詢股票：`查詢 股票代碼`（例：查詢 2330）
- 技術分析：`技術分析 股票代碼`
- ETF 分析：`分析 ETF代碼1 ETF代碼2`（例：分析 0050 0056）
- 市場資訊：`大盤` 或 `市場`
- 幫助：`/help`

### 自然語言查詢

支援自然語言輸入，例如：

- "台積電最近表現如何？"
- "0050 和 0056 有哪些重疊的成分股？"
- "請分析台積電的投資價值"
- "最近市場趨勢如何？"

## 技術架構

- FastAPI：Web 框架
- LINE Messaging API：訊息處理
- Google Gemini AI：自然語言處理
- TWSE API：股市資料來源
- MongoDB：資料儲存
- APScheduler：定時任務

## 注意事項

1. 投資建議僅供參考，請自行評估風險
2. API 呼叫有速率限制，請適度使用
3. 每個用戶每月可設定的到價提醒最多 2 檔
4. LLM 回應可能需要等待 1-2 秒

## 貢獻指南

歡迎提交 Pull Request 或建立 Issue。

## 授權

MIT License

## 更新日誌

### v1.0.0 (2024-03)

- 初始版本發布
- 實現基本股票查詢功能
- 整合 Gemini AI 自然語言處理
- 加入 ETF 分析功能
