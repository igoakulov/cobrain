import json
import re

from cobrain.parsers.chatgpt.lookups import (
    build_citations_dict_from_attachments,
    build_citations_dicts,
)
from cobrain.parsers.chatgpt.utils import trim_url


def transform_assistant_messages_deep_research(
    content: str,
    content_refs: list[dict],
    source_refs: dict[str, int],
) -> str:
    citations_dict_from_deep_research: dict[int, tuple[str, str]] = {}
    for ref in content_refs:
        matched_text = ref.get("matched_text", "")
        url = ref.get("url", "") or ""
        title = ref.get("title", "") or ref.get("attribution", "") or ""
        cleaned = trim_url(url) if url else ""

        m = re.search(r"[\u3010\u2018\u2019](\d+)", matched_text)
        if m:
            idx = int(m.group(1))
            citations_dict_from_deep_research[idx] = (cleaned, title)
            if cleaned and cleaned not in source_refs:
                n = len(source_refs) + 1
                source_refs[cleaned] = n

    def replace(m: re.Match) -> str:
        inner = m.group(0)
        num_m = re.search(r"(\d+)", inner)
        if not num_m:
            return inner
        idx = int(num_m.group(1))
        if idx in citations_dict_from_deep_research:
            cleaned, _ = citations_dict_from_deep_research[idx]
            if cleaned and cleaned in source_refs:
                return f" [{source_refs[cleaned]}]"
        return inner

    content = re.sub(r"[\u3010][^\u3011]*\d+[^\u3011]*[\u3011]", replace, content)
    content = content.replace("\\$", "$")
    content = re.sub(
        r"\[(\d+)\]\s*\[(\d+)\]",
        lambda m: f"[{m.group(1)}]" if m.group(1) == m.group(2) else m.group(0),
        content,
    )
    return content


