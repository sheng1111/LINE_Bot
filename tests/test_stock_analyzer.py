import pytest
from stock_analyzer import StockAnalyzer
from datetime import datetime, timedelta


def test_get_stock_info(test_db):
    """測試獲取股票資訊"""
    analyzer = StockAnalyzer()

    # 測試正常情況
    stock_info = analyzer.get_stock_info("2330")
    assert stock_info is not None
    assert "stock_code" in stock_info
    assert "price" in stock_info

    # 測試快取功能
    cached_info = analyzer.get_stock_info("2330")
    assert cached_info == stock_info

    # 測試錯誤情況
    with pytest.raises(Exception):
        analyzer.get_stock_info("invalid_code")


def test_analyze_stock():
    """測試股票分析"""
    analyzer = StockAnalyzer()

    # 測試正常情況
    report = analyzer.analyze_stock("2330")
    assert isinstance(report, str)
    assert "股票代碼" in report
    assert "技術分析" in report
    assert "投資建議" in report

    # 測試錯誤情況
    error_report = analyzer.analyze_stock("invalid_code")
    assert "抱歉" in error_report


def test_cache_expiration():
    """測試快取過期"""
    analyzer = StockAnalyzer()

    # 設定快取過期時間為 0
    analyzer.cache_timeout = timedelta(seconds=0)

    # 第一次獲取
    stock_info1 = analyzer.get_stock_info("2330")

    # 等待快取過期
    import time
    time.sleep(1)

    # 第二次獲取
    stock_info2 = analyzer.get_stock_info("2330")

    # 應該是不同的物件
    assert id(stock_info1) != id(stock_info2)
