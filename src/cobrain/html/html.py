import json
from pathlib import Path

from cobrain.directories import get_vault_dir, get_vault_graph_path
from cobrain.graph.category import infer_categories, merge_categories, save_categories
from cobrain.yaml_utils import read_yaml


def _load_graph() -> list[dict]:
    vault_graph_path = get_vault_graph_path()
    if not vault_graph_path.exists():
        return []

    data = read_yaml(vault_graph_path)
    if not data:
        return []

    return data.get("topics", [])


def _build_links(topics: list[dict]) -> tuple[list[dict], list[dict]]:
    topic_ids = {t["id"] for t in topics}

    parent_links: list[dict] = []
    related_links: list[dict] = []
    for topic in topics:
        parent = topic.get("parent", "")
        if parent and parent in topic_ids:
            parent_links.append({"source": parent, "target": topic["id"]})

        for related_id in topic.get("related", []):
            if related_id in topic_ids:
                related_links.append({"source": topic["id"], "target": related_id})

    return parent_links, related_links


def _generate_html(data: dict) -> str:
    json_data = json.dumps(data, ensure_ascii=False)

    script_dir = Path(__file__).parent
    template_path = script_dir / "template.html"
    css_path = script_dir / "style.css"
    js_path = script_dir / "script.js"

    html_template = template_path.read_text()
    css = css_path.read_text()
    js = js_path.read_text()

    html = html_template.replace("{{CSS}}", css)
    html = html.replace("{{JS}}", js)
    html = html.replace("{{DATA}}", json_data)

    return html


def build_html() -> Path:
    vault_dir = get_vault_dir()
    vault_name = vault_dir.parent.name

    topics = _load_graph()

    inferred = infer_categories(topics)
    category_list = merge_categories(inferred)
    save_categories(category_list)
    categories = {
        c.id: {"id": c.id, "title": c.title, "color": c.color} for c in category_list
    }

    topic_map: dict[str, dict] = {t["id"]: t for t in topics}
    parent_links, related_links = _build_links(topics)

    topic_count = len(topics)

    output = {
        "nodes": list(topic_map.values()),
        "parentLinks": parent_links,
        "relatedLinks": related_links,
        "categories": list(categories.values()),
        "vaultName": vault_name,
        "topicCount": topic_count,
        "vaultPath": str(vault_dir.parent),
    }

    html_content = _generate_html(output)

    vault_html_path = get_vault_dir().parent / "vault.html"
    vault_html_path.parent.mkdir(parents=True, exist_ok=True)
    vault_html_path.write_text(html_content)

    return vault_html_path
