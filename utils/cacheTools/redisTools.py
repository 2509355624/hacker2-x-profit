class RedisQueue:
    def __init__(self, key):
        self.key = key
        self._data = {}

    def addStrEX(self, ttl, value):
        self._data[self.key] = value

    def getKeys(self, pattern):
        return [k for k in self._data.keys() if pattern.replace('*', '') in k]

    def batchGetStr(self, keys):
        return [self._data.get(k, '') for k in keys]

    def getStr(self, key):
        return self._data.get(key, '')
