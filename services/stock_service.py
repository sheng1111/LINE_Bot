from typing import Dict, Optional
import logging
from datetime import datetime
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache
from config.settings import API_CONFIG, CACHE_CONFIG

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self):
        self.api_config = API_CONFIG['TWSE_API']
        self.base_url = self.api_config['STOCK_INFO']
        self.timeout = self.api_config['TIMEOUT']

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    @lru_cache(maxsize=CACHE_CONFIG['MAX_SIZE'])

    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """獲取股票資訊"""
        try:
            url = f"{self.base_url}?ex_ch=tse_{stock_code}.tw"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('msgArray'):
                raise ValueError(f"無效的股票代碼: {stock_code}")
                
            stock_data = data['msgArray'][0]
            return self._format_stock_data(stock_data, stock_code)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API請求錯誤: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"處理股票資料時發生錯誤: {str(e)}")
            raise

    def _safe_float_convert(self, value, default=0.0):
        if value is None or value == '-':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _format_stock_data(self, data: Dict, stock_code: str) -> Optional[Dict]:
        """格式化股票資料"""
        try:
            if not data:
                return None
            
            current_price = self._safe_float_convert(data.get('z'))
            change = self._safe_float_convert(data.get('y'))
            prev_close = self._safe_float_convert(data.get('u'))
            
            if current_price == 0 and prev_close == 0:
                return None  # Invalid stock data
                
            return {
                'code': stock_code,
                'name': data.get('n', ''),
                'price': current_price,
                'change': change,
                'change_percent': (change / prev_close * 100) if prev_close != 0 else 0,
                'volume': int(self._safe_float_convert(data.get('v'))),
                'high': self._safe_float_convert(data.get('h')),
                'low': self._safe_float_convert(data.get('l')),
                'open': self._safe_float_convert(data.get('o')),
                'prev_close': prev_close,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pe_ratio': data.get('pe', 'N/A')
            }
        except Exception as e:
            logger.error(f"格式化股票資料時發生錯誤: {str(e)}")
            return None

def format_stock_info(stock_info: dict) -> str:
    """
    格式化股票資訊
    :param stock_info: 股票資訊字典
    :return: 格式化後的字串
    """
    try:
        return f"""
📊 {stock_info.get('code')} {stock_info.get('name')}
現價: ${stock_info.get('price', 0):.2f}
漲跌: {stock_info.get('change', 0):+.2f} ({stock_info.get('change_percent', 0):+.2f}%)
成交量: {stock_info.get('volume', 0):,}
最高: ${stock_info.get('high', 0):.2f}
最低: ${stock_info.get('low', 0):.2f}
開盤: ${stock_info.get('open', 0):.2f}
昨收: ${stock_info.get('prev_close', 0):.2f}
本益比: {stock_info.get('pe_ratio', 'N/A')}
最後更新: {stock_info.get('timestamp')}
"""
    except Exception as e:
        return f"格式化股票資訊時發生錯誤: {str(e)}"
    
stock_service = StockService()
