import unittest
from services.stock_service import stock_service

class TestStockService(unittest.TestCase):
    def setUp(self):
        self.valid_stock_codes = ["00940"]  # Added 00940 as it's actually valid
        self.invalid_stock_code = "99999"  # Changed to a definitely invalid stock code

    def test_get_stock_info_valid(self):
        for code in self.valid_stock_codes:
            result = stock_service.get_stock_info(code)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)
            self.assertIn('name', result)
            self.assertIn('price', result)
            self.assertTrue(result['name'], f"Stock name should not be empty for {code}")
            self.assertIsInstance(result['price'], (int, float), f"Price should be numeric for {code}")

    def test_get_stock_info_invalid(self):
        result = stock_service.get_stock_info(self.invalid_stock_code)
        self.assertIsNone(result, f"Should return None for invalid stock code {self.invalid_stock_code}")
