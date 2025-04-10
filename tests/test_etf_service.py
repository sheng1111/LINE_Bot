import unittest
import asyncio
from services.etf_service import etf_service

class TestETFService(unittest.TestCase):
    def setUp(self):
        self.test_etf_code = "0050"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        self.loop.close()
        
    def test_analyze_etf(self):
        async def run_test():
            result = await etf_service.analyze_etf(self.test_etf_code)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, str)
        
        self.loop.run_until_complete(run_test())
        
    def test_get_etf_holdings(self):
        async def run_test():
            holdings = await etf_service.get_etf_holdings(self.test_etf_code)
            self.assertIsNotNone(holdings)
            self.assertIsInstance(holdings, list)
            self.assertGreater(len(holdings), 0)
            
        self.loop.run_until_complete(run_test())
