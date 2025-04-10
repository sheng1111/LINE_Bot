import unittest
import sys
import os
import asyncio
from datetime import datetime

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_tests():
    # 設定事件循環
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 確保有事件循環
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 載入所有測試
        loader = unittest.TestLoader()
        start_dir = os.path.dirname(os.path.abspath(__file__))
        suite = loader.discover(start_dir, pattern="test_*.py")
        
        # 設定測試結果輸出
        runner = unittest.TextTestRunner(verbosity=2)
        
        # 執行測試
        print(f"\n=== 開始執行測試 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        result = runner.run(suite)
        
        # 輸出測試結果摘要
        print(f"\n=== 測試結果摘要 ===")
        print(f"執行測試數: {result.testsRun}")
        print(f"成功數: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"失敗數: {len(result.failures)}")
        print(f"錯誤數: {len(result.errors)}")
        
        return result.wasSuccessful()
    finally:
        loop.close()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
