import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_bundle  # noqa: E402
import install  # noqa: E402
import next_version  # noqa: E402


class NextVersionTest(unittest.TestCase):
    def test_parse_tag_accepts_only_plain_semver(self):
        self.assertEqual(next_version.parse_tag("v1.2.3"), (1, 2, 3))
        self.assertIsNone(next_version.parse_tag("1.2.3"))
        self.assertIsNone(next_version.parse_tag("v1.2.3-rc1"))

    def test_latest_version_compares_numerically(self):
        tags = ["v0.9.0", "v0.10.0", "v0.2.5", "nightly"]
        self.assertEqual(next_version.latest_version(tags), (0, 10, 0))
        self.assertIsNone(next_version.latest_version(["nightly"]))

    def test_bump_kind_follows_conventional_commits(self):
        self.assertEqual(next_version.bump_kind(["fix: clamp tone", "docs: typo"]), "patch")
        self.assertEqual(next_version.bump_kind(["fix: x", "feat(wheel): ring"]), "minor")
        self.assertEqual(next_version.bump_kind(["feat!: new state format"]), "major")
        self.assertEqual(
            next_version.bump_kind(["refactor: state\n\nBREAKING CHANGE: settings reset"]), "major"
        )
        self.assertEqual(
            next_version.bump_kind(["refactor: state\n\nBREAKING-CHANGE: settings reset"]), "major"
        )
        self.assertEqual(next_version.bump_kind([]), "patch")

    def test_breaking_change_counts_only_as_a_footer(self):
        messages = [
            "docs: explain that no BREAKING CHANGE is needed",
            "fix: clamp\n\nthis is not a BREAKING CHANGE for users",
        ]
        self.assertEqual(next_version.bump_kind(messages), "patch")

    def test_bumped_resets_lower_parts(self):
        self.assertEqual(next_version.bumped((1, 4, 7), "major"), (2, 0, 0))
        self.assertEqual(next_version.bumped((1, 4, 7), "minor"), (1, 5, 0))
        self.assertEqual(next_version.bumped((1, 4, 7), "patch"), (1, 4, 8))


class BuildBundleTest(unittest.TestCase):
    def test_bundle_has_krita_plugin_layout(self):
        with tempfile.TemporaryDirectory() as output:
            archive = build_bundle.build_bundle(REPO_ROOT, "v1.2.3", Path(output))
            self.assertEqual(archive.name, "isotone-1.2.3.zip")
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
        self.assertIn("isotone.desktop", names)
        self.assertIn("isotone/", names)
        self.assertIn("isotone/__init__.py", names)
        self.assertIn("isotone/docker.py", names)
        self.assertIn("isotone/Manual.html", names)
        self.assertIn("isotone/LICENSE", names)
        self.assertFalse([name for name in names if "__pycache__" in name or name.endswith(".pyc")])
        self.assertFalse([name for name in names if name.startswith(("tests/", "scripts/"))])


class InstallTest(unittest.TestCase):
    def test_copy_then_remove(self):
        with tempfile.TemporaryDirectory() as directory:
            pykrita = Path(directory) / "pykrita"
            install.install_plugin(pykrita, linked=False)
            self.assertTrue((pykrita / "isotone" / "__init__.py").is_file())
            self.assertTrue((pykrita / "isotone.desktop").is_file())
            install.remove_plugin(pykrita)
            self.assertFalse((pykrita / "isotone").exists())
            self.assertFalse((pykrita / "isotone.desktop").exists())

    def test_link_then_remove_keeps_the_source(self):
        with tempfile.TemporaryDirectory() as directory:
            pykrita = Path(directory) / "pykrita"
            install.install_plugin(pykrita, linked=True)
            self.assertTrue((pykrita / "isotone" / "__init__.py").is_file())
            install.remove_plugin(pykrita)
            self.assertFalse((pykrita / "isotone").exists())
        self.assertTrue((REPO_ROOT / "isotone" / "__init__.py").is_file())

    def test_remove_clears_a_dangling_link(self):
        with tempfile.TemporaryDirectory() as directory:
            pykrita = Path(directory) / "pykrita"
            pykrita.mkdir()
            moved_checkout = Path(directory) / "moved_checkout"
            moved_checkout.mkdir()
            install.link_package(moved_checkout, pykrita / "isotone")
            moved_checkout.rmdir()
            install.remove_plugin(pykrita)
            self.assertFalse(os.path.lexists(pykrita / "isotone"))

    def test_remove_deletes_a_copy_under_a_linked_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            real_parent = Path(directory) / "real"
            real_parent.mkdir()
            linked_parent = Path(directory) / "linked"
            install.link_package(real_parent, linked_parent)
            pykrita = linked_parent / "pykrita"
            install.install_plugin(pykrita, linked=False)
            install.install_plugin(pykrita, linked=False)
            install.remove_plugin(pykrita)
            self.assertFalse((real_parent / "pykrita" / "isotone").exists())
            install.remove_directory_or_link(linked_parent)
            self.assertTrue(real_parent.is_dir())


if __name__ == "__main__":
    unittest.main()
