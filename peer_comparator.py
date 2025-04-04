import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from database import db
from stock_analyzer import analyzer as stock_analyzer
from dividend_analyzer import analyzer as dividend_analyzer

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PeerComparator:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(hours=1)  # 快取 1 小時
        self.api_url = "https://api.example.com/peers"  # 替換為實際的同業 API

    def get_peer_stocks(self, stock_code: str) -> Dict:
        """獲取同業股票資訊"""
        try:
            # 檢查緩存
            if stock_code in self.cache:
                cache_time, data = self.cache[stock_code]
                if datetime.now() - cache_time < self.cache_timeout:
                    return data

            # 模擬數據
            mock_data = {
                '2330': {
                    'peers': [
                        {
                            'code': '2303',
                            'name': '聯電',
                            'price': 52.3,
                            'change': 0.5,
                            'pe_ratio': 15.2,
                            'market_cap': 1234.5
                        },
                        {
                            'code': '2308',
                            'name': '台達電',
                            'price': 288.5,
                            'change': -1.2,
                            'pe_ratio': 18.7,
                            'market_cap': 789.3
                        },
                        {
                            'code': '2454',
                            'name': '聯發科',
                            'price': 788.0,
                            'change': 2.1,
                            'pe_ratio': 22.4,
                            'market_cap': 2345.6
                        }
                    ],
                    'industry': '半導體',
                    'avg_pe_ratio': 18.8,
                    'avg_market_cap': 1456.5
                },
                '2303': {
                    'peers': [
                        {
                            'code': '2330',
                            'name': '台積電',
                            'price': 683.0,
                            'change': 1.5,
                            'pe_ratio': 16.8,
                            'market_cap': 17721.3
                        },
                        {
                            'code': '2308',
                            'name': '台達電',
                            'price': 288.5,
                            'change': -1.2,
                            'pe_ratio': 18.7,
                            'market_cap': 789.3
                        }
                    ],
                    'industry': '半導體',
                    'avg_pe_ratio': 17.8,
                    'avg_market_cap': 9255.3
                }
            }

            # 如果股票代碼存在於模擬數據中，返回對應數據
            if stock_code in mock_data:
                data = mock_data[stock_code]
                # 更新緩存
                self.cache[stock_code] = (datetime.now(), data)
                return data
            else:
                return {'error': f'找不到股票代碼 {stock_code} 的同業資訊'}

        except Exception as e:
            self.logger.error(f"獲取同業股票時發生錯誤：{str(e)}")
            return {'error': '無法獲取同業股票資訊'}

    def compare_stocks(self, stock_code: str) -> Dict:
        """比較股票與同業的表現"""
        try:
            # 獲取同業股票資訊
            peer_info = self.get_peer_stocks(stock_code)

            if 'error' in peer_info:
                return peer_info

            # 格式化輸出
            result = {
                'stock_code': stock_code,
                'industry': peer_info['industry'],
                'peers': peer_info['peers'],
                'avg_pe_ratio': peer_info['avg_pe_ratio'],
                'avg_market_cap': peer_info['avg_market_cap']
            }

            return result

        except Exception as e:
            self.logger.error(f"比較股票時發生錯誤：{str(e)}")
            return {'error': '比較股票時發生錯誤'}


# 建立全域比較器實例
comparator = PeerComparator()
