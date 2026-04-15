import argparse
import re
import sys
from datetime import datetime

from hippo.parsers.x import (
    XPost,
    XTree,
    get_x_client,
    get_existing_post_ids,
    get_x_trees_dir,
    load_all_cached_trees,
    save_tree,
    expand_and_merge_tree,
    arrange_into_tree,
    get_output_filename,
    sort_tree_by_time,
    _find_tree_containing,
)
from hippo.directories import get_x_log_path, get_x_logs_dir
from hippo.sources_archive import add_reference
from hippo.yaml_utils import write_yaml


def cmd_ingest_x(args: argparse.Namespace) -> None:
    if args.since_id and not args.own:
        print("Error: --since-id only works with --own", file=sys.stderr)
        sys.exit(1)
    if args.until_id and not args.own:
        print("Error: --until-id only works with --own", file=sys.stderr)
        sys.exit(1)
    if args.new and args.count:
        print("Error: --new and --count are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    post_ids = _parse_post_args(args.ids)
    endpoint = args.own or args.likes or args.bookmarks

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

    if post_ids:
        post_type = "ids"
        for pid in post_ids:
            if _find_tree_containing(cached_trees, pid):
                continue
            post = client.get_post_by_id(pid, post_type)
            if post:
                target_posts.append(post)

    elif endpoint in ("own", "likes", "bookmarks"):
        existing_ids = get_existing_post_ids()

        if args.authorization_code:
            client._token_manager.authorization_code = args.authorization_code
            try:
                client._token_manager._exchange_code()
            except Exception:
                pass

        loop = getattr(args, "new", False)
        since_id = args.since_id
        until_id = args.until_id
        count = args.count

        if endpoint == "own":
            posts = client.get_own_posts(
                since_id=since_id,
                until_id=until_id,
                count=count,
                loop=loop,
                existing_ids=existing_ids,
            )
        elif endpoint == "likes":
            posts = client.get_liked_posts(
                count=count, loop=loop, existing_ids=existing_ids
            )
        elif endpoint == "bookmarks":
            posts = client.get_bookmarked_posts(
                count=count, loop=loop, existing_ids=existing_ids
            )
        else:
            posts = []

        for post in posts:
            if _find_tree_containing(cached_trees, post.id):
                continue
            target_posts.append(post)

    else:
        print(
            "ERROR: Must specify --ids or one of --own, --liked, --bookmarked",
            file=sys.stderr,
        )
        sys.exit(1)

    target_posts.sort(key=lambda p: p.id)

    target_ids = [p.id for p in target_posts]

    # Step 4: Create new_trees for ALL targets
    new_trees: dict[str, XTree] = {}
    for post in target_posts:
        tree = arrange_into_tree([post])
        new_trees[tree.root.id] = tree

    # Step 5: Run expand_and_merge_tree on each
    all_related_ids: list[str] = []
    updated_tree_ids: set[str] = set()
    for tree in list(new_trees.values()):
        related_ids = expand_and_merge_tree(
            tree, cached_trees, new_trees, updated_tree_ids
        )
        all_related_ids.extend(related_ids)

    # Step 6: Save unmerged trees
    created = []
    updated = []
    ingest_timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    warnings: list[str] = []

    for tree in new_trees.values():
        sort_tree_by_time(tree.root)
        created.append(get_output_filename(tree))
        save_tree(tree)
        add_reference("x", f"sources/x/{get_output_filename(tree)}", [])

    # Track which cached_trees were modified
    for tree in cached_trees.values():
        sort_tree_by_time(tree.root)
        save_tree(tree)
        add_reference("x", f"sources/x/{get_output_filename(tree)}", [])
        if tree.root.id in updated_tree_ids:
            updated.append(get_output_filename(tree))

    log_data = _build_log_data(
        args,
        endpoint,
        target_ids,
        all_related_ids,
        warnings,
    )

    log_path = get_x_log_path(ingest_timestamp)
    write_yaml(log_path, log_data)

    # Simple counts - reuse what we already have
    posts_added = len(target_ids) + len(all_related_ids)
    files_created = len(created)
    files_updated = len(updated)

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
    target_ids: list[str],
    related_ids: list[str],
    warnings: list[str] | None = None,
) -> dict:
    if endpoint and endpoint in ("own", "likes", "bookmarks"):
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
        "command": command,
        "target_ids": f"[{','.join(sorted(target_ids))}]" if target_ids else "[]",
        "target_ids_count": len(target_ids) if target_ids else 0,
        "related_ids": f"[{','.join(sorted(related_ids))}]" if related_ids else "[]",
        "related_ids_count": len(related_ids),
        "created_at": datetime.utcnow().strftime("%Y%m%dT%H%M%S"),
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
