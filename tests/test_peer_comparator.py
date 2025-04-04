import pytest
from peer_comparator import PeerComparator
from datetime import datetime, timedelta
import requests
from unittest.mock import patch, MagicMock


def test_get_peer_stocks(test_db):
    """測試獲取同業股票"""
    comparator = PeerComparator()

    # 測試正常情況
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'peers': ['2330', '2303', '2308']
        }
        mock_get.return_value = mock_response

        peers = comparator.get_peer_stocks('2330')
        assert len(peers) == 3
        assert '2330' in peers
        assert '2303' in peers
        assert '2308' in peers

    # 測試快取功能
    cached_peers = comparator.get_peer_stocks('2330')
    assert cached_peers == peers

    # 測試快取過期
    comparator.cache_timeout = timedelta(seconds=0)
    import time
    time.sleep(1)
    new_peers = comparator.get_peer_stocks('2330')
    assert new_peers != peers


def test_compare_stocks():
    """測試比較股票"""
    comparator = PeerComparator()

    # 測試正常情況
    with patch('requests.get') as mock_get:
        # 設定同業股票 API 回應
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'peers': ['2303', '2308']
        }
        mock_get.return_value = mock_response

        # 設定股票資訊 API 回應
        with patch('stock_analyzer.analyzer.get_stock_info') as mock_stock_info:
            mock_stock_info.return_value = {
                'name': '台積電',
                'price': 500,
                'pe_ratio': 15,
                'pb_ratio': 5
            }

            # 設定股息資訊 API 回應
            with patch('dividend_analyzer.analyzer.get_dividend_info') as mock_dividend:
                mock_dividend.return_value = {
                    'current_price': 500,
                    'annual_dividend': 20
                }

                result = comparator.compare_stocks('2330')
                assert 'target_stock' in result
                assert 'peers' in result
                assert result['target_stock']['stock_code'] == '2330'
                assert result['target_stock']['name'] == '台積電'
                assert result['target_stock']['price'] == 500
                assert len(result['peers']) <= 5  # 最多比較 5 家同業

    # 測試錯誤情況
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException()
        result = comparator.compare_stocks('2330')
        assert 'error' in result


def test_error_handling():
    """測試錯誤處理"""
    comparator = PeerComparator()

    # 測試 API 錯誤
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException()
        peers = comparator.get_peer_stocks('2330')
        assert peers == []

    # 測試資料庫錯誤
    original_db = comparator.db
    comparator.db = None
    result = comparator.compare_stocks('2330')
    assert 'error' in result
    comparator.db = original_db
