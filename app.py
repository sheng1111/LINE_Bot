# ======================================================
# LINE Bot 應用程式 - 股票與ETF資訊查詢與分析
# ======================================================

# ======== 導入必要的模組 ========
# FastAPI 相關
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# LINE Bot SDK 相關
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

# 系統與工具模組
import os
import re
import uvicorn
from dotenv import load_dotenv
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 自定義模組
from services.stock_service import stock_service, format_stock_info
from services.etf_service import etf_service
from services.market_service import market_service, format_futures_info
from services.database import db
from services.gemini_client import gemini
from services.stock_analyzer import stock_analyzer
from services.daily_recommender import DailyRecommender
from services.dividend_analyzer import dividend_analyzer
from services.stock_comparator import comparator
from services.twse_api import twse_api
from utils.cache import cache
from utils.logger import logger

# ======== 基本設定 ========
# 載入環境變數
load_dotenv()

# 全域變數宣告
handler = None
line_bot_api = None
scheduler = None
processing_requests = {}

# 投資相關關鍵字
investment_keywords = ['投資', '股票', '基金', 'ETF',
                       '債券', '風險', '報酬', '資產配置', '除權息', '配息', '股利',
                       '提醒', '技術分析', '新聞', '投資組合', '績效', '比較']


# ======== 輔助函數 ========
def is_investment_related(text: str) -> bool:
    """
    判斷文字是否與投資相關
    :param text: 輸入文字
    :return: 是否與投資相關
    """
    return any(keyword in text for keyword in investment_keywords)


# ======== 應用程式生命週期管理 ========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    管理應用程式的生命週期，包括啟動和關閉時的操作
    :param app: FastAPI 應用程式實例
    """
    # 啟動時執行的操作
    global handler, line_bot_api, scheduler
    try:
        # 讀取 LINE Bot 憑證
        channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        channel_secret = os.getenv('LINE_CHANNEL_SECRET')
        if not channel_access_token or not channel_secret:
            raise ValueError("LINE Bot 憑證未設定")

        # 初始化 LINE Bot 客戶端
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

            # 設定 ETF 重疊分析定時任務，每月 7 日和 14 日執行
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

        yield  # 應用程式執行階段

        # 關閉時執行的操作
        if scheduler:
            scheduler.shutdown()
            logger.info("定時任務調度器已關閉")
    except Exception as e:
        logger.error(f"LINE Bot 初始化失敗: {str(e)}")
        raise

# ======== FastAPI 應用程式初始化 ========
app = FastAPI(
    title="LINE Bot 股票資訊助手",
    description="提供股票、ETF查詢和分析服務的 LINE Bot API",
    version="1.1.0",
    lifespan=lifespan
)

# ======== 中間件設定 ========
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    錯誤處理中間件，捕捉並記錄所有請求的異常
    :param request: HTTP 請求
    :param call_next: 下一個處理函數
    :return: HTTP 響應
    """
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"請求處理錯誤: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "伺服器內部錯誤"}
        )

