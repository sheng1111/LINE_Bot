import logging
import requests
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union

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
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(
                url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API 請求失敗: {str(e)}")
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
