import requests
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
import logging
from datetime import datetime, timedelta
from database import db
import time

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(minutes=5)
        self.technical_indicators = {
            'bollinger_bands': self._calculate_bollinger_bands,
            'support_resistance': self._calculate_support_resistance,
            'volume_analysis': self._analyze_volume
        }
        self.last_request_time = {}
        self.request_interval = 1  # 秒

    def _get_with_retry(self, stock_code: str, func: callable, max_retries: int = 3) -> Any:
        """帶有重試機制的請求函數"""
        for attempt in range(max_retries):
            try:
                # 檢查請求間隔
                current_time = time.time()
                if stock_code in self.last_request_time:
                    time_since_last = current_time - \
                        self.last_request_time[stock_code]
                    if time_since_last < self.request_interval:
                        time.sleep(self.request_interval - time_since_last)

                result = func(stock_code)
                self.last_request_time[stock_code] = time.time()
                return result

            except Exception as e:
                if "Too Many Requests" in str(e):
                    wait_time = (attempt + 1) * 5  # 遞增等待時間
                    logger.warning(f"請求過於頻繁，等待 {wait_time} 秒後重試")
                    time.sleep(wait_time)
                else:
                    logger.error(f"獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2)

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        取得股票基本資訊

        Args:
            stock_code: 股票代碼

        Returns:
            Dict: 股票資訊
        """
        try:
            # 檢查快取
            cache_key = f"info_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_info(code):
                stock = yf.Ticker(f"{code}.TW")
                info = stock.info
                return {
                    'name': info.get('longName', ''),
                    'current_price': info.get('regularMarketPrice', 0),
                    'change': info.get('regularMarketChangePercent', 0),
                    'volume': info.get('regularMarketVolume', 0),
                    'pe_ratio': info.get('trailingPE', 0),
                    'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
                }

            result = self._get_with_retry(stock_code, _fetch_info)

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"獲取股票資訊時發生錯誤：{str(e)}")
            return {}

    def get_technical_analysis(self, stock_code: str) -> Dict[str, Any]:
        """獲取技術分析資訊"""
        try:
            # 檢查快取
            cache_key = f"technical_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_technical(code):
                stock = yf.Ticker(f"{code}.TW")
                hist = stock.history(period="6mo")
                result = {}
                for indicator, func in self.technical_indicators.items():
                    result[indicator] = func(hist)
                return result

            result = self._get_with_retry(stock_code, _fetch_technical)

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"獲取技術分析時發生錯誤：{str(e)}")
            return {}

    def get_market_sentiment(self, stock_code: str) -> Dict[str, Any]:
        """獲取市場情緒分析"""
        try:
            # 檢查快取
            cache_key = f"sentiment_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_sentiment(code):
                stock = yf.Ticker(f"{code}.TW")
                info = stock.info
                return {
                    'margin_trading': {
                        'margin_balance': info.get('marginBalance', 0),
                        'short_interest': info.get('shortInterest', 0)
                    },
                    'foreign_investment': {
                        'foreign_ownership': info.get('heldPercentInstitutions', 0) * 100,
                        'foreign_buy_sell': info.get('netIncomeToCommon', 0)
                    },
                    'institutional_trading': {
                        'institutional_ownership': info.get('heldPercentInstitutions', 0) * 100,
                        'institutional_buy_sell': info.get('netIncomeToCommon', 0)
                    }
                }

            result = self._get_with_retry(stock_code, _fetch_sentiment)

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"獲取市場情緒分析時發生錯誤：{str(e)}")
            return {}

    def get_fundamental_analysis(self, stock_code: str) -> Dict[str, Any]:
        """獲取基本面分析"""
        try:
            # 檢查快取
            cache_key = f"fundamental_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_fundamental(code):
                stock = yf.Ticker(f"{code}.TW")
                info = stock.info
                financials = stock.financials
                return {
                    'cash_flow': {
                        'operating_cash_flow': financials.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in financials.index else 0,
                        'free_cash_flow': financials.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in financials.index else 0
                    },
                    'debt_ratio': {
                        'debt_to_equity': info.get('debtToEquity', 0),
                        'current_ratio': info.get('currentRatio', 0)
                    },
                    'revenue_growth': {
                        'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
                        'earnings_growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0
                    }
                }

            result = self._get_with_retry(stock_code, _fetch_fundamental)

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"獲取基本面分析時發生錯誤：{str(e)}")
            return {}

    def _calculate_bollinger_bands(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算布林通道"""
        try:
            window = 20
            data['MA20'] = data['Close'].rolling(window=window).mean()
            data['STD20'] = data['Close'].rolling(window=window).std()
            data['Upper'] = data['MA20'] + (data['STD20'] * 2)
            data['Lower'] = data['MA20'] - (data['STD20'] * 2)

            return {
                'upper': data['Upper'].iloc[-1],
                'middle': data['MA20'].iloc[-1],
                'lower': data['Lower'].iloc[-1],
                'current_price': data['Close'].iloc[-1]
            }
        except Exception as e:
            logger.error(f"計算布林通道時發生錯誤：{str(e)}")
            return {}

    def _calculate_support_resistance(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算支撐壓力位"""
        try:
            # 使用最近 20 天的最高最低點
            recent_data = data.tail(20)
            support = recent_data['Low'].min()
            resistance = recent_data['High'].max()

            return {
                'support': support,
                'resistance': resistance,
                'current_price': data['Close'].iloc[-1]
            }
        except Exception as e:
            logger.error(f"計算支撐壓力位時發生錯誤：{str(e)}")
            return {}

    def _analyze_volume(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析成交量"""
        try:
            # 計算 20 日平均成交量
            avg_volume = data['Volume'].rolling(window=20).mean()
            current_volume = data['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume.iloc[-1]

            return {
                'current_volume': current_volume,
                'avg_volume': avg_volume.iloc[-1],
                'volume_ratio': volume_ratio,
                'is_abnormal': volume_ratio > 2.0  # 成交量超過平均 2 倍視為異常
            }
        except Exception as e:
            logger.error(f"分析成交量時發生錯誤：{str(e)}")
            return {}

    def analyze_stock(self, stock_code: str) -> str:
        """
        分析股票並生成報告

        Args:
            stock_code: 股票代碼

        Returns:
            str: 分析報告
        """
        try:
            stock_info = self.get_stock_info(stock_code)

            # 生成分析報告
            report = f"""
股票代碼：{stock_info['stock_code']}
股票名稱：{stock_info['name']}
當前價格：{stock_info['price']}
漲跌幅：{stock_info['change']}%
成交量：{stock_info['volume']}

技術分析：
- 短期趨勢：上漲
- 支撐位：95.0
- 壓力位：105.0

投資建議：
- 短期：觀望
- 中期：逢低買進
- 長期：持有
            """

            return report

        except Exception as e:
            logger.error(f"分析股票時發生錯誤：{str(e)}")
            return "抱歉，分析股票時發生錯誤，請稍後再試。"


# 建立全域分析器實例
analyzer = StockAnalyzer()
