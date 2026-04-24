from datetime import datetime, timezone
from pathlib import Path

from hippo.directories import get_backups_dir
from hippo.graph.diffs import compute_diff, save_diff
from hippo.yaml_utils import read_yaml, write_yaml

DEFAULT_RETENTION = 20


def list_backups() -> list[str]:
    backups_dir = get_backups_dir()
    if not backups_dir.exists():
        return []
    backups = []
    for path in backups_dir.glob("graph_backup_*.yaml"):
        ts = path.stem.replace("graph_backup_", "")
        backups.append(ts)
    return sorted(backups, reverse=True)


def create_backup(result) -> Path:
    from hippo.graph.builder import save_graph
    from hippo.directories import get_categories_path

    word_counts = save_graph(result)

    backups_dir = get_backups_dir()
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    backup_path = backups_dir / f"graph_backup_{timestamp}.yaml"

    categories_path = get_categories_path()
    backup_categories_path = backups_dir / f"categories_backup_{timestamp}.yaml"
    if categories_path.exists():
        backup_categories_path.write_text(categories_path.read_text())

    backup_data = {
        "timestamp": timestamp,
        "topics": [t.to_dict() for t in result.topics],
        "word_counts": word_counts,
    }
    write_yaml(backup_path, backup_data)

    _create_diff_from_previous(timestamp, result.topics)

    _prune_backups()

    return backup_path


def _create_diff_from_previous(timestamp: str, current_topics: list) -> None:
    backups = list_backups()
    if not backups:
        return

    previous_ts = backups[0]
    previous_backup_path = get_backups_dir() / f"graph_backup_{previous_ts}.yaml"

    if not previous_backup_path.exists():
        return

    previous_data = read_yaml(previous_backup_path)
    if not previous_data:
        return

    new_data = {"topics": [t.to_dict() for t in current_topics]}
    diff = compute_diff(previous_data, new_data)

    if not diff.is_empty():
        save_diff(diff)


def _prune_backups(retention: int = DEFAULT_RETENTION) -> None:
    backups_dir = get_backups_dir()
    backups = sorted(
        backups_dir.glob("graph_backup_*.yaml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[retention:]:
        old_backup.unlink()
