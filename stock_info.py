import yfinance as yf
import logging
from datetime import datetime
import requests
import time

logger = logging.getLogger(__name__)


def get_stock_info_twse(stock_code: str) -> dict:
    """
    從台灣證券交易所獲取股票資訊
    """
    try:
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_code}.tw"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        data = response.json()

        if 'msgArray' in data and len(data['msgArray']) > 0:
            stock_data = data['msgArray'][0]
            return {
                "name": stock_data.get('n', '未知'),
                "current_price": float(stock_data.get('z', 0)),
                "day_high": float(stock_data.get('h', 0)),
                "day_low": float(stock_data.get('l', 0)),
                "volume": int(stock_data.get('v', 0)),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
        return None


def get_stock_info(stock_code: str) -> dict:
    """
    獲取股票資訊，先嘗試使用 yfinance，如果失敗則使用證交所 API
    """
    try:
        # 先嘗試使用 yfinance
        ticker = yf.Ticker(f"{stock_code}.TW")
        info = ticker.info

        if info and len(info) > 0:
            history = ticker.history(period="1d")
            if not history.empty:
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

        # 如果 yfinance 獲取失敗，嘗試使用證交所 API
        logger.info(f"使用證交所 API 獲取股票 {stock_code} 資訊")
        return get_stock_info_twse(stock_code)

    except Exception as e:
        logger.error(f"獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
        # 如果 yfinance 失敗，嘗試使用證交所 API
        try:
            return get_stock_info_twse(stock_code)
        except Exception as e2:
            logger.error(f"所有方法獲取股票 {stock_code} 資訊均失敗: {str(e2)}")
            return None


def format_stock_info(stock_info: dict) -> str:
    """
    格式化股票資訊為易讀的字符串
    """
    if not stock_info:
        return "無法獲取股票資訊，請確認股票代碼是否正確。"

    # 移除 markdown 格式，使用純文字
    return f"""
{stock_info['name']} 股票資訊

當前價格: {stock_info['current_price']}
今日最高: {stock_info['day_high']}
今日最低: {stock_info['day_low']}
成交量: {stock_info['volume']}
市值: {stock_info.get('market_cap', '無資料')}
本益比: {stock_info.get('pe_ratio', '無資料')}
殖利率: {stock_info.get('dividend_yield', '無資料')}%

更新時間: {stock_info['last_updated']}
"""
