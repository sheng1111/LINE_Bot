import pytest
from daily_recommender import DailyRecommender
from datetime import datetime, timedelta
import random


def test_get_market_overview(test_db):
    """測試獲取市場概況"""
    recommender = DailyRecommender()

    # 測試正常情況
    overview = recommender.get_market_overview()
    assert isinstance(overview, str)
    assert "市場概況" in overview

    # 測試快取功能
    cached_overview = recommender.get_market_overview()
    assert cached_overview == overview

    # 測試快取過期
    recommender.cache_timeout = timedelta(seconds=0)
    import time
    time.sleep(1)
    new_overview = recommender.get_market_overview()
    assert new_overview != overview


def test_get_stock_recommendations():
    """測試股票推薦"""
    recommender = DailyRecommender()

    # 測試正常情況
    recommendations = recommender.get_stock_recommendations()
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 3  # 最多推薦 3 支股票

    # 測試推薦內容
    if recommendations:
        stock = recommendations[0]
        assert 'stock_code' in stock
        assert 'name' in stock
        assert 'price' in stock
        assert 'analysis' in stock


def test_get_etf_recommendations():
    """測試 ETF 推薦"""
    recommender = DailyRecommender()

    # 測試正常情況
    recommendations = recommender.get_etf_recommendations()
    assert isinstance(recommendations, list)

    # 測試推薦內容
    if recommendations:
        etf = recommendations[0]
        assert 'etf_code' in etf
        assert 'name' in etf
        assert 'price' in etf
        assert 'yield_rate' in etf


def test_generate_daily_recommendation():
    """測試生成每日建議"""
    recommender = DailyRecommender()

    # 測試正常情況
    recommendation = recommender.generate_daily_recommendation()
    assert isinstance(recommendation, str)
    assert "今日投資建議" in recommendation
    assert "市場概況" in recommendation


def test_error_handling():
    """測試錯誤處理"""
    recommender = DailyRecommender()

    # 測試資料庫錯誤
    original_db = recommender.db
    recommender.db = None
    overview = recommender.get_market_overview()
    assert "抱歉" in overview
    recommender.db = original_db

    # 測試 API 錯誤
    original_stocks = recommender.popular_stocks
    recommender.popular_stocks = []
    recommendations = recommender.get_stock_recommendations()
    assert recommendations == []
    recommender.popular_stocks = original_stocks
