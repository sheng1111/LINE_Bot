from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
from dotenv import load_dotenv
import logging
from database import db
from gemini_client import gemini
from stock_analyzer import analyzer
from etf_analyzer import analyzer as etf_analyzer
from datetime import datetime
from daily_recommender import DailyRecommender
from dividend_analyzer import analyzer as dividend_analyzer
from peer_comparator import comparator
import time
import threading
import asyncio
from stock_info import get_stock_info, format_stock_info
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from futures_info import get_futures_info, format_futures_info

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI()

# LINE Bot 設定
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
handler = WebhookHandler(channel_secret)

# 初始化 LINE Bot API
configuration = Configuration(access_token=channel_access_token)
async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)

# 投資相關關鍵字
investment_keywords = ['投資', '股票', '基金', 'ETF', '債券', '風險', '報酬', '資產配置']


def is_investment_related(text):
    return any(keyword in text for keyword in investment_keywords)


# 初始化每日建議器
recommender = DailyRecommender()

# 用於追蹤正在處理的請求
processing_requests = {}

# 初始化定時任務調度器
scheduler = AsyncIOScheduler()


def send_typing_animation(user_id):
    """發送輸入中動畫"""
    line_bot_api.push_message(
        user_id,
        TextMessage(text="正在思考中...")
    )


def process_message(user_id, message):
    """處理使用者訊息"""
    try:
        # 發送輸入中動畫
        send_typing_animation(user_id)

        # 生成回應
        response = gemini.generate_response(message, user_id)

        # 發送回應
        line_bot_api.push_message(
            user_id,
            TextMessage(text=response)
        )
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤：{str(e)}")
        line_bot_api.push_message(
            user_id,
            TextMessage(text="抱歉，處理您的請求時發生錯誤，請稍後再試。")
        )
    finally:
        # 清除處理標記
        if user_id in processing_requests:
            del processing_requests[user_id]


@app.get("/")
async def root():
    try:
        return {"status": "success", "message": "AI 投資導向機器人服務已啟動"}
    except Exception as e:
        logger.error(f"根路由處理錯誤：{str(e)}")
        return {"status": "error", "message": "服務暫時無法使用"}


@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()

    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"status": "error", "message": "Invalid signature"}

    return {"status": "success"}


def get_help_message() -> str:
    """
    獲取幫助訊息
    :return: 格式化後的幫助訊息
    """
    return """
🤖 投資小幫手使用說明

📊 股票查詢
輸入：`查詢 2330`
功能：查詢股票即時資訊，包括價格、成交量、本益比等

📈 台指期查詢
輸入：`台指期`
功能：查詢台指期即時資訊，包括價格、漲跌幅、成交量等

📊 ETF 分析
功能：每月 7 日和 14 日自動推送 ETF 重疊成分股分析

💬 投資諮詢
直接輸入您的投資問題，例如：
- "現在適合買 2330 嗎？"
- "0056 的配息情況如何？"
- "請分析台積電的技術面"

📅 除權息查詢
輸入：`除權息 0056`
功能：查詢股票的除權息資訊

📊 同類股比較
輸入：`比較 2330 2303 2317`
功能：比較多檔股票的表現

📢 到價提醒
輸入：`提醒 2330 600`
功能：設定股票價格提醒（每月限制 2 檔）

❓ 其他功能
- 輸入 `/help` 顯示此說明
- 輸入任何投資相關問題，AI 會為您解答

⚠️ 注意事項
- 每月推播次數有限制
- 資料僅供參考，投資需謹慎
"""


@handler.add(MessageEvent, message=TextMessageContent)
async def handle_message(event):
    user_message = event.message.text

    # 顯示 Loading Animation
    await line_bot_api.show_loading_animation(
        ShowLoadingAnimationRequest(
            chatId=event.source.user_id,
            loadingSeconds=5
        )
    )

    # 處理幫助指令
    if user_message == '/help':
        response = get_help_message()
    # 處理股票查詢
    elif user_message.startswith('查詢 '):
        stock_code = user_message.split(' ')[1]
        stock_info = get_stock_info(stock_code)
        response = format_stock_info(stock_info)
    # 處理台指期查詢
    elif user_message == '台指期':
        futures_info = get_futures_info()
        response = format_futures_info(futures_info)
    # 處理投資相關問題
    elif is_investment_related(user_message):
        # 先檢查是否包含股票代碼
        stock_codes = []
        words = user_message.split()
        for word in words:
            if word.isdigit() and len(word) == 4:  # 假設股票代碼是4位數字
                stock_codes.append(word)

        if stock_codes:
            # 如果有股票代碼，先獲取即時資訊
            stock_infos = []
            for code in stock_codes:
                info = get_stock_info(code)
                if info:
                    stock_infos.append(format_stock_info(info))

            # 將即時資訊加入 prompt
            real_time_info = "\n\n".join(stock_infos)
            prompt = f"""
            你是一個專業的投資顧問。以下是即時股票資訊：

            {real_time_info}

            使用者問了以下問題：
            {user_message}

            請根據即時資訊，用專業且易懂的方式回答使用者的問題。
            回答時要：
            1. 先引用即時數據
            2. 分析這些數據的意義
            3. 提供專業的投資建議
            4. 提醒投資風險

            請用中文回答，語氣要專業且友善。
            """
        else:
            # 如果沒有股票代碼，直接回答投資相關問題
            prompt = f"""
            你是一個專業的投資顧問。使用者問了以下問題：
            {user_message}

            請用專業且易懂的方式回答。
            回答時要：
            1. 提供專業的投資建議
            2. 分析可能的風險
            3. 給出具體的建議

            請用中文回答，語氣要專業且友善。
            """

        response = gemini.generate_response(prompt, event.source.user_id)
    else:
        # 對於非投資相關問題，使用 Gemini 生成引導回應
        prompt = f"""
        你是一個友善的投資顧問機器人。使用者問了以下問題：
        {user_message}

        請用友善且專業的語氣，引導使用者了解你可以提供的服務。
        參考以下功能：
        - 股票查詢（例如：查詢 2330）
        - 台指期查詢
        - ETF 分析
        - 投資諮詢
        - 除權息查詢
        - 同類股比較
        - 到價提醒

        請用中文回答，語氣要親切且專業。
        """
        response = gemini.generate_response(prompt, event.source.user_id)

    # 回覆訊息
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=response)]
        )
    )


