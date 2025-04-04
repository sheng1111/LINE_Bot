import os
import logging
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import time

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
SYSTEM_PROMPT = """你是一個專業且友善的投資顧問助手，我叫做小智。

我的特點是：
1. 溫暖親切 - 用友善的語氣與用戶對話
2. 專業細心 - 提供準確的投資建議和分析
3. 簡單易懂 - 用淺顯的方式解釋複雜的概念
4. 適度幽默 - 在適當時機加入輕鬆的互動
5. 謹慎負責 - 提醒投資風險，不誇大或誤導

我擅長回答：
✓ 股票分析與建議
✓ ETF 投資策略
✓ 市場趨勢解讀
✓ 基本面技術面分析
✓ 投資組合規劃
✓ 風險控管建議

溝通方式：
- 條列重點資訊方便閱讀
- 適時使用圖表輔助說明
- 給予具體可行的建議
- 主動關心用戶需求

如果問題超出投資範疇，我會這樣回應：
「不好意思，這個問題可能不是我的專長領域。不過我很樂意為您解答任何投資相關的問題！」

讓我們開始愉快的投資對話吧！😊"""


class GeminiClient:
    def __init__(self):
        self.chat = model.start_chat(history=[])
        self.chat.send_message(SYSTEM_PROMPT)
        self.last_request_time = {}  # 用於速率限制
        self.rate_limit = 5  # 5 秒內只能發送一次請求

    def generate_response(self, user_message: str, user_id: str) -> str:
        """
        生成回應

        Args:
            user_message: 使用者訊息
            user_id: 使用者 ID

        Returns:
            生成的回應
        """
        try:
            # 檢查速率限制
            current_time = time.time()
            if user_id in self.last_request_time:
                time_diff = current_time - self.last_request_time[user_id]
                if time_diff < self.rate_limit:
                    wait_time = int(self.rate_limit - time_diff)
                    return f"請等待 {wait_time} 秒後再發送問題。"

            # 更新最後請求時間
            self.last_request_time[user_id] = current_time

            # 檢查是否為投資相關問題
            if not self._is_investment_related(user_message):
                return "抱歉，我是一個投資顧問機器人，只能回答投資相關的問題。如果您有投資相關的問題，我很樂意為您解答。"

            # 生成回應
            response = self.chat.send_message(
                user_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    top_k=TOP_K
                )
            )
            return response.text

        except Exception as e:
            logger.error(f"生成回應時發生錯誤：{str(e)}")
            return "抱歉，生成回應時發生錯誤，請稍後再試。"

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
