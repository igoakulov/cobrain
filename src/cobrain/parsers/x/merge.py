from cobrain.parsers.x.models import (
    XTree,
    XTreeNode,
)
from cobrain.parsers.x.tree import (
    _find_tree_containing,
    _iter_all_nodes,
    _find_node_by_id,
    _post_to_node,
)


def expand_and_merge_trees(
    new_trees: dict[str, XTree],
    cached_trees: dict[str, XTree],
    updated_tree_ids: set[str] | None = None,
) -> list[str]:
    from cobrain.parsers.x.client import get_x_client

    client = get_x_client()
    related_ids: list[str] = []
    target_tree_ids = set(new_trees.keys())
    incomplete_trees = dict(new_trees)

    while incomplete_trees:
        collected_parents: dict[str, list[XTree]] = {}

        for tree in incomplete_trees.values():
            parent_id = tree.root.in_reply_to_post_id or tree.root.quoted_post_id
            if not parent_id:
                continue

            if parent_id not in collected_parents:
                collected_parents[parent_id] = []
            collected_parents[parent_id].append(tree)

        if not collected_parents:
            break

        for parent_id in list(collected_parents.keys()):
            found = _find_tree_containing(new_trees, parent_id)
            if found:
                parent_tree, parent_node = found
                _attach_parent_to_children(collected_parents[parent_id], parent_node)
                for child_tree in collected_parents[parent_id]:
                    if child_tree.id in new_trees:
                        del new_trees[child_tree.id]
                del collected_parents[parent_id]
                continue

            found = _find_tree_containing(cached_trees, parent_id)
            if found:
                parent_tree, parent_node = found
                _attach_parent_to_children(collected_parents[parent_id], parent_node)
                if updated_tree_ids is not None:
                    updated_tree_ids.add(parent_tree.root.id)
                for child_tree in collected_parents[parent_id]:
                    if child_tree.id in new_trees:
                        del new_trees[child_tree.id]
                del collected_parents[parent_id]
                continue

        if collected_parents:
            parent_ids_to_fetch = list(collected_parents.keys())
            fetched = client.get_posts_by_ids(parent_ids_to_fetch)
            fetched_map = {p.id: p for p in fetched if p}

            for parent_id, children in collected_parents.items():
                parent_post = fetched_map.get(parent_id)
                if parent_post:
                    related_ids.append(parent_id)
                    parent_node = _post_to_node(parent_post, "related")
                    _attach_parent_to_children(children, parent_node)

                    for child_tree in children:
                        if child_tree.id in new_trees:
                            del new_trees[child_tree.id]

                    new_tree = XTree(
                        id=parent_node.id,
                        root=parent_node,
                        created_at=parent_node.created_at[:19] + "Z"
                        if parent_node.created_at
                        else "",
                        updated_at=parent_node.created_at[:19] + "Z"
                        if parent_node.created_at
                        else "",
                        conversation_xurl=f"{parent_node.author}/status/{parent_node.id}",
                    )
                    new_trees[parent_node.id] = new_tree
                else:
                    for child_tree in children:
                        if child_tree.id in target_tree_ids:
                            child_tree.root.in_reply_to_post_id = None
                            child_tree.root.quoted_post_id = None
                        else:
                            child_tree.root.in_reply_to_post_id = None
                            child_tree.root.quoted_post_id = None

        _merge_by_overlap(new_trees, new_trees, updated_tree_ids)
        _merge_by_overlap(new_trees, cached_trees, updated_tree_ids)

        import cobrain.parsers.x.tree as tree_module

        tree_module._post_id_index = None

        incomplete_trees = {
            tid: tree
            for tid, tree in new_trees.items()
            if tree.root.in_reply_to_post_id or tree.root.quoted_post_id
        }

    return related_ids


_post_id_index: dict[str, tuple[XTree, XTreeNode]] | None = None


def _attach_parent_to_children(children: list[XTree], parent_node: XTreeNode) -> None:
    for child_tree in children:
        parent_node.children.append(child_tree.root)


def _merge_by_overlap(
    new_trees: dict[str, XTree],
    cached_trees: dict[str, XTree],
    updated_tree_ids: set[str] | None = None,
) -> None:
    for tree in list(new_trees.values()):
        for node in _iter_all_nodes(tree.root):
            if node.id in cached_trees:
                cached_tree = cached_trees[node.id]
                if tree.root.id != cached_tree.root.id:
                    overlap_node = _find_node_by_id(cached_tree.root, node.id)
                    if overlap_node:
                        overlap_node.children.append(tree.root)
                    if updated_tree_ids is not None:
                        updated_tree_ids.add(cached_tree.root.id)
                    if tree in list(new_trees.values()):
                        del new_trees[tree.root.id]
                break
