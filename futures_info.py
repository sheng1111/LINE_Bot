import yfinance as yf
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_futures_info() -> dict:
    """
    獲取台指期資訊
    :return: 期貨資訊字典
    """
    try:
        # 獲取台指期資訊（使用台指期代碼）
        ticker = yf.Ticker("^TWII")  # 先獲取加權指數
        futures_ticker = yf.Ticker("^TWII")  # 台指期

        # 獲取基本信息
        info = ticker.info
        futures_info = futures_ticker.info

        # 獲取當前價格
        current_price = futures_ticker.history(period="1d")["Close"].iloc[-1]

        # 獲取最近一年的歷史數據
        history = futures_ticker.history(period="1y")

        return {
            "name": "台指期",
            "current_price": current_price,
            "day_high": futures_info.get("dayHigh", 0),
            "day_low": futures_info.get("dayLow", 0),
            "volume": futures_info.get("volume", 0),
            "change": futures_info.get("regularMarketChange", 0),
            "change_percent": futures_info.get("regularMarketChangePercent", 0),
            "index_price": info.get("regularMarketPrice", 0),  # 加權指數價格
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"獲取台指期資訊時發生錯誤: {str(e)}")
        return None


def format_futures_info(futures_info: dict) -> str:
    """
    格式化期貨資訊為易讀的字符串
    :param futures_info: 期貨資訊字典
    :return: 格式化後的字符串
    """
    if not futures_info:
        return "無法獲取台指期資訊。"

    change_emoji = "📈" if futures_info['change'] >= 0 else "📉"

    return f"""
📊 {futures_info['name']} 資訊

💰 當前價格: {futures_info['current_price']}
{change_emoji} 漲跌幅: {futures_info['change']} ({futures_info['change_percent']}%)
📈 今日最高: {futures_info['day_high']}
📉 今日最低: {futures_info['day_low']}
📊 成交量: {futures_info['volume']}
📊 加權指數: {futures_info['index_price']}

⏰ 更新時間: {futures_info['last_updated']}
"""
