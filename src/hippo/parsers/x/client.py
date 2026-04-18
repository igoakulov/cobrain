from typing import Any

from hippo.parsers.x.auth import OAuth2TokenManager
from hippo.parsers.x.models import XPost
from hippo.parsers.x.storage import load_post_from_existing
from hippo.parsers.x.transform import (
    normalize_whitespace,
    format_article_as_text,
)

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


class XClient:
    def __init__(self, authorization_code: str | None = None):
        self._token_manager = OAuth2TokenManager(authorization_code=authorization_code)
        self._client: Any = None
        self._user_id: str = ""

    def _ensure_token(self) -> str:
        return self._token_manager.get_token()

    def _get_client(self) -> Any:
        if self._client is None:
            from xdk import Client

            access_token = self._ensure_token()
            self._client = Client(access_token=access_token)

        return self._client

    def _get_user_id(self) -> str:
        if not self._user_id:
            user = self._get_client().users.get_me()
            if user.data:
                self._user_id = str(user.data.get("id", ""))
        return self._user_id

    def get_post_by_id(
        self,
        post_id: str,
        post_type: str = POST_TYPE_IDS,
    ) -> XPost | None:
        existing = load_post_from_existing(post_id)
        if existing:
            from hippo.parsers.x.models import _post_from_existing

            return _post_from_existing(existing)

        try:
            response = self._get_client().posts.get_by_id(
                post_id,
                expansions=[
                    "author_id",
                    "attachments.poll_ids",
                    "attachments.media_keys",
                ],
                tweet_fields=X_TWEET_FIELDS,
                user_fields=X_USER_FIELDS,
            )
            if response.data:
                includes = getattr(response, "includes", {}) or {}
                return self._parse_post_data(
                    response.data, includes, post_type=post_type
                )
            return None
        except Exception:
            return None

    def get_posts_by_ids(
        self, post_ids: list[str], post_type: str = POST_TYPE_IDS
    ) -> list[XPost]:
        if not post_ids:
            return []

        all_posts = []
        for i in range(0, len(post_ids), 100):
            chunk = post_ids[i : i + 100]
            chunk_posts = self._fetch_posts_by_ids_chunk(chunk, post_type)
            all_posts.extend(chunk_posts)
        return all_posts

    def _fetch_posts_by_ids_chunk(
        self, post_ids: list[str], post_type: str
    ) -> list[XPost]:
        try:
            response = self._get_client().posts.get_by_ids(
                post_ids,
                tweet_fields=X_TWEET_FIELDS,
                user_fields=X_USER_FIELDS,
                expansions=[
                    "author_id",
                    "attachments.poll_ids",
                    "attachments.media_keys",
                ],
            )
            if not response.data:
                return []

            includes = getattr(response, "includes", {}) or {}
            posts = []
            for tweet in response.data:
                post = self._parse_post_data(tweet, includes, post_type=post_type)
                if post:
                    posts.append(post)
            return posts
        except Exception:
            return []

    def get_own_posts(
        self,
        since_id: str | None = None,
        until_id: str | None = None,
        count: int | None = None,
        existing_ids: set[str] | None = None,
        is_new: bool = False,
    ) -> list[XPost]:
        user_id = self._get_user_id()
        return self._fetch_posts(
            lambda params: self._get_client().users.get_posts(user_id, **params),
            POST_TYPE_OWN,
            existing_ids,
            since_id=since_id,
            until_id=until_id,
            count=count,
            _new=is_new,
        )

    def get_liked_posts(
        self,
        count: int | None = None,
        existing_ids: set[str] | None = None,
        is_new: bool = False,
    ) -> list[XPost]:
        return self._get_posts_by_type(POST_TYPE_LIKED, count, existing_ids, is_new)

    def get_bookmarked_posts(
        self,
        count: int | None = None,
        existing_ids: set[str] | None = None,
        is_new: bool = False,
    ) -> list[XPost]:
        return self._get_posts_by_type(
            POST_TYPE_BOOKMARKED, count, existing_ids, is_new
        )

    def _get_posts_by_type(
        self,
        post_type: str,
        count: int | None,
        existing_ids: set[str] | None,
        is_new: bool,
    ) -> list[XPost]:
        user_id = self._get_user_id()
        client = self._get_client()

        def get_liked(params):
            return client.users.get_liked_posts(user_id, **params)

        def get_bookmarked(params):
            return client.users.get_bookmarks(user_id, **params)

        def get_empty(params):
            return []

        if post_type == POST_TYPE_LIKED:
            fetch_fn = get_liked
        elif post_type == POST_TYPE_BOOKMARKED:
            fetch_fn = get_bookmarked
        else:
            fetch_fn = get_empty
        return self._fetch_posts(
            fetch_fn, post_type, existing_ids, count=count, _new=is_new
        )

    def _fetch_posts(
        self,
        fetch_fn,
        post_type: str,
        existing_ids: set[str] | None,
        **extra_params,
    ) -> list[XPost]:
        existing_ids = existing_ids or set()
        since_id = extra_params.get("since_id")
        until_id = extra_params.get("until_id")
        count = extra_params.get("count")
        is_new = extra_params.get("_new")

        if count is not None:
            page_size = calculate_page_size(count)
        elif since_id or until_id:
            page_size = 100
        else:
            page_size = DEFAULT_PAGE_SIZE

        should_paginate = since_id or until_id or count is not None

        params = get_base_params(page_size)
        for key, value in extra_params.items():
            if value is not None and key not in ("_new", "count"):
                params[key] = value

        all_posts: list[XPost] = []
        response_gen = fetch_fn(params)

        for response in response_gen:
            if response.data:
                includes = getattr(response, "includes", {}) or {}
                for tweet in response.data:
                    post = self._parse_post_data(tweet, includes, post_type=post_type)

                    if is_new and post.id in existing_ids:
                        return all_posts

                    all_posts.append(post)

                    if count and len(all_posts) >= count:
                        return all_posts

            meta = getattr(response, "meta", None)
            next_token = meta.next_token if meta else None

            if not should_paginate or not next_token:
                break

        return all_posts

    def _parse_post_data(self, data: dict, includes: dict, post_type: str) -> XPost:
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
                referenced_tweets.append(
                    {"type": "replied_to", "id": in_reply_to_post_id}
                )
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
                total_votes = sum(
                    opt.get("votes", 0) for opt in poll.get("options", [])
                )
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


_cached_client: XClient | None = None
_cached_auth_code: str | None = None


def get_x_client(authorization_code: str | None = None) -> XClient:
    global _cached_client, _cached_auth_code
    if _cached_client is None or authorization_code != _cached_auth_code:
        _cached_client = XClient(authorization_code)
        _cached_auth_code = authorization_code
    return _cached_client
