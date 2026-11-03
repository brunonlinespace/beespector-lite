import unittest
from beespector_lite.color_engine import byte_class, detected_string_mask

class ColourEngineTests(unittest.TestCase):
    def test_character_classes(self):
        self.assertEqual(byte_class(0), "nul")
        self.assertEqual(byte_class(ord("A")), "letter")
        self.assertEqual(byte_class(ord("7")), "number")
        self.assertEqual(byte_class(ord("/")), "punctuation")
        self.assertEqual(byte_class(10), "space")
        self.assertEqual(byte_class(1), "control")
        self.assertEqual(byte_class(0xFF), "non_ascii")

    def test_detected_strings(self):
        data=b"\x00ABC\x00HELLO world\xFFxyzz"
        mask=detected_string_mask(data, minimum=4)
        self.assertFalse(any(mask[1:4]))
        start=data.index(b"HELLO")
        self.assertTrue(all(mask[start:start+11]))
        tail=data.index(b"xyzz")
        self.assertTrue(all(mask[tail:tail+4]))
