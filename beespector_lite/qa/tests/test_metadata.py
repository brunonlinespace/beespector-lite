import os, struct, tempfile, unittest, zipfile
from pathlib import Path
from beespector_lite.byte_source import ByteSource
from beespector_lite.metadata import filesystem_metadata, identification_metadata, embedded_metadata, metadata_snapshot

class MetadataTests(unittest.TestCase):
    def test_unknown_file_still_has_universal_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"mystery.bin"; p.write_bytes(b"\x01\x02\x03\x04")
            with ByteSource(p) as src:
                snap=metadata_snapshot(src)
            self.assertIn("Filesystem",snap); self.assertIn("Embedded Metadata",snap)
            self.assertTrue(any(k=="Path" for k,_ in snap["Filesystem"]))
            self.assertIn("No recognised embedded metadata parser",snap["Embedded Metadata"][0][1])

    def test_png_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.png"
            ihdr=struct.pack(">IIBBBBB",320,200,8,6,0,0,0)
            p.write_bytes(b"\x89PNG\r\n\x1a\n"+struct.pack(">I",13)+b"IHDR"+ihdr+b"\x00\x00\x00\x00"+struct.pack(">I",0)+b"IEND"+b"\x00\x00\x00\x00")
            with ByteSource(p) as src: rows=dict(embedded_metadata(src))
            self.assertEqual(rows["Dimensions"],"320 × 200"); self.assertEqual(rows["Colour type"],"Truecolour RGBA")

    def test_elf_header(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.elf"; data=bytearray(64); data[:4]=b"\x7fELF"; data[4]=2; data[5]=1; data[6]=1; data[7]=3; data[16:18]=(2).to_bytes(2,"little"); data[18:20]=(62).to_bytes(2,"little"); p.write_bytes(data)
            with ByteSource(p) as src: rows=dict(embedded_metadata(src))
            self.assertEqual(rows["Class"],"64-bit"); self.assertEqual(rows["Architecture"],"x86-64"); self.assertEqual(rows["Endianness"],"Little endian")

    def test_zip_metadata_does_not_extract(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"x.zip"
            with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z: z.writestr("folder/file.txt","hello")
            before=set(root.iterdir())
            with ByteSource(p) as src: rows=dict(embedded_metadata(src))
            after=set(root.iterdir())
            self.assertEqual(before,after); self.assertEqual(rows["Members"],"1")

    def test_original_symlink_path_is_preserved_without_changing_target(self):
        if os.name=="nt": self.skipTest("symlink permissions vary on Windows")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target=root/"target.bin"; link=root/"alias.bin"; target.write_bytes(b"abc"); link.symlink_to(target.name)
            with ByteSource(link) as src:
                rows=dict(filesystem_metadata(src)); self.assertEqual(src.original_path,link.absolute())
            self.assertIn("Opened through symlink",rows); self.assertEqual(target.read_bytes(),b"abc")
    def test_signature_metadata_reports_real_offset_and_extensions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"scan.dcm"; data=bytearray(200); data[128:132]=b"DICM"; p.write_bytes(data)
            with ByteSource(p) as src: rows=dict(identification_metadata(src))
            self.assertEqual(rows["Likely signature"],"DICOM")
            self.assertEqual(rows["Signature offset"],"0x80")
            self.assertIn(".dcm",rows["Known extensions"])
            self.assertEqual(rows["Signature bytes"],"44 49 43 4D")

