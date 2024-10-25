import unittest

from yfcache import YFCache

class TestYFCache(unittest.TestCase):

    def test_cache_ticker(self):
        c = YFCache()
        msft = c.get_ticker('MSFT')
        self.assertIsNotNone(msft)
        # Test last price.
        print(msft.last_price())
        
        
        
        

