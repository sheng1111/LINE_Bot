import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# 台灣證交所 API 設定
TWSE_API_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def get_futures_info() -> dict:
    """
    獲取台指期資訊
    :return: 期貨資訊字典
    """
    try:
        # 獲取台指期資訊
        url = f"{TWSE_API_URL}?ex_ch=tse_TX00.tw"
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
            futures_data = data['msgArray'][0]

            def safe_float(value, default=0):
                try:
                    return float(value) if value != '-' else default
                except (ValueError, TypeError):
                    return default

            # 計算漲跌
            current_price = safe_float(futures_data.get('z', 0))
            yesterday_price = safe_float(futures_data.get('y', 0))
            change = current_price - yesterday_price
            change_percent = (change / yesterday_price *
                              100) if yesterday_price > 0 else 0

            return {
                "name": "台指期",
                "current_price": current_price,
                "yesterday_price": yesterday_price,
                "day_high": safe_float(futures_data.get('h', 0)),
                "day_low": safe_float(futures_data.get('l', 0)),
                "volume": int(safe_float(futures_data.get('v', 0))),
                "change": change,
                "change_percent": change_percent,
                "open_price": safe_float(futures_data.get('o', 0)),
                "trading_value": safe_float(futures_data.get('tv', 0)),  # 成交金額
                # 成交口數
                "trading_volume": int(safe_float(futures_data.get('v', 0))),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": futures_data.get('s', '正常交易'),  # 交易狀態
                # 結算價
                "settlement_price": safe_float(futures_data.get('u', 0)),
                "bid_price": safe_float(futures_data.get('b', 0)),  # 買價
                "ask_price": safe_float(futures_data.get('a', 0))   # 賣價
            }
        else:
            logger.error("無法從證交所獲取台指期資訊")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"從證交所獲取台指期資訊時發生網路錯誤: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"從證交所獲取台指期資訊時發生錯誤: {str(e)}")
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
{change_emoji} 漲跌幅: {futures_info['change']} ({futures_info['change_percent']:.2f}%)
📈 今日最高: {futures_info['day_high']}
📉 今日最低: {futures_info['day_low']}
📊 成交量: {futures_info['volume']:,}
💰 成交金額: {futures_info['trading_value']:,.0f}
📊 成交口數: {futures_info['trading_volume']:,}
💰 結算價: {futures_info['settlement_price']}
💰 買價: {futures_info['bid_price']}
💰 賣價: {futures_info['ask_price']}

⏰ 更新時間: {futures_info['last_updated']}
"""
