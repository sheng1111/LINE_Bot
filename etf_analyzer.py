import requests
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
from database import db
import pandas as pd
import yfinance as yf
import time

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ETFAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(minutes=30)  # ETF 資料更新較慢，快取時間較長
        self.popular_etfs = ['0050', '0056',
                             '006208', '00878', '00692']  # 熱門 ETF 列表
        self.etf_list = {
            '0050.TW': '元大台灣50',      # 大盤型
            '0056.TW': '元大高股息',      # 高股息型
            '006208.TW': '富邦台50',      # 大盤型
            '00878.TW': '國泰永續高股息',  # 高股息型
            '00891.TW': '中信關鍵半導體',  # 半導體產業
            '00881.TW': '國泰台灣5G+'     # 5G通訊產業
        }
        self.industry_mapping = {
            '半導體': ['2330', '2303', '2317'],
            '金融': ['2881', '2882', '2891'],
            '電子': ['2317', '2324', '2357'],
            '傳產': ['1301', '1326', '1402'],
            '5G通訊': ['2454', '2317', '2324'],
            '其他': []
        }
        self.last_request_time = {}
        self.request_interval = 1  # 秒

    def _get_with_retry(self, etf_code: str, func: callable, max_retries: int = 3) -> Any:
        """帶有重試機制的請求函數"""
        for attempt in range(max_retries):
            try:
                # 檢查請求間隔
                current_time = time.time()
                if etf_code in self.last_request_time:
                    time_since_last = current_time - \
                        self.last_request_time[etf_code]
                    if time_since_last < self.request_interval:
                        time.sleep(self.request_interval - time_since_last)

                result = func(etf_code)
                self.last_request_time[etf_code] = time.time()
                return result

            except Exception as e:
                if "Too Many Requests" in str(e):
                    wait_time = (attempt + 1) * 5  # 遞增等待時間
                    logger.warning(f"請求過於頻繁，等待 {wait_time} 秒後重試")
                    time.sleep(wait_time)
                else:
                    logger.error(f"獲取 ETF {etf_code} 資訊時發生錯誤: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2)

    def get_etf_info(self, etf_code: str) -> Dict:
        """
        取得 ETF 基本資訊

        Args:
            etf_code: ETF 代碼

        Returns:
            Dict: ETF 資訊
        """
        try:
            # 檢查快取
            if etf_code in self.cache:
                cache_data = self.cache[etf_code]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 從資料庫查詢
            collection = db.get_collection('etf_info')
            etf_data = collection.find_one({'etf_code': etf_code})

            if etf_data:
                # 更新快取
                self.cache[etf_code] = {
                    'data': etf_data,
                    'timestamp': datetime.now()
                }
                return etf_data

            # 如果資料庫沒有，從 API 獲取
            # TODO: 實作實際的 ETF API 呼叫
            etf_data = {
                'etf_code': etf_code,
                'name': f'測試ETF_{etf_code}',
                'price': 100.0,
                'change': 1.5,
                'volume': 1000000,
                'yield_rate': 3.5,  # 殖利率
                'expense_ratio': 0.3,  # 管理費
                'timestamp': datetime.now()
            }

            # 儲存到資料庫
            collection.insert_one(etf_data)

            # 更新快取
            self.cache[etf_code] = {
                'data': etf_data,
                'timestamp': datetime.now()
            }

            return etf_data

        except Exception as e:
            logger.error(f"獲取 ETF 資訊時發生錯誤：{str(e)}")
            raise

    def get_etf_ranking(self) -> Dict[str, Any]:
        """獲取 ETF 排行"""
        try:
            # 檢查快取
            cache_key = "etf_ranking"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_ranking(code):
                etf = yf.Ticker(code)
                info = etf.info
                return {
                    'name': self.etf_list[code],
                    'price': info.get('regularMarketPrice', 0),
                    'change': info.get('regularMarketChangePercent', 0),
                    'volume': info.get('regularMarketVolume', 0)
                }

            ranking = {}
            for etf_code in self.etf_list.keys():
                ranking[etf_code] = self._get_with_retry(
                    etf_code, _fetch_ranking)

            # 更新快取
            self.cache[cache_key] = {
                'data': ranking,
                'timestamp': datetime.now()
            }

            return ranking
        except Exception as e:
            logger.error(f"獲取 ETF 排行時發生錯誤：{str(e)}")
            return {}

    def analyze_etf_overlap(self, etf_codes: List[str]) -> Dict[str, Any]:
        """分析 ETF 重疊成分股"""
        try:
            # 檢查快取
            cache_key = f"overlap_{'_'.join(sorted(etf_codes))}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_holdings(code):
                etf = yf.Ticker(code)
                return etf.get_holdings()

            overlap_stocks = {}
            for etf_code in etf_codes:
                holdings = self._get_with_retry(etf_code, _fetch_holdings)
                for _, row in holdings.iterrows():
                    stock_code = row['Symbol']
                    if stock_code not in overlap_stocks:
                        overlap_stocks[stock_code] = {'etfs': [], 'weight': 0}
                    overlap_stocks[stock_code]['etfs'].append(etf_code)
                    overlap_stocks[stock_code]['weight'] += row['% of Assets']

            # 過濾出重疊的股票
            result = {
                'timestamp': pd.Timestamp.now(),
                'overlap_stocks': {
                    code: info for code, info in overlap_stocks.items()
                    if len(info['etfs']) > 1
                }
            }

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"分析 ETF 重疊成分股時發生錯誤：{str(e)}")
            return {}

    def analyze_industry_distribution(self, etf_codes: List[str]) -> Dict[str, Any]:
        """分析 ETF 產業分布"""
        try:
            # 檢查快取
            cache_key = f"industry_{'_'.join(sorted(etf_codes))}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_holdings(code):
                etf = yf.Ticker(code)
                return etf.get_holdings()

            industry_dist = {}
            etf_comparison = {}

            for etf_code in etf_codes:
                holdings = self._get_with_retry(etf_code, _fetch_holdings)
                etf_comparison[etf_code] = {'industries': {}}

                for _, row in holdings.iterrows():
                    stock_code = row['Symbol']
                    weight = row['% of Assets']

                    # 找出股票所屬產業
                    for industry, stocks in self.industry_mapping.items():
                        if stock_code in stocks:
                            if industry not in industry_dist:
                                industry_dist[industry] = 0
                            industry_dist[industry] += weight
                            etf_comparison[etf_code]['industries'][industry] = \
                                etf_comparison[etf_code]['industries'].get(
                                    industry, 0) + weight
                            break

            result = {
                'industry_distribution': industry_dist,
                'etf_comparison': etf_comparison
            }

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"分析產業分布時發生錯誤：{str(e)}")
            return {}

    def compare_etf_fees(self, etf_codes: List[str]) -> Dict[str, Any]:
        """比較 ETF 費用率"""
        try:
            # 檢查快取
            cache_key = f"fees_{'_'.join(sorted(etf_codes))}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            def _fetch_fees(code):
                etf = yf.Ticker(code)
                info = etf.info
                return {
                    'name': self.etf_list[code],
                    'expense_ratio': info.get('annualReportExpenseRatio', 0),
                    'aum': info.get('totalAssets', 0)
                }

            fee_comparison = {}
            for etf_code in etf_codes:
                fee_comparison[etf_code] = self._get_with_retry(
                    etf_code, _fetch_fees)

            # 生成建議
            sorted_fees = sorted(
                fee_comparison.items(),
                key=lambda x: x[1]['expense_ratio']
            )
            recommendation = {
                'lowest_fee': sorted_fees[0][0],
                'highest_fee': sorted_fees[-1][0],
                'average_fee': sum(x[1]['expense_ratio'] for x in sorted_fees) / len(sorted_fees)
            }

            result = {
                'fee_comparison': fee_comparison,
                'recommendation': recommendation
            }

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result
        except Exception as e:
            logger.error(f"比較 ETF 費用率時發生錯誤：{str(e)}")
            return {}

    def format_overlap_analysis(self, analysis: Dict[str, Any]) -> str:
        """格式化重疊分析結果"""
        if not analysis or 'overlap_stocks' not in analysis:
            return "無法取得 ETF 重疊分析結果"

        result = "📊 ETF 重疊成分股分析\n\n"
        for stock_code, info in analysis['overlap_stocks'].items():
            etf_names = [self.etf_list[etf] for etf in info['etfs']]
            result += f"股票代碼：{stock_code}\n"
            result += f"出現於：{', '.join(etf_names)}\n"
            result += f"總權重：{info['weight']:.2f}%\n"
            result += "---\n"

        result += "\n📝 分析說明：\n"
        result += "1. 本分析包含以下 ETF：\n"
        for code, name in self.etf_list.items():
            result += f"   - {code}: {name}\n"
        result += "2. 每月 14 日自動更新\n"
        result += "3. 建議關注重疊度高且權重大的股票"

        return result


