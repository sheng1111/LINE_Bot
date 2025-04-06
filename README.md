# LINE Bot 股票投資助手

這是一個基於 LINE Bot 的股票投資助手，提供多種股票相關功能，包括股票查詢、ETF 分析、除權息分析、同類股比較等。

## 功能特點

1. **智能對話**：使用 LLM 理解用戶意圖，無需記住特定指令
2. **股票查詢**：查詢股票即時資訊，包括價格、成交量、漲跌幅等
3. **ETF 分析**：分析 ETF 的組成、績效和風險
4. **除權息分析**：查詢股票的除權息資訊和殖利率
5. **同類股比較**：比較同類股票的表現和基本面
6. **台指期資訊**：查詢台指期的即時資訊
7. **ETF 重疊分析**：分析不同 ETF 的成分股重疊情況
8. **投資諮詢**：回答各種投資相關問題

## 使用方式

直接與機器人對話，例如：

- "台積電現在股價多少？"
- "0050 的表現如何？"
- "台積電的除權息資訊"
- "台積電和聯發科的比較"
- "台指期現在多少點？"
- "0050 和 0056 的成分股重疊情況"
- "現在適合投資台積電嗎？"

機器人會自動理解您的意圖並提供相應的資訊。

## 技術架構

- **後端框架**：FastAPI
- **資料庫**：MongoDB
- **AI 模型**：Gemini
- **股票資料來源**：台灣證券交易所 API
- **部署平台**：Render

## 環境變數設定

需要設定以下環境變數：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的 LINE Channel Access Token
LINE_CHANNEL_SECRET=你的 LINE Channel Secret
MONGODB_URI=你的 MongoDB 連接字串
GEMINI_API_KEY=你的 Gemini API Key
```

## 安裝與執行

1. 安裝依賴套件：

```bash
pip install -r requirements.txt
```

2. 設定環境變數

3. 執行應用程式：

```bash
python app.py
```

## 開發者

- 作者：Your Name
- 聯絡方式：your.email@example.com

## 授權

MIT License

## 更新日誌

### v1.0.0 (2024-03)

- 初始版本發布
- 實現基本股票查詢功能
- 整合 Gemini AI 自然語言處理
- 加入 ETF 分析功能
