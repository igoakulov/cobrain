from dataclasses import dataclass, field

from cobrain.parsers.x.helpers import POST_TYPE_RELATED


@dataclass
class XPost:
    id: str
    text: str
    author_id: str
    author_username: str
    created_at: str
    conversation_id: str
    in_reply_to_user_id: str | None
    in_reply_to_post_id: str | None
    referenced_tweets: list[dict] = field(default_factory=list)
    quoted_post_id: str | None = None
    post_type: str = POST_TYPE_RELATED
    children: list["XPost"] = field(default_factory=list)
    semantic_type: str = "post"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author_username,
            "created_at": self.created_at,
            "conversation_id": self.conversation_id,
            "in_reply_to_post_id": self.in_reply_to_post_id,
            "quoted_post_id": self.quoted_post_id,
            "post_type": self.post_type,
        }


def _post_from_existing(data: dict) -> XPost:
    xurl = data.get("xurl", "")
    post_id = xurl.rsplit("/status/", 1)[1] if "/status/" in xurl else ""
    return XPost(
        id=post_id,
        text=data.get("text", ""),
        author_id="",
        author_username=xurl.rsplit("/status/", 1)[0].split("/")[0]
        if "/status/" in xurl
        else "",
        created_at=data.get("created_at", ""),
        conversation_id=post_id,
        in_reply_to_user_id=None,
        in_reply_to_post_id=data.get("in_reply_to_post_id"),
        referenced_tweets=[],
        quoted_post_id=data.get("quoted_post_id"),
        post_type=data.get("type", POST_TYPE_RELATED),
        semantic_type=data.get("semantic_type", "post"),
    )


@dataclass
class XTree:
    id: str
    root: "XTreeNode"
    created_at: str
    updated_at: str
    conversation_xurl: str = ""


@dataclass
class XTreeNode:
    id: str
    author: str
    created_at: str
    text: str
    post_type: str = POST_TYPE_RELATED
    children: list["XTreeNode"] = field(default_factory=list)
    quoted_post_id: str | None = None
    in_reply_to_post_id: str | None = None
    semantic_type: str = "post"
    conversation_id: str = ""

    def to_dict(self) -> dict:
        xurl = f"{self.author}/status/{self.id}"
        truncated_created = self.created_at[:19] + "Z" if self.created_at else ""
        combined_type = f"{self.post_type}-{self.semantic_type}"
        return {
            "xurl": xurl,
            "created_at": truncated_created,
            "type": combined_type,
            "text": self.text,
            "children": [c.to_dict() for c in self.children],
        }

    @staticmethod
    def from_dict(data: dict) -> "XTreeNode":
        xurl = data.get("xurl", "")
        parts = xurl.split("/status/")
        author = parts[0] if len(parts) > 1 else "unknown"
        post_id = parts[1] if len(parts) > 1 else ""
        type_value = data.get("type", POST_TYPE_RELATED)
        parts_type = type_value.split("-", 1)
        post_type = parts_type[0] if len(parts_type) > 0 else POST_TYPE_RELATED
        semantic_type = parts_type[1] if len(parts_type) > 1 else "post"
        return XTreeNode(
            id=post_id,
            author=author,
            created_at=data.get("created_at", ""),
            text=data.get("text", ""),
            post_type=post_type,
            children=[XTreeNode.from_dict(c) for c in data.get("children", [])],
            quoted_post_id=None,
            semantic_type=semantic_type,
        )
