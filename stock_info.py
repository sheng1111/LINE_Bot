import yfinance as yf
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_stock_info(stock_code: str) -> dict:
    """
    獲取股票資訊
    :param stock_code: 股票代碼
    :return: 股票資訊字典
    """
    try:
        # 添加 .TW 後綴以獲取台灣股票資訊
        ticker = yf.Ticker(f"{stock_code}.TW")

        # 獲取基本信息
        info = ticker.info

        # 獲取當前價格
        current_price = ticker.history(period="1d")["Close"].iloc[-1]

        # 獲取最近一年的歷史數據
        history = ticker.history(period="1y")

        return {
            "name": info.get("longName", "未知"),
            "current_price": current_price,
            "day_high": info.get("dayHigh", 0),
            "day_low": info.get("dayLow", 0),
            "volume": info.get("volume", 0),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "dividend_yield": info.get("dividendYield", 0),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
        return None


def format_stock_info(stock_info: dict) -> str:
    """
    格式化股票資訊為易讀的字符串
    :param stock_info: 股票資訊字典
    :return: 格式化後的字符串
    """
    if not stock_info:
        return "無法獲取股票資訊，請確認股票代碼是否正確。"

    return f"""
📊 {stock_info['name']} 股票資訊

💰 當前價格: {stock_info['current_price']}
📈 今日最高: {stock_info['day_high']}
📉 今日最低: {stock_info['day_low']}
📊 成交量: {stock_info['volume']}
💵 市值: {stock_info['market_cap']}
📊 本益比: {stock_info['pe_ratio']}
💰 殖利率: {stock_info['dividend_yield']}%

⏰ 更新時間: {stock_info['last_updated']}
"""
