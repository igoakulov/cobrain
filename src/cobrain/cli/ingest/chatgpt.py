import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from cobrain.cli.utils import _parse_iso_datetime
from cobrain.config import _get_vault_dir as _get_vault_dir
from cobrain.directories import (
    get_chat_log_path,
    get_chats_dir,
    get_chats_logs_dir,
)
from cobrain.parsers.chatgpt import (
    compute_word_count,
    conversation_to_markdown,
    filter_conversations,
    get_existing_file_for_conversation,
    get_existing_last_message_id,
    get_output_filename,
    load_conversations,
    parse_conversation,
)
from cobrain.yaml_utils import write_yaml


def cmd_ingest_chat(args: argparse.Namespace) -> None:
    paths = [Path(p).expanduser().resolve() for p in args.paths]
    for path in paths:
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)

    from_time = None
    till_time = None
    titles = None

    if args.since_datetime:
        try:
            from_time = _parse_iso_datetime(args.since_datetime).timestamp()
        except ValueError:
            print(
                f"ERROR: Invalid --since datetime: {args.since_datetime}",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.until_datetime:
        try:
            till_time = _parse_iso_datetime(args.until_datetime).timestamp()
        except ValueError:
            print(
                f"ERROR: Invalid --until datetime: {args.until_datetime}",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.titles:
        titles = [t.strip() for t in args.titles.split(",") if t.strip()]

    conversations = []
    for path in paths:
        convs = load_conversations(path)
        conversations.extend(convs)

    filtered = filter_conversations(conversations, from_time, till_time, titles)

    chats_dir = get_chats_dir()
    logs_dir = get_chats_logs_dir()
    vault_dir = _get_vault_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    updated_files = []
    skipped_files = []

    ingest_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")

    for conv_data in filtered:
        conv_id = conv_data.get("conversation_id") or conv_data.get("id", "")

        existing_file = get_existing_file_for_conversation(chats_dir, conv_id)
        existing_last_msg_id = None
        created_at = datetime.now(UTC).isoformat()
        existing_title = None

        if existing_file:
            existing_last_msg_id = get_existing_last_message_id(existing_file)
            existing_content = existing_file.read_text(encoding="utf-8")
            fm, _ = _split_frontmatter(existing_content)
            created_at = _get_created_at_from_file(existing_file)
            existing_title = fm.get("title") if fm else None

        conv = parse_conversation(conv_data)

        last_msg_id = conv.messages[-1].id if conv.messages else ""

        if existing_last_msg_id and last_msg_id == existing_last_msg_id:
            skipped_files.append(conv_id)
            continue

        output_filename = get_output_filename(conv)

        if existing_file:
            output_path = existing_file
            rel_path = str(existing_file.relative_to(vault_dir))
            updated_files.append((conv_id, last_msg_id, rel_path))
        else:
            output_path = chats_dir / output_filename
            rel_path = f"sources/chatgpt/{output_filename}"
            created_files.append((conv_id, last_msg_id, rel_path))

        updated_at = datetime.now(UTC).isoformat()
        word_count = compute_word_count(conv)
        title = existing_title or conv.title
        content = conversation_to_markdown(
            conv,
            source_path=None,
            word_count=word_count,
            created_at=created_at,
            updated_at=updated_at,
            last_message_id=last_msg_id,
            title=title,
        )

        output_path.write_text(content, encoding="utf-8")

    log_parts = ["brn", "sources", "--ingest", args.ingest, "--paths"]
    log_parts.extend(args.paths)
    if args.since_datetime:
        log_parts.extend(["--since", args.since_datetime])
    if args.until_datetime:
        log_parts.extend(["--until", args.until_datetime])
    if args.titles:
        log_parts.extend(["--titles", args.titles])

    log_data = {
        "created_at": ingest_timestamp,
        "command": " ".join(log_parts),
        "files_created": [
            {"conversation_id": c_id, "last_message_id": lmid, "output_file": opf}
            for c_id, lmid, opf in created_files
        ],
        "files_updated": [
            {"conversation_id": c_id, "last_message_id": lmid, "output_file": opf}
            for c_id, lmid, opf in updated_files
        ],
        "skipped": len(skipped_files),
    }

    if log_data["files_created"] or log_data["files_updated"]:
        log_path = get_chat_log_path(ingest_timestamp)
        write_yaml(log_path, log_data)

    total_created = len(created_files)
    total_updated = len(updated_files)
    print(
        f"Ingest complete: {total_created} created, {total_updated} updated, {len(skipped_files)} skipped",
    )


def _split_frontmatter(content: str) -> tuple[dict, str]:
    fm_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = fm_pattern.search(content)
    if match:
        fm_text = match.group(1)
        body = content[match.end() :]
        body = body.lstrip("\n")
        fm = {}
        for line in fm_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                fm[key.strip()] = value.strip()
        return fm, body
    return {}, content


def _get_created_at_from_file(file_path: Path) -> str:
    try:
        content = file_path.read_text(encoding="utf-8")
        pattern = re.compile(r"^created_at:\s*(.+)$", re.MULTILINE)
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return datetime.now(UTC).isoformat()
