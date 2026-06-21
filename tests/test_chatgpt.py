import json
import os
import tempfile
import unittest
from pathlib import Path

from cobrain.parsers.chatgpt import (
    EXCLUDE_CONTENT_TYPES,
    INCLUDE_CONTENT_TYPES,
    Conversation,
    MessageNode,
    build_citations_dicts,
    compute_word_count,
    conversation_to_markdown,
    filter_conversations,
    get_existing_file_for_conversation,
    get_output_filename,
    load_conversations,
    should_include_message,
    transform_assistant_messages,
)
from tests.base import TEST_VAULT, TestCase


class TestContentTypes(unittest.TestCase):
    def test_included_content_types(self):
        self.assertIn("text", INCLUDE_CONTENT_TYPES)
        self.assertIn("execution_output", INCLUDE_CONTENT_TYPES)
        self.assertNotIn("code", INCLUDE_CONTENT_TYPES)

    def test_excluded_content_types(self):
        self.assertIn("user_editable_context", EXCLUDE_CONTENT_TYPES)
        self.assertIn("thoughts", EXCLUDE_CONTENT_TYPES)
        self.assertIn("reasoning_recap", EXCLUDE_CONTENT_TYPES)

    def test_message_inclusion_rules(self):
        cases = [
            # (should_include, msg_dict)
            (
                True,
                {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["hello"]},
                    "metadata": {},
                },
            ),
            (
                True,
                {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": ["response"]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "system"},
                    "content": {"content_type": "text", "parts": ["system"]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "tool", "name": "web"},
                    "content": {"content_type": "text", "parts": ["tool"]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["hidden"]},
                    "metadata": {"is_visually_hidden_from_conversation": True},
                },
            ),
            (
                False,
                {
                    "author": {"role": "user"},
                    "content": {
                        "content_type": "user_editable_context",
                        "parts": ["profile"],
                    },
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": [""]},
                    "metadata": {},
                },
            ),
            (
                False,
                {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "code", "text": "{}"},
                    "metadata": {},
                },
            ),
        ]
        for expected, msg in cases:
            self.assertEqual(
                should_include_message(msg),
                expected,
                f"Failed for msg: {msg.get('author', {}).get('role')}/{msg.get('content', {}).get('content_type')}",
            )


class TestFilters(unittest.TestCase):
    @property
    def convs(self):
        return [
            {
                "conversation_id": "1",
                "title": "Test Conversation A",
                "create_time": 1700000000.0,
                "mapping": {},
            },
            {
                "conversation_id": "2",
                "title": "Test Conversation B",
                "create_time": 1700100000.0,
                "mapping": {},
            },
            {
                "conversation_id": "3",
                "title": "Other Conversation",
                "create_time": 1700200000.0,
                "mapping": {},
            },
        ]

    def test_filter_cases(self):
        cases = [
            # (expected_count, from_time, till_time, titles, description)
            (3, None, None, None, "no filters"),
            (2, None, None, ["Test"], "single title"),
            (2, None, None, ["Conversation A", "Conversation B"], "multiple titles"),
            (2, 1700100000.0, None, None, "from_time"),
            (2, None, 1700100000.0, None, "till_time"),
            (1, 1700100000.0, 1700100000.0, None, "time range"),
            (1, 1700000000.0, 1700050000.0, ["Test"], "combined filters"),
        ]
        for expected, from_t, till_t, titles, desc in cases:
            result = filter_conversations(self.convs, from_t, till_t, titles)
            self.assertEqual(len(result), expected, f"Failed for: {desc}")


class TestTransformations(unittest.TestCase):
    def test_cite_lookups(self):
        msg = {
            "metadata": {
                "content_references": [
                    {
                        "type": "link_title",
                        "url": "https://example.com/",
                        "title": "Example Site",
                        "matched_text": "\ue200link_title\ue202Example Site\ue202key1\ue201",
                    },
                    {
                        "type": "grouped_webpages",
                        "url": "",
                        "items": [
                            {
                                "url": "https://example.com/page",
                                "title": "Page Title",
                                "attribution": "example.com",
                            },
                        ],
                        "matched_text": "\ue200cite\ue202key1\ue201",
                    },
                ],
            },
        }
        citations_dict_from_link_title, citations_dict_from_grouped_webpages = (
            build_citations_dicts(msg)
        )
        self.assertEqual(
            citations_dict_from_link_title["key1"],
            ("https://example.com/", "Example Site"),
        )
        self.assertEqual(
            citations_dict_from_grouped_webpages["key1"],
            ("https://example.com/page", "Page Title"),
        )

    def test_content_transformations(self):
        cases = [
            # (input, msg, citation_urls, source_refs, expected, description)
            (
                "\ue200filecite\ue202file123\ue201",
                {
                    "metadata": {
                        "content_references": [
                            {
                                "type": "file",
                                "name": "document.pdf",
                                "matched_text": "\ue200filecite\ue202file123\ue201",
                            },
                        ],
                    },
                },
                set(),
                {},
                "[1]",
                "filecite",
            ),
            (
                '\ue200entity\ue202["app","ChatGPT"]\ue201',
                {},
                set(),
                {},
                '["app","ChatGPT"]',
                "entity",
            ),
            (
                '\ue200entity\ue202["software", "uv", 0]\ue201',
                {},
                set(),
                {},
                "[software, uv]",
                "entity with 0",
            ),
            (
                '\ue200entity\ue202["software", "uv"]\ue201',
                {},
                set(),
                {},
                '["software", "uv"]',
                "entity alt text",
            ),
            (
                '\ue200product_entity\ue202["turn0product1","NVIDIA\u202fGeForce\u202fRTX\u202f4090"]\ue201',
                {},
                set(),
                {},
                "[NVIDIA\u202fGeForce\u202fRTX\u202f4090]",
                "product_entity",
            ),
            (
                '\ue200image_group\ue202{"layout":"carousel","query":["Toyota MR2","Porsche 924"]}\ue201',
                {},
                set(),
                {},
                "[IMAGE: Toyota MR2] [IMAGE: Porsche 924]",
                "image_group",
            ),
            (
                "\ue200link_title\ue202Open Site\ue202search1\ue201",
                {
                    "metadata": {
                        "content_references": [
                            {
                                "type": "link_title",
                                "url": "https://example.com/",
                                "title": "Open Site",
                                "matched_text": "\ue200link_title\ue202Open Site\ue202search1\ue201",
                            },
                        ],
                        "search_result_groups": [
                            {
                                "entries": [
                                    {
                                        "ref_id": {"turn_index": 0, "ref_index": 1},
                                        "url": "https://example.com/",
                                        "title": "Example",
                                    },
                                ],
                            },
                        ],
                    },
                },
                set(),
                {},
                "[Open Site](https://example.com/)",
                "link_title",
            ),
        ]
        for input_content, msg, citation_urls, source_refs, expected, desc in cases:
            result = transform_assistant_messages(
                input_content,
                msg,
                citation_urls,
                source_refs,
            )
            self.assertEqual(result, expected, f"Failed for: {desc}")


