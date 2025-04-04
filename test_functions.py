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


def test_etf_ranking():
    """測試 ETF 排行功能"""
    logger.info("\n=== 測試 ETF 排行 ===")
    result = etf_analyzer.get_etf_ranking()
    logger.info(f"ETF 排行：{result}")


def test_daily_recommendation():
    """測試每日建議功能"""
    print("\n=== 測試每日建議 ===")
    try:
        recommendation = recommender.generate_daily_recommendation("test_user")
        print(f"每日建議：{recommendation}")
    except Exception as e:
        print(f"生成每日建議時發生錯誤：{str(e)}")


def test_dividend_info():
    """測試股息查詢功能"""
    logger.info("\n=== 測試股息查詢 ===")
    result = dividend_analyzer.get_dividend_info('2330')
    logger.info(f"股息資訊：{result}")

    yield_rate = dividend_analyzer.calculate_dividend_yield('2330')
    logger.info(f"殖利率：{yield_rate}%")


def test_peer_comparison():
    """測試同業比較功能"""
    logger.info("\n=== 測試同業比較 ===")
    result = comparator.compare_stocks('2330')
    logger.info(f"同業比較：{result}")


def test_ai_response():
    """測試 AI 回應功能"""
    print("\n=== 測試 AI 回應 ===")
    test_questions = [
        "台積電的投資價值如何？",
        "推薦一些適合長期投資的 ETF",
    ]

    for question in test_questions:
        print(f"\n問題：{question}")
        try:
            # 等待速率限制時間
            time.sleep(6)  # 等待 6 秒，確保超過速率限制時間
            response = gemini.generate_response(question, "test_user")
            print(f"回應：{response}")
        except Exception as e:
            print(f"測試過程中發生錯誤：{str(e)}")
            continue


def test_stock_info():
    """測試股票資訊查詢功能"""
    # 測試台積電
    stock_info = get_stock_info('2330')
    assert stock_info is not None
    assert 'name' in stock_info
    assert 'current_price' in stock_info
    assert 'volume' in stock_info

    # 測試格式化
    formatted = format_stock_info(stock_info)
    assert isinstance(formatted, str)
    assert '台積電' in formatted or 'TSMC' in formatted


def test_futures_info():
    """測試台指期資訊查詢功能"""
    futures_info = get_futures_info()
    assert futures_info is not None
    assert 'name' in futures_info
    assert 'current_price' in futures_info
    assert 'change' in futures_info

    # 測試格式化
    formatted = format_futures_info(futures_info)
    assert isinstance(formatted, str)
    assert '台指期' in formatted


def test_etf_overlap_analysis():
    """測試 ETF 重疊分析功能"""
    # 測試分析
    analysis = analyze_etf_overlap(['0050.TW', '0056.TW'])
    assert analysis is not None
    assert 'timestamp' in analysis
    assert 'overlap_stocks' in analysis

    # 測試格式化
    formatted = format_overlap_analysis(analysis)
    assert isinstance(formatted, str)
    assert 'ETF 重疊成分股分析' in formatted


def test_etf_analysis_days():
    """測試 ETF 分析日期設定"""
    etf_days = os.getenv('ETF_ANALYSIS_DAYS', '7,14')
    days = [int(day) for day in etf_days.split(',')]
    assert len(days) > 0
    assert all(1 <= day <= 31 for day in days)
    assert 7 in days
    assert 14 in days


def test_etf_industry_analysis():
    """測試 ETF 產業分布分析功能"""
    logger.info("\n=== 測試 ETF 產業分布分析 ===")
    etfs = ['0050.TW', '0056.TW', '00878.TW', '00891.TW', '00892.TW']
    result = etf_analyzer.analyze_industry_distribution(etfs)
    assert result is not None
    assert 'industry_distribution' in result
    assert 'etf_comparison' in result
    logger.info(f"產業分布分析：{result}")


def test_technical_analysis():
    """測試技術分析功能"""
    logger.info("\n=== 測試技術分析 ===")
    stock_code = '2330'
    result = stock_analyzer.get_technical_analysis(stock_code)
    assert result is not None
    assert 'bollinger_bands' in result
    assert 'support_resistance' in result
    assert 'volume_analysis' in result
    logger.info(f"技術分析結果：{result}")


def test_market_sentiment():
    """測試市場情緒分析功能"""
    logger.info("\n=== 測試市場情緒分析 ===")
    stock_code = '2330'
    result = stock_analyzer.get_market_sentiment(stock_code)
    assert result is not None
    assert 'margin_trading' in result
    assert 'foreign_investment' in result
    assert 'institutional_trading' in result
    logger.info(f"市場情緒分析：{result}")


def test_fundamental_analysis():
    """測試基本面分析功能"""
    logger.info("\n=== 測試基本面分析 ===")
    stock_code = '2330'
    result = stock_analyzer.get_fundamental_analysis(stock_code)
    assert result is not None
    assert 'cash_flow' in result
    assert 'debt_ratio' in result
    assert 'revenue_growth' in result
    logger.info(f"基本面分析：{result}")


def test_etf_fee_comparison():
    """測試 ETF 費用率比較功能"""
    logger.info("\n=== 測試 ETF 費用率比較 ===")
    etfs = ['0050.TW', '0056.TW', '00878.TW', '00891.TW', '00892.TW']
    result = etf_analyzer.compare_etf_fees(etfs)
    assert result is not None
    assert 'fee_comparison' in result
    assert 'recommendation' in result
    logger.info(f"ETF 費用率比較：{result}")


if __name__ == "__main__":
    try:
        test_stock_analysis()
        test_etf_ranking()
        test_daily_recommendation()
        test_dividend_info()
        test_peer_comparison()
        test_ai_response()
        test_stock_info()
        test_futures_info()
        test_etf_overlap_analysis()
        test_etf_analysis_days()
        test_etf_industry_analysis()
        test_technical_analysis()
        test_market_sentiment()
        test_fundamental_analysis()
        test_etf_fee_comparison()
    except Exception as e:
        logger.error(f"測試過程中發生錯誤：{str(e)}")

    pytest.main([__file__])
