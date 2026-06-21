import unittest
from pathlib import Path
from unittest.mock import patch

from cobrain.cli.sources import is_ignored
from cobrain.config import get_warnings_ignored_sources
from tests.base import TestCase


class TestIsIgnored(unittest.TestCase):
    def test_dotfile_auto_skipped(self):
        self.assertTrue(is_ignored(Path("sources/chats/.DS_Store"), []))

    def test_junk_substring_matches_chats_junk(self):
        self.assertTrue(is_ignored(Path("sources/chats/junk/foo.md"), ["/junk/"]))

    def test_junk_substring_matches_x_junk(self):
        self.assertTrue(is_ignored(Path("sources/x/junk/bar.yaml"), ["/junk/"]))

    def test_junk_substring_does_not_match_notjunk(self):
        self.assertFalse(is_ignored(Path("sources/notjunk/foo.md"), ["/junk/"]))

    def test_junk_substring_does_not_match_junkrelated(self):
        self.assertFalse(is_ignored(Path("sources/junkrelated/foo.md"), ["/junk/"]))

    def test_empty_ignore_list_keeps_regular_file(self):
        self.assertFalse(is_ignored(Path("sources/chats/foo.md"), []))

    def test_partial_filename_substring_matches(self):
        self.assertTrue(
            is_ignored(Path("sources/chats/ai-guitar-chord.md"), ["ai-guitar-chord"]),
        )

    def test_no_match_returns_false(self):
        self.assertFalse(is_ignored(Path("sources/chats/foo.md"), ["/junk/"]))

    def test_multiple_entries_first_matches(self):
        self.assertTrue(
            is_ignored(
                Path("sources/x/junk/bar.yaml"),
                ["pending/", "/junk/"],
            ),
        )

    def test_multiple_entries_second_matches(self):
        self.assertTrue(
            is_ignored(
                Path("sources/chats/pending/baz.md"),
                ["pending/", "/junk/"],
            ),
        )

    def test_multiple_entries_neither_matches(self):
        self.assertFalse(
            is_ignored(
                Path("sources/chats/active.md"),
                ["pending/", "/junk/"],
            ),
        )


class TestGetWarningsIgnoredSources(TestCase):
    def test_absent_key_returns_empty(self):
        with patch("cobrain.config.load_config") as mock_load:
            mock_load.return_value = {}
            self.assertEqual(get_warnings_ignored_sources(), [])

    def test_single_entry(self):
        with patch("cobrain.config.load_config") as mock_load:
            mock_load.return_value = {"warnings_ignored_sources": "/junk/"}
            self.assertEqual(get_warnings_ignored_sources(), ["/junk/"])

    def test_multiple_entries(self):
        with patch("cobrain.config.load_config") as mock_load:
            mock_load.return_value = {"warnings_ignored_sources": "/junk/,pending/"}
            self.assertEqual(get_warnings_ignored_sources(), ["/junk/", "pending/"])

    def test_strips_whitespace(self):
        with patch("cobrain.config.load_config") as mock_load:
            mock_load.return_value = {
                "warnings_ignored_sources": " /junk/ , pending/ ",
            }
            self.assertEqual(get_warnings_ignored_sources(), ["/junk/", "pending/"])

    def test_drops_empties(self):
        with patch("cobrain.config.load_config") as mock_load:
            mock_load.return_value = {
                "warnings_ignored_sources": "/junk/,,pending/,",
            }
            self.assertEqual(get_warnings_ignored_sources(), ["/junk/", "pending/"])

    def test_empty_value_returns_empty(self):
        with patch("cobrain.config.load_config") as mock_load:
            mock_load.return_value = {"warnings_ignored_sources": ""}
            self.assertEqual(get_warnings_ignored_sources(), [])


if __name__ == "__main__":
    unittest.main()
