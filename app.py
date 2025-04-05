from fastapi import FastAPI, Request
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
from datetime import datetime
import uvicorn
from database import db
from gemini_client import gemini
from stock_analyzer import analyzer
from etf_analyzer import analyzer as etf_analyzer
from daily_recommender import DailyRecommender
from dividend_analyzer import analyzer as dividend_analyzer
from peer_comparator import comparator
from stock_info import get_stock_info, format_stock_info
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from futures_info import get_futures_info, format_futures_info
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import re

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 投資相關關鍵字
investment_keywords = ['投資', '股票', '基金', 'ETF',
                       '債券', '風險', '報酬', '資產配置', '除權息', '配息', '股利',
                       '提醒', '技術分析', '新聞', '投資組合', '績效', '比較']


def is_investment_related(text):
    return any(keyword in text for keyword in investment_keywords)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時執行
    global handler, line_bot_api, scheduler
    try:
        channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        channel_secret = os.getenv('LINE_CHANNEL_SECRET')
        if not channel_access_token or not channel_secret:
            raise ValueError("LINE Bot 憑證未設定")

        # 初始化 LINE Bot
        handler = WebhookHandler(channel_secret)
        configuration = Configuration(access_token=channel_access_token)
        async_api_client = AsyncApiClient(configuration)
        line_bot_api = AsyncMessagingApi(async_api_client)
        logger.info("LINE Bot 初始化成功")

        # 註冊事件處理器
        register_event_handlers()
        logger.info("LINE Bot 事件處理器註冊成功")

        # 初始化定時任務調度器
        try:
            scheduler = AsyncIOScheduler()
            scheduler.start()
            logger.info("定時任務調度器初始化成功")

            # 設定每月 7 日和 14 日執行
            scheduler.add_job(
                send_etf_overlap_analysis,
                CronTrigger(day='7,14', hour=9, minute=0),
                id='etf_overlap_analysis',
                replace_existing=True
            )
            logger.info("成功設定 ETF 重疊分析定時任務")
        except Exception as e:
            logger.error(f"定時任務調度器初始化失敗: {str(e)}")
            scheduler = None

        # 初始化每日建議器
        try:
            recommender = DailyRecommender()
            logger.info("每日建議器初始化成功")
        except Exception as e:
            logger.error(f"每日建議器初始化失敗: {str(e)}")
            recommender = None

        # 用於追蹤正在處理的請求
        global processing_requests
        processing_requests = {}

        yield

        # 關閉時執行
        if scheduler:
            scheduler.shutdown()
            logger.info("定時任務調度器已關閉")
    except Exception as e:
        logger.error(f"LINE Bot 初始化失敗: {str(e)}")
        raise

# 初始化 FastAPI
app = FastAPI(lifespan=lifespan)

# 添加錯誤處理中間件


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"請求處理錯誤: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "伺服器內部錯誤"}
        )

# 添加健康檢查端點


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# LINE Bot 設定


def register_event_handlers():
    """註冊 LINE Bot 事件處理器"""
    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event):
        # 使用 asyncio 來執行異步函數
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_handle_message_async(event))
        else:
            loop.run_until_complete(_handle_message_async(event))


async def _handle_message_async(event):
    try:
        user_message = event.message.text
        user_id = event.source.user_id

        # 顯示 Loading Animation
        await show_loading_animation(user_id)

        # 處理幫助指令
        if user_message == '/help':
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=get_help_message())]
                )
            )
        # 處理股票查詢
        elif user_message.startswith('查詢 '):
            stock_code = user_message.split(' ')[1]
            stock_info = get_stock_info(stock_code)
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text=format_stock_info(stock_info))]
                )
            )
        # 處理台指期查詢
        elif user_message == '台指期':
            futures_info = get_futures_info()
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text=format_futures_info(futures_info))]
                )
            )
        # 處理其他訊息
        else:
            await process_message(user_id, user_message, event.reply_token)
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤：{str(e)}", exc_info=True)
        try:
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="抱歉，處理您的請求時發生錯誤，請稍後再試。")]
                )
            )
        except Exception as reply_error:
            logger.error(f"發送錯誤訊息時發生錯誤：{str(reply_error)}")


