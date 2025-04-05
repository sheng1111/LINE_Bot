# LINE Bot 投資助手

這是一個基於 LINE Bot 的投資助手，提供股票市場資訊、分析工具和投資建議。

## 主要功能

### 1. 市場概況

- 輸入「大盤」、「市場」或「行情」查看：
  - 加權指數
  - 櫃買指數
  - 市場成交金額
  - 市場成交股數

### 2. 股票查詢

- 直接輸入股票代碼（如「2330」）
- 輸入「查詢 2330」查看詳細資訊：
  - 即時股價
  - 漲跌幅
  - 成交量
  - 成交金額
  - 基本面分析（本益比、殖利率、每股盈餘）
  - 技術分析（MA、KD、RSI）
  - 法人買賣超
  - 融資融券

### 3. 股票分析

- 輸入「分析 2330」獲取：
  - 技術面分析
  - 籌碼面分析
  - 投資建議
  - 風險提示

### 4. 市場統計

- 輸入「排行」查看：
  - 成交量排行
  - 漲跌幅排行
  - 成交金額排行

### 5. 新聞資訊

- 輸入「新聞」查看：
  - 市場重要新聞
  - 個股相關新聞

### 6. 技術分析

- 輸入「技術 2330」查看：
  - 移動平均線（MA5、MA10、MA20）
  - KD 指標
  - MACD 指標
  - RSI 指標

### 7. 籌碼分析

- 輸入「籌碼 2330」查看：
  - 外資買賣超
  - 投信買賣超
  - 自營商買賣超
  - 融資融券餘額

### 8. 歷史資料

- 輸入「歷史 2330」查看：
  - 歷史股價
  - 歷史成交量
  - 歷史成交金額

### 9. 投資組合

- 輸入「我的組合」查看：
  - 已追蹤的股票
  - 個股表現
  - 整體績效

### 10. 提醒功能

- 輸入「提醒 2330 600」設定：
  - 股價提醒
  - 成交量提醒
  - 漲跌幅提醒

## 使用說明

1. 加入 LINE Bot 好友
2. 輸入「/help」查看所有可用指令
3. 直接輸入股票代碼或使用指令查詢資訊

## 技術特點

- 使用台灣證券交易所開放 API
- 即時市場數據
- 專業技術分析
- AI 投資建議
- 自動化提醒功能

## 注意事項

- 所有資訊僅供參考，不構成投資建議
- 投資有風險，請謹慎評估
- 資料更新頻率依證交所 API 限制
- 部分功能可能需要註冊會員

## 開發環境

- Python 3.8+
- FastAPI
- LINE Bot SDK
- MongoDB
- Google Gemini API

## 安裝說明

1. 克隆專案

```bash
git clone [專案網址]
```

2. 安裝依賴

```bash
pip install -r requirements.txt
```

3. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 文件，填入必要的 API 金鑰
```

4. 啟動服務

```bash
uvicorn app:app --reload
```

## 貢獻指南

歡迎提交 Pull Request 或提出 Issue。

## 授權說明

MIT License
