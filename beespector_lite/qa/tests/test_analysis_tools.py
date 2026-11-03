import math, tempfile, unittest
from pathlib import Path
from beespector_lite.byte_source import ByteSource
from beespector_lite.analysis_tools import selection_interpretation, range_checksums, range_entropy, find_printable_strings, find_repeated_runs, export_range

class AnalysisToolsTests(unittest.TestCase):
    def test_endian_interpretation(self):
        values=selection_interpretation(bytes.fromhex('01000000'))
        self.assertEqual(values['Unsigned 32-bit LE'],'1')
        self.assertEqual(values['Unsigned 32-bit BE'],'16777216')

    def test_export_range_preserves_source(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"source.bin"; out=root/"selection.bin"; p.write_bytes(bytes(range(256))*4)
            before=hashlib.sha256(p.read_bytes()).hexdigest()
            with ByteSource(p) as src: export_range(src,100,50,out)
            self.assertEqual(out.read_bytes(),p.read_bytes()[100:150])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)


    def test_chunk_boundary_strings_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"boundary.bin"; p.write_bytes(b"xxHELLO\x00"+b"A"*20+b"yy")
            with ByteSource(p) as src:
                strings=find_printable_strings(src,5,chunk_size=4)
                self.assertTrue(any(data.startswith(b"xxHELLO") for _,_,data in strings))
                runs=find_repeated_runs(src,16,chunk_size=3)
                self.assertTrue(any(v==0x41 and n==20 for _,v,n in runs))

    def test_export_refuses_source_path(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"source.bin"; p.write_bytes(b"abcdef")
            with ByteSource(p) as src:
                with self.assertRaises(ValueError): export_range(src,0,3,p)

    def test_strings_preview_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"long-text.bin"; p.write_bytes(b"A"*100000)
            with ByteSource(p) as src:
                rows=find_printable_strings(src,4,preview_bytes=64)
            self.assertEqual(rows[0][1],100000)
            self.assertEqual(len(rows[0][2]),64)

    def test_strings_runs_checksums_entropy(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.bin'; p.write_bytes(b'\x00'*20+b'Hello world'+b'\xff'*18)
            with ByteSource(p) as src:
                strings=find_printable_strings(src,4); self.assertTrue(any(data==b'Hello world' for _,_,data in strings))
                runs=find_repeated_runs(src,16); self.assertIn((0,0,20),runs); self.assertTrue(any(v==255 and n==18 for _,v,n in runs))
                sums=range_checksums(src,20,11); self.assertEqual(sums['CRC32'],'8BD69E52')
                e=range_entropy(src,0,20); self.assertAlmostEqual(e,0.0,places=6)
