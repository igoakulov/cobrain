from typing import Any

DEFAULT_PAGE_SIZE = 10

X_TWEET_FIELDS = [
    "text",
    "author_id",
    "created_at",
    "attachments",
    "referenced_tweets",
    "note_tweet",
    "article",
    "entities",
    "conversation_id",
]
X_USER_FIELDS = ["username"]

POST_TYPE_IDS = "ids"
POST_TYPE_OWN = "own"
POST_TYPE_LIKED = "liked"
POST_TYPE_BOOKMARKED = "bookmarked"
POST_TYPE_RELATED = "related"

SEMANTIC_TYPE_POST = "post"
SEMANTIC_TYPE_REPLY = "reply"
SEMANTIC_TYPE_QUOTE = "quote"
SEMANTIC_TYPE_REPOST = "repost"


def calculate_page_size(count: int) -> int:
    if count <= 0:
        return DEFAULT_PAGE_SIZE

    best_p = DEFAULT_PAGE_SIZE
    best_ratio = float("inf")

    for p in range(DEFAULT_PAGE_SIZE, 101):
        pages = (count + p - 1) // p
        remainder = pages * p - count
        if remainder < 1:
            remainder = 0.99
        ratio = remainder / p

        if ratio < best_ratio:
            best_ratio = ratio
            best_p = p

    return best_p


def get_base_params(page_size: int) -> dict[str, Any]:
    return {
        "max_results": page_size,
        "tweet_fields": X_TWEET_FIELDS,
        "user_fields": X_USER_FIELDS,
        "expansions": ["author_id", "attachments.poll_ids", "attachments.media_keys"],
    }
