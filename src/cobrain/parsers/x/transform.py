import re


def format_article_as_text(data: dict, includes: dict) -> str:
    article = data.get("article", {})
    if not article:
        return data.get("text", "")

    title = article.get("title", "")
    plain_text = article.get("plain_text", "")
    entities = article.get("entities", {})
    code_blocks = entities.get("code", [])

    parts = []

    if title:
        parts.append(title)

    if plain_text:
        parts.append(plain_text)

    for code in code_blocks:
        content = code.get("content", "")
        if content:
            parts.append(content)

    return "\n".join(parts)


def normalize_whitespace(
    text: str,
    entities: dict | None = None,
    poll_indicator: str | None = None,
    media_indicators: list[str] | None = None,
    quoted_post_url_to_skip: str | None = None,
) -> str:
    if entities and entities.get("urls"):
        for url_obj in entities["urls"]:
            tco_url = url_obj.get("url", "")
            expanded_url = url_obj.get("expanded_url", "")
            if not tco_url or not expanded_url:
                continue
            if tco_url == quoted_post_url_to_skip:
                text = text.replace(tco_url, "")
                continue
            if expanded_url.startswith("https://x.com/") or expanded_url.startswith(
                "http://x.com/",
            ):
                text = text.replace(tco_url, "")
            else:
                text = text.replace(tco_url, expanded_url)

    text = re.sub(r"\n\n+", "\n", text)
    text = text.strip()

    indicators = []
    if poll_indicator:
        indicators.append(poll_indicator)
    if media_indicators:
        indicators.extend(media_indicators)

    if indicators:
        indicators_str = " ".join(indicators)
        text = (text + " " + indicators_str) if text else indicators_str

    return text
