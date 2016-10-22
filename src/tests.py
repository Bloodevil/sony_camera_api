import unittest
import pysony

class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

    def test_loadpysony(self):
        api = pysony.SonyAPI()
        self.assertEqual(api.QX_ADDR, 'http://10.0.0.1:10000')


if __name__ == '__main__':
    unittest.main()

