import argparse

from hippo.cli.ingest import cmd_ingest_chat, cmd_ingest_x
from hippo.directories import VAULT_DIR
from hippo.sources_archive import get_source_stats
from hippo.topics.topic import get_frontmatter
from hippo.yaml_utils import read_yaml


def cmd_sources(args: argparse.Namespace) -> None:
    if args.ingest == "x":
        cmd_ingest_x(args)
        return
    if args.ingest == "chatgpt":
        cmd_ingest_chat(args)
        return

    stats = get_source_stats()
    unused_sources = _find_unused_sources()
    incomplete_conversations = _find_incomplete_x_conversations()

    parts = []
    x_count = stats["by_type"].get("x", 0)
    if x_count:
        parts.append(f"{x_count} X conversations")
    for type_name, count in stats["by_type"].items():
        if type_name != "x":
            parts.append(f"{count} {type_name}")

    warning_count = sum(len(v) for v in unused_sources.values()) + len(
        incomplete_conversations
    )
    summary = f"Total sources: {', '.join(parts)}, {stats['removed']} removed, {warning_count} warnings"
    if warning_count > 0 and not args.warnings:
        summary += " (see --warnings)"
    print(summary)

    if args.warnings:
        if unused_sources:
            print()
            _print_unused_sources(unused_sources)
        if incomplete_conversations:
            print()
            _print_incomplete_conversations(incomplete_conversations)


def _print_unused_sources(unused_sources: dict[str, list[str]]) -> None:
    for dir_path, files in sorted(unused_sources.items()):
        dir_display = dir_path if dir_path.endswith("/") else f"{dir_path}/"
        header = f"UNUSED SOURCES in {dir_display}:"
        print(header)
        for f in files:
            print(f"- {f}")


def _find_unused_sources() -> dict[str, list[str]]:
    sources_dir = VAULT_DIR / "sources"
    if not sources_dir.exists():
        return {}

    all_sources_files: dict[str, set[str]] = {}
    for subdir in sources_dir.rglob("*"):
        if subdir.is_file():
            rel = subdir.relative_to(VAULT_DIR)
            parent_dir = str(rel.parent)
            filename = rel.name
            if parent_dir not in all_sources_files:
                all_sources_files[parent_dir] = set()
            all_sources_files[parent_dir].add(filename)

    referenced_sources: set[str] = set()
    topics_dir = VAULT_DIR / "topics"
    if topics_dir.exists():
        for topic_file in topics_dir.glob("*.md"):
            fm = get_frontmatter(topic_file.stem)
            if fm and fm.get("sources"):
                for src in fm.get("sources", []):
                    referenced_sources.add(src)

    result: dict[str, list[str]] = {}
    for dir_path, files in all_sources_files.items():
        unused = [f for f in files if f"{dir_path}/{f}" not in referenced_sources]
        if unused:
            result[dir_path] = sorted(unused)

    return result


def _find_incomplete_x_conversations() -> list[str]:
    sources_x_dir = VAULT_DIR / "sources" / "x"
    if not sources_x_dir.exists():
        return []

    incomplete = []
    for yaml_file in sources_x_dir.glob("*.yaml"):
        data = read_yaml(yaml_file)
        if not data:
            continue
        conversation_xurl = data.get("conversation_xurl", "")
        xurl = data.get("xurl", "")
        if conversation_xurl and xurl and conversation_xurl != xurl:
            incomplete.append(yaml_file.name)
    return sorted(incomplete)


def _print_incomplete_conversations(incomplete_conversations: list[str]) -> None:
    print("INCOMPLETE CONVERSATIONS (root xurl != conversation_xurl) in sources/x/:")
    for conv in incomplete_conversations:
        print(f"- {conv}")
