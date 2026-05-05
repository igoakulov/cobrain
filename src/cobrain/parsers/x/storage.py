from pathlib import Path

from cobrain.directories import (
    get_x_trees_dir as _get_x_trees_dir,
)
from cobrain.parsers.x.models import XTree, XTreeNode
from cobrain.yaml_utils import read_yaml, write_yaml


def get_x_trees_dir() -> Path:
    return _get_x_trees_dir()


def load_all_cached_trees() -> list[XTree]:
    trees_dir = get_x_trees_dir()
    if not trees_dir.exists():
        return []

    cached_trees: list[XTree] = []
    for tree_file in trees_dir.rglob("*.yaml"):
        data = read_yaml(tree_file)
        if not data:
            continue

        root_node = XTreeNode.from_dict(data)
        cached_trees.append(
            XTree(
                id=root_node.id,
                root=root_node,
                created_at=data.get("created_at", ""),
                updated_at=data.get("conversation_updated_at", ""),
                conversation_xurl=data.get("conversation_xurl", ""),
            )
        )

    return cached_trees


def get_existing_post_ids() -> set[str]:
    trees_dir = get_x_trees_dir()
    if not trees_dir.exists():
        return set()

    post_ids: set[str] = set()
    for tree_file in trees_dir.rglob("*.yaml"):
        data = read_yaml(tree_file)
        if not data:
            continue

        def collect_ids(data: dict) -> set:
            ids = set()
            if "xurl" in data:
                parts = data["xurl"].split("/status/")
                if len(parts) == 2:
                    ids.add(parts[1])
            if "children" in data:
                for child in data["children"]:
                    ids.update(collect_ids(child))
            return ids

        post_ids.update(collect_ids(data))

    return post_ids


def get_output_filename(tree: XTree) -> str:
    if tree.conversation_xurl:
        parts = tree.conversation_xurl.split("/")
        if len(parts) >= 2 and parts[-1]:
            author = parts[0]
            post_id = parts[-1]
            return f"{author}_{post_id}.yaml"
    raise ValueError(f"conversation_xurl is not set for tree {tree.root.id}")


def tree_to_yaml(tree: XTree) -> dict:
    truncated_updated = tree.updated_at[:20] if tree.updated_at else ""
    result = {}
    if tree.conversation_xurl:
        result["conversation_xurl"] = tree.conversation_xurl
    result["conversation_updated_at"] = truncated_updated
    root_dict = tree.root.to_dict()
    for key, value in root_dict.items():
        result[key] = value
    return result


def find_tree_file_by_id(post_id: str) -> Path | None:
    trees_dir = get_x_trees_dir()
    if not trees_dir.exists():
        return None

    for tree_file in trees_dir.rglob("*.yaml"):
        data = read_yaml(tree_file)
        if not data:
            continue
        root_id = data.get("id")
        if root_id == post_id:
            return tree_file
        xurl = data.get("xurl", "")
        if xurl:
            parts = xurl.split("/status/")
            if len(parts) == 2 and parts[1] == post_id:
                return tree_file
    return None


def save_tree(tree: XTree, existing_path: Path | None = None) -> Path:
    trees_dir = get_x_trees_dir()
    trees_dir.mkdir(parents=True, exist_ok=True)
    if existing_path:
        tree_path = existing_path
    else:
        filename = get_output_filename(tree)
        tree_path = trees_dir / filename
    write_yaml(tree_path, tree_to_yaml(tree))
    return tree_path
