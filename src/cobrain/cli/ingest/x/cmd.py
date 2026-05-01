import argparse
import sys

from cobrain.parsers.x import (
    POST_TYPE_OWN,
    POST_TYPE_LIKED,
    POST_TYPE_BOOKMARKED,
)


def _validate_args(args: argparse.Namespace) -> None:
    requires_own = ("since_id", "until_id")
    mutually_exclusive = (
        ("new", "count"),
        ("new", "since_id"),
        ("new", "until_id"),
        ("count", "since_id"),
        ("count", "until_id"),
    )

    for arg in requires_own:
        if getattr(args, arg) and not args.own:
            print(
                f"Error: --{arg.replace('_', '-')} only works with --own",
                file=sys.stderr,
            )
            sys.exit(1)

    for arg1, arg2 in mutually_exclusive:
        if getattr(args, arg1) and getattr(args, arg2):
            print(
                f"Error: --{arg1.replace('_', '-')} and --{arg2.replace('_', '-')} are mutually exclusive",
                file=sys.stderr,
            )
            sys.exit(1)


def cmd_ingest_x(args: argparse.Namespace) -> None:
    from cobrain.cli.ingest.x.parse import _parse_post_args

    _validate_args(args)

    post_ids = _parse_post_args(args.ids)
    endpoint = None
    if args.own:
        endpoint = POST_TYPE_OWN
    elif args.likes:
        endpoint = POST_TYPE_LIKED
    elif args.bookmarks:
        endpoint = POST_TYPE_BOOKMARKED

    try:
        from cobrain.parsers.x import get_x_client

        client = get_x_client(authorization_code=args.authorization_code)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to initialize X client: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        from cobrain.cli.ingest.x.ingest import _ingest_posts

        _ingest_posts(client, args, post_ids, endpoint)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
