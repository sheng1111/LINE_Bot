import requests
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
from database import db
import pandas as pd
import time
import json

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 台灣證交所 API 設定
TWSE_API_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
ETF_INFO_URL = "https://www.twse.com.tw/rwd/zh/ETF/etfBasicInfo"
ETF_PRICE_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


class ETFAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(minutes=30)  # ETF 資料更新較慢，快取時間較長
        self.popular_etfs = ['0050', '0056',
                             '006208', '00878', '00692']  # 熱門 ETF 列表
        self.etf_list = {
            '0050': '元大台灣50',      # 大盤型
            '0056': '元大高股息',      # 高股息型
            '006208': '富邦台50',      # 大盤型
            '00878': '國泰永續高股息',  # 高股息型
            '00891': '中信關鍵半導體',  # 半導體產業
            '00881': '國泰台灣5G+'     # 5G通訊產業
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
        self.request_interval = 5  # 增加到 5 秒
        self.max_retries = 3
        self.retry_delay = 5  # 重試等待時間

    def _get_with_retry(self, etf_code: str, func: callable) -> Any:
        """帶有重試機制的請求函數"""
        for attempt in range(self.max_retries):
            try:
                # 檢查請求間隔
                current_time = time.time()
                if etf_code in self.last_request_time:
                    time_since_last = current_time - \
                        self.last_request_time[etf_code]
                    if time_since_last < self.request_interval:
                        wait_time = self.request_interval - time_since_last
                        logger.warning(f"請求過於頻繁，等待 {int(wait_time)} 秒後重試")
                        time.sleep(wait_time)

                result = func(etf_code)
                if result is None:  # 如果結果為 None，視為失敗
                    raise ValueError("API returned None")

                self.last_request_time[etf_code] = time.time()
                return result

            except Exception as e:
                if "Too Many Requests" in str(e):
                    wait_time = (attempt + 1) * self.retry_delay
                    logger.warning(f"請求過於頻繁，等待 {wait_time} 秒後重試")
                    time.sleep(wait_time)
                else:
                    logger.error(f"獲取 ETF {etf_code} 資訊時發生錯誤: {str(e)}")
                    if attempt == self.max_retries - 1:  # 最后一次嘗試
                        return {}  # 返回空字典而不是 None
                    time.sleep(self.retry_delay)

        return {}  # 所有重試都失敗後返回空字典

    def _fetch_etf_info(self, etf_code: str) -> Optional[Dict]:
        """
        從證交所 API 獲取 ETF 資訊
        :param etf_code: ETF 代碼
        :return: ETF 資訊字典
        """
        try:
            # 保存原始代碼
            original_code = etf_code
            
            # 獲取 ETF 價格資訊 - 使用證交所即時行情 API
            price_url = f"{ETF_PRICE_URL}?ex_ch=tse_{original_code}.tw"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://mis.twse.com.tw/stock/index.jsp'
            }
            
            # 先從即時行情 API 獲取價格資訊
            price_response = requests.get(price_url, headers=headers, timeout=10)
            if price_response.status_code == 200:
                price_data = price_response.json()
                if price_data.get('msgArray') and len(price_data['msgArray']) > 0:
                    price_info = price_data['msgArray'][0]
                    
                    # 如果成功獲取價格資訊，則不需要再查詢基本資訊
                    # 直接返回結果
                    etf_name = price_info.get('n', f'ETF_{original_code}')
                    
                    return {
                        'etf_code': original_code,
                        'name': etf_name,
                        'price': float(price_info.get('z', 0)) if price_info.get('z') and price_info.get('z') != '-' else 0,
                        'change': float(price_info.get('z', 0)) - float(price_info.get('y', 0)) if price_info.get('z') and price_info.get('y') and price_info.get('z') != '-' and price_info.get('y') != '-' else 0,
                        'volume': int(price_info.get('v', 0)) if price_info.get('v') and price_info.get('v') != '-' else 0,
                        'yield_rate': 0,  # 預設值
                        'expense_ratio': 0,  # 預設值
                        'timestamp': datetime.now()
                    }
                else:
                    price_info = None
            else:
                price_info = None
                
            # 如果無法從即時行情 API 獲取資訊，嘗試從 ETF 基本資訊 API 獲取
            # 正規化 ETF 代碼格式以符合基本資訊 API 的要求
            if len(etf_code) == 4 and etf_code.isdigit():
                etf_code = '00' + etf_code  # 例如：0050 -> 000050
            elif len(etf_code) == 5 and etf_code.isdigit():
                etf_code = '0' + etf_code  # 例如：00692 -> 000692
            
            # 獲取 ETF 基本資訊
            url = f"{ETF_INFO_URL}?stockNo={etf_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://www.twse.com.tw/rwd/zh/ETF/etfBasicInfo'
            }

            # 獲取 ETF 基本資訊
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 檢查回應內容
            if not response.text.strip():
                logger.error(f"API 返回空資料：{etf_code}")
                return None

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"解析 API 回應失敗：{str(e)}")
                return None

            if not data or not isinstance(data, dict) or 'data' not in data or not data['data']:
                logger.error(f"API 返回無效資料：{etf_code}")
                return None

            # 解析基本資訊
            if 'data' in data and data['data'] and len(data['data']) > 0:
                etf_data = data['data'][0]
                # 先從 API 結果取得名稱，如果沒有則從預設列表取得
                etf_name = etf_data[0] if etf_data and len(etf_data) > 0 else self.etf_list.get(original_code, f'ETF_{original_code}')
            else:
                etf_name = self.etf_list.get(original_code, f'ETF_{original_code}')
            
            # 無論如何都使用預設值
            price = 100.0
            change = 0
            volume = 0

            # 解析費率和殖利率
            try:
                yield_rate = float(etf_data[3].replace('%', '')) if len(etf_data) > 3 and etf_data[3] else 0
                expense_ratio = float(etf_data[4].replace('%', '')) if len(etf_data) > 4 and etf_data[4] else 0
            except (ValueError, IndexError):
                yield_rate = 0
                expense_ratio = 0

            return {
                'etf_code': original_code,  # 返回原始代碼以便前端顯示
                'name': etf_name,
                'price': price,
                'change': change,
                'volume': volume,
                'yield_rate': yield_rate,
                'expense_ratio': expense_ratio,
                'timestamp': datetime.now()
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"API 請求失敗：{str(e)}")
            return None
        except Exception as e:
            logger.error(f"獲取 ETF 資訊時發生錯誤：{str(e)}")
            return None

    def get_etf_info(self, etf_code: str) -> Dict:
        """
        取得 ETF 基本資訊
        :param etf_code: ETF 代碼
        :return: ETF 資訊
        """
        try:
            # 保存原始代碼以便查詢價格
            original_code = etf_code
            
            # 檢查 ETF 代碼是否有效
            if not etf_code.isdigit() or len(etf_code) not in [4, 5, 6]:
                logger.error(f"無效的 ETF 代碼格式：{etf_code}")
                return {'error': f'無效的 ETF 代碼格式：{etf_code}'}

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

            # 從即時行情 API 獲取價格資訊
            price_url = f"{ETF_PRICE_URL}?ex_ch=tse_{original_code}.tw"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://mis.twse.com.tw/stock/index.jsp'
            }
            
            try:
                price_response = requests.get(price_url, headers=headers, timeout=10)
                if price_response.status_code == 200:
                    price_data = price_response.json()
                    if price_data.get('msgArray') and len(price_data['msgArray']) > 0:
                        price_info = price_data['msgArray'][0]
                        
                        # 如果成功獲取價格資訊，則直接返回結果
                        etf_name = price_info.get('n', f'ETF_{original_code}')
                        
                        etf_data = {
                            'etf_code': original_code,
                            'name': etf_name,
                            'price': float(price_info.get('z', 0)) if price_info.get('z') and price_info.get('z') != '-' else 0,
                            'change': float(price_info.get('z', 0)) - float(price_info.get('y', 0)) if price_info.get('z') and price_info.get('y') and price_info.get('z') != '-' and price_info.get('y') != '-' else 0,
                            'volume': int(price_info.get('v', 0)) if price_info.get('v') and price_info.get('v') != '-' else 0,
                            'yield_rate': 0,  # 預設值
                            'expense_ratio': 0,  # 預設值
                            'timestamp': datetime.now()
                        }
                        
                        # 更新快取
                        self.cache[original_code] = {
                            'data': etf_data,
                            'timestamp': datetime.now()
                        }
                        
                        return etf_data
            except Exception as e:
                logger.warning(f"從即時行情 API 獲取 ETF {original_code} 資訊失敗：{str(e)}")
            
            # 如果無法從即時行情 API 獲取資訊，嘗試從 ETF 基本資訊 API 獲取
            # 如果是 4 位數代碼，轉換為 6 位數格式
            if len(etf_code) == 4 and etf_code.isdigit():
                etf_code = '00' + etf_code  # 例如：0050 -> 000050
            # 如果是 5 位數代碼，轉換為 6 位數格式
            elif len(etf_code) == 5 and etf_code.isdigit():
                etf_code = '0' + etf_code  # 例如：00692 -> 000692
                
            # 從證交所 API 獲取
            etf_data = self._get_with_retry(etf_code, self._fetch_etf_info)

            if not etf_data:
                return {'error': f'無法獲取 ETF {etf_code} 的資訊，請確認代碼是否正確'}

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
            return {'error': f'獲取 ETF {etf_code} 的資訊時發生錯誤：{str(e)}'}

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
                # 實現獲取 ETF 排行的邏輯
                # 這裡需要根據實際情況實現
                pass

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

    def fetch_etf_holdings(self, etf_code: str) -> List[str]:
        """
        從台灣證交所獲取 ETF 成分股資料
        :param etf_code: ETF 代碼
        :return: 成分股代碼列表
        """
        try:
            # 獲取當前日期
            today = datetime.now()
            date_str = today.strftime('%Y%m%d')
            
            # 構建 API URL
            url = f"https://www.twse.com.tw/rwd/zh/ETF/etfComposition?date={date_str}&stockNo={etf_code}"
            
            # 添加請求頭，模擬瀏覽器行為
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://www.twse.com.tw/'
            }
            
            # 發送請求
            response = requests.get(url, headers=headers, timeout=10)
            
            # 檢查響應
            if response.status_code != 200:
                logger.error(f"獲取 ETF {etf_code} 成分股失敗: HTTP {response.status_code}")
                return []
            
            # 解析 JSON 響應
            data = response.json()
            
            # 檢查數據格式
            if 'data' not in data:
                logger.error(f"獲取 ETF {etf_code} 成分股失敗: 無效的數據格式")
                return []
            
            # 提取成分股代碼
            holdings = []
            for item in data['data']:
                if len(item) >= 2:  # 確保有足夠的列
                    stock_code = item[0].strip()
                    if stock_code.isdigit():  # 確保是有效的股票代碼
                        holdings.append(stock_code)
            
            logger.info(f"成功獲取 ETF {etf_code} 的 {len(holdings)} 個成分股")
            
            # 更新資料庫
            collection = db.get_collection('etf_holdings')
            collection.update_one(
                {'etf_code': etf_code},
                {
                    '$set': {
                        'holdings': holdings,
                        'updated_at': datetime.now()
                    }
                },
                upsert=True
            )
            
            return holdings
        
        except Exception as e:
            logger.error(f"獲取 ETF {etf_code} 成分股時發生錯誤: {str(e)}")
            return []
    
    def analyze_etf_overlap(self, etf_codes: List[str]) -> Dict[str, Any]:
        """分析 ETF 重疊成分股"""
        try:
            # 檢查快取
            cache_key = f"overlap_{'_'.join(sorted(etf_codes))}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 直接從網路獲取最新的 ETF 成分股資料
            overlap_stocks = {}

            for etf_code in etf_codes:
                # 獲取 ETF 成分股
                holdings = self.fetch_etf_holdings(etf_code)
                
                # 如果無法從網路獲取，嘗試從資料庫獲取
                if not holdings:
                    collection = db.get_collection('etf_holdings')
                    etf_data = collection.find_one({'etf_code': etf_code})
                    if etf_data and 'holdings' in etf_data:
                        holdings = etf_data['holdings']
                
                # 處理成分股資料
                if holdings:
                    for stock_code in holdings:
                        if stock_code not in overlap_stocks:
                            overlap_stocks[stock_code] = {
                                'etfs': [], 'weight': 1.0  # 使用預設權重
                            }
                        overlap_stocks[stock_code]['etfs'].append(etf_code)

            # 過濾出重疊的股票
            result = {
                'timestamp': datetime.now(),
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
                # 實現獲取 ETF 成分股的邏輯
                # 這裡需要根據實際情況實現
                pass

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
                # 實現獲取 ETF 費用率的邏輯
                # 這裡需要根據實際情況實現
                pass

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
            return """目前無法完成 ETF 重疊分析，可能原因如下：
1. 資料暫時無法取得
2. ETF 代碼有誤
3. 系統處理中斷

建議您：
1. 確認 ETF 代碼是否正確
2. 稍後再試一次
3. 可先查看單一 ETF 的資訊
4. 需要我幫您查詢個別 ETF 嗎？
5. 禁止回答 Markdown、符號、表情符號"""

        result = """🔍 ETF 重疊持股分析報告

以下是您關注的 ETF 中重疊的持股：\n\n"""

        # 按權重排序
        sorted_stocks = sorted(
            analysis['overlap_stocks'].items(),
            key=lambda x: x[1]['weight'],
            reverse=True
        )

        for stock_code, info in sorted_stocks:
            etf_names = [self.etf_list.get(etf, etf) for etf in info['etfs']]
            result += f"""📊 {stock_code}
• 出現於：{', '.join(etf_names)}
• 總權重：{info['weight']:.2f}%
{'• 建議關注！' if info['weight'] > 10 else ''}
───────────────\n"""

        result += """\n💡 分析重點：
1. 重疊度高的股票可能對多檔 ETF 都有重要影響
2. 總權重越高，代表該股票在這些 ETF 中的影響力越大
3. 建議關注權重超過 10% 的重疊股票

⚠️ 注意事項：
• ETF 成分股會定期調整
• 投資時請考慮個人風險承受度
• 建議適度分散投資降低風險
• 禁止回答 Markdown、符號、表情符號

更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return result

    def analyze_etf(self, etf_code: str) -> Dict:
        """
        分析單一 ETF
        :param etf_code: ETF 代碼
        :return: 分析結果字典
        """
        try:
            # 檢查快取
            cache_key = f"analysis_{etf_code}"
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 獲取 ETF 基本資訊
            etf_info = self.get_etf_info(etf_code)
            if not etf_info or 'error' in etf_info:
                return {'error': f'無法獲取 ETF {etf_code} 的資訊'}

            # 從資料庫獲取成分股資料
            collection = db.get_collection('etf_holdings')
            holdings_data = collection.find_one({'etf_code': etf_code})

            # 分析產業分布
            industry_dist = {}
            top_holdings = []

            if holdings_data:
                for stock in holdings_data.get('holdings', []):
                    stock_code = stock.get('code')
                    weight = stock.get('weight', 0)

                    # 找出股票所屬產業
                    for industry, stocks in self.industry_mapping.items():
                        if stock_code in stocks:
                            if industry not in industry_dist:
                                industry_dist[industry] = 0
                            industry_dist[industry] += weight
                            break

                    # 記錄前十大持股
                    if len(top_holdings) < 10:
                        top_holdings.append({
                            'code': stock_code,
                            'name': stock.get('name', 'Unknown'),
                            'weight': weight
                        })

            # 生成分析結果
            result = {
                'etf_code': etf_code,
                'name': etf_info['name'],
                'price': etf_info['price'],
                'yield_rate': etf_info['yield_rate'],
                'expense_ratio': etf_info['expense_ratio'],
                'industry_distribution': industry_dist,
                'top_holdings': top_holdings,
                'total_holdings': len(holdings_data.get('holdings', [])) if holdings_data else 0,
                'analysis_time': datetime.now()
            }

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result

        except Exception as e:
            logger.error(f"分析 ETF {etf_code} 時發生錯誤：{str(e)}")
            return {'error': f'分析 ETF {etf_code} 時發生錯誤：{str(e)}'}

    def format_etf_analysis(self, analysis: Dict) -> str:
        """
        格式化 ETF 分析結果
        :param analysis: 分析結果字典
        :return: 格式化後的字符串
        """
        if not analysis or 'error' in analysis:
            return "無法獲取 ETF 分析結果。"

        try:
            # 確保價格和比率有正確的格式
            price = analysis['price'] if analysis['price'] else 0
            yield_rate = analysis['yield_rate'] if analysis['yield_rate'] else 0
            expense_ratio = analysis['expense_ratio'] if analysis['expense_ratio'] else 0
            total_holdings = analysis.get('total_holdings', 0)
            
            result = f"""📊 {analysis['name']} ({analysis['etf_code']}) 分析報告

💰 基本資訊：
• 當前價格：{price}
• 殖利率：{yield_rate:.2f}%
• 費用率：{expense_ratio:.2f}%
• 總持股數：{total_holdings}

📈 產業分布："""

            if analysis['industry_distribution']:
                for industry, weight in analysis['industry_distribution'].items():
                    result += f"\n• {industry}：{weight:.2f}%"
            else:
                result += "\n• 暫無產業分布資料"

            result += "\n\n🏆 前十大持股："
            if analysis['top_holdings']:
                for holding in analysis['top_holdings']:
                    result += f"\n• {holding['code']} ({holding['name']})：{holding['weight']:.2f}%"
            else:
                result += "\n• 暫無持股資料"

            result += f"\n\n⏰ 更新時間：{analysis['analysis_time'].strftime('%Y-%m-%d %H:%M:%S')}"

            return result

        except Exception as e:
            logger.error(f"格式化 ETF 分析結果時發生錯誤：{str(e)}")
            return "格式化分析結果時發生錯誤。"


# 建立全域分析器實例
analyzer = ETFAnalyzer()


def analyze_etf_overlap(etf_codes: List[str] = ['0050', '0056', '006208']) -> Dict:
    """
    分析多個 ETF 的重疊成分股
    :param etf_codes: ETF 代碼列表
    :return: 重疊成分股資訊
    """
    try:
        # 使用 ETFAnalyzer 實例進行分析
        return analyzer.analyze_etf_overlap(etf_codes)
    except Exception as e:
        logger.error(f"分析 ETF 重疊成分股時發生錯誤: {str(e)}")
        return None


def format_overlap_analysis(analysis: Dict) -> str:
    """
    格式化重疊分析結果為易讀的字符串
    :param analysis: 分析結果
    :return: 格式化後的字符串
    """
    if not analysis:
        return "無法獲取 ETF 重疊分析結果。"

    return analyzer.format_overlap_analysis(analysis)
