from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
import logging
from database import db
from gemini_client import gemini
from stock_analyzer import analyzer
from etf_analyzer import etf_analyzer
from datetime import datetime
from daily_recommender import DailyRecommender
from dividend_analyzer import analyzer as dividend_analyzer
from peer_comparator import comparator
import time
import threading

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI()

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 初始化每日建議器
recommender = DailyRecommender()

# 用於追蹤正在處理的請求
processing_requests = {}


def send_typing_animation(user_id):
    """發送輸入中動畫"""
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text="正在思考中...")
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
            TextSendMessage(text=response)
        )
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤：{str(e)}")
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text="抱歉，處理您的請求時發生錯誤，請稍後再試。")
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


@app.post("/webhook")
async def webhook(request: Request):
    # 取得 X-Line-Signature header 的值
    signature = request.headers.get('X-Line-Signature', '')

    # 取得 request body 作為文字
    body = await request.body()

    try:
        handler.handle(body.decode(), signature)
        return {"message": "OK"}
    except InvalidSignatureError:
        return {"message": "Invalid signature"}, 400
    except Exception as e:
        logger.error(f"Webhook 處理錯誤：{str(e)}")
        return {"message": "Internal server error"}, 500


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理文字訊息"""
    try:
        user_id = event.source.user_id
        user_message = event.message.text

        # 記錄使用者查詢
        log_query(user_id, user_message)

        # 處理不同類型的訊息
        if user_message.startswith('查詢 '):
            try:
                stock_code = user_message.split(' ')[1]
                response = analyzer.analyze_stock(stock_code)
            except Exception as e:
                logger.error(f"查詢股票時發生錯誤：{str(e)}")
                response = "抱歉，查詢股票時發生錯誤，請確認股票代碼是否正確。"
        elif user_message == 'ETF排行':
            try:
                response = etf_analyzer.get_etf_ranking()
            except Exception as e:
                logger.error(f"查詢 ETF 排行時發生錯誤：{str(e)}")
                response = "抱歉，查詢 ETF 排行時發生錯誤，請稍後再試。"
        elif user_message == '每日建議':
            try:
                response = recommender.generate_daily_recommendation(user_id)
            except Exception as e:
                logger.error(f"生成每日建議時發生錯誤: {str(e)}")
                response = "抱歉，生成每日建議時發生錯誤，請稍後再試。"
        elif user_message.startswith('股息 '):
            try:
                stock_code = user_message.split(' ')[1]
                dividend_info = dividend_analyzer.get_dividend_info(stock_code)
                if dividend_info:
                    yield_rate = dividend_analyzer.calculate_dividend_yield(
                        stock_code)
                    history = dividend_analyzer.get_dividend_history(
                        stock_code)

                    response = f"""
📊 {stock_code} 股息資訊：
- 當前價格：{dividend_info['current_price']}
- 年度股息：{dividend_info['annual_dividend']}
- 股息殖利率：{yield_rate:.2f}%

📅 最近股息發放記錄：
"""
                    for record in history[:3]:  # 顯示最近 3 筆記錄
                        response += f"- {record['date']}: {record['amount']} ({record['type']})\n"
                else:
                    response = "抱歉，無法獲取該股票的股息資訊，請確認股票代碼是否正確。"
            except Exception as e:
                logger.error(f"查詢股息時發生錯誤：{str(e)}")
                response = "抱歉，查詢股息時發生錯誤，請稍後再試。"
        elif user_message.startswith('比較 '):
            try:
                stock_code = user_message.split(' ')[1]
                comparison = comparator.compare_stocks(stock_code)

                if 'error' in comparison:
                    response = comparison['error']
                else:
                    target = comparison['target_stock']
                    peers = comparison['peers']

                    response = f"""
📊 {target['name']} ({target['stock_code']}) 同業比較：
- 當前價格：{target['price']}
- 股息殖利率：{target['dividend_yield']:.2f}%
- 本益比：{target['pe_ratio']}
- 股價淨值比：{target['pb_ratio']}
- 殖利率排名：{target['rank']}/{comparison['total_companies']}

📈 同業比較（按殖利率排序）：
"""
                    for peer in peers:
                        response += f"""
{peer['name']} ({peer['stock_code']})
- 價格：{peer['price']}
- 殖利率：{peer['dividend_yield']:.2f}%
- 本益比：{peer['pe_ratio']}
- 股價淨值比：{peer['pb_ratio']}
"""
            except Exception as e:
                logger.error(f"比較股票時發生錯誤：{str(e)}")
                response = "抱歉，比較股票時發生錯誤，請稍後再試。"
        else:
            # 使用 Gemini 處理一般對話
            response = gemini.generate_response(user_message, user_id)

        # 回覆訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤：{str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，處理您的訊息時發生錯誤。")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
