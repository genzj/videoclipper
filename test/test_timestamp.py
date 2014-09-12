#!/usr/bin/env python3
import sys
import os
import unittest

srclib = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, srclib)

from videoclipper import parse_timestamp

class TestTimestampParseNormal(unittest.TestCase):

    def test_HHMMSS(self):
        res = parse_timestamp('99:70:1')
        self.assertEqual(res.total_seconds(), 360601)

    def test_HHMMSSMil(self):
        res = parse_timestamp('99:70:1.12345')
        self.assertEqual(res.total_seconds(), 360601.123)

    def test_MMSS(self):
        res = parse_timestamp('0:01')
        self.assertEqual(res.total_seconds(), 1)

    def test_MMSSMil(self):
        res = parse_timestamp('0:0.300000')
        self.assertEqual(res.total_seconds(), 0.3)

    def test_SS(self):
        res = parse_timestamp('0')
        self.assertEqual(res.total_seconds(), 0)

    def test_SSMil(self):
        res = parse_timestamp('0.050')
        self.assertEqual(res.total_seconds(), 0.05)

    def test_Float(self):
        res = parse_timestamp(0.55)
        self.assertEqual(res.total_seconds(), 0.55)

class TestTimestampParseException(unittest.TestCase):
    def do_test(self, s):
        with self.assertRaises(Exception, msg='"%s" is not a valid time string'%(s,)):
            parse_timestamp(s)

    def test_nonblank(self):
        self.do_test('')

    def test_none(self):
        self.do_test(None)

    def test_nondigital(self):
        self.do_test('0x:00:00')

    def test_nondigitalmil(self):
        self.do_test('00:00:00.00i')

    def test_morecolumn(self):
        self.do_test('01:02:03:1')

    def test_moredot(self):
        self.do_test('01:02.03.1')

    def test_misdotted(self):
        self.do_test('01:02.03:1')

if __name__ == '__main__':
    unittest.main()
