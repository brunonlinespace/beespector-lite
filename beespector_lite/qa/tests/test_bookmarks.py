import json, tempfile, unittest
from pathlib import Path
from beespector_lite.byte_source import ByteSource
from beespector_lite.bookmarks import BookmarkStore, source_fingerprint

class BookmarkTests(unittest.TestCase):
    def test_hashed_database_has_no_source_path(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src_path=root/'private-secret-name.bin'; src_path.write_bytes(b'abc'*50000)
            db=root/'bookmarks.json'
            with ByteSource(src_path) as source:
                fp=source_fingerprint(source); store=BookmarkStore(db); store.add(fp,source.size,12,'header'); rows=store.list(fp,source.size)
            self.assertEqual(rows[0].offset,12); text=db.read_text(); self.assertNotIn('private-secret-name.bin',text); self.assertIn(fp,text)
    def test_fingerprint_survives_rename(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); a=root/'a.bin'; b=root/'b.bin'; a.write_bytes(b'x'*100000)
            with ByteSource(a) as source: one=source_fingerprint(source)
            a.rename(b)
            with ByteSource(b) as source: two=source_fingerprint(source)
            self.assertEqual(one,two)
