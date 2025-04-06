import requests
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
import logging
from datetime import datetime, timedelta
from database import db
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from stock_info import get_stock_info, format_stock_info

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 快取時間 5 分鐘
        self.technical_indicators = {
            'bollinger_bands': self._calculate_bollinger_bands,
            'support_resistance': self._calculate_support_resistance,
            'volume_analysis': self._analyze_volume
        }
        self.last_request_time = {}
        self.request_interval = 5  # 證交所 API 可以更頻繁請求
        self.max_retries = 2
        self.retry_delay = 5

        # 設定 requests session
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        取得股票基本資訊，使用證交所 API
        """
        try:
            # 檢查快取
            cache_key = f"info_{stock_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 組合API需要的股票清單字串
            stock_list = f'tse_{stock_code}.tw'

            # 組合完整的URL
            query_url = f'http://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={stock_list}'

            # 呼叫股票資訊API
            response = requests.get(query_url)

            if response.status_code != 200:
                raise Exception('取得股票資訊失敗')

            data = response.json()

            if not data or 'msgArray' not in data or not data['msgArray']:
                raise Exception('無股票資料')

            stock_data = data['msgArray'][0]

            # 確保所有必要的欄位都存在且有效
            if not all(key in stock_data for key in ['c', 'n', 'z', 'y', 'v', 'h', 'l', 'o']):
                raise Exception('股票資料不完整')

            # 安全地轉換數值
            try:
                price = float(stock_data['z']) if stock_data['z'] else 0
                prev_price = float(stock_data['y']) if stock_data['y'] else price
                volume = int(stock_data['v']) if stock_data['v'] else 0
                high = float(stock_data['h']) if stock_data['h'] else price
                low = float(stock_data['l']) if stock_data['l'] else price
                open_price = float(stock_data['o']) if stock_data['o'] else price

                # 計算漲跌幅
                change = price - prev_price
                change_percent = (change / prev_price * 100) if prev_price > 0 else 0

                result = {
                    'code': stock_data['c'],
                    'name': stock_data['n'],
                    'price': price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': volume,
                    'high': high,
                    'low': low,
                    'open': open_price,
                    'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except (ValueError, TypeError) as e:
                raise Exception(f'處理股票數據時發生錯誤: {str(e)}')

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"獲取股票資訊時發生錯誤：{str(e)}")
            return {
                'error': f'獲取股票資訊時發生錯誤：{str(e)}',
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

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

    def analyze_stock(self, stock_code: str) -> Dict[str, Any]:
        """
        分析股票
        :param stock_code: 股票代碼
        :return: 分析結果
        """
        try:
            # 檢查快取
            if stock_code in self.cache:
                cache_data = self.cache[stock_code]
                if (datetime.now() - cache_data['timestamp']).total_seconds() < self.cache_timeout:
                    return cache_data['data']

            # 獲取股票資訊
            stock_info = self.get_stock_info(stock_code)
            if not stock_info or 'error' in stock_info:
                return {'error': '無法獲取股票資訊'}

            # 從資料庫獲取歷史資料
            collection = db.get_collection('stock_history')
            history = collection.find_one({'stock_code': stock_code})

            # 生成分析結果
            result = {
                'stock_code': stock_code,
                'current_price': stock_info['price'],
                'change': stock_info['change'],
                'change_percent': stock_info['change_percent'],
                'volume': stock_info['volume'],
                'pe_ratio': history.get('pe_ratio', 0) if history else 0,
                'dividend_yield': history.get('dividend_yield', 0) if history else 0,
                'market_cap': history.get('market_cap', 0) if history else 0,
                'analysis_time': datetime.now()
            }

            # 更新快取
            self.cache[stock_code] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result

        except Exception as e:
            logger.error(f"分析股票時發生錯誤：{str(e)}")
            return {'error': f'分析股票時發生錯誤：{str(e)}'}

    def format_analysis(self, analysis: Dict[str, Any]) -> str:
        """
        格式化分析結果
        :param analysis: 分析結果
        :return: 格式化後的字串
        """
        if 'error' in analysis:
            return f"分析失敗：{analysis['error']}"

        change_emoji = "📈" if analysis['change'] >= 0 else "📉"

        return f"""
📊 {analysis['stock_code']} 分析報告

💰 當前價格: {analysis['current_price']}
{change_emoji} 漲跌幅: {analysis['change']} ({analysis['change_percent']:.2f}%)
📊 成交量: {analysis['volume']:,}
📈 本益比: {analysis['pe_ratio']:.2f}
💰 殖利率: {analysis['dividend_yield']:.2f}%
💵 市值: {analysis['market_cap']:,.0f}

⏰ 分析時間: {analysis['analysis_time'].strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _get_trend_description(self, stock_info: Dict[str, Any]) -> str:
        """根據股票資訊生成趨勢描述"""
        if not stock_info.get('change_percent'):
            return "持平"
        change = stock_info['change_percent']
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
        if not stock_info.get('change_percent'):
            return "建議觀望，等待更明確的市場訊號"
        change = stock_info['change_percent']
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
        if not stock_info.get('change_percent'):
            return "關注產業發展和公司基本面，找適當進場點"
        change = stock_info['change_percent']
        if change > 0:
            return "可考慮分批布局，注意產業動態"
        else:
            return "等待更好的進場時機，關注公司基本面"

    def _get_long_term_advice(self, stock_info: Dict[str, Any]) -> str:
        """生成長期投資建議"""
        if not stock_info.get('change_percent'):
            return "觀察公司營運與產業前景，做好資金配置"
        change = stock_info['change_percent']
        if change > 0:
            return "可考慮長期持有，定期檢視公司營運狀況"
        else:
            return "等待更好的進場點，長期投資需耐心"

    def _get_with_retry(self, stock_code: str, func: callable) -> Dict[str, Any]:
        """重試機制"""
        for _ in range(self.max_retries):
            try:
                ticker = yf.Ticker(stock_code)
                result = func(ticker)
                return result
            except Exception as e:
                logger.warning(f"重試 {_ + 1} 失敗，原因：{str(e)}")
                time.sleep(self.retry_delay)
        logger.error(f"所有重試均失敗，無法獲取股票 {stock_code} 的資訊")
        return {}


# 建立全域分析器實例
analyzer = StockAnalyzer()
