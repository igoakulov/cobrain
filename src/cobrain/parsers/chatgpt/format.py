from datetime import datetime

from cobrain.parsers.chatgpt.models import Conversation, MessageNode


def format_timestamp(create_time: float) -> str:
    dt = datetime.fromtimestamp(create_time)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _format_message_lines(msg: MessageNode) -> list[str]:
    lines = []
    role_prefix = "USER" if msg.role == "user" else "ASSISTANT"
    lines.append(f"{role_prefix} · {msg.timestamp}")
    lines.append("")
    if msg.content_type == "code":
        lang = msg.language or ""
        content_lines = msg.content.split("\n")
        lines.append(f"```{lang}")
        lines.extend(content_lines)
        lines.append("```")
    else:
        lines.append(msg.content)
    return lines


def message_to_markdown(msg: MessageNode) -> str:
    return "\n".join(_format_message_lines(msg))


def conversation_to_markdown(
    conv: Conversation,
    source_path: str | None,
    word_count: int,
    created_at: str,
    updated_at: str,
    last_message_id: str = "",
    title: str = "",
) -> str:
    lines = ["---"]
    lines.append(f"id: {conv.id}")
    lines.append(f"title: {title or conv.title}")
    lines.append(f"created_at: {created_at}")
    lines.append(f"updated_at: {updated_at}")
    lines.append(
        f"original_conversation_created_at: {format_timestamp(conv.create_time)}",
    )
    if last_message_id:
        lines.append(f"last_message_id: {last_message_id}")
    lines.append(f"word_count: {word_count}")
    lines.append("citations:")
    if conv.citations:
        for num in sorted(conv.citations):
            lines.append(f"  {num}: {conv.citations[num]}")
    lines.append("---")
    lines.append("")

    for msg in conv.messages:
        lines.extend(_format_message_lines(msg))
        lines.append("")
        lines.append("***")
        lines.append("")

    return "\n".join(lines).strip()
