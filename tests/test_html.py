import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cobrain.html.html import build_html
from tests.base import TestCase


class TestLoadGraph(TestCase):
    pass


class TestBuildLinks(TestCase):
    pass


class TestGenerateHtml(TestCase):
    pass


class TestBuildHtml(TestCase):
    def test_build_html_writes_file(self):
        with patch("cobrain.html.html._load_graph") as mock_load:
            mock_load.return_value = [
                {"id": "a", "parent": "", "related": [], "sources": []},
            ]
            with patch("cobrain.html.html._generate_html") as mock_gen:
                mock_gen.return_value = "<html></html>"
                with patch("cobrain.html.html.get_vault_dir") as mock_dir:
                    mock_dir.return_value = MagicMock()
                    mock_dir.return_value.parent = MagicMock()
                    mock_dir.return_value.parent.name = "test_vault"
                    mock_dir.return_value.parent.__truediv__ = lambda self, x: Path(
                        "/tmp/vault.html",
                    )
                    with patch("cobrain.html.html.save_categories"):
                        path = build_html()
        self.assertEqual(str(path), "/tmp/vault.html")


if __name__ == "__main__":
    unittest.main()
