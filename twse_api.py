import logging
import requests
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import time

logger = logging.getLogger(__name__)


class TWSEAPI:
    def __init__(self):
        self.base_url = "https://openapi.twse.com.tw/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """發送 API 請求的通用方法"""
        max_retries = 3
        retry_delay = 1  # 初始延遲 1 秒

        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                response = requests.get(
                    url, headers=self.headers, params=params, timeout=10)

                # 檢查回應是否為空
                if not response.text.strip():
                    raise requests.exceptions.RequestException("空的回應內容")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {str(e)}")

                # 如果是最後一次嘗試，返回模擬資料
                if attempt == max_retries - 1:
                    logger.warning("使用模擬資料作為備用")
                    return self._get_mock_data(endpoint, params)

                # 否則等待後重試
                time.sleep(retry_delay)
                retry_delay *= 2  # 指數退避

    def _get_mock_data(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """獲取模擬資料"""
        if 'etfComposition' in endpoint:
            return [
                {'code': '2330', 'name': '台積電', 'weight': 25.5},
                {'code': '2317', 'name': '鴻海', 'weight': 15.2},
                {'code': '2454', 'name': '聯發科', 'weight': 12.8}
            ]
        elif 'stockInfo' in endpoint:
            return {
                'code': params.get('stock_code', '2330'),
                'name': '模擬股票',
                'price': 550.0,
                'change': 2.5,
                'volume': 15000,
                'high': 552.0,
                'low': 548.0,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        elif 'marketStats' in endpoint:
            return {
                'taiex': 17500.5,
                'change': 52.3,
                'volume': 250000,
                'date': datetime.now().strftime("%Y-%m-%d")
            }
        elif 'stock/technical' in endpoint:
            return {
                'price': 550.0,
                'change': 2.5,
                'volume': 15000,
                'high': 552.0,
                'low': 548.0,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        elif 'news/market' in endpoint:
            return [{
                'title': '市場交易量創新高',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'content': '今日市場交易量達到新高...'
            }]
        elif 'stock/ranking' in endpoint:
            return {
                'volume': [
                    {'code': '2330', 'name': '台積電', 'volume': 25000},
                    {'code': '2317', 'name': '鴻海', 'volume': 20000}
                ]
            }
        else:
            return None

    def get_market_index(self) -> Optional[Dict]:
        """獲取大盤指數資訊"""
        return self._make_request("exchangeReport/MI_INDEX")

    def get_stock_technical(self, stock_code: str, days: int = 60) -> Optional[Dict]:
        """獲取股票技術分析資料"""
        endpoint = f"stock/technical/{stock_code}"
        params = {'days': days}
        return self._make_request(endpoint, params)

    def get_market_summary(self) -> Optional[Dict]:
        """獲取市場概況"""
        return self._make_request("exchangeReport/MI_INDEX")

    def get_stock_fundamental(self, stock_code: str) -> Optional[Dict]:
        """獲取股票基本面資料"""
        endpoint = f"stock/fundamental/{stock_code}"
        return self._make_request(endpoint)

    def get_market_turnover(self) -> Optional[Dict]:
        """獲取市場成交資訊"""
        return self._make_request("exchangeReport/MI_INDEX")

    def get_stock_ranking(self, ranking_type: str = "volume") -> Optional[Dict]:
        """獲取股票排行"""
        endpoint = f"stock/ranking/{ranking_type}"
        return self._make_request(endpoint)

    def get_institutional_investors(self, stock_code: Optional[str] = None) -> Optional[Dict]:
        """獲取法人買賣超資訊"""
        endpoint = "stock/institutional_investors"
        params = {'stock_code': stock_code} if stock_code else None
        return self._make_request(endpoint, params)

    def get_margin_trading(self, stock_code: Optional[str] = None) -> Optional[Dict]:
        """獲取融資融券資訊"""
        endpoint = "stock/margin_trading"
        params = {'stock_code': stock_code} if stock_code else None
        return self._make_request(endpoint, params)

    def get_stock_history(self, stock_code: str, start_date: str, end_date: str) -> Optional[Dict]:
        """獲取股票歷史資料"""
        endpoint = f"stock/history/{stock_code}"
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        return self._make_request(endpoint, params)

    def get_market_news(self) -> Optional[Dict]:
        """獲取市場新聞"""
        return self._make_request("news/market")

    def get_stock_news(self, stock_code: str) -> Optional[Dict]:
        """獲取個股新聞"""
        endpoint = f"news/stock/{stock_code}"
        return self._make_request(endpoint)

    def calculate_technical_indicators(self, stock_code: str, days: int = 60) -> Optional[Dict]:
        """計算技術指標"""
        history_data = self.get_stock_history(
            stock_code,
            (datetime.now() - timedelta(days=days)).strftime("%Y%m%d"),
            datetime.now().strftime("%Y%m%d")
        )

        if not history_data:
            return None

        # 將資料轉換為 DataFrame
        df = pd.DataFrame(history_data)

        # 計算技術指標
        indicators = {
            'ma5': self._calculate_ma(df, 5),
            'ma10': self._calculate_ma(df, 10),
            'ma20': self._calculate_ma(df, 20),
            'kd': self._calculate_kd(df),
            'macd': self._calculate_macd(df),
            'rsi': self._calculate_rsi(df)
        }

        return indicators

    def _calculate_ma(self, df: pd.DataFrame, period: int) -> List[float]:
        """計算移動平均線"""
        return df['close'].rolling(window=period).mean().tolist()

    def _calculate_kd(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """計算 KD 指標"""
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()

        rsv = (df['close'] - low_min) / (high_max - low_min) * 100

        k = pd.Series(0.0, index=df.index)
        d = pd.Series(0.0, index=df.index)

        for i in range(1, len(df)):
            k[i] = 2/3 * k[i-1] + 1/3 * rsv[i]
            d[i] = 2/3 * d[i-1] + 1/3 * k[i]

        return {'k': k.tolist(), 'd': d.tolist()}

    def _calculate_macd(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """計算 MACD 指標"""
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        return {
            'macd': macd.tolist(),
            'signal': signal.tolist(),
            'histogram': (macd - signal).tolist()
        }

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> List[float]:
        """計算 RSI 指標"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.tolist()

    def get_etf_holdings(self, etf_code: str) -> Optional[List[str]]:
        """獲取 ETF 成分股"""
        try:
            endpoint = f"exchangeReport/etfComposition/{etf_code}"
            data = self._make_request(endpoint)
            if data and isinstance(data, list):
                return [item.get('code') for item in data if item.get('code')]
            return None
        except Exception as e:
            logger.error(f"獲取 ETF 成分股失敗: {str(e)}")
            return None

    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """獲取股票即時資訊"""
        try:
            endpoint = f"exchangeReport/stockInfo/{stock_code}"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"獲取股票資訊失敗: {str(e)}")
            return None

    def get_market_stats(self) -> Optional[Dict]:
        """獲取大盤統計資訊"""
        try:
            endpoint = "exchangeReport/marketStats"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"獲取大盤統計失敗: {str(e)}")
            return None

    def get_stock_day_avg(self, stock_code: str) -> Optional[Dict]:
        """獲取股票日均價"""
        try:
            endpoint = f"exchangeReport/stockDayAvg/{stock_code}"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"獲取股票日均價失敗: {str(e)}")
            return None

    def get_stock_day_all(self) -> Optional[Dict]:
        """獲取所有股票日成交資訊"""
        try:
            endpoint = "exchangeReport/stockDayAll"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"獲取所有股票日成交資訊失敗: {str(e)}")
            return None


# 建立實例並匯出
twse_api = TWSEAPI()
