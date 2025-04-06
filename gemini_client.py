import os
import logging
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import time
from datetime import datetime

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定 Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# 從環境變數讀取模型設定
MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')
TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.7'))
TOP_P = float(os.getenv('GEMINI_TOP_P', '0.8'))
TOP_K = int(os.getenv('GEMINI_TOP_K', '40'))

# 設定模型
model = genai.GenerativeModel(MODEL_NAME)

# 系統提示詞
SYSTEM_PROMPT = """你是一個專業的投資顧問助手，名字是小智。

你的風格：
- 語氣親切，像朋友一樣溝通
- 分析準確，建議具體可行
- 解說簡單易懂，不用專業術語堆砌
- 適度加入輕鬆幽默
- 強調風險意識，不誇大績效

你擅長的領域：
- 股票與 ETF 分析與建議
- 台指期操作策略
- 市場趨勢與總體經濟解析
- 產業基本面與技術面分析
- 投資組合與風險控管規劃

溝通原則：
- 回應使用純文字，禁止 Markdown、符號、表情符號
- 回答要重點明確，不要冗長
- 遇到不熟悉的主題，誠實告知並盡力協助
- 偶爾主動提醒投資風險"""


class GeminiClient:
    def __init__(self):
        self.chat = model.start_chat(history=[])
        self.chat.send_message(SYSTEM_PROMPT)
        self.last_request_time = {}  # 用於速率限制
        self.rate_limit = 1  # 1 秒內只能發送一次請求
        self.cache = {}  # 用於快取
        self.cache_timeout = 300  # 快取超時時間（秒）
        self.max_cache_size = 1000  # 最大快取數量

    def _clean_cache(self):
        """清理過期的快取"""
        current_time = datetime.now()
        expired_keys = [
            key for key, value in self.cache.items()
            if (current_time - value['timestamp']).total_seconds() > self.cache_timeout
        ]
        for key in expired_keys:
            del self.cache[key]

        # 如果快取數量超過限制，刪除最舊的項目
        if len(self.cache) > self.max_cache_size:
            sorted_cache = sorted(
                self.cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for key, _ in sorted_cache[:len(self.cache) - self.max_cache_size]:
                del self.cache[key]

    def _get_cache_key(self, prompt: str, user_id: str = None) -> str:
        """生成快取鍵值"""
        return f"response_{user_id}_{hash(prompt)}" if user_id else f"response_{hash(prompt)}"

    def generate_response(self, prompt: str, user_id: str = None) -> str:
        """生成回應"""
        try:
            # 清理過期快取
            self._clean_cache()

            # 檢查快取
            cache_key = self._get_cache_key(prompt, user_id)
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if (datetime.now() - cache_data['timestamp']).total_seconds() < self.cache_timeout:
                    return cache_data['data']

            # 檢查速率限制
            current_time = time.time()
            if user_id in self.last_request_time:
                time_diff = current_time - self.last_request_time[user_id]
                if time_diff < self.rate_limit:
                    return f"系統正在處理中，請稍候再試。"

            # 更新最後請求時間
            self.last_request_time[user_id] = current_time

            # 檢查是否為投資相關問題
            if not self._is_investment_related(prompt):
                return "抱歉，我是一個投資顧問機器人，只能回答投資相關的問題。如果您有投資相關的問題，我很樂意為您解答。"

            # 生成回應
            response = self.chat.send_message(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    top_k=TOP_K
                )
            )
            result = response.text

            # 更新快取
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }

            return result

        except Exception as e:
            logger.error(f"生成回應時發生錯誤：{str(e)}")
            return f"抱歉，系統暫時無法處理您的請求，請稍後再試。"

    def _is_investment_related(self, message: str) -> bool:
        """
        判斷訊息是否與投資相關

        Args:
            message: 使用者訊息

        Returns:
            是否與投資相關
        """
        investment_keywords = [
            # 股票相關
            '股票', '股市', '股價', '漲跌', '買進', '賣出', '持有',
            '多頭', '空頭', '盤整', '盤面', '盤勢', '成交量',

            # ETF 相關
            'ETF', '基金', '被動式投資', '指數型',

            # 技術分析
            '均線', 'KD', 'MACD', 'RSI', '技術分析', '型態',
            '支撐', '壓力', '趨勢', '反轉', '突破',

            # 基本面分析
            '基本面', '財報', '營收', '獲利', 'EPS', '本益比',
            '股價淨值比', 'ROE', 'ROA', '毛利率', '淨利率',

            # 股息相關
            '股息', '股利', '殖利率', '配息', '配股',

            # 市場相關
            '大盤', '指數', '台股', '美股', '外資', '投信',
            '融資', '融券', '市值', '產業', '類股',

            # 投資策略
            '投資', '理財', '報酬', '風險', '資產配置',
            '長期', '短期', '波段', '進場', '出場',

            # 其他金融商品
            '債券', '期貨', '選擇權', '權證', '認購', '認售',
            '黃金', '外匯', '加密貨幣', '房地產'
        ]

        # 將訊息轉換為小寫進行比對
        message = message.lower()

        # 檢查是否包含投資關鍵字
        if any(keyword in message for keyword in investment_keywords):
            return True

        # 檢查是否包含股票代碼格式（例如：2330或006208）
        if any(part.isdigit() and (len(part) == 4 or len(part) == 5) for part in message.split()):
            return True

        # 檢查是否包含常見公司名稱
        company_names = ['台積電', '鴻海', '聯發科', '台達電', '聯電',
                         'tsmc', 'foxconn', 'mediatek', 'delta',
                         '元大', '國泰', '富邦', '中信', '第一金']  # 增加 ETF 發行商
        if any(name in message.lower() for name in company_names):
            return True

        return False


# 建立全域客戶端實例
gemini = GeminiClient()
