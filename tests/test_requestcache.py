import unittest

from ..callback import Callback
from ..requestcache import RequestCache, Cache

class TestRequestCache(unittest.TestCase):

    def setUp(self):
        self.callback = Callback()
        self.request_cache = RequestCache(self.callback)

        self.callback.start()

    def tearDown(self):
        self.callback.stop()

    def test_set_has(self):
        class Cache1(Cache):
            pass
        class Cache2(Cache):
            pass

        identifier = self.request_cache.generate_identifier()
        if not self.request_cache.has(identifier, Cache1):
            self.request_cache.set(identifier, Cache1())

        if not self.request_cache.has(identifier, Cache2):
            self.request_cache.set(identifier, Cache2())

        assert self.request_cache.has(identifier, Cache), 'should be possible to pass a parent to check if a subclass is set'
        assert self.request_cache.has(identifier, Cache1), 'should not have replaced the first assigned cache'
