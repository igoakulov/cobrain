from hippo.parsers.x.helpers import (
    SEMANTIC_TYPE_POST,
    SEMANTIC_TYPE_REPLY,
    SEMANTIC_TYPE_QUOTE,
    SEMANTIC_TYPE_REPOST,
)
from hippo.parsers.x.models import XPost
from hippo.parsers.x.transform import (
    normalize_whitespace,
    format_article_as_text,
)


def _parse_post_data(data: dict, includes: dict, post_type: str) -> XPost:
    author_id = data.get("author_id", "")
    author_username = "unknown"

    users = includes.get("users", [])
    for u in users:
        if str(u.get("id")) == str(author_id):
            author_username = u.get("username", "unknown")
            break

    created_at = data.get("created_at", "")
    conversation_id = data.get("conversation_id", data.get("id", ""))

    in_reply_to_user_id = data.get("in_reply_to_user_id")
    in_reply_to_post_id = None
    quoted_post_id = None
    referenced_tweets = []
    has_retweet = False

    referenced = data.get("referenced_tweets", [])
    for ref in referenced:
        ref_type = ref.get("type")
        if ref_type == "replied_to":
            in_reply_to_post_id = str(ref.get("id"))
            referenced_tweets.append({"type": "replied_to", "id": in_reply_to_post_id})
        elif ref_type == "quoted":
            quoted_post_id = str(ref.get("id"))
            referenced_tweets.append({"type": "quoted", "id": quoted_post_id})
        elif ref_type == "retweeted":
            has_retweet = True
        referenced_tweets.append({"type": ref_type, "id": str(ref.get("id"))})

    if has_retweet:
        semantic_type = SEMANTIC_TYPE_REPOST
    elif quoted_post_id:
        semantic_type = SEMANTIC_TYPE_QUOTE
    elif in_reply_to_post_id:
        semantic_type = SEMANTIC_TYPE_REPLY
    else:
        semantic_type = SEMANTIC_TYPE_POST

    if "note_tweet" in data:
        text = data.get("note_tweet", {}).get("text", data.get("text", ""))
    elif "article" in data:
        text = format_article_as_text(data, includes)
        return XPost(
            id=str(data.get("id", "")),
            text=text,
            author_id=author_id,
            author_username=author_username,
            created_at=created_at,
            conversation_id=conversation_id,
            in_reply_to_user_id=in_reply_to_user_id,
            in_reply_to_post_id=in_reply_to_post_id,
            referenced_tweets=referenced_tweets,
            quoted_post_id=quoted_post_id,
            post_type=post_type,
            semantic_type=semantic_type,
        )
    else:
        text = data.get("text", "")

    attachments = data.get("attachments", {})
    poll_ids = attachments.get("poll_ids", [])
    poll_indicator = None
    if poll_ids:
        polls = includes.get("polls", [])
        for poll in polls:
            total_votes = sum(opt.get("votes", 0) for opt in poll.get("options", []))
            options_str = ", ".join(
                f"{int((opt.get('votes', 0) / total_votes * 100) if total_votes > 0 else 0)}% {opt.get('label', '')}"
                for opt in poll.get("options", [])
            )
            poll_indicator = f"[POLL: {total_votes} votes, {options_str}]"

    media_keys = attachments.get("media_keys", [])
    media_indicators = []
    if media_keys:
        for key in media_keys:
            if key.startswith("3_"):
                media_indicators.append("[IMAGE]")
            elif key.startswith("13_"):
                media_indicators.append("[VIDEO]")
            elif key.startswith("16_"):
                media_indicators.append("[GIF]")

    entities = data.get("entities")

    quoted_post_url_to_skip = None
    if quoted_post_id and entities and entities.get("urls"):
        for url_obj in entities["urls"]:
            expanded_url = url_obj.get("expanded_url", "")
            if quoted_post_id in expanded_url:
                quoted_post_url_to_skip = url_obj.get("url", "")
                break

    text = normalize_whitespace(
        text,
        entities,
        poll_indicator,
        media_indicators,
        quoted_post_url_to_skip,
    )

    return XPost(
        id=str(data.get("id", "")),
        text=text,
        author_id=author_id,
        author_username=author_username,
        created_at=created_at,
        conversation_id=conversation_id,
        in_reply_to_user_id=in_reply_to_user_id,
        in_reply_to_post_id=in_reply_to_post_id,
        referenced_tweets=referenced_tweets,
        quoted_post_id=quoted_post_id,
        post_type=post_type,
        semantic_type=semantic_type,
    )