def log_query(user_id: str, query: str):
    """記錄使用者查詢"""
    try:
        collection = db.get_collection('query_logs')
        collection.insert_one({
            'user_id': user_id,
            'query': query,
            'timestamp': datetime.now()
        })
    except Exception as e:
        logger.error(f"記錄查詢時發生錯誤：{str(e)}")


def handle_daily_recommendation() -> str:
    """處理每日建議"""
    # TODO: 實作每日建議邏輯
    return "正在生成今日投資建議..."


def analyze_etf_overlap():
    """
    分析 ETF 重疊成分股
    :return: 包含重疊分析結果的字典
    """
    try:
        # 從資料庫獲取所有 ETF 的成分股資料
        collection = db.get_collection('etf_holdings')
        etfs = collection.find({})

        # 建立 ETF 代碼到成分股的映射
        etf_holdings = {}
        for etf in etfs:
            etf_holdings[etf['etf_code']] = set(etf['holdings'])

        # 分析重疊情況
        overlap_analysis = {}
        etf_codes = list(etf_holdings.keys())

        for i in range(len(etf_codes)):
            for j in range(i + 1, len(etf_codes)):
                etf1 = etf_codes[i]
                etf2 = etf_codes[j]

                # 計算交集
                common_stocks = etf_holdings[etf1] & etf_holdings[etf2]

                if common_stocks:
                    overlap_analysis[f"{etf1}-{etf2}"] = {
                        "etf1": etf1,
                        "etf2": etf2,
                        "common_stocks": list(common_stocks),
                        "overlap_ratio": len(common_stocks) / min(len(etf_holdings[etf1]), len(etf_holdings[etf2]))
                    }

        return overlap_analysis
    except Exception as e:
        logger.error(f"分析 ETF 重疊時發生錯誤: {str(e)}")
        return None


def format_overlap_analysis(analysis):
    """
    格式化 ETF 重疊分析結果
    :param analysis: 重疊分析結果字典
    :return: 格式化後的字串訊息
    """
    if not analysis:
        return "目前沒有足夠的 ETF 資料進行重疊分析。"

    message = "📊 ETF 重疊成分股分析報告\n\n"

    for key, data in analysis.items():
        if data['overlap_ratio'] > 0.3:  # 只顯示重疊率大於 30% 的組合
            message += f"🔍 {data['etf1']} 與 {data['etf2']} 重疊分析：\n"
            message += f"重疊率：{data['overlap_ratio']:.2%}\n"
            message += f"共同成分股：\n"
            for stock in data['common_stocks'][:5]:  # 只顯示前 5 檔
                message += f"- {stock}\n"
            if len(data['common_stocks']) > 5:
                message += f"... 等共 {len(data['common_stocks'])} 檔\n"
            message += "\n"

    if len(message) == len("📊 ETF 重疊成分股分析報告\n\n"):
        message += "目前沒有發現顯著的重疊情況。"

    return message


async def send_etf_overlap_analysis():
    """
    發送 ETF 重疊分析結果給所有使用者
    """
    try:
        # 獲取所有使用者
        collection = db.get_collection('users')
        users = collection.find({})

        # 分析 ETF 重疊
        analysis = analyze_etf_overlap()
        if not analysis:
            return

        # 格式化分析結果
        message = format_overlap_analysis(analysis)

        # 發送給每個使用者
        for user in users:
            try:
                await line_bot_api.push_message(
                    user['user_id'],
                    TextMessage(text=message)
                )
            except Exception as e:
                logger.error(
                    f"發送 ETF 重疊分析給使用者 {user['user_id']} 時發生錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"執行 ETF 重疊分析時發生錯誤: {str(e)}")


# 設定每月 14 日執行
scheduler.add_job(
    send_etf_overlap_analysis,
    CronTrigger(day=14, hour=9, minute=0),
    id='etf_overlap_analysis'
)

# 啟動定時任務
scheduler.start()


if __name__ == "__main__":
    import uvicorn
    # 獲取環境變數中的PORT，如果不存在則使用8000
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"啟動服務 - 主機: 0.0.0.0, 端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
