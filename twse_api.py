import logging
import requests
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import time
import xml.etree.ElementTree as ET
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TWSEAPI:
    def __init__(self):
        self.base_url = "https://openapi.twse.com.tw/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }

    def _make_request(self, url: str, params: dict = None, max_retries: int = 3) -> dict:
        """
        發送 API 請求
        :param url: API URL
        :param params: 請求參數
        :param max_retries: 最大重試次數
        :return: API 回應
        """
        # 確保 URL 是完整的
        if not url.startswith('http'):
            url = f"{self.base_url}/{url.lstrip('/')}"

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()

                # 檢查回應內容是否為有效的 JSON
                try:
                    data = response.json()
                    if not data:
                        raise ValueError("API 回應為空")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(
                        f"API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): 無效的 JSON 回應: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # 指數退避
                        continue
                    raise

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"API 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                    continue
                raise

        raise Exception(f"API 請求最終失敗: 無效的 JSON 回應")

    def get_market_index(self) -> Optional[Dict]:
        """獲取大盤指數資訊"""
        return self._make_request("exchangeReport/MI_INDEX")

    def get_stock_technical(self, stock_code: str, days: int = 60) -> Optional[Dict]:
        """獲取股票技術分析資料"""
        endpoint = f"exchangeReport/STOCK_DAY_ALL"
        params = {'stockNo': stock_code}
        return self._make_request(endpoint, params)

    def get_market_summary(self) -> Optional[Dict]:
        """獲取市場概況"""
        return self._make_request("exchangeReport/MI_INDEX")

    def get_stock_fundamental(self, stock_code: str) -> Optional[Dict]:
        """獲取股票基本面資料"""
        endpoint = f"opendata/t187ap03_L"
        params = {'stockNo': stock_code}
        return self._make_request(endpoint, params)

    def get_market_turnover(self) -> Optional[Dict]:
        """獲取市場成交資訊"""
        return self._make_request("exchangeReport/MI_INDEX")

    def get_stock_ranking(self, ranking_type: str = "volume") -> Optional[Dict]:
        """獲取股票排行"""
        endpoint = f"exchangeReport/MI_INDEX20"
        return self._make_request(endpoint)

    def get_institutional_investors(self, stock_code: Optional[str] = None) -> Optional[Dict]:
        """獲取法人買賣超資訊"""
        endpoint = "fund/MI_QFIIS_sort_20"
        return self._make_request(endpoint)

    def get_margin_trading(self, stock_code: Optional[str] = None) -> Optional[Dict]:
        """獲取融資融券資訊"""
        endpoint = "exchangeReport/MI_MARGN"
        return self._make_request(endpoint)

    def get_stock_history(self, stock_code: str, start_date: str, end_date: str) -> Optional[Dict]:
        """獲取股票歷史資料"""
        endpoint = f"exchangeReport/STOCK_DAY_ALL"
        params = {
            'stockNo': stock_code,
            'date': start_date
        }
        return self._make_request(endpoint, params)

    def get_market_news(self) -> list:
        """
        獲取市場新聞
        :return: 新聞列表
        """
        try:
            url = "https://www.twse.com.tw/rss/news"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # 使用 lxml 解析 XML
            soup = BeautifulSoup(response.content, 'lxml-xml')
            items = soup.find_all('item')

            news_list = []
            for item in items:
                try:
                    news_list.append({
                        'title': item.title.text.strip() if item.title else '',
                        'link': item.link.text.strip() if item.link else '',
                        'pubDate': item.pubDate.text.strip() if item.pubDate else ''
                    })
                except Exception as e:
                    logger.warning(f"解析新聞項目時發生錯誤：{str(e)}")
                    continue

            return news_list

        except Exception as e:
            logger.error(f"獲取新聞時發生錯誤：{str(e)}")
            return []

    def get_stock_news(self, stock_code: str) -> list:
        """
        獲取個股新聞
        :param stock_code: 股票代碼
        :return: 新聞列表
        """
        try:
            url = f"https://www.twse.com.tw/rss/news/{stock_code}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # 使用 lxml 解析 XML
            soup = BeautifulSoup(response.content, 'lxml-xml')
            items = soup.find_all('item')

            news_list = []
            for item in items:
                try:
                    news_list.append({
                        'title': item.title.text.strip() if item.title else '',
                        'link': item.link.text.strip() if item.link else '',
                        'pubDate': item.pubDate.text.strip() if item.pubDate else ''
                    })
                except Exception as e:
                    logger.warning(f"解析新聞項目時發生錯誤：{str(e)}")
                    continue

            return news_list

        except Exception as e:
            logger.error(f"獲取個股新聞時發生錯誤：{str(e)}")
            return []

    def get_etf_holdings(self, etf_code: str) -> Optional[List[str]]:
        """獲取 ETF 成分股"""
        try:
            endpoint = f"opendata/t187ap47_L"
            params = {'stockNo': etf_code}
            data = self._make_request(endpoint, params)
            if data and isinstance(data, list):
                return [item.get('code') for item in data if item.get('code')]
            return None
        except Exception as e:
            logger.error(f"獲取 ETF 成分股失敗: {str(e)}")
            raise Exception(f"無法獲取 ETF {etf_code} 的成分股資訊: {str(e)}")

    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """獲取股票即時資訊"""
        try:
            endpoint = f"exchangeReport/STOCK_DAY_ALL"
            params = {'stockNo': stock_code}
            return self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"獲取股票資訊失敗: {str(e)}")
            raise Exception(f"無法獲取股票 {stock_code} 的資訊: {str(e)}")

    def get_market_stats(self) -> Optional[Dict]:
        """獲取大盤統計資訊"""
        try:
            endpoint = "exchangeReport/MI_INDEX"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"獲取大盤統計失敗: {str(e)}")
            raise Exception(f"無法獲取大盤統計資訊: {str(e)}")

    def get_stock_day_avg(self, stock_code: str) -> Optional[Dict]:
        """獲取股票日均價"""
        try:
            endpoint = f"exchangeReport/STOCK_DAY_AVG_ALL"
            params = {'stockNo': stock_code}
            return self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"獲取股票日均價失敗: {str(e)}")
            raise Exception(f"無法獲取股票 {stock_code} 的日均價資訊: {str(e)}")

    def get_stock_day_all(self) -> Optional[Dict]:
        """獲取所有股票日成交資訊"""
        try:
            endpoint = "exchangeReport/STOCK_DAY_ALL"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"獲取所有股票日成交資訊失敗: {str(e)}")
            raise Exception(f"無法獲取所有股票日成交資訊: {str(e)}")

    def get_company_esg(self, stock_code: str) -> Optional[Dict]:
        """獲取公司 ESG 資訊"""
        try:
            endpoint = f"opendata/t187ap46_L_1"
            params = {'stockNo': stock_code}
            return self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"獲取公司 ESG 資訊失敗: {str(e)}")
            raise Exception(f"無法獲取公司 {stock_code} 的 ESG 資訊: {str(e)}")

    def get_company_governance(self, stock_code: str) -> Optional[Dict]:
        """獲取公司治理資訊"""
        try:
            endpoint = f"opendata/t187ap32_L"
            params = {'stockNo': stock_code}
            return self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"獲取公司治理資訊失敗: {str(e)}")
            raise Exception(f"無法獲取公司 {stock_code} 的治理資訊: {str(e)}")

    def get_company_financial(self, stock_code: str) -> Optional[Dict]:
        """獲取公司財務報表"""
        try:
            endpoint = f"opendata/t187ap06_L_ci"
            params = {'stockNo': stock_code}
            return self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"獲取公司財務報表失敗: {str(e)}")
            raise Exception(f"無法獲取公司 {stock_code} 的財務報表: {str(e)}")

    def calculate_technical_indicators(self, stock_code: str) -> dict:
        """
        計算股票的技術指標
        :param stock_code: 股票代碼
        :return: 包含技術指標的字典
        """
        try:
            # 獲取股票歷史資料
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
            params = {
                "response": "json",
                "date": datetime.now().strftime("%Y%m%d"),
                "stockNo": stock_code
            }

            response = self._make_request(url, params)
            if not response or not isinstance(response, dict) or not response.get("data"):
                return None

            # 解析歷史資料
            data = response["data"]
            if not isinstance(data, list):
                return None

            closes = []
            for row in data:
                try:
                    if isinstance(row, list) and len(row) > 6:
                        close = float(row[6])
                        closes.append(close)
                except (ValueError, IndexError):
                    continue

            if not closes:
                return None

            # 計算移動平均線
            ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else None
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None

            # 計算 KD 值
            k, d = self._calculate_kd(closes)

            # 計算 RSI
            rsi = self._calculate_rsi(closes)

            return {
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "kd": {"k": k, "d": d},
                "rsi": rsi
            }

        except Exception as e:
            logger.error(f"計算技術指標時發生錯誤：{str(e)}")
            return None

    def _calculate_kd(self, closes: list) -> tuple:
        """
        計算 KD 值
        :param closes: 收盤價列表
        :return: (K值, D值)
        """
        if len(closes) < 9:
            return None, None

        # 計算 RSV
        rsvs = []
        for i in range(8, len(closes)):
            high = max(closes[i-8:i+1])
            low = min(closes[i-8:i+1])
            close = closes[i]
            rsv = (close - low) / (high - low) * 100 if high != low else 50
            rsvs.append(rsv)

        # 計算 K 值和 D 值
        k = 50
        d = 50
        for rsv in rsvs:
            k = k * 2/3 + rsv * 1/3
            d = d * 2/3 + k * 1/3

        return k, d

    def _calculate_rsi(self, closes: list, period: int = 14) -> float:
        """
        計算 RSI
        :param closes: 收盤價列表
        :param period: RSI 週期
        :return: RSI 值
        """
        if len(closes) < period + 1:
            return None

        # 計算價格變動
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        # 計算上漲和下跌的平均值
        gains = [change if change > 0 else 0 for change in changes]
        losses = [-change if change < 0 else 0 for change in changes]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        # 計算 RSI
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi


# 建立實例並匯出
twse_api = TWSEAPI()
