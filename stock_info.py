import logging
from datetime import datetime
import requests
import time

logger = logging.getLogger(__name__)

# 台灣證交所 API 設定
TWSE_API_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def get_stock_info(stock_code: str) -> dict:
    """
    從台灣證券交易所獲取股票資訊
    """
    try:
        url = f"{TWSE_API_URL}?ex_ch=tse_{stock_code}.tw"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Referer': 'https://mis.twse.com.tw/stock/index.jsp'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'msgArray' in data and len(data['msgArray']) > 0:
            stock_data = data['msgArray'][0]

            # 計算漲跌
            current_price = float(stock_data.get('z', 0))
            yesterday_price = float(stock_data.get('y', 0))
            change = current_price - yesterday_price
            change_percent = (change / yesterday_price *
                              100) if yesterday_price > 0 else 0

            return {
                "name": stock_data.get('n', '未知'),
                "current_price": current_price,
                "yesterday_price": yesterday_price,
                "day_high": float(stock_data.get('h', 0)),
                "day_low": float(stock_data.get('l', 0)),
                "volume": int(stock_data.get('v', 0)),
                "change": change,
                "change_percent": change_percent,
                "open_price": float(stock_data.get('o', 0)),
                "trading_value": float(stock_data.get('tv', 0)),  # 成交金額
                "trading_volume": int(stock_data.get('v', 0)),    # 成交股數
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": stock_data.get('s', '正常交易')  # 交易狀態
            }
        else:
            logger.error(f"無法從證交所獲取股票 {stock_code} 的資訊")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生網路錯誤: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
        return None


def format_stock_info(stock_info: dict) -> str:
    """
    格式化股票資訊為易讀的字符串
    """
    if not stock_info:
        return "無法獲取股票資訊，請確認股票代碼是否正確。"

    change_emoji = "📈" if stock_info['change'] >= 0 else "📉"

    return f"""
📊 {stock_info['name']} 股票資訊

💰 當前價格: {stock_info['current_price']}
{change_emoji} 漲跌幅: {stock_info['change']} ({stock_info['change_percent']:.2f}%)
📈 今日最高: {stock_info['day_high']}
📉 今日最低: {stock_info['day_low']}
📊 成交量: {stock_info['volume']:,}
💰 成交金額: {stock_info['trading_value']:,.0f}
⏰ 更新時間: {stock_info['last_updated']}
"""
