from stock_analyzer import analyzer as stock_analyzer
from etf_analyzer import analyzer as etf_analyzer
from daily_recommender import recommender
from dividend_analyzer import analyzer as dividend_analyzer
from peer_comparator import comparator
from gemini_client import gemini
import logging
import time
import pytest
from stock_info import get_stock_info, format_stock_info
from futures_info import get_futures_info, format_futures_info
from etf_analyzer import analyze_etf_overlap, format_overlap_analysis
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_stock_analysis():
    """測試股票分析功能"""
    logger.info("\n=== 測試股票分析 ===")
    max_retries = 3
    retry_delay = 5  # 秒

    for attempt in range(max_retries):
        try:
            result = stock_analyzer.get_stock_info('2330')
            if result:  # 如果成功獲取數據
                logger.info(f"股票資訊：{result}")
                break
        except Exception as e:
            logger.warning(f"第 {attempt + 1} 次嘗試失敗: {str(e)}")
            if attempt < max_retries - 1:  # 如果不是最後一次嘗試
                logger.info(f"等待 {retry_delay} 秒後重試...")
                time.sleep(retry_delay)
            else:
                logger.error("所有重試均失敗")
                result = {}


def test_etf_analysis():
    """測試 ETF 分析功能"""
    logger.info("\n=== 測試 ETF 分析 ===")
    result = etf_analyzer.analyze_etf('0050')
    logger.info(f"ETF 分析：{result}")


def test_dividend_analysis():
    """測試除權息分析功能"""
    logger.info("\n=== 測試除權息分析 ===")
    result = dividend_analyzer.analyze_dividend('2330')
    logger.info(f"除權息分析：{result}")


def test_peer_comparison():
    """測試同類股比較功能"""
    logger.info("\n=== 測試同類股比較 ===")
    result = comparator.compare_stocks('2330')  # 只傳入單一股票代碼
    logger.info(f"同類股比較：{result}")


def test_futures_info():
    """測試台指期資訊功能"""
    logger.info("\n=== 測試台指期資訊 ===")
    result = get_futures_info()
    logger.info(f"台指期資訊：{result}")


def test_etf_overlap_analysis():
    """測試 ETF 重疊分析功能"""
    logger.info("\n=== 測試 ETF 重疊分析 ===")
    result = analyze_etf_overlap(['0050', '0056'])
    logger.info(f"ETF 重疊分析：{result}")


def test_ai_response():
    """測試 AI 回應功能"""
    logger.info("\n=== 測試 AI 回應 ===")
    test_questions = [
        "台積電的投資價值如何？",
        "0050 和 0056 哪個比較適合長期投資？"
    ]

    for question in test_questions:
        try:
            response = gemini.generate_response(question)
            logger.info(f"問題：{question}")
            logger.info(f"回應：{response}")
            time.sleep(1)  # 避免觸發 API 限制
        except Exception as e:
            logger.error(f"生成回應時發生錯誤：{str(e)}")


if __name__ == "__main__":
    try:
        test_stock_analysis()
        test_etf_analysis()
        test_dividend_analysis()
        test_peer_comparison()
        test_futures_info()
        test_etf_overlap_analysis()
        test_ai_response()
    except Exception as e:
        logger.error(f"測試過程中發生錯誤：{str(e)}")

    pytest.main([__file__])
