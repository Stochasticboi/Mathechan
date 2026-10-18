"""Local documentation links must remain inside the distributed repository."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_repository.py"
SPECIFICATION = importlib.util.spec_from_file_location("repository_check", SCRIPT)
repository = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(repository)


class RepositoryLinkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = self.parent / "repository"
        (self.root / "docs").mkdir(parents=True)
        self.document = self.root / "docs" / "guide.md"
        self.document.write_text("Guide", encoding="utf-8")
        (self.root / "README.md").write_text("Overview", encoding="utf-8")
        (self.parent / "outside.md").write_text("External fixture", encoding="utf-8")

    def test_internal_parent_link_and_fragment_are_allowed(self):
        self.assertIsNone(repository.local_link_error(self.document, "../README.md#intro", self.root))
        self.assertIsNone(repository.local_link_error(self.document, "#intro", self.root))

    def test_external_parent_link_and_encoded_traversal_are_rejected(self):
        for target in ("../../outside.md", "%2e%2e/%2e%2e/outside.md"):
            with self.subTest(target=target):
                self.assertIn("link leaves repository", repository.local_link_error(self.document, target, self.root))

    def test_missing_internal_target_is_rejected(self):
        self.assertIn("broken link", repository.local_link_error(self.document, "missing.md", self.root))

    def test_absolute_external_target_is_rejected(self):
        self.assertIn("link leaves repository", repository.local_link_error(self.document, str(self.parent / "outside.md"), self.root))

    def test_symlink_to_external_target_is_rejected(self):
        link = self.root / "docs" / "shortcut.md"
        try:
            link.symlink_to(self.parent / "outside.md")
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks requires platform support or permission.")
        self.assertIn("link leaves repository", repository.local_link_error(self.document, "shortcut.md", self.root))


if __name__ == "__main__":
    unittest.main()
