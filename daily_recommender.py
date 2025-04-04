import logging
from datetime import datetime, timedelta
from typing import List, Dict
from database import db
from stock_analyzer import analyzer
from etf_analyzer import analyzer as etf_analyzer
from gemini_client import gemini
import random

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DailyRecommender:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = {}
        self.cache_timeout = timedelta(hours=24)  # 每日更新一次
        self.popular_stocks = ['2330', '2317',
                               '2454', '2303', '2308']  # 熱門股票列表

    def _generate_market_overview(self):
        """生成市場概況的模擬數據"""
        try:
            market_overview = {
                'market_trend': random.choice(['上漲', '下跌', '盤整']),
                'market_sentiment': random.choice(['樂觀', '中性', '謹慎']),
                'key_indices': {
                    '台股': random.uniform(-2, 2),
                    '美股': random.uniform(-2, 2),
                    '亞股': random.uniform(-2, 2)
                },
                'key_sectors': {
                    '半導體': random.uniform(-3, 3),
                    '金融': random.uniform(-2, 2),
                    '傳產': random.uniform(-1, 1)
                },
                'risk_factors': [
                    '全球經濟成長預期',
                    '通膨壓力',
                    '地緣政治風險'
                ]
            }
            return market_overview
        except Exception as e:
            self.logger.error(f"生成市場概況時發生錯誤：{str(e)}")
            return None

    def get_market_overview(self) -> str:
        """
        獲取市場概況

        Returns:
            市場概況字串
        """
        try:
            # 檢查快取
            cache_key = 'market_overview'
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if datetime.now() - cache_data['timestamp'] < self.cache_timeout:
                    return cache_data['data']

            # 從資料庫查詢
            collection = db.get_collection('market_overview')
            overview = collection.find_one({
                'date': datetime.now().strftime('%Y-%m-%d')
            })

            if overview:
                # 更新快取
                self.cache[cache_key] = {
                    'data': overview['content'],
                    'timestamp': datetime.now()
                }
                return overview['content']

            # 如果資料庫沒有，生成新的概況
            content = self._generate_market_overview()

            # 儲存到資料庫
            collection.insert_one({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'content': content,
                'timestamp': datetime.now()
            })

            # 更新快取
            self.cache[cache_key] = {
                'data': content,
                'timestamp': datetime.now()
            }

            return content

        except Exception as e:
            logger.error(f"獲取市場概況時發生錯誤：{str(e)}")
            return "抱歉，目前無法取得市場概況。"

    def get_stock_recommendations(self) -> List[Dict]:
        """
        取得股票推薦列表

        Returns:
            List[Dict]: 推薦股票列表
        """
        try:
            recommendations = []

            # 隨機選擇 3 支股票進行分析
            selected_stocks = random.sample(
                self.popular_stocks, min(3, len(self.popular_stocks)))

            for stock_code in selected_stocks:
                try:
                    stock_info = analyzer.get_stock_info(stock_code)
                    recommendations.append({
                        'stock_code': stock_code,
                        'name': stock_info['name'],
                        'price': stock_info['price'],
                        'change': stock_info['change'],
                        'analysis': analyzer.analyze_stock(stock_code)
                    })
                except Exception as e:
                    logger.error(f"分析股票 {stock_code} 時發生錯誤：{str(e)}")
                    continue

            return recommendations

        except Exception as e:
            logger.error(f"生成股票推薦時發生錯誤：{str(e)}")
            return []

    def get_etf_recommendations(self) -> List[Dict]:
        """
        取得 ETF 推薦列表

        Returns:
            List[Dict]: 推薦 ETF 列表
        """
        try:
            recommendations = []

            # 獲取所有熱門 ETF 的資訊
            for etf_code in etf_analyzer.popular_etfs:
                try:
                    etf_info = etf_analyzer.get_etf_info(etf_code)
                    recommendations.append({
                        'etf_code': etf_code,
                        'name': etf_info['name'],
                        'price': etf_info['price'],
                        'yield_rate': etf_info['yield_rate'],
                        'expense_ratio': etf_info['expense_ratio']
                    })
                except Exception as e:
                    logger.error(f"分析 ETF {etf_code} 時發生錯誤：{str(e)}")
                    continue

            return recommendations

        except Exception as e:
            logger.error(f"生成 ETF 推薦時發生錯誤：{str(e)}")
            return []

    def generate_daily_recommendation(self, user_id: str = "system") -> str:
        """
        生成每日投資建議

        Args:
            user_id: 使用者 ID，預設為 "system"

        Returns:
            每日投資建議
        """
        try:
            # 獲取市場概況
            market_overview = self.get_market_overview()
            if not market_overview:
                return "抱歉，無法獲取市場概況，請稍後再試。"

            # 獲取股票推薦
            stock_recommendations = self.get_stock_recommendations()
            if not stock_recommendations:
                return "抱歉，無法獲取股票推薦，請稍後再試。"

            # 獲取 ETF 推薦
            etf_recommendations = self.get_etf_recommendations()
            if not etf_recommendations:
                return "抱歉，無法獲取 ETF 推薦，請稍後再試。"

            # 生成建議
            prompt = f"""
            請根據以下資訊生成今日投資建議：

            市場概況：
            {market_overview}

            股票推薦：
            {stock_recommendations}

            ETF 推薦：
            {etf_recommendations}

            請提供：
            1. 市場趨勢分析
            2. 投資建議
            3. 風險提示
            4. 操作策略
            """

            # 使用 Gemini 生成建議
            response = gemini.generate_response(prompt, user_id)
            return response

        except Exception as e:
            logger.error(f"生成每日建議時發生錯誤：{str(e)}")
            return "抱歉，生成每日建議時發生錯誤，請稍後再試。"


# 建立全域推薦器實例
recommender = DailyRecommender()
