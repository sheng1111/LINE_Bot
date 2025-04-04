import pytest
import os
from dotenv import load_dotenv
from database import Database
from gemini_client import GeminiClient

# 載入環境變數
load_dotenv()


@pytest.fixture(scope="session")
def test_db():
    """測試用資料庫實例"""
    db = Database()
    yield db
    # 測試結束後清理
    db.close()


@pytest.fixture(scope="session")
def test_gemini():
    """測試用 Gemini 實例"""
    gemini = GeminiClient()
    yield gemini
