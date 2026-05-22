import re
from datetime import datetime
from pathlib import Path

from cobrain.parsers.chatgpt.models import Conversation
from cobrain.yaml_utils import read_yaml_list


def trim_url(url: str) -> str:
    url = re.sub(r"[?&]utm_source=[^&]*", "", url)
    url = re.sub(r"#:~:.*", "", url)
    url = url.rstrip(")")
    return url


def compute_word_count(conv: Conversation) -> int:
    count = 0
    for msg in conv.messages:
        count += len(msg.content.split())
    return count


def get_output_filename(conv: Conversation) -> str:
    slug = conv.title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")
    dt = datetime.fromtimestamp(conv.create_time).strftime("%Y-%m-%dT%H-%M-%S")
    return f"{slug}_{dt}.md"


def get_existing_last_message_id(file_path: Path) -> str | None:
    if not file_path.exists():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        fm_pattern = re.compile(r"^last_message_id:\s*(.+)$", re.MULTILINE)
        match = fm_pattern.search(content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None


def get_existing_file_for_conversation(
    chats_dir: Path,
    conversation_id: str,
) -> Path | None:
    if not chats_dir.exists():
        return None
    for md_file in chats_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            id_pattern = re.compile(r"^id:\s*(.+)$", re.MULTILINE)
            match = id_pattern.search(content)
            if match and match.group(1).strip() == conversation_id:
                return md_file
        except Exception:
            continue
    return None


def get_stem_from_filename(filename: str) -> str:
    return filename.rsplit(".", 1)[0]


def get_log_entries(logs_dir: Path) -> list[dict]:
    entries = {}
    if not logs_dir.exists():
        return []
    for log_file in sorted(logs_dir.glob("ingest_*.yaml")):
        data = read_yaml_list(log_file)
        if not data:
            continue
        for entry in data:
            conv_id = entry.get("conversation_id")
            if conv_id:
                entries[conv_id] = entry
    return list(entries.values())
