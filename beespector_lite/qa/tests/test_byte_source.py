import hashlib, os, tempfile, unittest
from pathlib import Path
from beespector_lite.byte_source import ByteSource
class ByteSourceTests(unittest.TestCase):
    def test_read_only_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.bin"; original=bytes(range(256))*64; p.write_bytes(original); before=hashlib.sha256(p.read_bytes()).hexdigest(); os.chmod(p,0o444)
            with ByteSource(p) as s:
                self.assertEqual(s.size,len(original)); self.assertEqual(s.read(10,8),original[10:18]); self.assertEqual(s.sha256(),before)
            after=hashlib.sha256(p.read_bytes()).hexdigest(); self.assertEqual(before,after)
    def test_refuses_directory(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises((ValueError,OSError)): ByteSource(td)
    def test_descriptor_is_read_only_on_posix(self):
        try: import fcntl
        except ImportError: self.skipTest("fcntl unavailable")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"; p.write_bytes(b"abc")
            with ByteSource(p) as s:
                flags=fcntl.fcntl(s.fileno(),fcntl.F_GETFL)
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
    def test_random_read_sparse_large_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"large.bin"
            with open(p,"wb") as f:
                f.seek((2*1024*1024*1024)+123); f.write(b"BEE")
            with ByteSource(p) as s:
                self.assertGreater(s.size,2*1024*1024*1024)
                self.assertEqual(s.read((2*1024*1024*1024)+123,3),b"BEE")
