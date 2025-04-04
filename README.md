# AI 投資導向機器人 - 完整說明文件

## 🚀 一、專案目的

此機器人主要為個人及少數朋友使用，基於免費資源（Vercel + LINE + Gemini API）開發，並具備以下能力與特色：

- 📈 經濟資訊數據自動抓取與整合
- 🧠 AI 資料分析與投資建議
- 💬 LINE 互動式對話與通知功能
- 📊 管理後台模擬（未來商業化考量）
- ♻️ 資源最佳化與節能設計，免費且穩定

> 💡 免費版限制：
>
> - LINE Bot：每月推播 200 則
> - Gemini API：每分鐘 60 次請求
> - MongoDB Atlas：512MB 儲存空間
> - Vercel：每月 100GB 流量
> - 建議使用人數：5~10 人

---

## ⚙️ 二、功能模組說明

### 📌 基本功能

1. **ETF 成分股分析**

   - 自動爬取 ETF（如 0050、006208、0056）成分股
   - 找出重複成分股，提供市場共識股票建議

2. **個股財務與技術分析**

   - 財務面：EPS、ROE、殖利率
   - 技術面：KD、MACD、成交量

3. **AI 投資建議（Gemini API）**

   - 將結構化數據轉成易讀投資建議與風險提示

4. **LINE Bot 互動**

   - 使用者透過 LINE 簡單指令進行互動，如：
     - `查詢 2330` (個股分析)
     - `ETF排行` (熱門 ETF 績效)
     - `今日建議` (AI 推薦個股)

5. **個人化投資風格設定**

   - 簡易測驗分類使用者偏好，提供個人化 AI 建議

6. **到價提醒功能**（注意免費推播限制）

   - 每日固定時間檢查，滿足條件透過 LINE 推送
   - 每位使用者最多 2 檔股票提醒

7. **除權息與股東會查詢**

   - 輸入：`除權息 0056`或`股東會 2330`，即可取得資訊

8. **自然語言互動問答**

   - 支援類似：「現在適合買 2330 嗎？」之自然語言提問

9. **同類股比較功能**

   - 輸入：`比較 2330 2303 2317` 即可生成比較圖表

10. **AI 財報摘要功能**

- 自動抓取上市公司季報，推播重點摘要

---

## 🖥️ 商業級應用模組（模擬）

1. **管理後台 Dashboard**

   - 查看使用情況、推播剩餘次數、熱門查詢

2. **使用者行為分析與紀錄**

   - MongoDB Atlas 儲存互動紀錄與用戶偏好

3. **資源管理與優化**

   - 限制每日 API 使用次數
   - 快取常用資料，降低 API 重複呼叫

4. **免費服務限制管控**
   - 每月 200 則推播上限管理
   - API 使用次數即時監控與通知

---

## 🎨 三、使用者互動設計

- 使用者透過 LINE 傳送簡短指令，系統使用 `reply_message` 回覆以保持上下文。
- 當免費推播額度即將用盡時，主動通知使用者：
  > 📢 本月剩餘推播次數僅剩 12 次。
- 若推播次數用盡，改以回覆文字建議用戶主動查詢：
  > ⚠️ 您的提醒條件可能已觸發，但免費推播額度已達上限，請輸入`查詢 2330`以取得最新資訊。

---

## 🛠️ 四、系統架構與部署環境

### 📁 專案目錄結構

```
invest-bot/
├── app.py                  # FastAPI主程式
├── .env                    # 環境變數設定
├── requirements.txt        # Python依賴
├── vercel.json            # Vercel部署設定
└── README.md              # 專案說明
```

### 🛠️ 技術使用說明

| 元件       | 說明                  | 免費版限制       |
| ---------- | --------------------- | ---------------- |
| 部署平台   | Vercel (Serverless)   | 每月 100GB 流量  |
| 語言與框架 | Python 3.11+、FastAPI | -                |
| AI 服務    | Gemini API            | 每分鐘 60 次請求 |
| LINE Bot   | 免費版                | 每月 200 則推播  |
| 資料庫     | MongoDB Atlas 免費版  | 512MB 儲存空間   |

## 🔧 五、部署指南

### 1. 本地開發環境設置

```bash
# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 啟動本地伺服器
uvicorn app:app --reload
```

### 2. Vercel 部署步驟

1. 將專案推送到 GitHub
2. 在 Vercel 中導入 GitHub 專案
3. 設定環境變數：
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_CHANNEL_SECRET
   - MONGODB_URI
   - MONGODB_DB_NAME
   - GEMINI_API_KEY
4. 部署專案

### 3. LINE Bot 設定

1. 在 [LINE Developers](https://developers.line.biz/) 建立新的 Channel
2. 設定 Webhook URL 為 Vercel 部署的 URL + /webhook
3. 啟用 Webhook

### 4. 部署到 Render

1. 在 [Render](https://render.com) 註冊帳號
2. 點擊 "New +" 按鈕，選擇 "Web Service"
3. 連接您的 GitHub 倉庫
4. 配置以下設置：
   - Name: 您的服務名稱
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. 在 Environment Variables 部分添加以下環境變數：
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_CHANNEL_SECRET`
   - `GEMINI_API_KEY`
6. 點擊 "Create Web Service" 開始部署

## 📝 六、使用限制與注意事項

1. **資料庫使用限制**

   - 定期清理舊資料
   - 使用資料壓縮
   - 避免儲存大量歷史數據

2. **API 使用限制**

   - 實作快取機制
   - 限制使用者請求頻率
   - 監控 API 使用量

3. **推播限制**
   - 優先處理重要通知
   - 合併相似通知
   - 提供使用者主動查詢選項

## 🔮 七、未來優化方向

- 導入情緒分析，分析新聞與社群輿情
- 開發回測系統，驗證投資策略表現
- 提供更詳細的統計數據與使用者行為分析
- 支援 RAG 架構提升知識管理與回答準確性

## 🚩 八、結語

本機器人以免費資源搭建，提供個人與小群體的投資決策輔助工具，兼具易用性、實用性和擴充性。在使用過程中，請注意各項免費服務的限制，並適時進行優化與調整。

歡迎使用 AI 協作工具（如 Cursor）繼續維護與優化此專案！
