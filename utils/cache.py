from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from config.settings import CACHE_CONFIG

class Cache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = CACHE_CONFIG['TTL']
        self.max_size = CACHE_CONFIG['MAX_SIZE']

    def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        if key not in self._cache:
            return None
            
        cache_data = self._cache[key]
        if datetime.now() - cache_data['timestamp'] > timedelta(seconds=self.ttl):
            del self._cache[key]
            return None
            
        return cache_data['value']

    def set(self, key: str, value: Any):
        """設置快取值"""
        if len(self._cache) >= self.max_size:
            # 移除最舊的項目
            oldest_key = min(self._cache.items(), key=lambda x: x[1]['timestamp'])[0]
            del self._cache[oldest_key]
            
        self._cache[key] = {
            'value': value,
            'timestamp': datetime.now()
        }

    def clear(self):
        """清除所有快取"""
        self._cache.clear()

cache = Cache()
