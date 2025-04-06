import logging
from datetime import datetime
import requests
import time
from twse_api import TWSEAPI

logger = logging.getLogger(__name__)

# 台灣證交所 API 設定
TWSE_API_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
twse_api = TWSEAPI()


def get_etf_basic_info(etf_code: str) -> dict:
    """
    獲取ETF的基本資訊，使用直接的API請求而不進行複雜處理
    :param etf_code: ETF代碼
    :return: ETF基本資訊字典
    """
    try:
        # 對於ETF使用證交所API
        url = f"{TWSE_API_URL}?ex_ch=tse_{etf_code}.tw"
        logger.info(f"請求ETF資訊 URL: {url}")
        
        # 簡化的headers
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {'error': f'無法獲取ETF {etf_code} 資訊，狀態碼: {response.status_code}'}
        
        # 嘗試解析JSON
        try:
            data = response.json()
        except Exception as e:
            return {'error': f'無法解析ETF {etf_code} 資訊回應: {str(e)}'}
        
        # 檢查是否有資料
        if not data or 'msgArray' not in data or not data['msgArray']:
            return {'error': f'無法獲取ETF {etf_code} 資訊，回應中無資料'}
            
        # 取得ETF資料
        etf_data = data['msgArray'][0]
        
        # 安全地轉換數字
        def safe_float(value, default=0.0):
            if not value or value == '-':
                return default
            try:
                return float(value)
            except:
                return default
                
        # 取得基本價格資訊
        price = safe_float(etf_data.get('z', 0))
        prev_price = safe_float(etf_data.get('y', 0))
        change = price - prev_price
        change_percent = (change / prev_price * 100) if prev_price > 0 else 0
        
        # 建立基本資訊字典
        basic_info = {
            'code': etf_code,
            'name': etf_data.get('n', ''),
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'volume': int(safe_float(etf_data.get('v', 0))),
            'high': safe_float(etf_data.get('h', 0)),
            'low': safe_float(etf_data.get('l', 0)),
            'open': safe_float(etf_data.get('o', 0)),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return basic_info
        
    except Exception as e:
        logger.error(f"獲取ETF {etf_code} 資訊時發生錯誤: {str(e)}")
        return {'error': f'系統錯誤: {str(e)}'}


def get_stock_info(stock_code: str) -> dict:
    """
    獲取股票或ETF即時資訊
    :param stock_code: 股票或ETF代碼
    :return: 股票或ETF資訊字典
    """
    try:
        # 檢查代碼是否有效
        if not stock_code or not stock_code.strip():
            logger.error("代碼不能為空")
            return {'error': '代碼不能為空'}
            
        # 移除可能的空格和特殊字符
        stock_code = stock_code.strip().replace('.', '')
        
        # 檢查是否為有效的股票或ETF代碼
        if not stock_code.isdigit():
            logger.error(f"無效的代碼格式：{stock_code}")
            return {'error': f'無效的代碼格式：{stock_code}'}
        
        # 檢查是否為ETF (通常ETF代碼以00開頭且長度為4-6位)
        is_etf = stock_code.startswith('00') and 4 <= len(stock_code) <= 6
        
        # 如果是ETF，使用特別的處理方式
        if is_etf:
            # 取得ETF基本資訊
            etf_info = get_etf_basic_info(stock_code)
            
            # 如果發生錯誤，直接返回錯誤訊息
            if 'error' in etf_info:
                return etf_info
                
            # 添加ETF特有欄位
            etf_info['type'] = 'ETF'
            etf_info['fundamental'] = {'type': 'ETF'}
            etf_info['technical'] = {'type': 'ETF'}
            etf_info['institutional'] = {'type': 'ETF'}
            etf_info['margin'] = {'type': 'ETF'}
            
            return etf_info
            
        # 對於一般股票使用原有的處理方式
        url = f"{TWSE_API_URL}?ex_ch=tse_{stock_code}.tw"
        logger.info(f"請求股票資訊 URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Referer': 'https://mis.twse.com.tw/stock/index.jsp'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 檢查響應內容
        if not response.content or len(response.content.strip()) == 0:
            logger.error(f"股票 {stock_code} API 回應為空")
            return {'error': f'無法獲取股票 {stock_code} 資訊，請確認代碼是否正確'}
            
        data = response.json()

        # 詳細檢查資料格式
        if not isinstance(data, dict):
            logger.error(f"API 返回的資料不是字典格式: {type(data).__name__}")
            return {'error': 'API 返回的資料格式不正確'}
            
        if 'msgArray' not in data:
            logger.error(f"API 返回的資料中缺少 msgArray 欄位: {data.keys()}")
            return {'error': 'API 返回的資料格式不正確'}
            
        if not data['msgArray'] or len(data['msgArray']) == 0:
            logger.error(f"無法獲取股票 {stock_code} 資訊，返回的 msgArray 為空")
            return {'error': f'無法獲取股票 {stock_code} 資訊，請確認代碼是否正確'}

        # 確保 stock_data 是字典
        stock_data = data['msgArray'][0]
        if not isinstance(stock_data, dict):
            logger.error(f"API 返回的股票資料不是字典格式: {type(stock_data).__name__}")
            return {'error': f'無法解析股票 {stock_code} 資訊'}

        def safe_float(value, default=0):
            try:
                return float(value) if value != '-' else default
            except (ValueError, TypeError):
                return default

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
        # 先建立空字典，避免後續出現 None 的情況
        fundamental = {}
        technical = {}
        institutional = {}
        margin = {}
        
        # 嘗試獲取基本面資料，但不要因為這個失敗就中斷整個查詢
        try:
            # 如果是ETF，使用不同的方法獲取基本面資料
            if is_etf:
                # 對於ETF，設置ETF特有的基本資訊
                fundamental = {
                    "類型": "ETF",
                    "名稱": stock_data.get('n', ''),
                    "全名": stock_data.get('nf', ''),
                    "追蹤指數": stock_data.get('n', '').replace('元大', '').replace('富邦', '')
                }
                
                # 如果有ETF淨值網址，添加到基本資料中
                if 'nu' in stock_data and stock_data['nu']:
                    fundamental["淨值網址"] = stock_data.get('nu', '')
            else:
                # 獲取一般股票的基本面資料
                try:
                    fundamental_data = twse_api.get_stock_fundamental(stock_code)
                    if fundamental_data is None:
                        logger.warning(f"基本面資料為 None")
                    elif isinstance(fundamental_data, dict):
                        fundamental = fundamental_data
                    elif isinstance(fundamental_data, list) and fundamental_data:
                        # 如果是列表，轉換為字典
                        for item in fundamental_data:
                            if isinstance(item, dict):
                                for key, value in item.items():
                                    fundamental[key] = value
                                break  # 只使用第一個項目
                    else:
                        logger.warning(f"基本面資料格式不正確: {type(fundamental_data).__name__}")
                except Exception as e:
                    logger.warning(f"獲取股票基本面資料失敗: {str(e)}")
        except Exception as e:
            logger.warning(f"獲取基本面資料失敗: {str(e)}")
            # 不要因為這個失敗就中斷整個查詢

        # 設置默認技術指標
        technical = {
            "ma5": [0],
            "ma10": [0],
            "ma20": [0],
            "kd": {"k": [0], "d": [0]},
            "rsi": [0]
        }
        
        # 如果不是ETF，嘗試獲取技術指標
        if not is_etf:
            try:
                technical_data = twse_api.calculate_technical_indicators(stock_code)
                if technical_data is not None and isinstance(technical_data, dict):
                    # 確保 technical_data 包含所有必要的欄位
                    if "ma5" in technical_data and technical_data["ma5"] is not None:
                        technical["ma5"] = technical_data["ma5"]
                    if "ma10" in technical_data and technical_data["ma10"] is not None:
                        technical["ma10"] = technical_data["ma10"]
                    if "ma20" in technical_data and technical_data["ma20"] is not None:
                        technical["ma20"] = technical_data["ma20"]
                    if "kd" in technical_data and technical_data["kd"] is not None:
                        if isinstance(technical_data["kd"], dict):
                            if "k" in technical_data["kd"] and technical_data["kd"]["k"] is not None:
                                technical["kd"]["k"] = technical_data["kd"]["k"]
                            if "d" in technical_data["kd"] and technical_data["kd"]["d"] is not None:
                                technical["kd"]["d"] = technical_data["kd"]["d"]
                    if "rsi" in technical_data and technical_data["rsi"] is not None:
                        technical["rsi"] = technical_data["rsi"]
            except Exception as e:
                logger.warning(f"獲取技術指標失敗: {str(e)}")

        # 如果不是ETF，嘗試獲取法人買賣超
        if not is_etf:
            try:
                institutional_data = twse_api.get_institutional_investors(stock_code)
                if institutional_data is None:
                    logger.warning(f"法人買賣超為 None")
                elif isinstance(institutional_data, dict):
                    institutional = institutional_data
                elif isinstance(institutional_data, list) and institutional_data:
                    # 如果是列表，轉換為字典
                    for item in institutional_data:
                        if isinstance(item, dict) and 'stock_code' in item and item.get('stock_code') == stock_code:
                            for key, value in item.items():
                                institutional[key] = value
                            break  # 找到目標股票後停止
                    if not institutional:
                        # 如果沒有找到目標股票，使用第一個項目
                        for item in institutional_data:
                            if isinstance(item, dict):
                                for key, value in item.items():
                                    institutional[key] = value
                                break
                else:
                    logger.warning(f"法人買賣超格式不正確: {type(institutional_data).__name__}")
            except Exception as e:
                logger.warning(f"獲取法人買賣超失敗: {str(e)}")
        else:
            # 對於ETF，設置簡單的法人資訊
            institutional = {"說明": "ETF無法獲取詳細法人買賣超資訊"}

        # 如果不是ETF，嘗試獲取融資融券
        if not is_etf:
            try:
                margin_data = twse_api.get_margin_trading(stock_code)
                if margin_data is None:
                    logger.warning(f"融資融券為 None")
                elif isinstance(margin_data, dict):
                    margin = margin_data
                elif isinstance(margin_data, list) and margin_data:
                    # 如果是列表，轉換為字典
                    for item in margin_data:
                        if isinstance(item, dict) and 'stock_code' in item and item.get('stock_code') == stock_code:
                            for key, value in item.items():
                                margin[key] = value
                            break  # 找到目標股票後停止
                    if not margin:
                        # 如果沒有找到目標股票，使用第一個項目
                        for item in margin_data:
                            if isinstance(item, dict):
                                for key, value in item.items():
                                    margin[key] = value
                                break
                else:
                    logger.warning(f"融資融券格式不正確: {type(margin_data).__name__}")
            except Exception as e:
                logger.warning(f"獲取融資融券失敗: {str(e)}")
        else:
            # 對於ETF，設置簡單的融資融券資訊
            margin = {"說明": "ETF可能有不同的融資融券規則"}

        # 確保 technical 字典中的所有欄位都是可訂閱的
        if technical is None:
            technical = {
                "ma5": [0],
                "ma10": [0],
                "ma20": [0],
                "kd": {"k": [0], "d": [0]},
                "rsi": [0]
            }
        
        # 確保 technical 中的欄位是列表且非空
        for key in ["ma5", "ma10", "ma20", "rsi"]:
            if key not in technical or not isinstance(technical[key], list) or not technical[key]:
                technical[key] = [0]
        
        # 確保 kd 欄位存在且包含 k 和 d
        if "kd" not in technical or not isinstance(technical["kd"], dict):
            technical["kd"] = {"k": [0], "d": [0]}
        else:
            if "k" not in technical["kd"] or not isinstance(technical["kd"]["k"], list) or not technical["kd"]["k"]:
                technical["kd"]["k"] = [0]
            if "d" not in technical["kd"] or not isinstance(technical["kd"]["d"], list) or not technical["kd"]["d"]:
                technical["kd"]["d"] = [0]
        
        # 構建返回結果
        result = {
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
            "status": stock_data.get('s', '正常交易')
        }
        
        # 添加ETF特有信息
        if is_etf:
            result["type"] = "ETF"
            result["full_name"] = stock_data.get('nf', '')
            # 如果有ETF淨值資訊，可以添加
            if 'nu' in stock_data:
                result["nav_url"] = stock_data.get('nu', '')
        else:
            result["type"] = "股票"
        
        # 添加其他分析資訊
        result["fundamental"] = fundamental
        result["technical"] = technical
        result["institutional"] = institutional
        result["margin"] = margin
        
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生網路錯誤: {str(e)}")
        return {'error': f'網路錯誤：{str(e)}'}
    except Exception as e:
        logger.error(f"從證交所獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
        return {'error': f'系統錯誤：{str(e)}'}


def format_stock_info(stock_info: dict) -> str:
    """
    格式化股票或ETF資訊為易讀的字符串
    """
    if not stock_info:
        return "無法獲取資訊，請確認代碼是否正確。"
    
    if 'error' in stock_info:
        return f"獲取資訊時發生錯誤：{stock_info['error']}"
    
    # 檢查是否為ETF
    is_etf = stock_info.get('type') == 'ETF'
    
    # 基本資訊
    title = f"{stock_info['name']} {'ETF' if is_etf else '股票'}資訊"
    
    message = f"""
{title}

當前價格: {stock_info['price']}
漲跌幅: {stock_info['change']} ({stock_info['change_percent']:.2f}%)
今日最高: {stock_info['high']}
今日最低: {stock_info['low']}
成交量: {stock_info['volume']:,}
更新時間: {stock_info['last_updated']}
"""

    # 如果是ETF，顯示簡化的資訊
    if is_etf:
        # 如果有全名，顯示它
        if 'full_name' in stock_info:
            message += f"""
全名: {stock_info.get('full_name', 'N/A')}"""
        
        # 如果有淨值網址，顯示它
        if 'nav_url' in stock_info:
            message += f"""
淨值網址: {stock_info.get('nav_url', 'N/A')}"""
            
        message += """

說明: ETF無法提供詳細的技術指標和法人買賣超資訊。"""
        return message

    # 以下是一般股票的資訊格式化
    # 基本面資訊
    if stock_info.get('fundamental') and not is_etf:
        fundamental = stock_info['fundamental']
        if isinstance(fundamental, dict) and len(fundamental) > 1:  # 確保不是空字典或只有type欄位
            message += f"""
基本面分析
本益比: {fundamental.get('pe_ratio', 'N/A')}
殖利率: {fundamental.get('dividend_yield', 'N/A')}%
每股盈餘: {fundamental.get('eps', 'N/A')}
"""

    # 技術指標
    if stock_info.get('technical') and not is_etf:
        technical = stock_info['technical']
        if isinstance(technical, dict) and 'ma5' in technical and 'ma10' in technical and 'ma20' in technical:
            try:
                message += f"""
技術分析
MA5: {technical['ma5'][-1]:.2f}
MA10: {technical['ma10'][-1]:.2f}
MA20: {technical['ma20'][-1]:.2f}
KD: K={technical['kd']['k'][-1]:.2f} D={technical['kd']['d'][-1]:.2f}
RSI: {technical['rsi'][-1]:.2f}
"""
            except (IndexError, KeyError, TypeError):
                message += """

技術分析: 無法取得技術指標資料"""

    # 法人買賣超
    if stock_info.get('institutional') and not is_etf:
        institutional = stock_info['institutional']
        if isinstance(institutional, dict) and len(institutional) > 1:  # 確保不是空字典或只有type欄位
            message += f"""
法人買賣超
外資: {institutional.get('foreign', 'N/A')}
投信: {institutional.get('investment_trust', 'N/A')}
自營商: {institutional.get('dealer', 'N/A')}
"""

    # 融資融券
    if stock_info.get('margin') and not is_etf:
        margin = stock_info['margin']
        if isinstance(margin, dict) and len(margin) > 1:  # 確保不是空字典或只有type欄位
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
