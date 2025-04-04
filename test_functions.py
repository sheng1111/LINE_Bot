from stock_analyzer import analyzer as stock_analyzer
from etf_analyzer import analyzer as etf_analyzer
from daily_recommender import recommender
from dividend_analyzer import analyzer as dividend_analyzer
from peer_comparator import comparator
from gemini_client import gemini
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_stock_analysis():
    """測試股票分析功能"""
    logger.info("\n=== 測試股票分析 ===")
    result = stock_analyzer.get_stock_info('2330')
    logger.info(f"股票資訊：{result}")


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
        "現在是買進台積電的好時機嗎？",
        "如何評估一家公司的基本面？",
        "今天天氣如何？"  # 非投資相關問題
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


if __name__ == "__main__":
    try:
        test_stock_analysis()
        test_etf_ranking()
        test_daily_recommendation()
        test_dividend_info()
        test_peer_comparison()
        test_ai_response()
    except Exception as e:
        logger.error(f"測試過程中發生錯誤：{str(e)}")
