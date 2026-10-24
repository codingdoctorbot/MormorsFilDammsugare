import tempfile
import unittest
from pathlib import Path
from mormorsfildammsugare.core.sniffer import MediaCategory, sniff_file


class TestSniffer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sniff_png(self):
        f = Path(self.temp_dir.name) / "image.fake"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
        res = sniff_file(f)
        self.assertIsNotNone(res)
        self.assertEqual(res.canonical_ext, ".png")
        self.assertEqual(res.category, MediaCategory.PHOTO)

    def test_sniff_jpeg(self):
        f = Path(self.temp_dir.name) / "image.dat"
        f.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 20)
        res = sniff_file(f)
        self.assertIsNotNone(res)
        self.assertEqual(res.canonical_ext, ".jpg")
        self.assertEqual(res.category, MediaCategory.PHOTO)

    def test_sniff_pdf(self):
        f = Path(self.temp_dir.name) / "doc.bin"
        f.write_bytes(b"%PDF-1.4\n" + b"\x00" * 20)
        res = sniff_file(f)
        self.assertIsNotNone(res)
        self.assertEqual(res.canonical_ext, ".pdf")
        self.assertEqual(res.category, MediaCategory.DOCUMENT)


if __name__ == "__main__":
    unittest.main()
