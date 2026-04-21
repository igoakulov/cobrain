import argparse
import sys
from collections import deque

import yaml

from hippo.cli.utils import _print_errors, print_sync_summary
from hippo.graph import read_graph, sync as graph_sync

MINIMAL_FIELDS = frozenset({"id", "aliases", "cluster", "parent", "related"})
FULL_FIELDS = frozenset(
    {
        "id",
        "title",
        "aliases",
        "progress",
        "created_at",
        "updated_at",
        "cluster",
        "parent",
        "related",
    }
)
FULL_PLUS_FIELDS = frozenset(
    {
        "id",
        "title",
        "aliases",
        "progress",
        "created_at",
        "updated_at",
        "cluster",
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


def cmd_graph(args: argparse.Namespace) -> None:
    yaml_style = False if args.block else True  # True = flow, False = block
    show_sync_summary = False

    field_set = None
    if hasattr(args, "full_plus") and args.full_plus:
        field_set = FULL_PLUS_FIELDS
    elif hasattr(args, "full") and args.full:
        field_set = FULL_FIELDS
    elif hasattr(args, "minimal") and args.minimal:
        field_set = MINIMAL_FIELDS
    else:
        field_set = MINIMAL_FIELDS

    if args.sync:
        result = graph_sync()
        if result.validation_errors:
            print(f"Sync failed: {len(result.validation_errors)} errors\n")
            _print_errors(result.validation_errors)
            sys.exit(1)
        print_sync_summary(result, show_warnings=args.warnings)
        show_sync_summary = True
        topics = [t.to_dict() for t in result.topics]
    else:
        result = read_graph()
        topics = [t.to_dict() for t in result.topics]

    if args.from_topic:
        _show_neighborhood(
            args.from_topic, topics, args.depth, args.to_topic, yaml_style, field_set
        )
    elif args.to_topic:
        _show_path_to(args.to_topic, topics, yaml_style, field_set)
    else:
        if show_sync_summary and not args.warnings:
            print()
        output_data = {
            "topics": _project_fields(topics, field_set),
        }
        print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


def cmd_backup(args: argparse.Namespace) -> None:
    from hippo.graph import create_backup, read_graph

    result = read_graph()
    backup_path = create_backup(result)
    print(f"Backup created: {backup_path.name}")


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


def _show_neighborhood(
    from_id: str,
    topics: list,
    depth: int,
    to_id: str | None,
    yaml_style: bool = True,
    field_set: frozenset | None = None,
) -> None:
    topic_map = {t["id"]: t for t in topics}

    if from_id not in topic_map:
        print(f"ERROR: Topic not found: {from_id}", file=sys.stderr)
        sys.exit(1)

    output_data = None
    if to_id:
        path = _find_path(from_id, to_id, topic_map)
        if path:
            path_topics = _project_fields(
                [topic_map[tid] for tid in path if tid in topic_map], field_set
            )
            output_data = path_topics
        else:
            print(f"ERROR: No path from {from_id} to {to_id}", file=sys.stderr)
            sys.exit(1)
    else:
        reachable = _get_reachable(from_id, topic_map, topics, depth)
        reachable_topics = [topic_map[tid] for tid in reachable if tid in topic_map]
        output_data = _project_fields(reachable_topics, field_set)

    print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


def _show_path_to(
    to_id: str,
    topics: list,
    yaml_style: bool = True,
    field_set: frozenset | None = None,
) -> None:
    topic_map = {t["id"]: t for t in topics}

    if to_id not in topic_map:
        print(f"ERROR: Topic not found: {to_id}", file=sys.stderr)
        sys.exit(1)

    path = _find_path_to_root(to_id, topic_map)
    if path:
        path_topics = _project_fields(
            [topic_map[tid] for tid in path if tid in topic_map], field_set
        )
        output_data = path_topics
    else:
        print(f"ERROR: No path to root for: {to_id}", file=sys.stderr)
        sys.exit(1)

    print(yaml.dump(output_data, default_flow_style=yaml_style, sort_keys=False))


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
    start_id: str, topic_map: dict, topics: list, max_depth: int
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


def _find_path(from_id: str, to_id: str, topic_map: dict) -> list[str] | None:
    conn_map = _build_connection_map(list(topic_map.values()))
    queue = deque([(from_id, [from_id])])
    visited = {from_id}

    while queue:
        current, path = queue.popleft()
        if current == to_id:
            return path

        for neighbor, conn_type in conn_map.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None
