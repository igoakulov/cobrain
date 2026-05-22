import re

from cobrain.parsers.chatgpt.utils import trim_url


def build_citations_dict_from_attachments(msg: dict) -> dict[str, str]:
    refs: dict[str, str] = {}

    for ref in msg.get("metadata", {}).get("content_references", []):
        matched_text = ref.get("matched_text", "")
        name = ref.get("name", "")
        ref_type = ref.get("type", "")

        if matched_text and name:
            ref_id_match = re.search(r"\ue200filecite\ue202(.+?)\ue201", matched_text)
            if ref_id_match:
                ref_id = ref_id_match.group(1)
                refs[ref_id] = name
            elif ref_type == "file":
                refs[matched_text] = name
            else:
                refs[matched_text] = name

    return refs


def build_citations_dicts(
    msg: dict,
) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    citations_dict_from_link_title: dict[str, tuple[str, str]] = {}
    citations_dict_from_grouped_webpages: dict[str, tuple[str, str]] = {}

    search_groups = msg.get("metadata", {}).get("search_result_groups", [])
    for group in search_groups:
        title_fallback = group.get("domain", "")
        for entry in group.get("entries", []):
            ref_id_dict = entry.get("ref_id", {})
            turn_index = ref_id_dict.get("turn_index", 0)
            ref_index = ref_id_dict.get("ref_index", 0)
            key = f"turn{turn_index}search{ref_index}"

            url = entry.get("url", "")
            title = (
                entry.get("title", "") or entry.get("attribution", "") or title_fallback
            )
            if url:
                url = trim_url(url)
                if key not in citations_dict_from_link_title:
                    citations_dict_from_link_title[key] = (url, title)
                if key not in citations_dict_from_grouped_webpages:
                    citations_dict_from_grouped_webpages[key] = (url, title)

    content_refs = msg.get("metadata", {}).get("content_references", [])
    for ref in content_refs:
        ref_type = ref.get("type", "")
        if ref_type not in ("grouped_webpages", "link_title"):
            continue

        url = ref.get("url", "")
        title = ref.get("title", "")

        if ref_type == "grouped_webpages":
            items = ref.get("items", [])
            for item in items:
                if not url:
                    url = item.get("url", "")
                if not title:
                    title = item.get("title", "")
                if url or title:
                    break

        matched_text = ref.get("matched_text", "")

        if ref_type == "link_title":
            cite_match = re.search(
                r"\ue200link_title\ue202.+?\ue202(.+?)\ue201", matched_text,
            )
            if cite_match:
                key = cite_match.group(1)
                if key not in citations_dict_from_link_title:
                    if url:
                        citations_dict_from_link_title[key] = (trim_url(url), title)
                    else:
                        refs_in_entry = ref.get("refs", [])
                        for r in refs_in_entry:
                            turn = r.get("turn_index", 0)
                            idx = r.get("ref_index", 0)
                            search_key = f"turn{turn}search{idx}"
                            if search_key in citations_dict_from_link_title:
                                existing = citations_dict_from_link_title[search_key]
                                citations_dict_from_link_title[key] = (
                                    existing[0],
                                    title,
                                )
                                break
        else:
            cite_match = re.search(r"\ue200cite\ue202(.+?)\ue201", matched_text)
            if cite_match:
                key = cite_match.group(1)
                display_title = title
                if key not in citations_dict_from_grouped_webpages:
                    if url:
                        citations_dict_from_grouped_webpages[key] = (
                            trim_url(url),
                            display_title,
                        )
                    else:
                        refs_in_entry = ref.get("refs", [])
                        for r in refs_in_entry:
                            turn = r.get("turn_index", 0)
                            idx = r.get("ref_index", 0)
                            search_key = f"turn{turn}search{idx}"
                            if search_key in citations_dict_from_grouped_webpages:
                                existing = citations_dict_from_grouped_webpages[
                                    search_key
                                ]
                                citations_dict_from_grouped_webpages[key] = (
                                    existing[0],
                                    display_title,
                                )
                                break

                items = ref.get("items", [])
                for item in items:
                    item_url = item.get("url", "")
                    item_title = (
                        item.get("title", "")
                        or item.get("attribution", "")
                        or display_title
                    )
                    item_refs = item.get("refs", [])
                    for r in item_refs:
                        turn = r.get("turn_index", 0)
                        idx = r.get("ref_index", 0)
                        search_key = f"turn{turn}search{idx}"
                        if item_url:
                            citations_dict_from_grouped_webpages[search_key] = (
                                trim_url(item_url),
                                item_title,
                            )

    return citations_dict_from_link_title, citations_dict_from_grouped_webpages
