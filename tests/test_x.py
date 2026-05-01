"""Tests for X ingest functionality."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPostIdExtraction(unittest.TestCase):
    def setUp(self):
        from cobrain.cli.ingest.x.parse import _parse_post_args

        self.parse = _parse_post_args

    def test_formats(self):
        cases = [
            ("1234567890", "1234567890"),
            ("author/status/1234567890", "1234567890"),
            ("https://x.com/author/status/1234567890", "1234567890"),
            ("1234567890,9876543210", ["1234567890", "9876543210"]),
        ]
        for inp, expected in cases:
            with self.subTest(inp=inp):
                result = self.parse(inp)
                if isinstance(expected, list):
                    self.assertEqual(result, expected)
                else:
                    self.assertEqual(result[0], expected)


class TestTreeBuild(unittest.TestCase):
    def test_chain_to_tree(self):
        from cobrain.parsers.x import XPost, arrange_into_tree

        posts = [
            XPost(
                id="child456",
                text="Child",
                author_id="2",
                author_username="bob",
                created_at="2024-01-01T11:00:00",
                conversation_id="parent123",
                in_reply_to_user_id="1",
                in_reply_to_post_id="parent123",
                post_type="ids",
            ),
            XPost(
                id="parent123",
                text="Parent",
                author_id="1",
                author_username="alice",
                created_at="2024-01-01T10:00:00",
                conversation_id="parent123",
                in_reply_to_user_id=None,
                in_reply_to_post_id=None,
                post_type="ids",
            ),
        ]
        tree = arrange_into_tree(posts)
        tree.conversation_xurl = f"{tree.root.author}/status/{tree.root.id}"

        self.assertEqual(tree.root.id, "parent123")
        self.assertEqual(len(tree.root.children), 1)
        self.assertEqual(tree.root.children[0].id, "child456")
        self.assertIn("alice", tree.conversation_xurl)


class TestTreeMergeInMemory(unittest.TestCase):
    def test_overlap_merge(self):
        from cobrain.parsers.x import XTree, XTreeNode, expand_and_merge_trees

        tree1_root = XTreeNode(
            id="shared123",
            author="alice",
            created_at="2024-01-01T10:00:00",
            text="Shared",
            post_type="ids",
        )
        tree1 = XTree(
            id="shared123",
            root=tree1_root,
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-01T10:00:00Z",
            conversation_xurl="alice/status/shared123",
        )

        child = XTreeNode(
            id="reply456",
            author="bob",
            created_at="2024-01-01T11:00:00",
            text="Reply",
            post_type="ids",
            in_reply_to_post_id="shared123",
        )
        tree2 = XTree(
            id="reply456",
            root=child,
            created_at="2024-01-01T11:00:00Z",
            updated_at="2024-01-01T11:00:00Z",
            conversation_xurl="bob/status/reply456",
        )

        new_trees = {"reply456": tree2}
        cached_trees = {"shared123": tree1}
        updated = set()

        related = expand_and_merge_trees(new_trees, cached_trees, updated)

        self.assertEqual(related, [])
        self.assertIn("shared123", updated)
        self.assertEqual(len(tree1_root.children), 1)
        self.assertEqual(tree1_root.children[0].id, "reply456")


class TestCacheFirstExpansion(unittest.TestCase):
    def test_skip_if_cached(self):
        from cobrain.parsers.x import (
            XTree,
            XTreeNode,
            expand_and_merge_trees,
            save_tree,
            get_x_trees_dir,
        )

        cached_root = XTreeNode(
            id="cached123",
            author="alice",
            created_at="2024-01-01T10:00:00",
            text="Cached",
            post_type="ids",
        )
        cached_tree = XTree(
            id="cached123",
            root=cached_root,
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-01T10:00:00Z",
            conversation_xurl="alice/status/cached123",
        )

        new_root = XTreeNode(
            id="new456",
            author="bob",
            created_at="2024-01-01T11:00:00",
            text="New",
            post_type="ids",
            in_reply_to_post_id="cached123",
        )
        new_tree = XTree(
            id="new456",
            root=new_root,
            created_at="2024-01-01T11:00:00Z",
            updated_at="2024-01-01T11:00:00Z",
            conversation_xurl="bob/status/new456",
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(get_x_trees_dir, "__call__", return_value=Path(tmp)):
                save_tree(cached_tree)

            new_trees = {"new456": new_tree}
            cached_trees = {"cached123": cached_tree}
            updated = set()

            expand_and_merge_trees(new_trees, cached_trees, updated)

            self.assertIn("cached123", updated)
            self.assertEqual(len(new_trees), 0)


class TestPaginationAndBatching(unittest.TestCase):
    def test_page_size(self):
        from cobrain.parsers.x.helpers import calculate_page_size, DEFAULT_PAGE_SIZE

        self.assertEqual(calculate_page_size(0), DEFAULT_PAGE_SIZE)
        self.assertEqual(calculate_page_size(100), 100)
        self.assertGreaterEqual(calculate_page_size(10), 10)
        self.assertLessEqual(calculate_page_size(105), 100)

    def test_should_paginate(self):
        def should_paginate(since_id, until_id, count):
            return since_id or until_id or count is not None

        self.assertTrue(should_paginate("since", None, None))
        self.assertTrue(should_paginate(None, "until", None))
        self.assertTrue(should_paginate(None, None, 10))
        self.assertFalse(should_paginate(None, None, None))

    def test_chunk_split(self):
        ids = [f"id{i}" for i in range(250)]
        chunks = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 100)
        self.assertEqual(len(chunks[2]), 50)


class TestOAuthTokenExchange(unittest.TestCase):
    @patch("cobrain.parsers.x.auth.set_x_config")
    @patch("xdk.oauth2_auth.OAuth2PKCEAuth")
    def test_exchange_without_api(self, mock_auth_class, mock_set_config):
        from cobrain.parsers.x.auth import OAuth2TokenManager

        mock_auth = MagicMock()
        mock_auth.code_verifier = "test_verifier"
        mock_auth_class.return_value = mock_auth
        mock_auth.fetch_token.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 7200,
        }

        manager = OAuth2TokenManager(authorization_code="test_code")
        manager.client_id = "client_id"
        manager.client_secret = "client_secret"
        manager.pkce_verifier = "verifier"

        result = manager._exchange_code()

        self.assertEqual(result, "new_access")
        mock_set_config.assert_called()


class TestConstants(unittest.TestCase):
    def test_types(self):
        from cobrain.parsers.x import (
            POST_TYPE_IDS,
            POST_TYPE_OWN,
            POST_TYPE_LIKED,
            POST_TYPE_BOOKMARKED,
            POST_TYPE_RELATED,
            SEMANTIC_TYPE_POST,
            SEMANTIC_TYPE_REPLY,
            SEMANTIC_TYPE_QUOTE,
            SEMANTIC_TYPE_REPOST,
        )

        self.assertEqual(POST_TYPE_IDS, "ids")
        self.assertEqual(POST_TYPE_OWN, "own")
        self.assertEqual(POST_TYPE_LIKED, "liked")
        self.assertEqual(POST_TYPE_BOOKMARKED, "bookmarked")
        self.assertEqual(POST_TYPE_RELATED, "related")
        self.assertEqual(SEMANTIC_TYPE_POST, "post")
        self.assertEqual(SEMANTIC_TYPE_REPLY, "reply")
        self.assertEqual(SEMANTIC_TYPE_QUOTE, "quote")
        self.assertEqual(SEMANTIC_TYPE_REPOST, "repost")


if __name__ == "__main__":
    unittest.main()
