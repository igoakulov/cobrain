from cobrain.parsers.x.models import (
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
    trees: dict[str, XTree],
    post_id: str,
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
