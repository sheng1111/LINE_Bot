import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from database import db
import time

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 台灣證交所 API 設定
TWSE_API_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
DIVIDEND_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DIVIDEND"


class DividendAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(minutes=30)
        self.logger = logging.getLogger(__name__)
        self.last_request_time = {}
        self.request_interval = 5
        self.max_retries = 3
        self.retry_delay = 5

    def _get_with_retry(self, stock_code: str, func: callable) -> Optional[Dict]:
        """帶有重試機制的請求函數"""
        for attempt in range(self.max_retries):
            try:
                # 檢查請求間隔
                current_time = time.time()
                if stock_code in self.last_request_time:
                    time_since_last = current_time - \
                        self.last_request_time[stock_code]
                    if time_since_last < self.request_interval:
                        wait_time = self.request_interval - time_since_last
                        logger.warning(f"請求過於頻繁，等待 {int(wait_time)} 秒後重試")
                        time.sleep(wait_time)

                result = func(stock_code)
                if result is None:
                    raise ValueError("API returned None")

                self.last_request_time[stock_code] = time.time()
                return result

            except Exception as e:
                if "Too Many Requests" in str(e):
                    wait_time = (attempt + 1) * self.retry_delay
                    logger.warning(f"請求過於頻繁，等待 {wait_time} 秒後重試")
                    time.sleep(wait_time)
                else:
                    logger.error(f"獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
                    if attempt == self.max_retries - 1:
                        return {}
                    time.sleep(self.retry_delay)

        return {}

    def get_dividend_info(self, stock_code: str) -> Optional[Dict]:
        """
        獲取股票的股息資訊
        :param stock_code: 股票代碼
        :return: 包含股息資訊的字典
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

            # 如果資料庫沒有，從證交所 API 獲取
            def _fetch_dividend_info(code):
                # 獲取股票基本資訊
                today = datetime.now().strftime('%Y%m%d')
                response = requests.get(
                    f"{TWSE_API_URL}?response=json&date={today}&stockNo={code}")
                response.raise_for_status()
                price_data = response.json()

                # 獲取股息資訊
                dividend_response = requests.get(
                    f"{DIVIDEND_URL}?response=json&stockNo={code}")
                dividend_data = dividend_response.json()

                return {
                    'stock_code': code,
                    'current_price': float(price_data.get('data', [{}])[0].get('close', 0)),
                    'annual_dividend': float(dividend_data.get('data', [{}])[0].get('dividend', 0)),
                    'dividend_history': [
                        {
                            'date': item.get('date', ''),
                            'amount': float(item.get('amount', 0)),
                            'type': item.get('type', 'cash')
                        }
                        for item in dividend_data.get('data', [])
                    ]
                }

            dividend_info = self._get_with_retry(
                stock_code, _fetch_dividend_info)

            # 儲存到資料庫
            collection.insert_one(dividend_info)

            # 更新快取
            self.cache[cache_key] = {
                'data': dividend_info,
                'timestamp': datetime.now()
            }

            return dividend_info

        except Exception as e:
            logger.error(f"獲取股息資訊時發生錯誤：{str(e)}")
            return None

    def calculate_dividend_yield(self, stock_code: str) -> Optional[float]:
        """
        計算股票的股息殖利率
        :param stock_code: 股票代碼
        :return: 股息殖利率
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

    def analyze_dividend(self, stock_code: str) -> Dict:
        """
        分析股票的除權息資訊
        :param stock_code: 股票代碼
        :return: 分析結果字典
        """
        try:
            # 檢查快取
            cache_key = f"dividend_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 從資料庫獲取股息資料
            collection = db.get_collection('dividend_info')
            dividend_data = collection.find_one({'stock_code': stock_code})

            if not dividend_data:
                # 如果資料庫沒有，從證交所 API 獲取
                def _fetch_dividend_analysis(code):
                    # 獲取股票基本資訊
                    today = datetime.now().strftime('%Y%m%d')
                    response = requests.get(
                        f"{TWSE_API_URL}?response=json&date={today}&stockNo={code}")
                    response.raise_for_status()
                    price_data = response.json()

                    # 獲取股息資訊
                    dividend_response = requests.get(
                        f"{DIVIDEND_URL}?response=json&stockNo={code}")
                    dividend_data = dividend_response.json()

                    # 計算股息殖利率
                    current_price = float(price_data.get(
                        'data', [{}])[0].get('close', 0))
                    annual_dividend = float(dividend_data.get(
                        'data', [{}])[0].get('dividend', 0))
                    dividend_yield = (
                        annual_dividend / current_price) * 100 if current_price > 0 else 0

                    return {
                        'stock_code': code,
                        'name': price_data.get('data', [{}])[0].get('name', 'Unknown'),
                        'current_price': current_price,
                        'last_dividend': float(dividend_data.get('data', [{}])[0].get('dividend', 0)),
                        'annual_dividend': annual_dividend,
                        'dividend_yield': dividend_yield,
                        'payout_ratio': float(dividend_data.get('data', [{}])[0].get('payout_ratio', 0)),
                        'dividend_history': [
                            {
                                'date': item.get('date', ''),
                                'amount': float(item.get('amount', 0)),
                                'type': item.get('type', 'cash')
                            }
                            for item in dividend_data.get('data', [])
                        ],
                        'analysis_time': datetime.now()
                    }

                dividend_data = self._get_with_retry(
                    stock_code, _fetch_dividend_analysis)

                # 儲存到資料庫
                collection.insert_one(dividend_data)

            # 更新快取
            self.cache[cache_key] = {
                'data': dividend_data,
                'timestamp': datetime.now()
            }

            return dividend_data

        except Exception as e:
            self.logger.error(f"分析股票 {stock_code} 除權息時發生錯誤：{str(e)}")
            return {'error': f'分析股票 {stock_code} 除權息時發生錯誤：{str(e)}'}


# 建立全域分析器實例
analyzer = DividendAnalyzer()
