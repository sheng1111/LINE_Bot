import google.generativeai as genai
from typing import Optional
import logging
from config.settings import AI_CONFIG

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.api_key = AI_CONFIG['GEMINI_API_KEY']
        self.model_name = AI_CONFIG.get('GEMINI_MODEL_NAME', 'gemini-pro')
        self.temperature = AI_CONFIG.get('GEMINI_TEMPERATURE', 0.9)
        self.top_p = AI_CONFIG.get('GEMINI_TOP_P', 0.8)
        self.top_k = AI_CONFIG.get('GEMINI_TOP_K', 40)
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k
            }
        )

    async def generate_response(self, prompt: str) -> str:
        """生成AI回應"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"生成AI回應時發生錯誤: {str(e)}")
            return "抱歉，無法生成回應。"

gemini = GeminiClient()
