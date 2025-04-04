import yfinance as yf
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_stock_info(stock_code: str) -> dict:
    """
    获取股票信息
    :param stock_code: 股票代码
    :return: 股票信息字典
    """
    try:
        # 添加 .TW 后缀以获取台湾股票信息
        ticker = yf.Ticker(f"{stock_code}.TW")

        # 获取基本信息
        info = ticker.info
        if not info:
            logger.warning(f"无法获取股票 {stock_code} 的基本信息")
            return {}

        # 获取当前价格
        history = ticker.history(period="1d")
        if history.empty:
            logger.warning(f"无法获取股票 {stock_code} 的历史数据")
            return {}

        current_price = history["Close"].iloc[-1]

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
        logger.error(f"获取股票 {stock_code} 信息时发生错误: {str(e)}")
        return {}  # 返回空字典而不是 None


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
