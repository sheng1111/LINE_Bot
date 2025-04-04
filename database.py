from pymongo import MongoClient
import os
from dotenv import load_dotenv
import logging
import certifi
from pymongo.errors import ServerSelectionTimeoutError
import time

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    _instance = None
    _max_retries = 3
    _retry_delay = 5  # 秒

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        retries = 0
        while retries < self._max_retries:
            try:
                # 連接 MongoDB，添加 SSL 相關配置
                self.client = MongoClient(
                    os.getenv('MONGODB_URI'),
                    tls=True,
                    tlsCAFile=certifi.where(),
                    tlsAllowInvalidCertificates=False,
                    connectTimeoutMS=30000,
                    socketTimeoutMS=30000,
                    serverSelectionTimeoutMS=30000,
                    retryWrites=True,
                    retryReads=True,
                    maxPoolSize=50,
                    minPoolSize=10,
                    ssl=True,
                    ssl_cert_reqs=False
                )

                # 測試連接
                self.client.admin.command('ping')

                self.db = self.client[os.getenv('MONGODB_DB_NAME')]
                self._create_indexes()
                logger.info("MongoDB 連接成功")
                return

            except ServerSelectionTimeoutError as e:
                retries += 1
                logger.error(
                    f"MongoDB 連接失敗 (嘗試 {retries}/{self._max_retries}): {str(e)}")
                if retries < self._max_retries:
                    time.sleep(self._retry_delay)
                else:
                    raise
            except Exception as e:
                logger.error(f"MongoDB 連接失敗: {str(e)}")
                raise

    def _create_indexes(self):
        """建立必要的索引"""
        try:
            # 使用者資料索引
            self.db.users.create_index("user_id", unique=True)

            # 股票提醒索引
            self.db.stock_alerts.create_index(
                [("user_id", 1), ("stock_code", 1)])

            # 查詢記錄索引
            self.db.query_logs.create_index("timestamp")

            logger.info("MongoDB 索引建立成功")
        except Exception as e:
            logger.error(f"MongoDB 索引建立失敗: {str(e)}")
            raise

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