# ======== API 端點 ========
@app.get("/health")
async def health_check():
    """
    健康檢查端點，用於監控服務狀態
    :return: 服務狀態資訊
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ======== LINE Bot 事件處理設定 ========
def register_event_handlers():
    """
    註冊 LINE Bot 事件處理器
    設定各種事件的處理函數
    """
    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event):
        """
        處理文字訊息事件
        :param event: LINE 訊息事件
        """
        # 使用 asyncio 來執行異步函數
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_handle_message_async(event))
        else:
            loop.run_until_complete(_handle_message_async(event))


# ======== 訊息處理函數 ========
async def _handle_message_async(event):
    """
    處理使用者的文字訊息
    :param event: LINE 訊息事件
    """
    try:
        user_message = event.message.text
        user_id = event.source.user_id
        reply_token = event.reply_token
        
        # 記錄查詢
        log_query(user_id, user_message)

        # 顯示載入動畫
        await show_loading_animation(user_id)

        # 分析使用者意圖
        command, params = await _analyze_user_intent(user_message)
        
        # 處理使用者意圖並生成回應
        response = await _process_command(command, params, user_id, reply_token, user_message)
        
        # 確保回應不為空且是字符串
        if not response:
            response = "抱歉，發生未知錯誤，請稍後再試。"
        elif not isinstance(response, str):
            response = str(await response)
            
        # 回覆訊息
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=response)]
            )
        )
        
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {str(e)}")
        try:
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="抱歉，處理您的請求時發生錯誤。請稍後再試。")]
                )
            )
        except Exception as reply_error:
            logger.error(f"回覆錯誤訊息時發生錯誤: {str(reply_error)}")


async def _analyze_user_intent(user_message: str) -> tuple:
    """
    分析使用者意圖
    :param user_message: 使用者訊息
    :return: (指令, 參數)
    """
    # 使用 LLM 判斷使用者意圖
    intent_prompt = f"""
    請分析以下用戶輸入的意圖，並返回對應的指令和參數：

    用戶輸入：{user_message}

    支援的指令類型：
    1. STOCK_QUERY - 單純查詢股票資訊（參數：股票代碼）
    2. STOCK_ANALYSIS - 分析股票（參數：股票代碼）
    3. ETF_ANALYSIS - ETF 分析（參數：ETF代碼）
    4. DIVIDEND_ANALYSIS - 除權息分析（參數：股票代碼）
    5. PEER_COMPARISON - 同類股比較（參數：股票代碼）
    6. FUTURES_INFO - 台指期資訊（無參數）
    7. ETF_OVERLAP - ETF 重疊分析（參數：ETF代碼1,ETF代碼2）
    8. MARKET_NEWS - 市場新聞（無參數）
    9. STOCK_NEWS - 個股新聞（參數：股票代碼）
    10. PRICE_ALERT - 設定提醒（參數：股票代碼 價格）
    11. GENERAL_QUERY - 一般問答（無參數）

    請根據以下規則判斷：
    - 如果只是查詢股票現況（如：2330現在多少錢？），使用 STOCK_QUERY
    - 如果要求分析股票（如：分析台積電的走勢），使用 STOCK_ANALYSIS
    - 如果要求分析 ETF，使用 ETF_ANALYSIS
    - 如果要求除權息資訊，使用 DIVIDEND_ANALYSIS
    - 如果要求比較同類股，使用 PEER_COMPARISON
    - 如果要求台指期資訊，使用 FUTURES_INFO
    - 如果要求 ETF 重疊分析，使用 ETF_OVERLAP
    - 如果要求市場新聞，使用 MARKET_NEWS
    - 如果要求個股新聞，使用 STOCK_NEWS
    - 如果要求價格提醒，使用 PRICE_ALERT
    - 如果無法確定，使用 GENERAL_QUERY

    請只返回如下格式：
    COMMAND:對應指令
    PARAMS:參數（如果有多個參數用逗號分隔）
    """

    # 獲取意圖分析結果
    intent_result = (await gemini.generate_response(intent_prompt)).strip()

    # 解析意圖結果
    command = None
    params = None

    for line in intent_result.split('\n'):
        if line.startswith('COMMAND:'):
            command = line.replace('COMMAND:', '').strip()
        elif line.startswith('PARAMS:'):
            params = line.replace('PARAMS:', '').strip()
            
    return command, params

async def _process_command(command: str, params: str, user_id: str, reply_token: str, user_message: str) -> str:
    """
    處理使用者命令
    :param command: 命令類型
    :param params: 命令參數
    :param user_id: 使用者ID
    :param reply_token: 回覆標記
    :param user_message: 使用者訊息
    :return: 回應訊息
    """
    try:
        # 根據命令類型執行對應功能
        if command == 'STOCK_QUERY' and params:
            return await _handle_stock_query(params)
        elif command == 'STOCK_ANALYSIS' and params:
            return await _handle_stock_analysis(params)
        elif command == 'ETF_ANALYSIS' and params:
            return await _handle_etf_analysis(params)
        elif command == 'DIVIDEND_ANALYSIS' and params:
            return await _handle_dividend_analysis(params)
        elif command == 'PEER_COMPARISON' and params:
            return await _handle_peer_comparison(params)
        elif command == 'FUTURES_INFO':
            return await _handle_futures_info()
        elif command == 'ETF_OVERLAP' and params:
            return await _handle_etf_overlap(params)
        elif command == 'MARKET_NEWS':
            return await _handle_market_news()
        elif command == 'STOCK_NEWS' and params:
            return await _handle_stock_news(params)
        elif command == 'PRICE_ALERT' and params:
            try:
                stock_code, price = params.split()
                target_price = float(price)
                return await _handle_price_alert(stock_code, target_price, user_id)
            except ValueError:
                return "請輸入正確的股票代碼和目標價格，格式：提醒 股票代碼 價格"
        elif command == 'GENERAL_QUERY':
            return await handle_general_query(user_message)
        else:
            # 使用 LLM 處理一般問答
            return await handle_general_query(user_message)
    except Exception as e:
        logger.error(f"處理命令 {command} 時發生錯誤: {str(e)}")
        return f"處理您的請求時發生錯誤。請稍後再試。"

async def handle_general_query(message: str) -> str:
    """處理一般問答查詢
    :param message: 用戶輸入的文字
    :return: AI 的回答
    """
    prompt = f"""
    請回答以下問題：
    {message}

    要求：
    1. 保持友善和專業 
    2. 回答要簡短，不超過 200 字
    3. 如果是投資相關問題，可以提供專業建議
    4. 如果是其他問題，就正常回答
    5. 用繁體中文回答
    """
    response = await gemini.generate_response(prompt)
    return remove_markdown(response)

async def _handle_stock_query(stock_code: str) -> str:
    """
    處理股票查詢
    :param stock_code: 股票代碼
    :return: 回應訊息
    """
    try:
        # 單純查詢股票資訊
        stock_info = stock_service.get_stock_info(stock_code)
        if stock_info and isinstance(stock_info, dict):
            return format_stock_info(stock_info)
        else:
            return f"無法獲取股票 {stock_code} 的資訊，請確認股票代碼是否正確。"
    except Exception as e:
        logger.error(f"獲取股票資訊時發生錯誤：{str(e)}")
        return f"獲取股票 {stock_code} 資訊時發生錯誤，請稍後再試。"

async def _handle_stock_analysis(stock_code: str) -> str:
    """處理股票分析"""
    try:
        stock_info = stock_service.get_stock_info(stock_code)
        if stock_info and 'error' not in stock_info:
            # 使用 LLM 分析股票資料
            analysis_prompt = f"""
            請分析以下股票資料並給出專業的見解：
            {format_stock_info(stock_info)}

            請用通俗易懂的語言總結重要資訊，並給出簡短的分析。
            """
            analysis = await gemini.generate_response(analysis_prompt)
            return f"{format_stock_info(stock_info)}\n\n分析：\n{analysis}"
        else:
            error_msg = stock_info.get('error', '無法獲取該股票資訊') if stock_info else '無法獲取該股票資訊'
            return f"抱歉，{error_msg}。"
    except Exception as e:
        logger.error(f"分析股票時發生錯誤：{str(e)}")
        return f"分析股票 {stock_code} 時發生錯誤，請稍後再試。"

async def _handle_etf_analysis(etf_code: str) -> str:
    """處理 ETF 分析"""
    try:
        analysis = etf_service.analyze_etf(etf_code)
        if analysis:
            return analysis
        return f"無法分析 ETF {etf_code}，請確認代碼是否正確。"
    except Exception as e:
        logger.error(f"分析 ETF 時發生錯誤：{str(e)}")
        return f"分析 ETF {etf_code} 時發生錯誤，請稍後再試。"

async def _handle_dividend_analysis(stock_code: str) -> str:
    """處理除權息分析"""
    try:
        analysis = dividend_analyzer.analyze_dividend(stock_code)
        if analysis:
            return analysis
        return f"無法獲取 {stock_code} 的除權息資訊，請確認代碼是否正確。"
    except Exception as e:
        logger.error(f"分析除權息時發生錯誤：{str(e)}")
        return f"分析 {stock_code} 的除權息資訊時發生錯誤，請稍後再試。"

async def _handle_peer_comparison(stock_code: str) -> str:
    """處理同類股比較"""
    try:
        comparison = comparator.compare_stocks(stock_code)
        if comparison:
            return comparison
        return f"無法進行 {stock_code} 的同類股比較，請確認代碼是否正確。"
    except Exception as e:
        logger.error(f"進行同類股比較時發生錯誤：{str(e)}")
        return f"比較 {stock_code} 的同類股時發生錯誤，請稍後再試。"

async def _handle_futures_info() -> str:
    """處理台指期資訊"""
    try:
        info = market_service.get_futures_info()
        if info:
            return format_futures_info(info)
        return "無法獲取台指期資訊。"
    except Exception as e:
        logger.error(f"獲取台指期資訊時發生錯誤：{str(e)}")
        return "獲取台指期資訊時發生錯誤，請稍後再試。"

async def _handle_etf_overlap(params: str) -> str:
    """處理 ETF 重疊分析"""
    try:
        etf_codes = params.split()
        if len(etf_codes) != 2:
            return "請提供兩個 ETF 代碼進行比較。"
            
        analysis = await analyze_etf_overlap(etf_codes)
        if analysis:
            return format_overlap_analysis(analysis)
        return "無法進行 ETF 重疊分析，請確認代碼是否正確。"
    except Exception as e:
        logger.error(f"進行 ETF 重疊分析時發生錯誤：{str(e)}")
        return "進行 ETF 重疊分析時發生錯誤，請稍後再試。"

async def _handle_market_news() -> str:
    """處理市場新聞"""
    try:
        news = twse_api.get_market_news()
        if news:
            response = "📰 最新市場新聞：\n\n"
            for i, item in enumerate(news[:5], 1):
                response += f"{i}. {item['title']}\n"
                response += f"   {item['date']}\n\n"
            return response
        return "目前沒有最新市場新聞。"
    except Exception as e:
        logger.error(f"獲取市場新聞時發生錯誤：{str(e)}")
        return "獲取市場新聞時發生錯誤，請稍後再試。"

async def _handle_stock_news(stock_code: str) -> str:
    """處理個股新聞"""
    try:
        news = twse_api.get_stock_news(stock_code)
        if news:
            response = f"📰 {stock_code} 相關新聞：\n\n"
            for i, item in enumerate(news[:5], 1):
                response += f"{i}. {item['title']}\n"
                response += f"   {item['date']}\n\n"
            return response
        return f"目前沒有 {stock_code} 的相關新聞。"
    except Exception as e:
        logger.error(f"獲取個股新聞時發生錯誤：{str(e)}")
        return f"獲取 {stock_code} 的新聞時發生錯誤，請稍後再試。"

async def _handle_price_alert(stock_code: str, target_price: float, user_id: str) -> str:
    """處理股價提醒設定"""
    try:
        # 檢查用戶當月提醒設定數量
        alerts_collection = db.get_collection('price_alerts')
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        user_alerts = alerts_collection.count_documents({
            'user_id': user_id,
            'created_at': {'$gte': current_month}
        })
        
        if user_alerts >= 2:
            return "您本月已達到設定提醒的上限（2個），請下月再試。"
            
        # 新增提醒設定
        alerts_collection.insert_one({
            'user_id': user_id,
            'stock_code': stock_code,
            'target_price': target_price,
            'created_at': datetime.now(),
            'status': 'active'
        })
        
        return f"已設定 {stock_code} 的價格提醒：{target_price} 元"
    except Exception as e:
        logger.error(f"設定價格提醒時發生錯誤：{str(e)}")
        return "設定價格提醒時發生錯誤，請稍後再試。"

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

        for i in len(etf_codes):
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

        # 定義要分析的熱門 ETF
        popular_etfs = ['0050', '0056', '00878', '00881', '00891']
        
        # 使用 ETFAnalyzer 的新方法直接從網路獲取最新的 ETF 成分股資料
        logger.info("開始獲取最新的 ETF 成分股資料")
        analysis = etf_service.analyze_etf_overlap(popular_etfs)
        
        # Check if analysis exists and has overlap_stocks
        if not analysis or not analysis.get('overlap_stocks'):
            logger.warning("沒有生成 ETF 重疊分析結果或沒有重疊股票")
            return

        # 格式化分析結果
        message = etf_service.format_overlap_analysis(analysis)
        logger.info(f"已生成 ETF 重疊分析結果，找到 {len(analysis['overlap_stocks'])} 個重疊股票")

        # 發送給每個使用者
        user_count = 0
        for user in users:
            user_count += 1
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
        
        logger.info(f"已完成 ETF 重疊分析通知發送，共發送給 {user_count} 個用戶")
    except Exception as e:
        logger.error(f"執行 ETF 重疊分析時發生錯誤: {str(e)}", exc_info=True)


def remove_markdown(text: str) -> str:
    """
    移除文字中的 markdown 格式
    :param text: 原始文字
    :return: 移除 markdown 格式後的文字
    """
    if not text:
        return ""
        
    # 移除標題
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 移除粗體和斜體 (更全面的模式)
    text = re.sub(r'(\*\*|\*|__|_)([^*_]+)(\*\*|\*|__|_)', r'\2', text)
    # 再次檢查任何剩餘的標記
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
    # 移除列表符號 (更全面的模式)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
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

        # 1. 處理簡單問候語
        greetings = ['hi', 'hello', '你好', '哈囉', '嗨']
        # Check greeting messages
        if message.lower() in greetings or any(greeting in message.lower() for greeting in greetings):
            response = "你好！我是一個 AI 助手，很高興為您服務！我擅長投資理財相關的諮詢，但也可以回答其他問題。"
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=response)]
                )
            )
            return

        # 2. 使用第一個 LLM 僅進行意圖分析
        intent_prompt = f"""
        請分析以下用戶輸入的意圖，僅返回對應的指令和參數，不需要其他解釋：
        {message}

        支援的指令類型：
        1. STOCK_QUERY - 查詢股票資訊（參數：股票代碼）
        2. STOCK_ANALYSIS - 股票分析（參數：股票代碼）
        3. TECHNICAL_ANALYSIS - 技術分析（參數：股票代碼）
        4. ETF_QUERY - 查詢 ETF 資訊（參數：ETF代碼）
        5. ETF_OVERLAP - ETF 重疊分析（參數：ETF代碼1 ETF代碼2）
        6. MARKET_NEWS - 查看市場新聞（無參數）
        7. MARKET_RANKING - 查看市場排行（無參數）
        8. CHIP_ANALYSIS - 籌碼分析（參數：股票代碼）
        9. PRICE_ALERT - 設定提醒（參數：股票代碼 價格）
        10. GENERAL_QUERY - 一般問答（無參數）

        請根據以下規則判斷：
        - 如果只是查詢股票現況，使用 STOCK_QUERY
        - 如果要求分析股票，使用 STOCK_ANALYSIS
        - 如果要求技術分析，使用 TECHNICAL_ANALYSIS
        - 如果查詢 ETF 資訊，使用 ETF_QUERY
        - 如果要求 ETF 重疊分析，使用 ETF_OVERLAP
        - 如果無法確定，使用 GENERAL_QUERY

        請只返回如下格式：
        COMMAND:對應指令
        PARAMS:參數（如果有多個參數用空格分隔）
        """

        # 獲取意圖分析結果
        intent_result = (await gemini.generate_response(intent_prompt)).strip()

        # 解析意圖結果
        command = None
        params = None

        for line in intent_result.split('\n'):
            if line.startswith('COMMAND:'):
                command = line.replace('COMMAND:', '').strip()
            elif line.startswith('PARAMS:'):
                params = line.replace('PARAMS:', '').strip()

        # 3. 根據意圖執行對應功能
        if command:
            if command == 'STOCK_QUERY' and params:
                # 處理股票查詢
                # 確保股票代碼格式正確
                stock_code = params.strip().replace('.', '')
                logger.info(f"處理股票查詢: {stock_code}")
                
                try:
                    # 獲取股票資訊
                    stock_info = stock_service.get_stock_info(stock_code)
                    
                    if stock_info and isinstance(stock_info, dict) and 'error' not in stock_info:
                        response = format_stock_info(stock_info)
                    else:
                        error_msg = stock_info.get('error', '無法獲取該股票資訊') if stock_info else '無法獲取該股票資訊'
                        logger.error(f"股票查詢錯誤: {error_msg}")
                        response = f"抱歉，{error_msg}。"
                except Exception as e:
                    logger.error(f"獲取股票資訊時發生錯誤：{str(e)}")
                    response = f"獲取股票 {stock_code} 資訊時發生錯誤，請稍後再試。"

            elif command == 'STOCK_ANALYSIS' and params:
                # 處理股票分析
                try:
                    stock_info = stock_service.get_stock_info(params)
                    if stock_info and 'error' not in stock_info:
                        # 使用 LLM 分析股票資料
                        analysis_prompt = f"""
                        請分析以下股票資料並給出專業的見解：
                        {format_stock_info(stock_info)}

                        請用通俗易懂的語言總結重要資訊，並給出簡短的分析。
                        """
                        analysis = await gemini.generate_response(analysis_prompt)
                        response = f"{format_stock_info(stock_info)}\n\n分析：\n{analysis}"
                    else:
                        error_msg = stock_info.get('error', '無法獲取該股票資訊') if stock_info else '無法獲取該股票資訊'
                        response = f"抱歉，{error_msg}。"
                except Exception as e:
                    logger.error(f"分析股票時發生錯誤：{str(e)}")
                    response = f"分析股票 {params} 時發生錯誤，請稍後再試。"

            elif command == 'TECHNICAL_ANALYSIS' and params:
                # 處理技術分析
                tech_data = twse_api.calculate_technical_indicators(params)
                if tech_data:
                    response = f"【{params} 技術分析】\n\n"
                    response += f"5日均線: {tech_data['ma5'][-1]:.2f}\n"
                    response += f"10日均線: {tech_data['ma10'][-1]:.2f}\n"
                    response += f"20日均線: {tech_data['ma20'][-1]:.2f}\n"
                    response += f"KD值: K={tech_data['kd']['k'][-1]:.2f}, D={tech_data['kd']['d'][-1]:.2f}\n"
                    response += f"RSI: {tech_data['rsi'][-1]:.2f}\n"

                    # 加入趨勢判斷
                    ma5 = tech_data['ma5'][-1]
                    ma20 = tech_data['ma20'][-1]
                    k = tech_data['kd']['k'][-1]
                    d = tech_data['kd']['d'][-1]
                    rsi = tech_data['rsi'][-1]

                    response += "\n趨勢分析：\n"
                    if ma5 > ma20:
                        response += "- 短期均線突破長期均線，呈現上升趨勢\n"
                    elif ma5 < ma20:
                        response += "- 短期均線跌破長期均線，呈現下降趨勢\n"

                    if k > d:
                        response += "- KD 指標顯示可能處於超買區\n"
                    elif k < d:
                        response += "- KD 指標顯示可能處於超賣區\n"

                    if rsi > 70:
                        response += "- RSI 指標顯示可能處於超買區\n"
                    elif rsi < 30:
                        response += "- RSI 指標顯示可能處於超賣區\n"
                else:
                    response = "抱歉，無法獲取技術分析資料。"

            elif command == 'ETF_QUERY' and params:
                # 處理 ETF 查詢
                # 使用原始 ETF 代碼，不需要轉換格式
                etf_code = params.strip().replace('.', '')
                logger.info(f"處理 ETF 查詢: {etf_code}")
                
                try:
                    # 使用 stock_service 獲取 ETF 資訊
                    etf_info = stock_service.get_stock_info(etf_code)
                    
                    if etf_info and isinstance(etf_info, dict) and 'error' not in etf_info:
                        response = format_stock_info(etf_info)
                    else:
                        error_msg = etf_info.get('error', f"無法獲取 ETF {etf_code} 的資訊") if etf_info else f"無法獲取 ETF {etf_code} 的資訊"
                        logger.error(f"ETF 查詢錯誤: {error_msg}")
                        response = f"抱歉，{error_msg}。"
                except Exception as e:
                    logger.error(f"獲取 ETF 資訊時發生錯誤：{str(e)}")
                    response = f"獲取 ETF {etf_code} 資訊時發生錯誤，請稍後再試。"
            
            elif command == 'ETF_OVERLAP' and params:
                # 處理 ETF 重疊分析
                etf_codes = params.split()
                if len(etf_codes) == 2:
                    # 清理 ETF 代碼
                    etf_code1 = etf_codes[0].strip().replace('.', '')
                    etf_code2 = etf_codes[1].strip().replace('.', '')
                    logger.info(f"處理 ETF 重疊分析: {etf_code1} 和 {etf_code2}")
                    
                    try:
                        # 使用 etf_service 獲取 ETF 成分股資料
                        holdings1 = etf_service.get_etf_holdings(etf_code1)
                        holdings2 = etf_service.get_etf_holdings(etf_code2)
                        
                        # Check ETF holdings data
                        if (holdings1 and holdings2 and 
                            isinstance(holdings1, list) and 
                            isinstance(holdings2, list)):
                            # 計算重疊成分股
                            overlap = set(holdings1) & set(holdings2)

                            response = f"【{etf_code1} 和 {etf_code2} 重疊分析】\n\n"
                            response += f"重疊成分股數量：{len(overlap)}\n\n"
                            
                            if overlap:
                                response += "重疊成分股：\n"
                                for stock in sorted(overlap):
                                    response += f"- {stock}\n"

                                # 計算重疊率
                                overlap_ratio = len(overlap) / min(len(holdings1), len(holdings2))
                                response += f"\n重疊率：{overlap_ratio:.2%}"
                            else:
                                response += "这兩個 ETF 沒有重疊的成分股。"
                        else:
                            logger.error(f"無法獲取 ETF 成分股: {etf_code1} 或 {etf_code2}")
                            response = f"抱歉，無法獲取 ETF {etf_code1} 或 {etf_code2} 的成分股資料。"
                    except Exception as e:
                        logger.error(f"分析 ETF 重疊時發生錯誤：{str(e)}")
                        response = f"分析 ETF {etf_code1} 和 {etf_code2} 重疊時發生錯誤，請稍後再試。"
                else:
                    response = "請提供兩個 ETF 代碼進行比較。"

            elif command == 'MARKET_NEWS':
                news = twse_api.get_market_news()
                if news:
                    response = "市場重要新聞：\n\n"
                    for i, item in enumerate(news[:5], 1):
                        response += f"{i}. {item['title']}\n"
                        response += f"   {item['date']}\n\n"
                else:
                    response = "目前沒有最新新聞。"

            elif command == 'MARKET_RANKING':
                rankings = twse_api.get_stock_ranking()
                if rankings:
                    response = "市場排行：\n\n"
                    response += "成交量排行：\n"
                    for i, stock in enumerate(rankings.get('volume', [])[:5], 1):
                        response += f"{i}. {stock['code']} {stock['name']} {stock['volume']:,}\n"
                else:
                    response = "無法獲取市場排行資訊。"

            elif command == 'GENERAL_QUERY':
                response = await handle_general_query(message)
            else:
                # 其他命令暫未實現，使用一般問答處理
                response = await handle_general_query(message)
        else:
            # 如果無法判斷意圖，使用一般問答處理
            response = await handle_general_query(message)

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
