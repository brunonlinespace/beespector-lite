import tempfile, unittest
from pathlib import Path
from beespector_lite.byte_source import ByteSource
from beespector_lite.signatures import likely_signature, library_rows, SIGNATURES, identify_source

class SignatureTests(unittest.TestCase):
    def test_png(self):
        self.assertEqual(likely_signature(bytes.fromhex("89504E470D0A1A0A0000")).name,"PNG image")

    def test_library_is_wikipedia_expanded(self):
        rows=library_rows(); cats={r[0] for r in rows}
        self.assertGreaterEqual(len(SIGNATURES),250)
        for cat in ("ASCII","Archives","Images","Executables","Audio/Video","Fonts","Network","Packages","Data/Scientific","Disk/Virtualization","Keys/Certificates"):
            self.assertIn(cat,cats)
        self.assertTrue(any(r[1]=="DICOM" and r[4]=="0x80" for r in rows))
        self.assertTrue(any(r[1]=="ISO 9660 image" and ".iso" in r[5] for r in rows))

    def test_riff_subtype(self):
        self.assertEqual(likely_signature(b"RIFF"+b"1234"+b"WEBP").name,"WebP image")

    def test_tar_offset(self):
        data=bytearray(512); data[257:262]=b"ustar"
        self.assertEqual(likely_signature(bytes(data)).name,"TAR archive")

    def test_mp4_ftyp_offset(self):
        self.assertEqual(likely_signature(b"\x00\x00\x00\x18ftypisom").name,"MP4 — isom brand")

    def test_targeted_nonzero_offset_identification(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"image.dcm"; data=bytearray(200); data[128:132]=b"DICM"; p.write_bytes(data)
            with ByteSource(p) as src: sig=identify_source(src)
            self.assertIsNotNone(sig); self.assertEqual(sig.name,"DICOM")

    def test_iso9660_large_offset_without_whole_file_read(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"disc.iso"; data=bytearray(0x8100); data[0x8001:0x8006]=b"CD001"; p.write_bytes(data)
            with ByteSource(p) as src: sig=identify_source(src)
            self.assertIsNotNone(sig); self.assertEqual(sig.name,"ISO 9660 image")

    def test_zip_extension_refines_container_knowledge(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.docx"; p.write_bytes(b"PK\x03\x04"+b"\x00"*64)
            with ByteSource(p) as src: sig=identify_source(src)
            self.assertIsNotNone(sig); self.assertEqual(sig.name,"Word OOXML / ZIP")
    def test_weak_short_signature_is_reference_only(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"ambiguous.bin"; p.write_bytes(bytes.fromhex("789C")+b"not enough evidence")
            with ByteSource(p) as src: sig=identify_source(src)
            self.assertTrue(sig is None or sig.name != "zlib stream — default compression")

