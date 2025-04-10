import unittest
from unittest.mock import patch, MagicMock
from services.market_service import market_service

class TestMarketService(unittest.TestCase):
    def setUp(self):
        self.mock_futures_data = {
            'data': {
                'price': '17000',
                'change': '100',
                'volume': '10000'
            }
        }
        
    @patch('requests.get')
    def test_get_futures_info(self, mock_get):
        # 設置模擬回應
        mock_response = MagicMock()
        mock_response.json.return_value = self.mock_futures_data
        mock_get.return_value = mock_response
        
        result = market_service.get_futures_info()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn('price', result)
        self.assertIn('volume', result)
