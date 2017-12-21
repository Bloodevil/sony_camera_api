import unittest
import pysony

class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_loadpysony(self):
        api = pysony.SonyAPI()
        self.assertEqual(api.QX_ADDR, 'http://10.0.0.1:10000')


if __name__ == '__main__':
    unittest.main()

