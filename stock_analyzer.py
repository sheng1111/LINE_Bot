import requests
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
import logging
from datetime import datetime, timedelta
from database import db
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        self.request_interval = 15  # 增加到 15 秒
        self.max_retries = 3
        self.retry_delay = 5  # 重試等待時間

        # 設定 requests session
        self.session = requests.Session()
        retries = Retry(
            total=5,  # 總重試次數
            backoff_factor=1,  # 重試間隔
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重試的狀態碼
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # 允許重試的請求方法
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        # 設定 yfinance 的請求 headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

        # 設定 yfinance 的快取
        yf.set_tz_cache_location(None)  # 禁用時區快取

    def _get_with_retry(self, stock_code: str, func: callable) -> Any:
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

                # 使用自定義的 session
                ticker = yf.Ticker(f"{stock_code}.TW")  # 添加 .TW 後綴
                ticker._session = self.session  # 使用自定義的 session

                result = func(ticker)
                if result is None:
                    raise ValueError("API returned None")

                self.last_request_time[stock_code] = time.time()
                return result

            except Exception as e:
                if "429" in str(e):
                    wait_time = (attempt + 1) * self.retry_delay
                    logger.warning(f"請求過於頻繁，等待 {wait_time} 秒後重試")
                    time.sleep(wait_time)
                else:
                    logger.error(f"獲取股票 {stock_code} 資訊時發生錯誤: {str(e)}")
                    if attempt == self.max_retries - 1:
                        return {}
                    time.sleep(self.retry_delay)

        return {}

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

            def _fetch_info(ticker):
                info = ticker.info
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

            def _fetch_technical(ticker):
                hist = ticker.history(period="6mo")
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

            def _fetch_sentiment(ticker):
                info = ticker.info
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

            def _fetch_fundamental(ticker):
                info = ticker.info
                financials = ticker.financials
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
            if not stock_info:
                return f"""抱歉，我暫時無法獲取 {stock_code} 的股票資訊

可能的原因：
1. 網路連線不穩定
2. 股票代碼可能有誤
3. 資料來源暫時無回應

建議您：
- 確認股票代碼是否正確
- 稍後再試一次
- 如果問題持續發生，可以先查看其他股票資訊

需要我為您查詢其他股票嗎？"""

            # 生成分析報告
            report = f"""
{stock_info['name']} ({stock_code}) 股票分析報告

基本資訊
• 當前價格：${stock_info['current_price']}
• 漲跌幅：{stock_info['change']}%
• 成交量：{stock_info['volume']:,}

技術分析
• 短期趨勢：{self._get_trend_description(stock_info)}
• 支撐位：${stock_info.get('support', '暫無數據')}
• 壓力位：${stock_info.get('resistance', '暫無數據')}

投資建議
• 短期：{self._get_short_term_advice(stock_info)}
• 中期：{self._get_mid_term_advice(stock_info)}
• 長期：{self._get_long_term_advice(stock_info)}

風險提醒：
投資有賺有賠，請審慎評估風險，並建議分散投資降低風險。

更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            return report

        except Exception as e:
            logger.error(f"分析股票時發生錯誤：{str(e)}")
            return """非常抱歉，在分析過程中遇到了一些技術問題

讓我們試試看：
1. 重新查詢一次
2. 換個時間再試
3. 查看其他股票資訊

您想要怎麼做呢？我很樂意協助您！"""

    def _get_trend_description(self, stock_info: Dict[str, Any]) -> str:
        """根據股票資訊生成趨勢描述"""
        if not stock_info.get('change'):
            return "持平"
        change = stock_info['change']
        if change > 3:
            return "強勢上漲"
        elif change > 0:
            return "緩步上揚"
        elif change > -3:
            return "輕微下跌"
        else:
            return "明顯下跌"

    def _get_short_term_advice(self, stock_info: Dict[str, Any]) -> str:
        """生成短期投資建議"""
        if not stock_info.get('change'):
            return "建議觀望，等待更明確的市場訊號"
        change = stock_info['change']
        if change > 5:
            return "注意獲利了結，留意回檔風險"
        elif change > 0:
            return "可小量承接，設好停損"
        elif change > -5:
            return "可逢低佈局，分批進場"
        else:
            return "等待企穩後再進場"

    def _get_mid_term_advice(self, stock_info: Dict[str, Any]) -> str:
        """生成中期投資建議"""
        return "關注產業發展和公司基本面，找適當進場點"

    def _get_long_term_advice(self, stock_info: Dict[str, Any]) -> str:
        """生成長期投資建議"""
        return "觀察公司營運與產業前景，做好資金配置"


# 建立全域分析器實例
analyzer = StockAnalyzer()
