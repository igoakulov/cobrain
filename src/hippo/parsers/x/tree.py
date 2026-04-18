from hippo.parsers.x.models import (
    XPost,
    XTree,
    XTreeNode,
)


def _build_x_tree(root: XTreeNode, conversation_xurl: str = "") -> XTree:
    created_at = root.created_at
    truncated_created = created_at[:19] + "Z" if created_at else ""
    updated_at = truncated_created

    return XTree(
        id=root.id,
        root=root,
        created_at=truncated_created,
        updated_at=updated_at,
        conversation_xurl=conversation_xurl,
    )


def _iter_all_nodes(node: XTreeNode):
    yield node
    for child in node.children:
        yield from _iter_all_nodes(child)


def sort_tree_by_time(root: XTreeNode, new_node_ids: set[str] | None = None) -> None:
    nodes_to_sort: set[str] = set()

    if new_node_ids:
        for node in _iter_all_nodes(root):
            if node.id in new_node_ids:
                nodes_to_sort.add(node.id)
                parent = _find_parent(root, node.id)
                if parent:
                    nodes_to_sort.add(parent.id)
    else:
        nodes_to_sort.add(root.id)

    for node in _iter_all_nodes(root):
        if node.id not in nodes_to_sort:
            continue
        replies = sorted(
            [c for c in node.children if c.quoted_post_id is None],
            key=lambda x: x.created_at,
            reverse=True,
        )
        quotes = sorted(
            [c for c in node.children if c.quoted_post_id is not None],
            key=lambda x: x.created_at,
            reverse=True,
        )
        node.children = replies + quotes


def _find_parent(root: XTreeNode, child_id: str) -> XTreeNode | None:
    for child in root.children:
        if child.id == child_id:
            return root
        parent = _find_parent(child, child_id)
        if parent:
            return parent
    return None


def _find_node_by_id(root: XTreeNode, target_id: str) -> XTreeNode | None:
    if root.id == target_id:
        return root
    for child in root.children:
        found = _find_node_by_id(child, target_id)
        if found:
            return found
    return None


_post_id_index: dict[str, tuple[XTree, XTreeNode]] | None = None
_index_trees: dict[str, XTree] | None = None


def _build_post_id_index(trees: dict[str, XTree]) -> dict[str, tuple[XTree, XTreeNode]]:
    index: dict[str, tuple[XTree, XTreeNode]] = {}
    for tree in trees.values():
        for node in _iter_all_nodes(tree.root):
            index[node.id] = (tree, node)
    return index


def _find_tree_containing(
    trees: dict[str, XTree], post_id: str
) -> tuple[XTree, XTreeNode] | None:
    global _post_id_index, _index_trees

    if trees is not _index_trees or _post_id_index is None:
        _index_trees = trees
        _post_id_index = _build_post_id_index(trees)

    return _post_id_index.get(post_id)


def _post_to_node(post: XPost, post_type: str | None = None) -> XTreeNode:
    return XTreeNode(
        id=post.id,
        author=post.author_username,
        created_at=post.created_at,
        text=post.text,
        post_type=post_type or post.post_type,
        children=[],
        quoted_post_id=post.quoted_post_id,
        in_reply_to_post_id=post.in_reply_to_post_id,
        semantic_type=getattr(post, "semantic_type", "post"),
        conversation_id=post.conversation_id,
    )


def arrange_into_tree(posts_chain: list[XPost]) -> XTree:
    posts_chain = list(reversed(posts_chain))
    oldest = _post_to_node(posts_chain[0])
    current = oldest
    for post in posts_chain[1:]:
        node = _post_to_node(post)
        current.children.append(node)
        current = node
    return _build_x_tree(oldest, "")


def batch_expand_and_merge_trees(
    new_trees: dict[str, XTree],
    cached_trees: dict[str, XTree],
    updated_tree_ids: set[str] | None = None,
) -> list[str]:
    """Batch expand all trees with parent traversal.

    Pass-based algorithm:
    1. Collect parent_ids from current trees
    2. Thin: check new_trees → attach if found
    3. Thin: check cached_trees → attach if found
    4. Batch fetch remaining from API
    5. Create trees for fetched parents, attach children
    6. Two-stage merge: new_trees→new_trees, then →cached_trees

    Returns all related_ids collected.
    """
    from hippo.parsers.x.client import get_x_client

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

        global _post_id_index
        _post_id_index = None

        incomplete_trees = {
            tid: tree
            for tid, tree in new_trees.items()
            if tree.root.in_reply_to_post_id or tree.root.quoted_post_id
        }

    return related_ids


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
