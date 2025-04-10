import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name: str, log_file: str = 'app.log') -> logging.Logger:
    """設置日誌記錄器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 確保日誌目錄存在
    os.makedirs('logs', exist_ok=True)
    file_path = os.path.join('logs', log_file)

    # 檔案處理器 (每個檔案最大 5MB，保留 5 個檔案)
    file_handler = RotatingFileHandler(
        file_path, 
        maxBytes=5*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)

    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加處理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 創建主日誌記錄器
logger = setup_logger('line_bot')
