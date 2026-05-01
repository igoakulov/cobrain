import argparse
import sys
import yaml

from cobrain.cli.utils import SetMetadataResult, _print_errors, print_sync_summary
from cobrain.graph import read_graph, sync as graph_sync
from cobrain.graph.validation import ValidationError
from cobrain.topics import update_frontmatter

MINIMAL_FIELDS = frozenset({"id", "aliases", "category", "parent", "related"})
FULL_FIELDS = frozenset(
    {
        "id",
        "title",
        "aliases",
        "created_at",
        "updated_at",
        "category",
        "parent",
        "related",
    }
)
FULL_PLUS_FIELDS = frozenset(
    {
        "id",
        "title",
        "aliases",
        "created_at",
        "updated_at",
        "category",
        "parent",
        "related",
        "sources",
        "word_count",
    }
)


def _project_fields(topics: list[dict], fields: frozenset | None) -> list[dict]:
    if fields is None:
        return topics
    return [{k: t.get(k) for k in fields} for t in topics]


def cmd_vault(args: argparse.Namespace) -> None:
    if args.vault_dir:
        _handle_vault_dir(args.vault_dir)
        return

    if args.to_topic and not args.from_topic:
        print("ERROR: --to requires --from", file=sys.stderr)
        sys.exit(1)

    if args.set:
        _handle_set(args)
        return

    if args.ids:
        _handle_ids(args)
        return

    if args.from_topic or args.to_topic:
        _handle_discovery(args)
        return

    _handle_list(args)


def _handle_vault_dir(vault_dir) -> None:
    from cobrain.config import init_vault
    from pathlib import Path

    vault_path = Path(vault_dir).expanduser().resolve()
    try:
        init_vault(vault_path)
        print(f"Vault ready at: {vault_path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _handle_set(args: argparse.Namespace) -> None:
    if not args.ids:
        print("ERROR: --set requires --ids", file=sys.stderr)
        sys.exit(1)

    topic_ids = [tid.strip() for tid in args.ids.split(",") if tid.strip()]
    if not topic_ids:
        print("ERROR: No topic ids provided", file=sys.stderr)
        sys.exit(1)

    result = _set_metadata(topic_ids, args.set)
    if result.errors:
        print(f"Update failed: {len(result.errors)} errors\n")
        _print_errors(result.errors)
        sys.exit(1)

    sync_result = graph_sync()
    if sync_result.validation_errors:
        print(f"Sync failed: {len(sync_result.validation_errors)} errors\n")
        _print_errors(sync_result.validation_errors)
        sys.exit(1)

    print_sync_summary(sync_result, show_warnings=False)


def _handle_ids(args: argparse.Namespace) -> None:
    topic_ids = [tid.strip() for tid in args.ids.split(",") if tid.strip()]
    if not topic_ids:
        print("ERROR: No topic ids provided", file=sys.stderr)
        sys.exit(1)

    yaml_style = False if args.block else True
    field_set = _get_field_set(args)

    topics = _get_topics()
    topic_map = {t["id"]: t for t in topics}

    selected = []
    for tid in topic_ids:
        if tid not in topic_map:
            print(f"ERROR: Topic not found: {tid}", file=sys.stderr)
            sys.exit(1)
        selected.append(topic_map[tid])

    output_data = _project_fields(selected, field_set)
    print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


def _handle_discovery(args: argparse.Namespace) -> None:
    yaml_style = False if args.block else True
    field_set = _get_field_set(args)

    topics = _get_topics()
    topic_map = {t["id"]: t for t in topics}

    if args.to_topic:
        path = _find_path_to_root(args.to_topic, topic_map)
        if path:
            output_topics = _project_fields(
                [topic_map[tid] for tid in path if tid in topic_map], field_set
            )
            print(
                yaml.dump(output_topics, default_flow_style=yaml_style, sort_keys=False)
            )
        else:
            print(f"ERROR: No path to root for: {args.to_topic}", file=sys.stderr)
            sys.exit(1)
    else:
        reachable = _get_reachable(args.from_topic, topic_map, topics, args.depth)
        reachable_topics = [topic_map[tid] for tid in reachable if tid in topic_map]
        output_data = _project_fields(reachable_topics, field_set)
        print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


def _handle_list(args: argparse.Namespace) -> None:
    result = read_graph()
    field_set = _get_field_set(args)
    yaml_style = False if args.block else True
    output_data = _project_fields([t.to_dict() for t in result.topics], field_set)
    print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


def _get_field_set(args: argparse.Namespace) -> frozenset:
    if hasattr(args, "full_plus") and args.full_plus:
        return FULL_PLUS_FIELDS
    if hasattr(args, "full") and args.full:
        return FULL_FIELDS
    return MINIMAL_FIELDS


def _get_topics() -> list[dict]:
    result = read_graph()
    return [t.to_dict() for t in result.topics]


def _set_metadata(topic_ids: list[str], set_fields: list[str]) -> SetMetadataResult:
    from cobrain.cli.utils import SetMetadataResult

    updates = {}
    for field in set_fields:
        if "=" not in field:
            print(
                f"ERROR: Invalid field format: {field} (expected key=value)",
                file=sys.stderr,
            )
            sys.exit(1)
        key, value = field.split("=", 1)
        updates[key.strip()] = _parse_value(value.strip())

    updated_count = 0
    errors: list[ValidationError] = []
    for topic_id in topic_ids:
        try:
            update_frontmatter(topic_id, updates)
            updated_count += 1
        except FileNotFoundError:
            errors.append(
                ValidationError(
                    topic_id=topic_id,
                    filename=f"{topic_id}.md",
                    message=f"Topic not found: {topic_id}",
                )
            )

    topic_str = "topic" if updated_count == 1 else "topics"
    print(f"Updated: {updated_count} {topic_str}")
    return SetMetadataResult(updated_count=updated_count, errors=errors)


def _parse_value(value: str):
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].split(",")
        return [v.strip() for v in items if v.strip()]
    return value


