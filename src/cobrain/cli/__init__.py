import argparse
import signal
import sys
from pathlib import Path

from cobrain import __version__
from cobrain.config import init_vault

from .show import cmd_show
from .sources import cmd_sources
from .sync import cmd_sync
from .vault import cmd_backup, cmd_vault


def cmd_version(args: argparse.Namespace) -> None:
    print(__version__)


def cmd_init(args: argparse.Namespace) -> None:
    vault_path = Path.cwd().resolve()
    try:
        init_vault(vault_path)
        print(f"Vault initialized at: {vault_path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    def _signal_handler(signum, frame):
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    prog = "brn" if "brn" in sys.argv[0] else "cobrain"
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Cobrain CLI helps AI agents gather, organize and visualize owner's knowledge locally on device. Use it to back up and organize your knowledge, help AI agents read your mind, or map and track your learning progress.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize vault in current directory",
    )
    init_parser.set_defaults(func=cmd_init)

    sync_parser = subparsers.add_parser("sync", help="Rebuild vault graph from files")
    sync_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    sync_parser.set_defaults(func=cmd_sync)

    vault_parser = subparsers.add_parser("vault", help="List or update topics")

    vault_parser.add_argument(
        "--set",
        nargs="+",
        help="Set metadata for --ids (also syncs)",
    )

    traversal_group = vault_parser.add_argument_group("Discovery")
    traversal_group.add_argument("--ids", help="Comma-separated topic IDs")
    traversal_group.add_argument("--from", dest="from_topic", help="Starting topic")
    traversal_group.add_argument("--depth", type=int, default=1, help="Traversal depth")
    traversal_group.add_argument("--to", dest="to_topic", help="Target topic for path")

    fields_group = vault_parser.add_argument_group("Fields")
    fields_group.add_argument(
        "--minimal",
        action="store_true",
        help="id, aliases, category, parent, related",
    )
    fields_group.add_argument(
        "--full",
        action="store_true",
        help="minimal + title, created_at, updated_at",
    )
    fields_group.add_argument(
        "--full+",
        dest="full_plus",
        action="store_true",
        help="full + sources, word_count",
    )

    format_group = vault_parser.add_argument_group("Format")
    format_group.add_argument(
        "--flow",
        action="store_true",
        default=True,
        help="Flow style (default, compact)",
    )
    format_group.add_argument(
        "--block",
        action="store_true",
        help="Block style (human-readable)",
    )

    vault_parser.set_defaults(func=cmd_vault)

    show_parser = subparsers.add_parser("show", help="Show vault in browser")
    show_parser.set_defaults(func=cmd_show)

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
        "--paths",
        nargs="+",
        help="Path(s) to conversations.json files",
    )
    chatgpt_group.add_argument(
        "--since",
        dest="since_datetime",
        help="Start datetime (ISO 8601, inclusive)",
    )
    chatgpt_group.add_argument(
        "--until",
        dest="until_datetime",
        help="End datetime (ISO 8601, inclusive)",
    )
    chatgpt_group.add_argument("--titles", help="Filter by titles (comma-separated)")

    x_endpoints_group = sources_parser.add_argument_group("X endpoints")
    x_endpoints_group.add_argument(
        "--ids",
        help="Comma-separated post IDs, URLs, or xurls",
    )
    x_endpoints_group.add_argument(
        "--own",
        action="store_true",
        help="Ingest own posts",
    )
    x_endpoints_group.add_argument(
        "--likes",
        action="store_true",
        help="Ingest liked posts",
    )
    x_endpoints_group.add_argument(
        "--bookmarks",
        action="store_true",
        help="Ingest bookmarked posts",
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

    try:
        args.func(args)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
