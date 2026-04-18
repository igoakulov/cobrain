import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from hippo.parsers.x import (
    XPost,
    XTree,
    get_x_client,
    get_existing_post_ids,
    get_x_trees_dir,
    load_all_cached_trees,
    save_tree,
    batch_expand_and_merge_trees,
    arrange_into_tree,
    get_output_filename,
    sort_tree_by_time,
    _find_tree_containing,
)
from hippo.parsers.x.client import (
    POST_TYPE_IDS,
    POST_TYPE_OWN,
    POST_TYPE_LIKED,
    POST_TYPE_BOOKMARKED,
)
from hippo.directories import get_x_log_path, get_x_logs_dir
from hippo.sources_archive import add_reference
from hippo.yaml_utils import write_yaml

X_ENDPOINTS = (POST_TYPE_OWN, POST_TYPE_LIKED, POST_TYPE_BOOKMARKED)


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
        client = get_x_client(authorization_code=args.authorization_code)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to initialize X client: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        _ingest_posts(client, args, post_ids, endpoint)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _ingest_posts(
    client, args: argparse.Namespace, post_ids: list[str], endpoint: str | None
) -> None:
    trees_dir = get_x_trees_dir()
    logs_dir = get_x_logs_dir()
    trees_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Load cached_trees
    cached_trees: dict[str, XTree] = {}
    for tree in load_all_cached_trees():
        cached_trees[tree.root.id] = tree

    # Step 2 & 3: Fetch all target posts
    target_posts: list[XPost] = []
    target_ids_returned: list[str] = []

    if post_ids:
        new_post_ids = []
        for pid in post_ids:
            if not _find_tree_containing(cached_trees, pid):
                new_post_ids.append(pid)

        if new_post_ids:
            post_type = endpoint if endpoint else POST_TYPE_IDS
            fetched = client.get_posts_by_ids(new_post_ids, post_type=post_type)
            for post in fetched:
                if post:
                    target_ids_returned.append(post.id)
                    if not _find_tree_containing(cached_trees, post.id):
                        target_posts.append(post)

    elif endpoint in X_ENDPOINTS:
        existing_ids = get_existing_post_ids()

        if args.authorization_code:
            client._token_manager.authorization_code = args.authorization_code
            try:
                client._token_manager._exchange_code()
            except Exception:
                pass

        since_id = args.since_id
        until_id = args.until_id
        count = args.count
        is_new = args.new if args.new else False

        if endpoint == POST_TYPE_OWN:
            posts = client.get_own_posts(
                since_id=since_id,
                until_id=until_id,
                count=count,
                existing_ids=existing_ids,
                is_new=is_new,
            )
        elif endpoint == POST_TYPE_LIKED:
            posts = client.get_liked_posts(
                count=count, existing_ids=existing_ids, is_new=is_new
            )
        elif endpoint == POST_TYPE_BOOKMARKED:
            posts = client.get_bookmarked_posts(
                count=count, existing_ids=existing_ids, is_new=is_new
            )
        else:
            posts = []

        for post in posts:
            target_ids_returned.append(post.id)
            if not _find_tree_containing(cached_trees, post.id):
                target_posts.append(post)

    else:
        print(
            "ERROR: Must specify --ids or one of --own, --likes, --bookmarks",
            file=sys.stderr,
        )
        sys.exit(1)

    target_posts.sort(key=lambda p: p.id)

    target_ids = [p.id for p in target_posts]

    # Step 4: Create new_trees for ALL targets
    new_trees: dict[str, XTree] = {}
    for post in target_posts:
        tree = arrange_into_tree([post])
        tree.conversation_xurl = f"{post.author_username}/status/{post.id}"
        new_trees[tree.root.id] = tree

    # Step 5: Run batch expand_and_merge_trees
    related_ids: list[str] = []
    updated_tree_ids: set[str] = set()

    related_ids = batch_expand_and_merge_trees(
        new_trees, cached_trees, updated_tree_ids
    )

    # Step 6: Save unmerged trees
    created = []
    updated = []
    ingest_timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    warnings: list[str] = []

    def save_tree_with_ref(tree: XTree) -> str | None:
        sort_tree_by_time(tree.root)
        filename = get_output_filename(tree)
        save_tree(tree)
        add_reference("x", f"sources/x/{filename}", [])
        return filename

    all_trees_to_save = list(new_trees.values())
    all_trees_to_save.extend(
        [t for t in cached_trees.values() if t.root.id in updated_tree_ids]
    )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(save_tree_with_ref, tree) for tree in all_trees_to_save
        ]
        for f in futures:
            f.result()

    for tree in new_trees.values():
        created.append(get_output_filename(tree))

    for tree in cached_trees.values():
        if tree.root.id in updated_tree_ids:
            updated.append(get_output_filename(tree))

    posts_added = len(target_ids) + len(related_ids)
    files_created = len(created)
    files_updated = len(updated)

    log_data = _build_log_data(
        args,
        endpoint,
        target_ids_returned,
        related_ids,
        posts_added,
        files_created,
        files_updated,
        warnings,
    )

    log_path = get_x_log_path(ingest_timestamp)
    write_yaml(log_path, log_data)

    parts = []
    if posts_added > 0 or files_created > 0 or files_updated > 0:
        if posts_added > 0:
            parts.append(f"{posts_added} posts added")
        if files_created > 0:
            parts.append(f"{files_created} files created")
        if files_updated > 0:
            parts.append(f"{files_updated} files updated")
    else:
        parts.append("0 new posts")

    print("Ingest complete: " + ", ".join(parts))
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"- {warning}")
    print(f"Log: {log_path}")


