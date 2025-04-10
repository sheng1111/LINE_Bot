import os
from dotenv import load_dotenv

load_dotenv()

# LINE Bot 設定
LINE_CONFIG = {
    'CHANNEL_ACCESS_TOKEN': os.getenv('LINE_CHANNEL_ACCESS_TOKEN'),
    'CHANNEL_SECRET': os.getenv('LINE_CHANNEL_SECRET')
}

# API 設定
API_CONFIG = {
    'TWSE_API': {
        'BASE_URL': 'https://www.twse.com.tw/v2/api',
        'STOCK_INFO': 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp',
        'FUTURES_INFO': 'https://mis.twse.com.tw/futures/api/getFuturesInfo.jsp',
        'MARKET_NEWS': 'https://www.twse.com.tw/v2/api/news',
        'TIMEOUT': 10
    },
    'YAHOO_FINANCE': {
        'BASE_URL': 'https://tw.stock.yahoo.com',
        'TIMEOUT': 15,
        'HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
}

# 快取設定
CACHE_CONFIG = {
    'TTL': 300,  # 5 minutes
    'MAX_SIZE': 1000
}

# 資料庫設定
DB_CONFIG = {
    'MONGODB_URI': os.getenv('MONGODB_URI', 'mongodb://localhost:27017'),
    'DATABASE': 'stock_bot'
}

# AI 設定
AI_CONFIG = {
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    'GEMINI_MODEL_NAME': os.getenv('GEMINI_MODEL_NAME', 'gemini-pro'),
    'GEMINI_TEMPERATURE': float(os.getenv('GEMINI_TEMPERATURE', '0.9')),
    'GEMINI_TOP_P': float(os.getenv('GEMINI_TOP_P', '0.8')),
    'GEMINI_TOP_K': int(os.getenv('GEMINI_TOP_K', '40')),
    'MAX_TOKENS': 4096
}
