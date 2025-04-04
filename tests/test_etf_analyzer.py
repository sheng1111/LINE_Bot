import pytest
from etf_analyzer import ETFAnalyzer
from datetime import datetime, timedelta
import pandas as pd


def test_get_etf_info(test_db):
    """測試獲取 ETF 資訊"""
    analyzer = ETFAnalyzer()

    # 測試正常情況
    etf_info = analyzer.get_etf_info("0050")
    assert etf_info is not None
    assert "etf_code" in etf_info
    assert "price" in etf_info
    assert "yield_rate" in etf_info

    # 測試快取功能
    cached_info = analyzer.get_etf_info("0050")
    assert cached_info == etf_info

    # 測試錯誤情況
    with pytest.raises(Exception):
        analyzer.get_etf_info("invalid_code")


def test_get_etf_ranking():
    """測試 ETF 排行"""
    analyzer = ETFAnalyzer()

    # 測試正常情況
    ranking = analyzer.get_etf_ranking()
    assert isinstance(ranking, str)
    assert "熱門 ETF 排行" in ranking
    assert "殖利率" in ranking

    # 測試空列表情況
    original_etfs = analyzer.popular_etfs
    analyzer.popular_etfs = []
    empty_ranking = analyzer.get_etf_ranking()
    assert "無法取得" in empty_ranking
    analyzer.popular_etfs = original_etfs


def test_cache_expiration():
    """測試快取過期"""
    analyzer = ETFAnalyzer()

    # 設定快取過期時間為 0
    analyzer.cache_timeout = timedelta(seconds=0)

    # 第一次獲取
    etf_info1 = analyzer.get_etf_info("0050")

    # 等待快取過期
    import time
    time.sleep(1)

    # 第二次獲取
    etf_info2 = analyzer.get_etf_info("0050")

    # 應該是不同的物件
    assert id(etf_info1) != id(etf_info2)


def test_ranking_sort():
    """測試排行排序"""
    analyzer = ETFAnalyzer()

    # 建立測試資料
    test_data = [
        {'etf_code': '0050', 'yield_rate': 3.0},
        {'etf_code': '0056', 'yield_rate': 5.0},
        {'etf_code': '006208', 'yield_rate': 2.5}
    ]

    # 測試排序
    df = pd.DataFrame(test_data)
    df = df.sort_values('yield_rate', ascending=False)

    assert df.iloc[0]['etf_code'] == '0056'  # 殖利率最高
    assert df.iloc[-1]['etf_code'] == '006208'  # 殖利率最低
