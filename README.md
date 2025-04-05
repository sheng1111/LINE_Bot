# LINE Bot 投資助手

這是一個基於 LINE Bot 的投資助手，提供股票查詢、分析、ETF 分析等功能。

## 功能特點

- 股票即時查詢
- 技術分析
- ETF 分析
- 除權息查詢
- 同類股比較
- 台指期查詢
- AI 投資諮詢

## 環境需求

- Python 3.11+
- MongoDB Atlas
- LINE Bot 帳號
- Google Gemini API

## 安裝步驟

1. 克隆專案

```bash
git clone [repository_url]
cd [project_directory]
```

2. 安裝依賴

```bash
pip install -r requirements.txt
```

3. 設定環境變數
   創建 `.env` 文件並設定以下變數：

```
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=your_mongodb_atlas_uri
MONGODB_DB_NAME=your_database_name
```

4. 啟動服務

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 資料庫設定

本專案使用 MongoDB Atlas 作為資料庫。請確保：

1. 在 MongoDB Atlas 創建一個新的資料庫
2. 設定適當的存取權限
3. 在環境變數中設定正確的 MONGODB_URI 和 MONGODB_DB_NAME

## 使用說明

1. 將 LINE Bot 加入好友
2. 輸入 `/help` 查看使用說明
3. 使用各種指令進行查詢和分析

## 部署

本專案支援部署到 Render 平台。請參考 `render.yaml` 的設定。

## 注意事項

- 股票資料僅供參考，投資需謹慎
- API 有使用限制，請注意使用頻率
- 建議定期備份資料庫
