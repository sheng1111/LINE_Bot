from pymongo import MongoClient
import os
from dotenv import load_dotenv
import logging

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            # 連接 MongoDB
            self.client = MongoClient(os.getenv('MONGODB_URI'))
            self.db = self.client[os.getenv('MONGODB_DB_NAME')]

            # 建立索引
            self._create_indexes()

            logger.info("MongoDB 連接成功")
        except Exception as e:
            logger.error(f"MongoDB 連接失敗: {str(e)}")
            raise

    def _create_indexes(self):
        """建立必要的索引"""
        # 使用者資料索引
        self.db.users.create_index("user_id", unique=True)

        # 股票提醒索引
        self.db.stock_alerts.create_index([("user_id", 1), ("stock_code", 1)])

        # 查詢記錄索引
        self.db.query_logs.create_index("timestamp")

    def get_collection(self, collection_name):
        """取得指定的集合"""
        return self.db[collection_name]

    def close(self):
        """關閉資料庫連接"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB 連接已關閉")


# 建立全域資料庫實例
db = Database()
