from pymongo import MongoClient
from config.settings import DB_CONFIG
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(DB_CONFIG['MONGODB_URI'])
            self.db = self.client[DB_CONFIG['DATABASE']]
            logger.info("資料庫連接成功")
        except Exception as e:
            logger.error(f"資料庫連接失敗: {str(e)}")
            raise

    def get_collection(self, collection_name: str):
        return self.db[collection_name]

    def close(self):
        try:
            self.client.close()
            logger.info("資料庫連接已關閉")
        except Exception as e:
            logger.error(f"關閉資料庫連接時發生錯誤: {str(e)}")

db = Database()
