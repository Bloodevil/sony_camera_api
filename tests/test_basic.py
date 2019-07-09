import unittest
import pysony


class TestBasics(unittest.TestCase):

    def test_loadpysony(self):
        api = pysony.SonyAPI()
        self.assertEqual(api.QX_ADDR, 'http://10.0.0.1:10000')