class TestMarkdown(unittest.TestCase):
    def test_markdown_generation(self):
        cases = [
            # (conv, expected_in_output, description)
            (
                MessageNode("msg1", "user", "Hello", "2024-01-01", "text"),
                [
                    "id: test-id",
                    "title: Test",
                    "created_at: 2024-01-01",
                    "word_count: 1",
                    "  1: https://example.com",
                ],
                "frontmatter fields",
            ),
            (
                MessageNode(
                    "msg1",
                    "user",
                    "Hello world",
                    "2024-01-01T10:30:00",
                    "text",
                ),
                ["USER · 2024-01-01T10:30:00", "Hello world"],
                "message format",
            ),
            (
                MessageNode(
                    "msg1",
                    "assistant",
                    'print("hello")',
                    "2024-01-01",
                    "code",
                    language="python",
                ),
                ["```python", 'print("hello")', "```"],
                "code block",
            ),
            (
                MessageNode("msg2", "assistant", "Branch", "2024-01-01", "text"),
                ["ASSISTANT · 2024-01-01", "Branch"],
                "assistant message",
            ),
        ]

        for i, (msg, expected_strings, desc) in enumerate(cases):
            if i == 0:
                conv = Conversation(
                    id="test-id",
                    title="Test",
                    create_time=1700000000.0,
                    messages=[msg],
                    citations={1: "https://example.com"},
                )
                content = conversation_to_markdown(
                    conv,
                    None,
                    1,
                    "2024-01-01",
                    "2024-01-01",
                )
            elif i == 3:
                main_msg = MessageNode(
                    "msg1",
                    "user",
                    "Main",
                    "2024-01-01",
                    "text",
                )
                conv = Conversation(
                    id="test",
                    title="Test",
                    create_time=0,
                    messages=[main_msg, msg],
                )
                content = conversation_to_markdown(
                    conv,
                    "/path",
                    2,
                    "2024-01-01",
                    "2024-01-01",
                )
            else:
                conv = Conversation(
                    id="test",
                    title="Test",
                    create_time=0,
                    messages=[msg],
                )
                content = conversation_to_markdown(
                    conv,
                    "/path",
                    2,
                    "2024-01-01",
                    "2024-01-01",
                )

            for exp in expected_strings:
                self.assertIn(exp, content, f"Failed for: {desc}, looking for: {exp}")

    def test_filename_and_wordcount(self):
        conv = Conversation(
            id="abc123",
            title="My Test Conversation",
            create_time=1700000000.0,
            messages=[],
        )
        filename = get_output_filename(conv)
        self.assertTrue(filename.startswith("my-test-conversation_"))
        self.assertTrue(filename.endswith(".md"))

        conv2 = Conversation(
            id="abc",
            title="Test",
            create_time=0,
            messages=[
                MessageNode("1", "user", "hello world", "2024-01-01", "text"),
                MessageNode(
                    "2",
                    "assistant",
                    "goodbye world",
                    "2024-01-01",
                    "text",
                ),
            ],
        )
        self.assertEqual(compute_word_count(conv2), 4)


class TestLoad(TestCase):
    def test_load_multiple_conversations(self):
        data = [
            {"conversation_id": "1", "title": "A", "create_time": 1.0, "mapping": {}},
            {"conversation_id": "2", "title": "B", "create_time": 2.0, "mapping": {}},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        try:
            result = load_conversations(Path(temp_path))
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["conversation_id"], "1")
            self.assertEqual(result[1]["conversation_id"], "2")
        finally:
            os.unlink(temp_path)

    def test_get_existing_file_in_subdir(self):
        conv_id = "subdir_conv_123"
        content = f"""---
id: {conv_id}
title: Test
---
# Body
"""
        junk_dir = TEST_VAULT / "sources" / "chats" / "junk"
        file_path = junk_dir / "test.md"
        file_path.write_text(content)

        chats_dir = TEST_VAULT / "sources" / "chats"
        found = get_existing_file_for_conversation(chats_dir, conv_id)
        self.assertIsNotNone(found)
        self.assertIn("junk", str(found))
        assert found is not None
        self.assertEqual(found.name, "test.md")


if __name__ == "__main__":
    unittest.main()