@app.post("/callback")
async def callback(request: Request):
    if not handler:
        logger.error("LINE Bot handler 尚未初始化")
        return {"status": "error", "message": "LINE Bot 尚未初始化"}

    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()

    try:
        # 直接使用 handler.handle
        handler.handle(body.decode(), signature)
        return {"status": "success"}
    except InvalidSignatureError:
        return {"status": "error", "message": "Invalid signature"}
    except Exception as e:
        logger.error(f"處理 callback 時發生錯誤：{str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


def get_help_message() -> str:
    """
    獲取幫助訊息
    :return: 格式化後的幫助訊息
    """
    return """
投資小幫手使用說明

股票查詢
輸入：查詢 2330
功能：查詢股票即時資訊，包括價格、成交量、本益比等

台指期查詢
輸入：台指期
功能：查詢台指期即時資訊，包括價格、漲跌幅、成交量等

ETF 分析
功能：每月 7 日和 14 日自動推送 ETF 重疊成分股分析

投資諮詢
直接輸入您的投資問題，例如：
- 現在適合買 2330 嗎？
- 0056 的配息情況如何？
- 請分析台積電的技術面

除權息查詢
輸入：除權息 0056
功能：查詢股票的除權息資訊

同類股比較
輸入：比較 2330 2303 2317
功能：比較多檔股票的表現

到價提醒
輸入：提醒 2330 600
功能：設定股票價格提醒（每月限制 2 檔）

其他功能
- 輸入 /help 顯示此說明
- 輸入任何投資相關問題，AI 會為您解答

注意事項
- 每月推播次數有限制
- 資料僅供參考，投資需謹慎
"""


async def show_loading_animation(user_id: str, seconds: int = 60):
    """顯示加載動畫"""
    if not line_bot_api:
        logger.error("LINE Bot API 尚未初始化")
        return

    try:
        await line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(
                chatId=user_id,
                loadingSeconds=seconds
            )
        )
    except Exception as e:
        logger.error(f"顯示加載動畫時發生錯誤：{str(e)}")


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


async def analyze_etf_overlap(etf_codes=None, max_retries=3):
    """
    分析 ETF 重疊成分股
    :param etf_codes: 要分析的 ETF 代碼列表，如果為 None 則分析所有 ETF
    :param max_retries: 最大重試次數
    :return: 包含重疊分析結果的字典
    """
    try:
        # 從資料庫獲取所有 ETF 的成分股資料
        collection = db.get_collection('etf_holdings')
        if etf_codes:
            etfs = collection.find({'etf_code': {'$in': etf_codes}})
        else:
            etfs = collection.find({})

        # 建立 ETF 代碼到成分股的映射
        etf_holdings = {}
        for etf in etfs:
            try:
                etf_holdings[etf['etf_code']] = set(etf['holdings'])
            except Exception as e:
                logger.error(
                    f"處理 ETF {etf.get('etf_code', 'unknown')} 資料時發生錯誤: {str(e)}")
                continue

        if not etf_holdings:
            logger.warning("沒有找到任何 ETF 資料")
            return None

        # 分析重疊情況
        overlap_analysis = {}
        etf_codes = list(etf_holdings.keys())

        for i in range(len(etf_codes)):
            for j in range(i + 1, len(etf_codes)):
                etf1 = etf_codes[i]
                etf2 = etf_codes[j]

                try:
                    # 計算交集
                    common_stocks = etf_holdings[etf1] & etf_holdings[etf2]

                    if common_stocks:
                        overlap_analysis[f"{etf1}-{etf2}"] = {
                            "etf1": etf1,
                            "etf2": etf2,
                            "common_stocks": list(common_stocks),
                            "overlap_ratio": len(common_stocks) / min(len(etf_holdings[etf1]), len(etf_holdings[etf2]))
                        }
                except Exception as e:
                    logger.error(f"分析 ETF {etf1} 和 {etf2} 重疊時發生錯誤: {str(e)}")
                    continue

        return {
            "timestamp": datetime.now(),
            "overlap_stocks": overlap_analysis
        }
    except Exception as e:
        logger.error(f"分析 ETF 重疊時發生錯誤: {str(e)}", exc_info=True)
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


async def send_etf_overlap_analysis(max_retries=3):
    """
    發送 ETF 重疊分析結果給所有使用者
    :param max_retries: 最大重試次數
    """
    try:
        # 獲取所有使用者
        collection = db.get_collection('users')
        users = collection.find({})

        # 分析 ETF 重疊
        analysis = await analyze_etf_overlap()
        if not analysis:
            logger.warning("沒有生成 ETF 重疊分析結果")
            return

        # 格式化分析結果
        message = format_overlap_analysis(analysis['overlap_stocks'])

        # 發送給每個使用者
        for user in users:
            for attempt in range(max_retries):
                try:
                    await line_bot_api.push_message(
                        user['user_id'],
                        TextMessage(text=message)
                    )
                    logger.info(f"成功發送 ETF 重疊分析給使用者 {user['user_id']}")
                    break
                except Exception as e:
                    logger.warning(
                        f"發送 ETF 重疊分析給使用者 {user['user_id']} 失敗 (嘗試 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        logger.error(
                            f"發送 ETF 重疊分析給使用者 {user['user_id']} 最終失敗: {str(e)}")
    except Exception as e:
        logger.error(f"執行 ETF 重疊分析時發生錯誤: {str(e)}", exc_info=True)


def remove_markdown(text: str) -> str:
    """
    移除文字中的 markdown 格式
    :param text: 原始文字
    :return: 移除 markdown 格式後的文字
    """
    # 移除標題
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 移除粗體和斜體
    text = re.sub(r'\*\*|\*|__|_', '', text)
    # 移除連結
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 移除圖片
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    # 移除程式碼區塊
    text = re.sub(r'```[\s\S]*?```', '', text)
    # 移除行內程式碼
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 移除引用
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    # 移除列表符號
    text = re.sub(r'^[\s-]*[-*+]\s+', '', text, flags=re.MULTILINE)
    # 移除表格
    text = re.sub(r'\|.*\|', '', text)
    # 移除多餘的空白行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


