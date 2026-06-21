import argparse
import sys
from pathlib import Path

from cobrain.cli.ingest import cmd_ingest_chat, cmd_ingest_x
from cobrain.config import get_warnings_ignored_sources
from cobrain.directories import VAULT_DIR
from cobrain.topics.topic import get_frontmatter


def is_ignored(rel_path: Path, ignore_list: list[str]) -> bool:
    if rel_path.name.startswith("."):
        return True
    rel_str = str(rel_path)
    for entry in ignore_list:
        if entry in rel_str:
            return True
    return False


def cmd_sources(args: argparse.Namespace) -> None:
    if args.ingest == "x":
        endpoints = [args.ids, args.own, args.likes, args.bookmarks]
        if sum(bool(e) for e in endpoints) > 1:
            print(
                "ERROR: --ids, --own, --likes, --bookmarks are mutually exclusive",
                file=sys.stderr,
            )
            sys.exit(1)

        filter_modes = [
            args.count is not None,
            args.new,
            args.since_id is not None,
            args.until_id is not None,
        ]
        if sum(filter_modes) > 1:
            print(
                "ERROR: --count, --new, --since-id, --until-id are mutually exclusive. Pick one.",
                file=sys.stderr,
            )
            sys.exit(1)

        cmd_ingest_x(args)
        return
    if args.ingest == "chatgpt":
        if not args.paths:
            print("ERROR: --paths required for chatgpt ingest", file=sys.stderr)
            sys.exit(1)
        cmd_ingest_chat(args)
        return

    summary_data = _get_sources_summary()
    unused_sources = _find_unused_sources()

    parts = []
    for dir_path, data in sorted(summary_data.items()):
        count = data["total"]
        parts.append(f"{dir_path}: {count}")

    warning_count = sum(len(v) for v in unused_sources.values())
    parts.append(f"warnings: {warning_count}")

    summary = ", ".join(parts)
    if warning_count > 0 and not args.warnings:
        summary += " (add --warnings)"
    print(summary)

    if args.warnings and unused_sources:
        _print_unused_sources(unused_sources)


def _get_sources_summary() -> dict[str, dict[str, int]]:
    sources_dir = VAULT_DIR / "sources"
    if not sources_dir.exists():
        return {}

    ignore_list = get_warnings_ignored_sources()
    result: dict[str, dict[str, int]] = {}
    for subdir in sources_dir.rglob("*"):
        if subdir.is_file():
            rel = subdir.relative_to(VAULT_DIR)
            if is_ignored(rel, ignore_list):
                continue
            parent_dir = str(rel.parent)
            if parent_dir not in result:
                result[parent_dir] = {"total": 0}
            result[parent_dir]["total"] += 1

    return result


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

    ignore_list = get_warnings_ignored_sources()
    all_sources_files: dict[str, set[str]] = {}
    for subdir in sources_dir.rglob("*"):
        if subdir.is_file():
            rel = subdir.relative_to(VAULT_DIR)
            if is_ignored(rel, ignore_list):
                continue
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
