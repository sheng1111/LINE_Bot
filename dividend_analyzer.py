import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from database import db

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DividendAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(hours=1)  # 快取 1 小時
        self.api_url = "https://api.example.com/dividend"  # 替換為實際的股息 API

    def get_dividend_info(self, stock_code: str) -> Optional[Dict]:
        """
        獲取股票的股息資訊

        Args:
            stock_code: 股票代碼

        Returns:
            包含股息資訊的字典，如果發生錯誤則返回 None
        """
        try:
            # 檢查快取
            cache_key = f"dividend_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 從資料庫查詢
            collection = db.get_collection('dividend_info')
            dividend_info = collection.find_one({'stock_code': stock_code})

            if dividend_info:
                # 更新快取
                self.cache[cache_key] = {
                    'data': dividend_info,
                    'timestamp': datetime.now()
                }
                return dividend_info

            # 如果資料庫沒有，使用 mock 數據（實際應用中應該從 API 獲取）
            mock_data = {
                'stock_code': stock_code,
                'current_price': 500,
                'annual_dividend': 20,
                'dividend_history': [
                    {'date': '2024-01-15', 'amount': 5, 'type': 'cash'},
                    {'date': '2023-07-15', 'amount': 5, 'type': 'cash'},
                    {'date': '2023-01-15', 'amount': 5, 'type': 'cash'},
                    {'date': '2022-07-15', 'amount': 5, 'type': 'cash'}
                ]
            }

            # 儲存到資料庫
            collection.insert_one(mock_data)

            # 更新快取
            self.cache[cache_key] = {
                'data': mock_data,
                'timestamp': datetime.now()
            }

            return mock_data

        except Exception as e:
            logger.error(f"獲取股息資訊時發生錯誤：{str(e)}")
            return None

    def get_dividend_history(self, stock_code: str) -> List[Dict]:
        """
        獲取股票的歷史股息記錄

        Args:
            stock_code: 股票代碼

        Returns:
            歷史股息記錄列表
        """
        try:
            # 檢查快取
            cache_key = f"history_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 從資料庫查詢
            collection = db.get_collection('dividend_history')
            history = list(collection.find(
                {'stock_code': stock_code}).sort('date', -1))

            if history:
                # 更新快取
                self.cache[cache_key] = {
                    'data': history,
                    'timestamp': datetime.now()
                }
                return history

            # 如果資料庫沒有，從 API 獲取
            response = requests.get(f"{self.api_url}/{stock_code}/history")
            response.raise_for_status()
            history = response.json()

            # 儲存到資料庫
            for record in history:
                collection.insert_one({
                    'stock_code': stock_code,
                    'date': record['date'],
                    'amount': record['amount'],
                    'type': record['type']
                })

            # 更新快取
            self.cache[cache_key] = {
                'data': history,
                'timestamp': datetime.now()
            }

            return history

        except Exception as e:
            logger.error(f"獲取歷史股息記錄時發生錯誤：{str(e)}")
            return []

    def calculate_dividend_yield(self, stock_code: str) -> Optional[float]:
        """
        計算股票的股息殖利率

        Args:
            stock_code: 股票代碼

        Returns:
            股息殖利率，如果發生錯誤則返回 None
        """
        try:
            dividend_info = self.get_dividend_info(stock_code)
            if not dividend_info:
                return None

            current_price = dividend_info.get('current_price')
            annual_dividend = dividend_info.get('annual_dividend')

            if not current_price or not annual_dividend:
                return None

            return (annual_dividend / current_price) * 100

        except Exception as e:
            logger.error(f"計算股息殖利率時發生錯誤：{str(e)}")
            return None


# 建立全域分析器實例
analyzer = DividendAnalyzer()
