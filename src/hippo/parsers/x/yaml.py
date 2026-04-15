from hippo.parsers.x.models import XTree


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
