import unittest
import asyncio
from services.gemini_client import gemini
from unittest.mock import patch

class TestGeminiClient(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        self.loop.close()

    def test_generate_response(self):
        async def run_test():
            with patch('google.generativeai.GenerativeModel.generate_content') as mock_generate:
                # Setup mock response
                mock_generate.return_value.text = "測試回應"
                
                prompt = "測試問題"
                response = await gemini.generate_response(prompt)
                
                self.assertIsNotNone(response)
                self.assertIsInstance(response, str)
                self.assertEqual(response, "測試回應")
                mock_generate.assert_called_once()
        
        self.loop.run_until_complete(run_test())
