import unittest

from utils import as_timestamp
from yfcache import YFCache


class TestYFCache(unittest.TestCase):

    def test_cache_ticker(self):
        c = YFCache()
        msft = c.get_ticker('MSFT')
        self.assertIsNotNone(msft)
        # Test last price.
        print(msft.last_price())
        
    def test_reader(self):
        c = YFCache()
        r = c.reader(start_date=as_timestamp('2020-01-02'))
        r.require_all(['MSFT', 'VTI', 'GOOG'])
        quote = next(r)
        self.assertIsNotNone(quote)
        self.assertGreater(quote.Close('MSFT'), 0)
        self.assertGreater(quote.Close('VTI'), 0)
        self.assertGreater(quote.Close('GOOG'), 0)
        
        
        
        
        

