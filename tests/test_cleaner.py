import tempfile
import unittest
from pathlib import Path
from mormorsfildammsugare.cleaner.duplicates import delete_duplicates, find_duplicates, pick_keeper
from mormorsfildammsugare.cleaner.empty_dirs import delete_empty_folders, find_empty_folders


class TestCleaner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_and_pick_duplicates(self):
        content = b"Exact duplicate contents for testing Czkawka engine"
        f1 = self.root / "original.txt"
        f2 = self.root / "original (1).txt"
        f1.write_bytes(content)
        f2.write_bytes(content)

        dupes = find_duplicates([self.root])
        self.assertEqual(len(dupes), 1)
        group = dupes[0]
        self.assertEqual(len(group.files), 2)

        keeper, to_delete = pick_keeper(group.files, strategy="cleanest")
        self.assertEqual(keeper, f1)
        self.assertEqual(to_delete, [f2])

    def test_empty_directory_pruner(self):
        empty_sub = self.root / "nested" / "deeply" / "empty"
        empty_sub.mkdir(parents=True)
        # Add a .DS_Store file which should still count as empty
        (empty_sub / ".DS_Store").write_text("junk")

        empties = find_empty_folders(self.root)
        self.assertIn(empty_sub, empties)

        deleted = delete_empty_folders(empties, dry_run=False)
        self.assertGreaterEqual(deleted, 1)
        self.assertFalse(empty_sub.exists())


if __name__ == "__main__":
    unittest.main()
