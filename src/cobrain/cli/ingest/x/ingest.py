import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from cobrain.parsers.x import (
    XPost,
    XTree,
    get_existing_post_ids,
    get_x_trees_dir,
    load_all_cached_trees,
    save_tree,
    expand_and_merge_trees,
    arrange_into_tree,
    sort_tree_by_time,
    _find_tree_containing,
    find_tree_file_by_id,
    POST_TYPE_IDS,
    POST_TYPE_OWN,
    POST_TYPE_LIKED,
    POST_TYPE_BOOKMARKED,
)
from cobrain.config import _get_vault_dir as _get_vault_dir
from cobrain.directories import (
    get_x_log_path,
    get_x_logs_dir,
)
from cobrain.yaml_utils import write_yaml

X_ENDPOINTS = (POST_TYPE_OWN, POST_TYPE_LIKED, POST_TYPE_BOOKMARKED)


def _ingest_posts(client, args, post_ids: list[str], endpoint: str | None) -> None:
    trees_dir = get_x_trees_dir()
    logs_dir = get_x_logs_dir()
    trees_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    cached_trees: dict[str, XTree] = {}
    for tree in load_all_cached_trees():
        cached_trees[tree.root.id] = tree

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

        if endpoint:
            posts = client.get_posts(
                endpoint,
                since_id=since_id,
                until_id=until_id,
                count=count,
                existing_ids=existing_ids,
                is_new=is_new,
            )
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

    new_trees: dict[str, XTree] = {}
    for post in target_posts:
        tree = arrange_into_tree([post])
        tree.conversation_xurl = f"{post.author_username}/status/{post.id}"
        new_trees[tree.root.id] = tree

    related_ids: list[str] = []
    updated_tree_ids: set[str] = set()

    related_ids = expand_and_merge_trees(new_trees, cached_trees, updated_tree_ids)

    created = []
    updated = []
    ingest_timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    warnings: list[str] = []
    vault_dir = _get_vault_dir()

    new_tree_ids = set(new_trees.keys())
    updated_tree_ids = set(updated_tree_ids)

    def save_tree_with_ref(tree: XTree) -> tuple[str, bool] | None:
        existing_path = find_tree_file_by_id(tree.root.id)
        sort_tree_by_time(tree.root)
        tree_path = save_tree(tree, existing_path)
        rel_path = tree_path.relative_to(vault_dir)
        is_new = tree.root.id in new_tree_ids
        return (str(rel_path), is_new)

    all_trees_to_save = list(new_trees.values())
    all_trees_to_save.extend(
        [t for t in cached_trees.values() if t.root.id in updated_tree_ids]
    )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(save_tree_with_ref, tree) for tree in all_trees_to_save
        ]
        for f in futures:
            result = f.result()
            if result:
                path, is_new = result
                if is_new:
                    created.append(path)
                else:
                    updated.append(path)

    posts_added = len(target_ids) + len(related_ids)
    files_created = len(created)
    files_updated = len(updated)

    log_data = _build_log_data(
        args,
        endpoint,
        target_ids_returned,
        related_ids,
        posts_added,
        created,
        updated,
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
    args,
    endpoint: str | None,
    target_ids_returned: list[str],
    related_ids_returned: list[str],
    posts_added: int,
    files_created: list[str],
    files_updated: list[str],
    warnings: list[str] | None = None,
) -> dict:
    command_parts = ["brn", "sources", "--ingest", args.ingest]

    if args.ids:
        command_parts.extend(["--ids", args.ids])
    elif args.own:
        command_parts.append("--own")
    elif args.likes:
        command_parts.append("--likes")
    elif args.bookmarks:
        command_parts.append("--bookmarks")

    if args.new:
        command_parts.append("--new")
    if args.since_id:
        command_parts.extend(["--since-id", args.since_id])
    if args.until_id:
        command_parts.extend(["--until-id", args.until_id])
    if args.count is not None:
        command_parts.extend(["--count", str(args.count)])

    command = " ".join(command_parts)

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