def transform_assistant_messages(
    content: str,
    msg: dict,
    citation_urls: set[str],
    source_refs: dict[str, int],
) -> str:
    citations_dict_from_attachments = build_citations_dict_from_attachments(msg)
    citations_dict_from_link_title, citations_dict_from_grouped_webpages = (
        build_citations_dicts(msg)
    )

    for k, v in citations_dict_from_link_title.items():
        if k not in citations_dict_from_grouped_webpages:
            citations_dict_from_grouped_webpages[k] = v

    citations_dict_from_webpage_extended: dict[str, tuple[str, str]] = {}

    for ref in msg.get("metadata", {}).get("content_references", []):
        ref_type = ref.get("type", "")
        matched = ref.get("matched_text", "")
        m = re.search(r"\d+", matched)
        if not m:
            continue
        idx_str = m.group(0)

        url = ref.get("url", "")
        title = ref.get("title", "") or ref.get("attribution", "")

        if ref_type == "webpage_extended" and url:
            cleaned = trim_url(url)
            citations_dict_from_webpage_extended[idx_str] = (cleaned, title)
            if cleaned and cleaned not in source_refs:
                n = len(source_refs) + 1
                source_refs[cleaned] = n
                citation_urls.add(cleaned)
        elif ref_type == "hidden":
            citations_dict_from_webpage_extended[idx_str] = ("", title)

    def replace_math(match: re.Match) -> str:  # genui{...} -> (math)
        try:
            inner = json.loads(match.group(1))
            math_content = inner.get("math_block_widget_common_keywords", {}).get(
                "content",
                "",
            ) or inner.get("content", "")
            if math_content:
                return f"({math_content})"
            return match.group(0)
        except (json.JSONDecodeError, KeyError):
            return match.group(0)

    content = re.sub(
        r"\ue200genui\ue202(\{.+?\})\ue201",
        replace_math,
        content,
        flags=re.DOTALL,
    )

    content = re.sub(
        r"\\\(([^)]*)\\\)",
        lambda m: "(" + m.group(1).replace("\\", "") + ")",
        content,
    )
    content = content.replace("\\$", "$")

    def replace_entities_product(
        match: re.Match,
    ) -> str:  # product_entity{...} -> [title]
        try:
            inner = json.loads(match.group(1))
            if isinstance(inner, list):
                filtered = [x for x in inner if x != 0]
                if len(filtered) >= 2:
                    return f"[{filtered[1]}]"
            else:
                title = inner.get("title", "")
                if title:
                    return f"[{title}]"
                arr = inner.get("arr", [])
                if len(arr) >= 2:
                    return f"[{arr[1]}]"
        except json.JSONDecodeError:
            pass
        return match.group(0)

    content = re.sub(
        r"\ue200product_entity\ue202(.+?)\ue201",
        replace_entities_product,
        content,
    )

    def replace_image_group(
        match: re.Match,
    ) -> str:  # image_group{...} -> [IMAGE: query]
        try:
            inner = json.loads(match.group(1))
            queries = inner.get("query", [])
            if queries:
                return " ".join(f"[IMAGE: {q}]" for q in queries)
        except json.JSONDecodeError:
            pass
        return match.group(0)

    content = re.sub(
        r"\ue200image_group\ue202(.+?)\ue201",
        replace_image_group,
        content,
        flags=re.DOTALL,
    )

    def replace_citations_inline(
        m: re.Match,
    ) -> str:  # link_title{title}{key} -> [title](url)
        title = m.group(1)
        key = m.group(2)
        result = citations_dict_from_link_title.get(key)
        if result:
            url, cite_title = result
            return f"[{cite_title}]({url})"
        return f"[{title}]"

    content = re.sub(
        r"\ue200link_title\ue202(.+?)\ue202(.+?)\ue201",
        replace_citations_inline,
        content,
    )

    def replace_citations(m: re.Match) -> str:  # cite{turn0search1} -> [1]
        inner = m.group(1)
        result = citations_dict_from_grouped_webpages.get(inner)
        if result:
            url, title = result
            cleaned = trim_url(url)
            if cleaned in source_refs:
                return f"[{source_refs[cleaned]}]"
            n = len(source_refs) + 1
            source_refs[cleaned] = n
            citation_urls.add(cleaned)
            return f"[{n}]"

        keys = inner.split("\ue202")
        first_url = ""
        for key in keys:
            key = key.strip()
            result = citations_dict_from_grouped_webpages.get(key)
            if result:
                url, title = result
                cleaned = trim_url(url)
                if cleaned in source_refs:
                    return f"[{source_refs[cleaned]}]"
                if not first_url:
                    first_url = url

        if first_url:
            cleaned = trim_url(first_url)
            if cleaned in source_refs:
                return f"[{source_refs[cleaned]}]"
            n = len(source_refs) + 1
            source_refs[cleaned] = n
            citation_urls.add(cleaned)
            return f"[{n}]"

        return f"[{inner}]"

    content = re.sub(r"\ue200cite\ue202(.+?)\ue201", replace_citations, content)

    def replace_citations_attachments(
        m: re.Match,
    ) -> str:  # filecite{turn0file0} -> [1]
        key = m.group(1)
        filename = citations_dict_from_attachments.get(key)
        if filename:
            if filename in source_refs:
                return f"[{source_refs[filename]}]"
            n = len(source_refs) + 1
            source_refs[filename] = n
            return f"[{n}]"
        return f"[{key}]"

    content = re.sub(
        r"\ue200filecite\ue202(.+?)\ue201",
        replace_citations_attachments,
        content,
    )

    def replace_entity(m: re.Match) -> str:  # entity{["company","Tesla"]} -> [Tesla]
        inner = m.group(1)
        try:
            arr = json.loads(inner)
            if isinstance(arr, list):
                filtered = [x for x in arr if x != 0 and x != ""]
                if len(filtered) < len(arr):
                    return f"[{', '.join(str(x) for x in filtered)}]"
        except json.JSONDecodeError:
            pass
        return inner

    content = re.sub(r"\ue200entity\ue202(.+?)\ue201", replace_entity, content)

    content = re.sub(
        r"\ue200cite\[(\d+)\]\ue201",
        lambda m: f"[{m.group(1)}]",
        content,
    )

    def _replace_webpage_extended_citations(
        m: re.Match,
        citation_dict: dict[str, tuple[str, str]],
        source_refs: dict[str, int],
    ) -> str:
        inner = m.group(0)
        idx_m = re.search(r"\d+", inner)
        if not idx_m:
            return inner
        idx_str = idx_m.group(0)
        if idx_str not in citation_dict:
            return inner
        url, _ = citation_dict[idx_str]
        if not url:
            return ""
        if url in source_refs:
            return f" [{source_refs[url]}]"
        return inner

    content = re.sub(
        r"[\u3010][^\u3011]*\d+[^\u3011]*[\u3011]",
        lambda m: _replace_webpage_extended_citations(
            m,
            citations_dict_from_webpage_extended,
            source_refs,
        ),
        content,
    )

    content = re.sub(
        r"\[(\d+)\]\s*\[(\d+)\]",
        lambda m: f"[{m.group(1)}]" if m.group(1) == m.group(2) else m.group(0),
        content,
    )

    return content
