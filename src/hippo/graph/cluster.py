from hippo.models import Cluster
from hippo.yaml_utils import read_yaml, write_yaml

PALETTE = [
    "#4A90D9",
    "#50C878",
    "#FF6B6B",
    "#FFD93D",
    "#6BCB77",
    "#4D96FF",
    "#FF922B",
    "#845EC2",
    "#00C9A7",
    "#F9F871",
    "#FFB3BA",
    "#BAFFC9",
    "#BAE1FF",
    "#FFFFBA",
    "#FFD1DC",
    "#C9B1FF",
    "#FF9F1C",
    "#2EC4B6",
    "#E71D36",
    "#011627",
    "#FDFFFC",
    "#011627",
    "#2EC4B6",
    "#FF9F1C",
    "#E71D36",
    "#7209B7",
    "#3A0CA3",
    "#4CC9F0",
    "#F72585",
    "#4361EE",
]


def save_clusters(clusters: list[Cluster]) -> None:
    from hippo.directories import get_clusters_path

    path = get_clusters_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"clusters": [c.to_dict() for c in clusters]}
    write_yaml(path, data)


def load_clusters() -> list[Cluster]:
    from hippo.directories import get_clusters_path

    path = get_clusters_path()
    if not path.exists():
        return []
    data = read_yaml(path)
    if not data:
        return []
    return [Cluster.from_dict(c) for c in data.get("clusters", [])]


def merge_clusters(inferred: list[Cluster]) -> list[Cluster]:
    existing = {c.id: c for c in load_clusters()}
    result: list[Cluster] = []
    for cluster in inferred:
        if cluster.id in existing:
            result.append(existing[cluster.id])
        else:
            result.append(cluster)
    return result


def infer_clusters(topics: list[dict]) -> list[Cluster]:
    unique_clusters: set[str] = set()
    for topic in topics:
        cluster_id = topic.get("cluster", "")
        if cluster_id:
            unique_clusters.add(cluster_id)

    clusters = []
    for i, cluster_id in enumerate(sorted(unique_clusters)):
        color = PALETTE[i % len(PALETTE)]
        words = cluster_id.replace("-", " ").replace("_", " ").split()
        title = " ".join(word.capitalize() for word in words)
        clusters.append(Cluster(id=cluster_id, title=title, color=color))

    return clusters


def get_cluster_color(cluster_id: str, clusters: list[Cluster]) -> str | None:
    for cluster in clusters:
        if cluster.id == cluster_id:
            return cluster.color
    return None
