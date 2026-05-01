import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cobrain.html.html import _build_links, _generate_html, build_html, _load_graph


class TestLoadGraph(unittest.TestCase):
    def test_with_topics(self):
        with patch("cobrain.html.html.read_yaml") as mock_read:
            mock_read.return_value = {
                "topics": [{"id": "t1", "parent": "", "related": [], "sources": []}]
            }
            result = _load_graph()
        self.assertEqual(len(result), 1)


class TestBuildLinks(unittest.TestCase):
    def test_parent_and_related_links(self):
        topics = [
            {"id": "root", "parent": "", "related": []},
            {"id": "child", "parent": "root", "related": ["missing"]},
        ]
        parent_links, related_links = _build_links(topics)
        self.assertEqual(parent_links, [{"source": "root", "target": "child"}])
        self.assertEqual(related_links, [])


class TestGenerateHtml(unittest.TestCase):
    def test_json_structure(self):
        data = {
            "nodes": [
                {"id": "t1", "title": "T1", "parent": "", "related": [], "sources": []}
            ],
            "parentLinks": [],
            "relatedLinks": [],
            "categories": [{"id": "cat1", "title": "Cat1", "color": "#aaa"}],
            "vaultName": "test_vault",
            "topicCount": 1,
            "vaultPath": "/tmp/test",
        }
        html = _generate_html(data)
        parsed = json.loads(
            html.split('type="application/json">')[1].split("</script>")[0]
        )
        self.assertEqual(parsed["vaultName"], "test_vault")
        self.assertEqual(parsed["topicCount"], 1)


class TestBuildHtml(unittest.TestCase):
    def test_build_html_writes_file(self):
        with patch("cobrain.html.html._load_graph") as mock_load:
            mock_load.return_value = [
                {"id": "a", "parent": "", "related": [], "sources": []}
            ]
            with patch("cobrain.html.html._generate_html") as mock_gen:
                mock_gen.return_value = "<html></html>"
                with patch("cobrain.html.html.get_vault_dir") as mock_dir:
                    mock_dir.return_value = MagicMock()
                    mock_dir.return_value.parent = MagicMock()
                    mock_dir.return_value.parent.name = "test_vault"
                    mock_dir.return_value.parent.__truediv__ = lambda self, x: Path(
                        "/tmp/vault.html"
                    )
                    with patch("cobrain.html.html.save_categories"):
                        path = build_html()
        self.assertEqual(str(path), "/tmp/vault.html")


if __name__ == "__main__":
    unittest.main()
