import argparse
import subprocess
import sys
from hippo.graph import sync as graph_sync
from hippo.graph.html.html import build_html
from hippo.cli.utils import print_sync_summary


def cmd_show(args: argparse.Namespace) -> None:
    if args.sync:
        result = graph_sync()
        if result.validation_errors:
            print(f"Sync failed: {len(result.validation_errors)} errors\n")
            sys.exit(1)
        print_sync_summary(
            result, show_warnings=args.warnings if hasattr(args, "warnings") else False
        )

    graph_path = build_html()
    print(f"Vault visualization: {graph_path}")

    _open_browser(str(graph_path))


def _open_browser(path: str) -> None:
    platform = sys.platform

    try:
        if platform == "darwin":
            subprocess.run(["open", path], check=True)
        elif platform == "win32":
            subprocess.run(["start", "", path], shell=True, check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
    except Exception:
        print(f"Open in browser: {path}")
