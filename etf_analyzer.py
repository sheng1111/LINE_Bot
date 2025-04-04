import requests
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
from database import db
import pandas as pd

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ETFAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = timedelta(minutes=30)  # ETF 資料更新較慢，快取時間較長
        self.popular_etfs = ['0050', '0056',
                             '006208', '00878', '00692']  # 熱門 ETF 列表

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

    def get_etf_ranking(self) -> str:
        """
        取得熱門 ETF 排行

        Returns:
            str: 排行報告
        """
        try:
            etf_list = []

            # 獲取所有熱門 ETF 的資訊
            for etf_code in self.popular_etfs:
                try:
                    etf_info = self.get_etf_info(etf_code)
                    etf_list.append(etf_info)
                except Exception as e:
                    logger.error(f"獲取 ETF {etf_code} 資訊時發生錯誤：{str(e)}")
                    continue

            if not etf_list:
                return "抱歉，目前無法取得 ETF 排行資訊。"

            # 使用 pandas 進行排序
            df = pd.DataFrame(etf_list)
            df = df.sort_values('yield_rate', ascending=False)

            # 生成排行報告
            report = "📊 熱門 ETF 排行（依殖利率排序）\n\n"
            for idx, row in df.iterrows():
                report += f"{row['etf_code']} {row['name']}\n"
                report += f"價格：{row['price']} 漲跌幅：{row['change']}%\n"
                report += f"殖利率：{row['yield_rate']}% 管理費：{row['expense_ratio']}%\n"
                report += "-------------------\n"

            return report

        except Exception as e:
            logger.error(f"生成 ETF 排行時發生錯誤：{str(e)}")
            return "抱歉，生成 ETF 排行時發生錯誤，請稍後再試。"


# 建立全域分析器實例
analyzer = ETFAnalyzer()