def _build_log_data(
    args: argparse.Namespace,
    endpoint: str | None,
    target_ids_returned: list[str],
    related_ids_returned: list[str],
    posts_added: int,
    files_created: int,
    files_updated: int,
    warnings: list[str] | None = None,
) -> dict:
    if endpoint and endpoint in X_ENDPOINTS:
        command_parts = [f"hippo sources --ingest x --{endpoint}"]
        if args.new:
            command_parts.append("--new")
        if args.since_id:
            command_parts.append(f"--since-id {args.since_id}")
        if args.until_id:
            command_parts.append(f"--until-id {args.until_id}")
        if args.count:
            command_parts.append(f"--count {args.count}")
        command = " ".join(command_parts)
    else:
        command = f"hippo sources --ingest x --ids {args.ids}"

    log_data = {
        "created_at": datetime.utcnow().strftime("%Y%m%dT%H%M%S"),
        "command": command,
        "target_ids_returned": (
            f"[{','.join(sorted(target_ids_returned))}]"
            if target_ids_returned
            else "[]"
        ),
        "target_ids_returned_count": len(target_ids_returned),
        "related_ids_returned": (
            f"[{','.join(sorted(related_ids_returned))}]"
            if related_ids_returned
            else "[]"
        ),
        "related_ids_returned_count": len(related_ids_returned),
        "posts_added": posts_added,
        "files_created": files_created,
        "files_updated": files_updated,
    }

    if warnings:
        log_data["warnings"] = warnings

    return log_data


def _parse_post_args(posts_arg: str | None) -> list[str]:
    if not posts_arg:
        return []

    post_ids = []
    for item in posts_arg.split(","):
        item = item.strip()
        if not item:
            continue

        post_id = _extract_post_id(item)
        if post_id:
            post_ids.append(post_id)

    return post_ids


def _extract_post_id(post_arg: str) -> str | None:
    post_arg = post_arg.strip()

    if post_arg.isdigit():
        return post_arg

    url_pattern = r"https?://x\.com/\w+/status/(\d+)"
    match = re.search(url_pattern, post_arg)
    if match:
        return match.group(1)

    return None
