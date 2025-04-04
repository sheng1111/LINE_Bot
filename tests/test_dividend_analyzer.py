import pytest
from dividend_analyzer import DividendAnalyzer
from datetime import datetime, timedelta
import requests
from unittest.mock import patch, MagicMock


def test_get_dividend_info(test_db):
    """測試獲取股息資訊"""
    analyzer = DividendAnalyzer()

    # 測試正常情況
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'stock_code': '2330',
            'current_price': 500,
            'annual_dividend': 20
        }
        mock_get.return_value = mock_response

        info = analyzer.get_dividend_info('2330')
        assert info is not None
        assert info['stock_code'] == '2330'
        assert info['current_price'] == 500
        assert info['annual_dividend'] == 20

    # 測試快取功能
    cached_info = analyzer.get_dividend_info('2330')
    assert cached_info == info

    # 測試快取過期
    analyzer.cache_timeout = timedelta(seconds=0)
    import time
    time.sleep(1)
    new_info = analyzer.get_dividend_info('2330')
    assert new_info != info


def test_get_dividend_history():
    """測試獲取歷史股息記錄"""
    analyzer = DividendAnalyzer()

    # 測試正常情況
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'date': '2023-01-01', 'amount': 10, 'type': 'cash'},
            {'date': '2022-07-01', 'amount': 8, 'type': 'cash'}
        ]
        mock_get.return_value = mock_response

        history = analyzer.get_dividend_history('2330')
        assert len(history) == 2
        assert history[0]['amount'] == 10
        assert history[1]['amount'] == 8

    # 測試快取功能
    cached_history = analyzer.get_dividend_history('2330')
    assert cached_history == history

    # 測試快取過期
    analyzer.cache_timeout = timedelta(seconds=0)
    import time
    time.sleep(1)
    new_history = analyzer.get_dividend_history('2330')
    assert new_history != history


def test_calculate_dividend_yield():
    """測試計算股息殖利率"""
    analyzer = DividendAnalyzer()

    # 測試正常情況
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'stock_code': '2330',
            'current_price': 500,
            'annual_dividend': 20
        }
        mock_get.return_value = mock_response

        yield_rate = analyzer.calculate_dividend_yield('2330')
        assert yield_rate == 4.0  # (20/500)*100 = 4%

    # 測試錯誤情況
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException()
        yield_rate = analyzer.calculate_dividend_yield('2330')
        assert yield_rate is None


def test_error_handling():
    """測試錯誤處理"""
    analyzer = DividendAnalyzer()

    # 測試 API 錯誤
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException()
        info = analyzer.get_dividend_info('2330')
        assert info is None

    # 測試資料庫錯誤
    original_db = analyzer.db
    analyzer.db = None
    history = analyzer.get_dividend_history('2330')
    assert history == []
    analyzer.db = original_db
