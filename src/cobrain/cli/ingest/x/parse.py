import re


def _parse_post_args(posts_arg: str | None) -> list[str]:
    if not posts_arg:
        return []

    post_ids = []
    for item in posts_arg.split(","):
        item = item.strip()
        if not item:
            continue

        post_id = _extract_post_id(item)
        if post_id:
            post_ids.append(post_id)

    return post_ids


def _extract_post_id(post_arg: str) -> str | None:
    post_arg = post_arg.strip()

    if post_arg.isdigit():
        return post_arg

    url_pattern = r"https?://x\.com/\w+/status/(\d+)"
    match = re.search(url_pattern, post_arg)
    if match:
        return match.group(1)

    xurl_pattern = r"^(\w+)/status/(\d+)$"
    match = re.match(xurl_pattern, post_arg)
    if match:
        return match.group(2)

    return None