# 建立全域分析器實例
analyzer = ETFAnalyzer()


def analyze_etf_overlap(etf_codes: List[str] = ['0050.TW', '0056.TW', '006208.TW']) -> Dict:
    """
    分析多個 ETF 的重疊成分股
    :param etf_codes: ETF 代碼列表
    :return: 重疊成分股資訊
    """
    try:
        overlap_stocks = {}
        etf_holdings = {}

        # 獲取每個 ETF 的成分股
        for etf_code in etf_codes:
            etf = yf.Ticker(etf_code)
            holdings = etf.get_holdings()
            etf_holdings[etf_code] = holdings

            # 統計每個股票出現的次數
            for stock in holdings.index:
                if stock in overlap_stocks:
                    overlap_stocks[stock]['count'] += 1
                    overlap_stocks[stock]['etfs'].append(etf_code)
                else:
                    overlap_stocks[stock] = {
                        'count': 1,
                        'etfs': [etf_code],
                        'name': holdings.loc[stock, 'Name'] if 'Name' in holdings.columns else 'Unknown'
                    }

        # 找出重疊的股票
        result = {
            'timestamp': datetime.now(),
            'overlap_stocks': {
                stock: info for stock, info in overlap_stocks.items()
                if info['count'] > 1
            },
            'etf_holdings': etf_holdings
        }

        # 保存到資料庫
        collection = db.get_collection('etf_overlap_analysis')
        collection.insert_one(result)

        return result
    except Exception as e:
        logger.error(f"分析 ETF 重疊成分股時發生錯誤: {str(e)}")
        return None


def format_overlap_analysis(analysis: Dict) -> str:
    """
    格式化重疊分析結果為易讀的字符串
    :param analysis: 分析結果
    :return: 格式化後的字符串
    """
    if not analysis or 'overlap_stocks' not in analysis:
        return "無法獲取 ETF 重疊分析結果。"

    result = "📊 ETF 重疊成分股分析\n\n"

    for stock, info in analysis['overlap_stocks'].items():
        result += f"📈 {stock} ({info['name']})\n"
        result += f"   📌 出現在 {info['count']} 個 ETF 中\n"
        result += f"   📋 ETF 列表: {', '.join(info['etfs'])}\n\n"

    result += f"⏰ 分析時間: {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
    return result