def _build_connection_map(topics: list[dict]) -> dict[str, list[tuple]]:
    conn_map: dict[str, list[tuple]] = {}
    for topic in topics:
        topic_id = topic["id"]
        conn_map.setdefault(topic_id, [])
        if topic.get("parent"):
            parent = topic["parent"]
            conn_map[topic_id].append((parent, "parent"))
            conn_map.setdefault(parent, []).append((topic_id, "parent"))
        for related_id in topic.get("related", []):
            conn_map[topic_id].append((related_id, "related"))
            conn_map.setdefault(related_id, []).append((topic_id, "related"))
    return conn_map


def _find_path_to_root(to_id: str, topic_map: dict) -> list[str] | None:
    if to_id not in topic_map:
        return None

    path = [to_id]
    current = to_id

    while True:
        current_topic = topic_map.get(current, {})
        parent = current_topic.get("parent")
        if not parent:
            break
        path.append(parent)
        current = parent

    path.reverse()
    return path


def _get_reachable(
    start_id: str, topic_map: dict, topics: list[dict], max_depth: int
) -> set[str]:
    conn_map = _build_connection_map(topics)
    reachable = {start_id}
    frontier = {start_id}

    for _ in range(max_depth):
        new_frontier = set()
        for tid in frontier:
            for neighbor, _ in conn_map.get(tid, []):
                new_frontier.add(neighbor)
        new_frontier -= reachable
        if not new_frontier:
            break
        reachable |= new_frontier
        frontier = new_frontier

    return reachable


def cmd_graph(args: argparse.Namespace) -> None:
    yaml_style = False if args.block else True

    field_set = None
    if hasattr(args, "full_plus") and args.full_plus:
        field_set = FULL_PLUS_FIELDS
    elif hasattr(args, "full") and args.full:
        field_set = FULL_FIELDS
    elif hasattr(args, "minimal") and args.minimal:
        field_set = MINIMAL_FIELDS
    else:
        field_set = MINIMAL_FIELDS

    if args.from_topic:
        _handle_discovery(args)
    elif args.to_topic:
        _handle_discovery(args)
    else:
        topics = _get_topics()
        output_data = {"topics": _project_fields(topics, field_set)}
        print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


def cmd_backup(args: argparse.Namespace) -> None:
    from cobrain.graph import create_backup

    backup_path = create_backup()
    print(f"Backup created: {backup_path.name}")
