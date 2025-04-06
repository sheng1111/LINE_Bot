import logging
from datetime import datetime
import requests
import time
from twse_api import TWSEAPI

logger = logging.getLogger(__name__)

# 台灣證交所 API 設定
TWSE_API_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
twse_api = TWSEAPI()


def get_stock_info(stock_code: str) -> dict:
    """
    獲取股票即時資訊
    :param stock_code: 股票代碼
    :return: 股票資訊字典
    """
    try:
        # 檢查股票代碼是否有效
        if not stock_code.isdigit() or len(stock_code) != 4:
            logger.error(f"無效的股票代碼格式：{stock_code}")
            return {'error': f'無效的股票代碼格式：{stock_code}'}

        # 獲取股票資訊
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

        if not isinstance(data, dict) or 'msgArray' not in data or not data['msgArray']:
            logger.error(f"API 返回的資料格式不正確：{data}")
            return {'error': 'API 返回的資料格式不正確'}

        if len(data['msgArray']) == 0:
            logger.error(f"無法獲取股票 {stock_code} 資訊")
            return {'error': f'無法獲取股票 {stock_code} 資訊'}

        stock_data = data['msgArray'][0]

        def safe_float(value, default=0):
            try:
                return float(value) if value != '-' else default
            except (ValueError, TypeError):
                return default

        # 確保 stock_data 是字典類型
        if not isinstance(stock_data, dict):
            logger.error(f"API 返回的股票資料不是字典類型：{type(stock_data).__name__}")
            return {'error': f'無法解析股票 {stock_code} 資訊'}
            
        # 確保所有必要的欄位都存在
        required_fields = ['c', 'n', 'z', 'y', 'v', 'h', 'l', 'o']
        for field in required_fields:
            if field not in stock_data:
                stock_data[field] = '0'

        # 計算漲跌
        current_price = safe_float(stock_data.get('z', 0))
        yesterday_price = safe_float(stock_data.get('y', 0))
        change = current_price - yesterday_price
        change_percent = (change / yesterday_price *
                          100) if yesterday_price > 0 else 0

        # 安全地獲取其他資訊
        # 安全地獲取其他資訊，確保返回字典類型
        fundamental = {}
        technical = {}
        institutional = {}
        margin = {}
        
        try:
            # 獲取基本面資料
            fundamental_data = twse_api.get_stock_fundamental(stock_code)
            if isinstance(fundamental_data, dict):
                fundamental = fundamental_data
            else:
                logger.warning(f"基本面資料不是字典類型: {type(fundamental_data).__name__}")
        except Exception as e:
            logger.warning(f"獲取基本面資料失敗: {str(e)}")

        try:
            # 獲取技術指標
            technical_data = twse_api.calculate_technical_indicators(stock_code)
            if isinstance(technical_data, dict):
                technical = technical_data
            else:
                logger.warning(f"技術指標不是字典類型: {type(technical_data).__name__}")
        except Exception as e:
            logger.warning(f"獲取技術指標失敗: {str(e)}")

        try:
            # 獲取法人買賣超
            institutional_data = twse_api.get_institutional_investors(stock_code)
            if isinstance(institutional_data, dict):
                institutional = institutional_data
            else:
                logger.warning(f"法人買賣超不是字典類型: {type(institutional_data).__name__}")
        except Exception as e:
            logger.warning(f"獲取法人買賣超失敗: {str(e)}")

        try:
            # 獲取融資融券
            margin_data = twse_api.get_margin_trading(stock_code)
            if isinstance(margin_data, dict):
                margin = margin_data
            else:
                logger.warning(f"融資融券不是字典類型: {type(margin_data).__name__}")
        except Exception as e:
            logger.warning(f"獲取融資融券失敗: {str(e)}")

        return {
            "code": stock_code,
            "name": stock_data.get('n', ''),
            "price": current_price,
            "change": change,
            "change_percent": change_percent,
            "volume": int(safe_float(stock_data.get('v', 0))),
            "high": safe_float(stock_data.get('h', 0)),
            "low": safe_float(stock_data.get('l', 0)),
            "open": safe_float(stock_data.get('o', 0)),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": stock_data.get('s', '正常交易'),
            "fundamental": fundamental,
            "technical": technical,
            "institutional": institutional,
            "margin": margin
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生網路錯誤: {str(e)}")
        return {'error': f'網路錯誤：{str(e)}'}
    except Exception as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
        return {'error': f'系統錯誤：{str(e)}'}


def format_stock_info(stock_info: dict) -> str:
    """
    格式化股票資訊為易讀的字符串
    """
    if not stock_info:
        return "無法獲取股票資訊，請確認股票代碼是否正確。"
    
    if 'error' in stock_info:
        return f"獲取股票資訊時發生錯誤：{stock_info['error']}"

    # 基本資訊
    message = f"""
{stock_info['name']} 股票資訊

當前價格: {stock_info['price']}
漲跌幅: {stock_info['change']} ({stock_info['change_percent']:.2f}%)
今日最高: {stock_info['high']}
今日最低: {stock_info['low']}
成交量: {stock_info['volume']:,}
更新時間: {stock_info['last_updated']}
"""

    # 基本面資訊
    if stock_info.get('fundamental'):
        fundamental = stock_info['fundamental']
        message += f"""
基本面分析
本益比: {fundamental.get('pe_ratio', 'N/A')}
殖利率: {fundamental.get('dividend_yield', 'N/A')}%
每股盈餘: {fundamental.get('eps', 'N/A')}
"""

    # 技術指標
    if stock_info.get('technical'):
        technical = stock_info['technical']
        message += f"""
技術分析
MA5: {technical['ma5'][-1]:.2f}
MA10: {technical['ma10'][-1]:.2f}
MA20: {technical['ma20'][-1]:.2f}
KD: K={technical['kd']['k'][-1]:.2f} D={technical['kd']['d'][-1]:.2f}
RSI: {technical['rsi'][-1]:.2f}
"""

    # 法人買賣超
    if stock_info.get('institutional'):
        institutional = stock_info['institutional']
        message += f"""
法人買賣超
外資: {institutional.get('foreign', 'N/A')}
投信: {institutional.get('investment_trust', 'N/A')}
自營商: {institutional.get('dealer', 'N/A')}
"""

    # 融資融券
    if stock_info.get('margin'):
        margin = stock_info['margin']
        message += f"""
融資融券
融資餘額: {margin.get('margin_balance', 'N/A')}
融券餘額: {margin.get('short_balance', 'N/A')}
"""

    return message


def get_market_summary() -> str:
    """
    獲取市場概況
    """
    try:
        market_data = twse_api.get_market_index()
        if not market_data:
            return "無法獲取市場資訊"

        # 格式化市場資訊
        message = "📊 市場概況\n\n"

        for index in market_data:
            if index['code'] == 'TAIEX':  # 加權指數
                message += f"加權指數: {index['close']} ({index['change']} {index['change_percent']}%)\n"
            elif index['code'] == 'TPEX':  # 櫃買指數
                message += f"櫃買指數: {index['close']} ({index['change']} {index['change_percent']}%)\n"

        # 獲取市場成交資訊
        turnover = twse_api.get_market_turnover()
        if turnover:
            message += f"\n📈 市場成交\n"
            message += f"成交金額: {turnover.get('total_amount', 'N/A')}\n"
            message += f"成交股數: {turnover.get('total_volume', 'N/A')}\n"

        return message
    except Exception as e:
        logger.error(f"獲取市場概況時發生錯誤: {str(e)}")
        return "無法獲取市場資訊"
