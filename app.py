from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
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
    # 快速回應 LINE 平台，避免超時
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()

    try:
        # 驗證簽名
        handler.handle(body.decode(), signature)

        # 立即返回 200 OK
        return Response(content='OK', status_code=200)

    except InvalidSignatureError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid signature"}
        )
    except Exception as e:
        logger.error(f"Webhook 處理錯誤：{str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"}
        )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理文字訊息"""
    try:
        user_id = event.source.user_id
        user_message = event.message.text

        # 使用非同步處理來處理訊息
        def process_message_async():
            try:
                # 發送輸入中動畫
                send_typing_animation(user_id)

                # 生成回應
                response = gemini.generate_response(user_message, user_id)

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

        # 在背景執行訊息處理
        threading.Thread(target=process_message_async).start()

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
    # 獲取環境變數中的PORT，如果不存在則使用8000
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"啟動服務 - 主機: 0.0.0.0, 端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