async def process_message(user_id, message, reply_token, max_retries=3):
    """處理用戶訊息"""
    try:
        # 顯示載入動畫
        await show_loading_animation(user_id)

        # 記錄查詢
        log_query(user_id, message)

        # 1. 首先處理股票查詢 - 更靈活的匹配方式
        stock_code = None
        # 檢查是否為純數字（可能是股票代碼）
        if message.isdigit() and (len(message) == 4 or len(message) == 5):
            stock_code = message
        # 處理 "查詢2330" 或 "查詢 2330" 的情況
        elif message.startswith('查詢'):
            parts = message.split('查詢')
            if len(parts) > 1:
                # 提取數字
                numbers = re.findall(r'\d+', parts[1])
                if numbers and (len(numbers[0]) == 4 or len(numbers[0]) == 5):
                    stock_code = numbers[0]

        if stock_code:
            # 獲取股票資訊
            stock_info = get_stock_info(stock_code)
            response = format_stock_info(stock_info)

            # 使用 LLM 提供簡短建議，並參考即時股價資訊
            prompt = f"""
            你是一個專業的投資顧問。以下是股票 {stock_code} 的即時資訊：

            {response}

            請根據以上即時資訊，提供一個簡短的投資建議。
            回答時要：
            1. 根據即時股價、漲跌幅、成交量等數據進行分析
            2. 提供簡要建議
            3. 提醒投資風險
            4. 回答要簡短，不要超過 100 字
            5. 不要使用任何格式符號（如 *、#、` 等）

            請用繁體中文回答，語氣要專業且友善。
            """
            advice = gemini.generate_response(prompt)
            # 移除可能的 markdown 格式
            advice = remove_markdown(advice)

            # 合併股票資訊和建議
            full_response = f"{response}\n\n📊 投資建議：\n{advice}"

            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=full_response)]
                )
            )
            return

        # 2. 處理股票分析相關問題
        if any(char.isdigit() for char in message) and ('買' in message or '賣' in message or '分析' in message):
            # 提取股票代碼
            numbers = re.findall(r'\d+', message)
            if numbers and (len(numbers[0]) == 4 or len(numbers[0]) == 5):
                stock_code = numbers[0]
                # 獲取即時股票資訊
                stock_info = get_stock_info(stock_code)
                stock_info_text = format_stock_info(stock_info)

                # 使用 LLM 分析股票，並參考即時資訊
                prompt = f"""
                你是一個專業的投資顧問。以下是股票 {stock_code} 的即時資訊：

                {stock_info_text}

                使用者問了以下問題：
                {message}

                請根據以上即時資訊，分析該股票的投資建議。
                回答時要：
                1. 根據即時股價、漲跌幅、成交量等數據進行分析
                2. 提供具體的投資建議
                3. 提醒投資風險
                4. 回答要簡短，不要超過 200 字
                5. 不要使用任何格式符號（如 *、#、` 等）

                請用繁體中文回答，語氣要專業且友善。
                """
                response = gemini.generate_response(prompt)
                # 移除可能的 markdown 格式
                response = remove_markdown(response)
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=response)]
                    )
                )
                return

        # 3. 處理一般對話
        if not is_investment_related(message):
            # 非投資相關問題，直接使用 AI 回答
            prompt = f"""
            你是一個友善的 AI 助手。使用者問了以下問題：
            {message}

            請用專業且友善的方式回答。
            回答時要：
            1. 保持禮貌和專業
            2. 提供有用的資訊
            3. 如果問題超出你的知識範圍，請禮貌地告知
            4. 回答要簡短，不要超過 200 字
            5. 不要使用任何格式符號（如 *、#、` 等）

            請用繁體中文回答，語氣要友善且專業。
            """
            response = gemini.generate_response(prompt)
            # 移除可能的 markdown 格式
            response = remove_markdown(response)
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=response)]
                )
            )
            return

        # 4. 其他投資相關問題
        prompt = f"""
        你是一個專業的投資顧問。使用者問了以下問題：
        {message}

        請用專業且易懂的方式回答。
        回答時要：
        1. 提供專業的投資建議
        2. 分析可能的風險
        3. 給出具體的建議
        4. 回答要簡短，不要超過 200 字
        5. 不要使用任何格式符號（如 *、#、` 等）

        請用繁體中文回答，語氣要專業且友善。
        """
        response = gemini.generate_response(prompt)
        # 移除可能的 markdown 格式
        response = remove_markdown(response)
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=response)]
            )
        )

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {str(e)}")
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="抱歉，處理您的請求時發生錯誤。請稍後再試。")]
            )
        )


@app.get("/")
async def root():
    try:
        return {"status": "success", "message": "AI 投資導向機器人服務已啟動"}
    except Exception as e:
        logger.error(f"根路由處理錯誤：{str(e)}")
        return {"status": "error", "message": "服務暫時無法使用"}

if __name__ == "__main__":
    # 獲取環境變數中的PORT，如果不存在則使用8000
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"啟動服務 - 主機: 0.0.0.0, 端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
