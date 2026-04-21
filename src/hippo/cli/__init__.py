import argparse
import signal
import sys
from pathlib import Path

from hippo import __version__
from hippo.config import init_vault

from .graph import cmd_backup, cmd_graph
from .sources import cmd_sources
from .sync import cmd_sync
from .topics import cmd_topics


def cmd_init(args: argparse.Namespace) -> None:
    vault_path = Path(args.vault).expanduser().resolve()
    try:
        init_vault(vault_path)
        print(f"Initialized vault at: {vault_path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_version(args: argparse.Namespace) -> None:
    print(__version__)


def main() -> None:
    def _signal_handler(signum, frame):
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    parser = argparse.ArgumentParser(
        prog="hippo",
        description="Hippo - Local-first knowledge graph for agent-driven research.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new vault")
    init_parser.add_argument("--vault", required=True, help="Path to vault directory")
    init_parser.set_defaults(func=cmd_init)

    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    sync_parser = subparsers.add_parser("sync", help="Rebuild graph from files")
    sync_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    sync_parser.set_defaults(func=cmd_sync)

    topics_parser = subparsers.add_parser("topics", help="List or update topics")
    topics_parser.add_argument("--ids", help="Comma-separated topic IDs")
    topics_parser.add_argument(
        "--set", nargs="+", help="Set metadata (field=value pairs) in frontmatter"
    )
    topics_parser.add_argument("--sync", action="store_true", help="Sync after update")
    topics_parser.add_argument(
        "--warnings", action="store_true", help="Show warnings with --sync"
    )
    topics_parser.set_defaults(func=cmd_topics)

    graph_parser = subparsers.add_parser("graph", help="View graph")

    graph_parser.add_argument("--sync", action="store_true", help="Sync before output")
    graph_parser.add_argument(
        "--warnings", action="store_true", help="Show warnings with --sync"
    )

    traversal_group = graph_parser.add_argument_group("Discovery")
    traversal_group.add_argument("--from", dest="from_topic", help="Starting topic")
    traversal_group.add_argument("--depth", type=int, default=1, help="Traversal depth")
    traversal_group.add_argument("--to", dest="to_topic", help="Target topic for path")

    fields_group = graph_parser.add_argument_group("Fields")
    fields_group.add_argument(
        "--minimal",
        action="store_true",
        help="id, aliases, cluster, parent, related",
    )
    fields_group.add_argument(
        "--full",
        action="store_true",
        help="minimal + title, progress, created_at, updated_at",
    )
    fields_group.add_argument(
        "--full+",
        dest="full_plus",
        action="store_true",
        help="full + sources, word_count",
    )

    format_group = graph_parser.add_argument_group("Format")
    format_group.add_argument(
        "--flow",
        action="store_true",
        default=True,
        help="Flow style (default, compact)",
    )
    format_group.add_argument(
        "--block", action="store_true", help="Block style (human-readable)"
    )

    graph_parser.set_defaults(func=cmd_graph)

    backup_parser = subparsers.add_parser("backup", help="Create rolling backup")
    backup_parser.set_defaults(func=cmd_backup)

    sources_parser = subparsers.add_parser("sources", help="Manage sources")

    sources_parser.add_argument("--warnings", action="store_true", help="Show warnings")

    chatgpt_group = sources_parser.add_argument_group("ChatGPT")
    chatgpt_group.add_argument(
        "--ingest",
        choices=["chatgpt", "x"],
        help="Ingest source (e.g., chatgpt, x)",
    )
    chatgpt_group.add_argument(
        "--paths", nargs="+", help="Path(s) to conversations.json files"
    )
    chatgpt_group.add_argument(
        "--since", dest="since_datetime", help="Start datetime (ISO 8601, inclusive)"
    )
    chatgpt_group.add_argument(
        "--until", dest="until_datetime", help="End datetime (ISO 8601, inclusive)"
    )
    chatgpt_group.add_argument("--titles", help="Filter by titles (comma-separated)")

    x_endpoints_group = sources_parser.add_argument_group("X endpoints")
    x_endpoints_group.add_argument(
        "--ids", help="Comma-separated post IDs, URLs, or xurls"
    )
    x_endpoints_group.add_argument(
        "--own",
        action="store_true",
        help="Ingest own posts",
    )
    x_endpoints_group.add_argument(
        "--likes", action="store_true", help="Ingest liked posts"
    )
    x_endpoints_group.add_argument(
        "--bookmarks", action="store_true", help="Ingest bookmarked posts"
    )

    x_filters_group = sources_parser.add_argument_group("X filters")
    x_filters_group.add_argument(
        "--new",
        action="store_true",
        help="Loop until hitting existing posts",
    )
    x_filters_group.add_argument("--count", type=int, help="Total posts to fetch")
    x_filters_group.add_argument(
        "--since-id",
        dest="since_id",
        help="Oldest post ID (excl., --own only)",
    )
    x_filters_group.add_argument(
        "--until-id",
        dest="until_id",
        help="Newest post ID (excl., --own only)",
    )

    x_auth_group = sources_parser.add_argument_group("X auth")
    x_auth_group.add_argument(
        "--authorization-code",
        help="Authorization code from redirect URL",
    )

    sources_parser.set_defaults(func=cmd_sources)

    args = parser.parse_args()

    if hasattr(args, "warnings") and args.warnings:
        if args.command in ("topics", "graph") and not getattr(args, "sync", False):
            parser.error("--warnings requires --sync")

    try:
        args.func(args)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
