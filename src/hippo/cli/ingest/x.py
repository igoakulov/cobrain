import argparse
import re
import sys
import time
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
from hippo.directories import get_x_log_path, get_x_logs_dir
from hippo.sources_archive import add_reference
from hippo.yaml_utils import write_yaml


_timing_start: float | None = None
_total_start: float | None = None
_lookup_count: int = 0
_lookup_time: float = 0.0
_lookup_section_start: float | None = None


def _start_total() -> None:
    global _total_start
    _total_start = time.perf_counter()


def _end_total() -> float:
    global _total_start
    if _total_start is None:
        return 0.0
    elapsed = time.perf_counter() - _total_start
    return elapsed


def _start_timing() -> None:
    global _timing_start
    _timing_start = time.perf_counter()


def _end_timing(label: str, count: int = 0) -> None:
    global _timing_start
    if _timing_start is None:
        return
    elapsed = time.perf_counter() - _timing_start
    if count > 0:
        print(f"{label}: {elapsed:.3f}s ({count}, avg {elapsed / count:.3f}s)")
    else:
        print(f"{label}: {elapsed:.3f}s (0)")
    _timing_start = None


def _start_lookup_section() -> None:
    global _lookup_section_start
    _lookup_section_start = time.perf_counter()


def _end_lookup_section() -> None:
    global _lookup_section_start, _lookup_count, _lookup_time
    if _lookup_section_start is not None:
        _lookup_time += time.perf_counter() - _lookup_section_start
        _lookup_section_start = None


def _tick_lookup() -> None:
    global _lookup_count
    _lookup_count += 1


def _report_lookup_timing(label: str) -> None:
    global _lookup_time, _lookup_count
    if _lookup_count > 0:
        print(
            f"{label}: {_lookup_count} lookups, {_lookup_time:.3f}s (avg {_lookup_time / _lookup_count:.3f}s)"
        )
    else:
        print(f"{label}: 0 lookups, 0.000s")
    _lookup_time = 0.0
    _lookup_count = 0


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
    if args.count and args.since_id:
        print("Error: --count and --since-id are mutually exclusive", file=sys.stderr)
        sys.exit(1)
    if args.count and args.until_id:
        print("Error: --count and --until-id are mutually exclusive", file=sys.stderr)
        sys.exit(1)
    if args.new and args.since_id:
        print("Error: --new and --since-id are mutually exclusive", file=sys.stderr)
        sys.exit(1)
    if args.new and args.until_id:
        print("Error: --new and --until-id are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    post_ids = _parse_post_args(args.ids)
    endpoint = (
        "own"
        if args.own
        else "likes"
        if args.likes
        else "bookmarks"
        if args.bookmarks
        else None
    )

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
    _start_total()
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
        _start_timing()
        _start_lookup_section()

        new_post_ids = []
        for pid in post_ids:
            if _find_tree_containing(cached_trees, pid):
                _tick_lookup()
            else:
                new_post_ids.append(pid)
                _tick_lookup()

        _end_lookup_section()
        _report_lookup_timing("Tree lookup")

        if new_post_ids:
            post_type = endpoint if endpoint else "ids"
            fetched = client.get_posts_by_ids(new_post_ids, post_type=post_type)
            for post in fetched:
                if post:
                    target_posts.append(post)

        _end_timing("Fetch --ids", len(post_ids))

    elif endpoint in ("own", "likes", "bookmarks"):
        _start_timing()
        existing_ids = get_existing_post_ids()
        _end_timing("Load existing IDs", len(existing_ids) if existing_ids else 0)

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

        if endpoint == "own":
            posts = client.get_own_posts(
                since_id=since_id,
                until_id=until_id,
                count=count,
                existing_ids=existing_ids,
                is_new=is_new,
            )
        elif endpoint == "likes":
            posts = client.get_liked_posts(
                count=count, existing_ids=existing_ids, is_new=is_new
            )
        elif endpoint == "bookmarks":
            posts = client.get_bookmarked_posts(
                count=count, existing_ids=existing_ids, is_new=is_new
            )
        else:
            posts = []

        for post in posts:
            _start_lookup_section()
            if _find_tree_containing(cached_trees, post.id):
                _end_lookup_section()
                _tick_lookup()
                continue
            _end_lookup_section()
            _tick_lookup()
            target_posts.append(post)
        _report_lookup_timing("Tree lookup")

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
    _start_timing()

    related_ids = batch_expand_and_merge_trees(
        new_trees, cached_trees, updated_tree_ids
    )

    tree_count = len(new_trees)
    _end_timing("Parent traversal", tree_count)

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

    _start_timing()
    save_count = 0

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
        save_count += 1
        created.append(get_output_filename(tree))

    for tree in cached_trees.values():
        if tree.root.id in updated_tree_ids:
            save_count += 1
            updated.append(get_output_filename(tree))

    _timing_count = save_count
    _end_timing("Save trees", save_count)

    log_data = _build_log_data(
        args,
        endpoint,
        target_ids,
        related_ids,
        warnings,
    )

    log_path = get_x_log_path(ingest_timestamp)
    write_yaml(log_path, log_data)

    # Simple counts - reuse what we already have
    posts_added = len(target_ids) + len(related_ids)
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

    # Total run time
    elapsed = _end_total()
    print(f"Total ingest: {elapsed:.3f}s")


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
