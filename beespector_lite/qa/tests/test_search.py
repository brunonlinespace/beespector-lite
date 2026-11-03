import tempfile, unittest
from pathlib import Path
from beespector_lite.byte_source import ByteSource
from beespector_lite.search_engine import parse_hex_pattern,find_forward,find_backward,encode_text_pattern
class SearchTests(unittest.TestCase):
    def test_parse_hex(self): self.assertEqual(parse_hex_pattern("89 50 4e 47"),bytes.fromhex("89504E47"))
    def test_forward_backward(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"; p.write_bytes(b"zero ABC one ABC tail")
            with ByteSource(p) as s:
                self.assertEqual(find_forward(s,b"ABC",0),5); self.assertEqual(find_forward(s,b"ABC",6),13); self.assertEqual(find_backward(s,b"ABC",20),13)
    def test_text_utf8(self): self.assertEqual(encode_text_pattern("bee"),b"bee")
    def test_boundary_crossing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"; p.write_bytes(b"A"*7+b"MAGIC"+b"Z"*7)
            with ByteSource(p) as s:
                self.assertEqual(find_forward(s,b"MAGIC",0,chunk_size=8),7)
                self.assertEqual(find_backward(s,b"MAGIC",20,chunk_size=8),7)

class FindAllTests(unittest.TestCase):
    def test_find_all_overlapping(self):
        import tempfile
        from pathlib import Path
        from beespector_lite.byte_source import ByteSource
        from beespector_lite.search_engine import find_all
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'all.bin'; p.write_bytes(b'AAAA')
            with ByteSource(p) as s:
                self.assertEqual(find_all(s,b'AA'),[0,1,2])
    def test_find_all_chunk_boundary(self):
        import tempfile
        from pathlib import Path
        from beespector_lite.byte_source import ByteSource
        from beespector_lite.search_engine import find_all
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'boundary.bin'; p.write_bytes(b'xxABCyyABCzz')
            with ByteSource(p) as s:
                self.assertEqual(find_all(s,b'ABC',chunk_size=4),[2,7])
