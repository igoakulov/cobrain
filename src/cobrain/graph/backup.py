from datetime import UTC, datetime
from pathlib import Path

from cobrain.directories import (
    get_backups_dir,
    get_categories_path,
    get_vault_graph_path,
)

DEFAULT_RETENTION = 20


def list_backups() -> list[str]:
    backups_dir = get_backups_dir()
    if not backups_dir.exists():
        return []
    backups = []
    for path in backups_dir.glob("vault_backup_*.yaml"):
        ts = path.stem.replace("vault_backup_", "")
        backups.append(ts)
    return sorted(backups, reverse=True)


def create_backup() -> Path:
    backups_dir = get_backups_dir()
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    backup_path = backups_dir / f"vault_backup_{timestamp}.yaml"

    vault_graph_path = get_vault_graph_path()
    if vault_graph_path.exists():
        backup_path.write_text(vault_graph_path.read_text())

    categories_path = get_categories_path()
    backup_categories_path = backups_dir / f"categories_backup_{timestamp}.yaml"
    if categories_path.exists():
        backup_categories_path.write_text(categories_path.read_text())

    _prune_backups()

    return backup_path


def _prune_backups(retention: int = DEFAULT_RETENTION) -> None:
    backups_dir = get_backups_dir()
    backups = sorted(
        backups_dir.glob("vault_backup_*.yaml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[retention:]:
        old_backup.unlink()
