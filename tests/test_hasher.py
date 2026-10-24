import tempfile
import unittest
from pathlib import Path
from mormorsfildammsugare.core.hasher import fast_fingerprint, full_sha256


class TestHasher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "sample.txt"
        self.test_file.write_text("Grandma's File Vacuum Cleaner Test Content 12345")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_sha256(self):
        sha = full_sha256(self.test_file)
        self.assertIsNotNone(sha)
        self.assertEqual(len(sha), 64)
        self.assertEqual(sha, full_sha256(self.test_file))

    def test_fast_fingerprint(self):
        probe = fast_fingerprint(self.test_file)
        self.assertIsNotNone(probe)
        self.assertEqual(probe, fast_fingerprint(self.test_file))


if __name__ == "__main__":
    unittest.main()
