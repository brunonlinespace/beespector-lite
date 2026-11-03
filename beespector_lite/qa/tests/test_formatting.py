import unittest
from beespector_lite.formatting import as_hex,as_compact_hex,as_escaped,as_ascii
class FormattingTests(unittest.TestCase):
    def test_formats(self):
        data=b"A\x00\xff"; self.assertEqual(as_hex(data),"41 00 FF"); self.assertEqual(as_compact_hex(data),"4100FF"); self.assertEqual(as_escaped(data),"\\x41\\x00\\xFF"); self.assertEqual(as_ascii(data),"A..")
