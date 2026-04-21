import argparse
import sys

from hippo.cli.utils import _print_errors, print_sync_summary
from hippo.graph import sync as graph_sync


def cmd_sync(args: argparse.Namespace) -> None:
    result = graph_sync()

    if result.validation_errors:
        print(f"Sync failed: {len(result.validation_errors)} errors\n")
        _print_errors(result.validation_errors)
        sys.exit(1)

    print_sync_summary(result, show_warnings=args.warnings)
