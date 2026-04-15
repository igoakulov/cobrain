import datetime

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


def _find_tree_containing(
    trees: dict[str, XTree], post_id: str
) -> tuple[XTree, XTreeNode] | None:
    for tree in trees.values():
        node = _find_node_by_id(tree.root, post_id)
        if node:
            return (tree, node)
    return None


def _post_to_node(post: XPost) -> XTreeNode:
    return XTreeNode(
        id=post.id,
        author=post.author_username,
        created_at=post.created_at,
        text=post.text,
        post_type=post.post_type,
        children=[],
        quoted_post_id=post.quoted_post_id,
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


def merge_posts(
    posts_chain: list[XPost],
    parent_tree: XTree,
    parent_node: XTreeNode,
) -> None:
    posts_chain = list(reversed(posts_chain))
    branch_root = _post_to_node(posts_chain[0])
    current = branch_root
    for post in posts_chain[1:]:
        node = _post_to_node(post)
        current.children.append(node)
        current = node
    parent_node.children.append(branch_root)
    truncated_updated = datetime.datetime.utcnow().strftime("%Y-%m-%dT%M:%SZ")
    parent_tree.updated_at = truncated_updated


def _attach_chain_to_tree(posts_chain: list[XPost], tree: XTree) -> None:
    """Attach fetched ancestors to tree root when no merge happened.

    posts_chain is [target, parent1, parent2, ...] where target is tree.root.
    In X, oldest post is root of conversation - target is descendant.
    So we need to rebuild the tree with oldest as root.
    """
    if len(posts_chain) <= 1:
        return

    posts_chain = list(reversed(posts_chain))
    oldest = _post_to_node(posts_chain[0])
    tree.root = oldest
    tree.id = oldest.id

    current = oldest
    for post in posts_chain[1:]:
        node = _post_to_node(post)
        current.children.append(node)
        current = node


def expand_and_merge_tree(
    tree: XTree,
    cached_trees: dict[str, XTree],
    new_trees: dict[str, XTree],
    updated_trees: set[str] | None = None,
) -> list[str]:
    """Walk parent chain and merge into existing trees.

    Returns list of related_ids (ancestor posts fetched from API).
    """
    from hippo.parsers.x.client import get_x_client

    client = get_x_client()

    root = tree.root
    post_id = root.id

    found = _find_tree_containing(cached_trees, post_id)
    if found:
        return []

    return _expand_tree(tree, cached_trees, new_trees, client, updated_trees)


def _expand_tree(
    tree: XTree,
    cached_trees: dict[str, XTree],
    new_trees: dict[str, XTree],
    client,
    updated_trees: set[str] | None = None,
) -> list[str]:
    """Walk parent chain of a tree and merge with existing trees."""
    root = tree.root
    post_id = root.id

    posts_chain: list[XPost] = []
    related_ids: list[str] = []

    initial_post = client.get_post_by_id(post_id, root.post_type)
    if not initial_post:
        return []
    posts_chain.append(initial_post)

    while True:
        parent_id = (
            posts_chain[-1].in_reply_to_post_id or posts_chain[-1].quoted_post_id
        )
        if not parent_id:
            break

        found = _find_tree_containing(cached_trees, parent_id)
        if found:
            parent_tree, parent_node = found
            merge_posts(posts_chain, parent_tree, parent_node)
            if updated_trees is not None:
                updated_trees.add(parent_tree.root.id)
            parent_root_id = parent_tree.root.id
            _continue_walking_from(root.id, parent_root_id, cached_trees, new_trees)
            return related_ids

        found = _find_tree_containing(new_trees, parent_id)
        if found:
            parent_tree, parent_node = found
            merge_posts(posts_chain, parent_tree, parent_node)
            if updated_trees is not None:
                updated_trees.add(parent_tree.root.id)
            parent_root_id = parent_tree.root.id
            _continue_walking_from(root.id, parent_root_id, cached_trees, new_trees)
            return related_ids

        parent = client.get_post_by_id(parent_id, "related")
        if not parent:
            break
        related_ids.append(parent_id)
        posts_chain.append(parent)

    if len(posts_chain) > 1:
        _attach_chain_to_tree(posts_chain, tree)

    return related_ids


def _continue_walking_from(
    merged_root_id: str,
    merged_into_id: str,
    cached_trees: dict[str, XTree],
    new_trees: dict[str, XTree],
) -> None:
    """Mark source tree as consumed after merge.

    After tree A merges into tree B, tree A's root is marked as consumed
    so it won't be saved as a separate file. The merged-into tree B
    will be saved via the normal loop.
    """
    if merged_root_id in new_trees:
        del new_trees[merged_root_id]
