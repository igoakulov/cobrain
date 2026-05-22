from cobrain.parsers.chatgpt.extract import (
    extract_content_with_attachments,
    extract_deep_research_from_call_tool,
    should_include_message,
)
from cobrain.parsers.chatgpt.format import format_timestamp
from cobrain.parsers.chatgpt.models import Conversation, MessageNode
from cobrain.parsers.chatgpt.transform import (
    transform_assistant_messages,
    transform_assistant_messages_deep_research,
)


def parse_conversation(conv: dict) -> Conversation:
    conv_id = conv.get("conversation_id") or conv.get("id", "")
    title = conv.get("title", "Untitled")
    create_time = conv.get("create_time", 0)

    mapping = conv.get("mapping", {})

    root = None
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            root = node_id
            break

    current_node = conv.get("current_node")
    ancestor_ids: set[str] = set()
    node_id = current_node
    while node_id:
        ancestor_ids.add(node_id)
        node = mapping.get(node_id)
        node_id = node.get("parent") if node else None

    deep_research_reports: list[tuple[str, list[dict]]] = []
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue
        author_name = msg.get("author", {}).get("name", "")
        if author_name == "api_tool.call_tool":
            result = extract_deep_research_from_call_tool(msg)
            if result:
                deep_research_reports.append(result)

    messages: list[MessageNode] = []
    source_refs: dict[str, int] = {}
    citation_urls: set[str] = set()

    if root:
        _traverse_messages(
            mapping,
            root,
            None,
            messages,
            deep_research_reports,
            source_refs,
            citation_urls,
            ancestor_ids,
        )

    while deep_research_reports:
        report_text, content_refs = deep_research_reports.pop(0)
        for node in mapping.values():
            msg = node.get("message")
            if not msg:
                continue
            if (
                msg.get("author", {}).get("role") == "assistant"
                and msg.get("recipient") == "api_tool.call_tool"
            ):
                parts = msg.get("content", {}).get("parts", [])
                text = parts[0] if parts else ""
                if "/Deep Research App/" in text:
                    content = transform_assistant_messages_deep_research(
                        report_text, content_refs, source_refs,
                    )
                    create_time = msg.get("create_time") or 0
                    messages.append(
                        MessageNode(
                            id=node.get("id", ""),
                            role="assistant",
                            content=content,
                            timestamp=format_timestamp(create_time),
                            content_type="text",
                            language="",
                            deep_research_report=report_text,
                        ),
                    )
                    break

    citations = {
        num: url for url, num in sorted(source_refs.items(), key=lambda x: x[1])
    }
    return Conversation(
        id=conv_id,
        title=title,
        create_time=create_time,
        messages=messages,
        citations=citations,
    )


def _traverse_messages(
    mapping: dict,
    node_id: str,
    parent_id: str | None,
    messages: list[MessageNode],
    deep_research_reports: list[tuple[str, list[dict]]],
    source_refs: dict[str, int],
    citation_urls: set[str],
    ancestor_ids: set[str] | None = None,
) -> str | None:
    node = mapping.get(node_id)
    if not node:
        return None

    if node.get("parent") != parent_id:
        return None

    if ancestor_ids and node_id not in ancestor_ids:
        children = node.get("children") or []
        for child_id in children:
            _traverse_messages(
                mapping,
                child_id,
                node_id,
                messages,
                deep_research_reports,
                source_refs,
                citation_urls,
                ancestor_ids,
            )
        return None

    msg = node.get("message")

    if should_include_message(msg):
        content, content_type, language, attachment_names, audio_placeholder = (
            extract_content_with_attachments(msg)
        )
        create_time = msg.get("create_time") or 0

        deep_research_refs: list[dict] | None = None
        deep_research_raw: str | None = None
        if (
            msg.get("recipient") == "api_tool.call_tool"
            and "/Deep Research App/" in content
            and deep_research_reports
        ):
            report_text, deep_research_refs = deep_research_reports.pop(0)
            deep_research_raw = report_text
            content = report_text

        if content or attachment_names or audio_placeholder:
            role = msg.get("author", {}).get("role", "")
            if role == "assistant":
                if deep_research_refs is not None:
                    content = transform_assistant_messages_deep_research(
                        content, deep_research_refs, source_refs,
                    )
                else:
                    content = transform_assistant_messages(
                        content, msg, citation_urls, source_refs,
                    )

            prefix_parts: list[str] = []
            if audio_placeholder:
                prefix_parts.append(audio_placeholder)
            prefix_parts.extend(attachment_names)

            final_content = content
            if prefix_parts:
                prefix = "\n".join(prefix_parts)
                if final_content:
                    final_content = f"{prefix}\n\n{final_content}"
                else:
                    final_content = prefix

            messages.append(
                MessageNode(
                    id=node_id,
                    role=msg["author"]["role"],
                    content=final_content,
                    timestamp=format_timestamp(create_time),
                    content_type=content_type,
                    language=language,
                    deep_research_report=deep_research_raw,
                ),
            )

    children = node.get("children") or []

    for child_id in children:
        _traverse_messages(
            mapping,
            child_id,
            node_id,
            messages,
            deep_research_reports,
            source_refs,
            citation_urls,
            ancestor_ids,
        )


def parse_conversation_expand(
    conv_data: dict, last_message_id: str | None,
) -> Conversation:
    conv = parse_conversation(conv_data)

    if last_message_id:
        seen_last = False
        filtered_messages = []
        for msg in conv.messages:
            if seen_last:
                filtered_messages.append(msg)
            elif msg.id == last_message_id:
                seen_last = True
        conv.messages = filtered_messages

    return conv
