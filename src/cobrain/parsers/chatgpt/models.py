from dataclasses import dataclass, field
from typing import Any

INCLUDE_CONTENT_TYPES = {
    "text",
    "execution_output",
    "tether_quote",
    "sonic_webpage",
    "system_error",
    "multimodal_text",
}

EXCLUDE_CONTENT_TYPES = {
    "user_editable_context",
    "thoughts",
    "reasoning_recap",
    "tether_browsing_display",
    "app_pairing_content",
}

EXCLUDE_ROLES = {"system", "tool"}


@dataclass
class MessageNode:
    id: str
    role: str
    content: str
    timestamp: str
    content_type: str
    language: str = ""
    deep_research_report: str | None = None


@dataclass
class Conversation:
    id: str
    title: str
    create_time: float
    messages: list[MessageNode] = field(default_factory=list)
    citations: dict[int, str] = field(default_factory=dict)


@dataclass
class IngestLog:
    conversation_id: str
    output_file: str
    last_message_id: str
    source_hash: str
    ingested_at: str
    filters: dict[str, Any] | None = None
