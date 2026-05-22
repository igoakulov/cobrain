from typing import Any

from cobrain.parsers.x.auth import OAuth2TokenManager
from cobrain.parsers.x.helpers import (
    DEFAULT_PAGE_SIZE,
    POST_TYPE_BOOKMARKED,
    POST_TYPE_IDS,
    POST_TYPE_LIKED,
    POST_TYPE_OWN,
    X_TWEET_FIELDS,
    X_USER_FIELDS,
    calculate_page_size,
    get_base_params,
)
from cobrain.parsers.x.models import XPost
from cobrain.parsers.x.parse import _parse_post_data

POST_TYPE_APIS = {
    POST_TYPE_OWN: lambda client, user_id, params: client.users.get_posts(
        user_id, **params,
    ),
    POST_TYPE_LIKED: lambda client, user_id, params: client.users.get_liked_posts(
        user_id, **params,
    ),
    POST_TYPE_BOOKMARKED: lambda client, user_id, params: client.users.get_bookmarks(
        user_id, **params,
    ),
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

    def get_posts_by_ids(
        self, post_ids: list[str], post_type: str = POST_TYPE_IDS,
    ) -> list[XPost]:
        if not post_ids:
            return []

        all_posts = []
        for i in range(0, len(post_ids), 100):
            chunk = post_ids[i : i + 100]
            all_posts.extend(self._fetch_posts_by_ids_chunk(chunk, post_type))
        return all_posts

    def _fetch_posts_by_ids_chunk(
        self, post_ids: list[str], post_type: str,
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
                post = _parse_post_data(tweet, includes, post_type=post_type)
                if post:
                    posts.append(post)
            return posts
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"X API error fetching posts: {e}")

    def get_posts(
        self,
        post_type: str,
        since_id: str | None = None,
        until_id: str | None = None,
        count: int | None = None,
        existing_ids: set[str] | None = None,
        is_new: bool = False,
    ) -> list[XPost]:
        user_id = self._get_user_id()
        client = self._get_client()
        fetch_fn = POST_TYPE_APIS.get(post_type, lambda c, uid, p: [])

        existing_ids = existing_ids or set()

        if count is not None:
            page_size = calculate_page_size(count)
        elif since_id or until_id:
            page_size = 100
        else:
            page_size = DEFAULT_PAGE_SIZE

        should_paginate = since_id or until_id or count is not None or is_new

        params = get_base_params(page_size)
        if since_id is not None:
            params["since_id"] = since_id
        if until_id is not None:
            params["until_id"] = until_id

        all_posts: list[XPost] = []
        try:
            response_gen = fetch_fn(client, user_id, params)

            for response in response_gen:
                if response.data:
                    includes = getattr(response, "includes", {}) or {}
                    for tweet in response.data:
                        post = _parse_post_data(tweet, includes, post_type=post_type)

                        if is_new and post.id in existing_ids:
                            return all_posts

                        all_posts.append(post)

                        if count and len(all_posts) >= count:
                            return all_posts

                meta = getattr(response, "meta", None)
                next_token = meta.next_token if meta else None

                if not should_paginate or not next_token:
                    break
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"X API error fetching posts: {e}")

        return all_posts


_cached_client: XClient | None = None
_cached_auth_code: str | None = None


def get_x_client(authorization_code: str | None = None) -> XClient:
    global _cached_client, _cached_auth_code
    if _cached_client is None or authorization_code != _cached_auth_code:
        _cached_client = XClient(authorization_code)
        _cached_auth_code = authorization_code
    return _cached_client
