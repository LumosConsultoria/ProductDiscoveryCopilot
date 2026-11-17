"""Storage tests that run without API keys, audio hardware, or GUI dependencies."""
import os
import tempfile
import unittest
from unittest.mock import patch

import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"APPDATA": self.tempdir.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()

    def test_save_and_load_roundtrip(self):
        item = storage.save_discovery("Sample Discovery", "Demo", "Example", [])
        loaded = storage.load_discovery(item["id"])
        self.assertEqual(loaded["title"], "Sample Discovery")
        self.assertEqual(len(storage.list_discoveries()), 1)

    def test_rejects_path_traversal_on_load(self):
        for value in ["../secret", "../../outside", "foo/bar", "foo\\bar", ""]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                storage.load_discovery(value)

    def test_rejects_invalid_id_on_save(self):
        with self.assertRaises(ValueError):
            storage.save_discovery("Sample", "Demo", "Example", [], discovery_id="../outside")


if __name__ == "__main__":
    unittest.main()
