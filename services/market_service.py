import logging
from typing import Dict, List, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache
from config.settings import API_CONFIG, CACHE_CONFIG
from datetime import datetime

logger = logging.getLogger(__name__)

class MarketService:
    def __init__(self):
        self.api_config = API_CONFIG['TWSE_API']
        self.timeout = self.api_config['TIMEOUT']

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_futures_info(self) -> Optional[Dict]:
        """獲取台指期資訊"""
        try:
            url = f"{self.api_config['FUTURES_INFO']}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data'):
                raise ValueError("無效的期貨資料")
                
            return self._format_futures_data(data['data'])
            
        except Exception as e:
            logger.error(f"獲取期貨資料時發生錯誤: {str(e)}")
            return None

    def _format_futures_data(self, data: Dict) -> Dict:
        """格式化期貨資料"""
        return {
            'price': float(data.get('price', 0)),
            'change': float(data.get('change', 0)),
            'volume': int(data.get('volume', 0)),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    @lru_cache(maxsize=CACHE_CONFIG['MAX_SIZE'])
    def get_market_news(self, limit: int = 5) -> List[Dict]:
        """獲取市場新聞"""
        try:
            url = f"{self.api_config['MARKET_NEWS']}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            news_list = response.json().get('data', [])
            return news_list[:limit]
            
        except Exception as e:
            logger.error(f"獲取市場新聞時發生錯誤: {str(e)}")
            return []

def format_futures_info(futures_info: dict) -> str:
    """
    格式化期貨資訊
    :param futures_info: 期貨資訊字典
    :return: 格式化後的字串
    """
    try:
        return f"""
📈 台指期即時資訊
現價: {futures_info.get('price', 0):.0f}
漲跌: {futures_info.get('change', 0):.0f} ({futures_info.get('change_percent', 0):.2f}%)
成交量: {futures_info.get('volume', 0):,}
最高: {futures_info.get('high', 0):.0f}
最低: {futures_info.get('low', 0):.0f}
開盤: {futures_info.get('open', 0):.0f}
持倉量: {futures_info.get('oi', 0):,}
"""
    except Exception as e:
        return f"格式化期貨資訊時發生錯誤: {str(e)}"

market_service = MarketService()
