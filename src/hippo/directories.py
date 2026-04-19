from pathlib import Path

from hippo.config import get_vault_dir

_vault_dir: Path | None = None


def _get_vault_dir() -> Path:
    global _vault_dir
    if _vault_dir is None:
        config_vault = get_vault_dir()
        if config_vault:
            _vault_dir = config_vault
        else:
            raise RuntimeError(
                "Vault not found. Run `hippo init --vault <path>` to set vault_dir in config."
            )
    return _vault_dir


def get_hippo_dir() -> Path:
    return _get_vault_dir() / ".hippo"


def get_topic_path(topic_id: str) -> Path:
    return _get_vault_dir() / "topics" / f"{topic_id}.md"


def get_backups_dir() -> Path:
    return get_hippo_dir() / "backups"


def get_diffs_dir() -> Path:
    return get_hippo_dir() / "diffs"


def get_graph_path() -> Path:
    return get_hippo_dir() / "graph.yaml"


def get_clusters_path() -> Path:
    return get_hippo_dir() / "clusters.yaml"


def get_chats_dir() -> Path:
    return _get_vault_dir() / "sources" / "chats"


def get_chats_logs_dir() -> Path:
    return get_hippo_dir() / "logs" / "chatgpt"


def get_chat_log_path(timestamp: str) -> Path:
    return get_chats_logs_dir() / f"ingest_{timestamp}.yaml"


def get_x_dir() -> Path:
    return _get_vault_dir() / "sources" / "x"


def get_x_trees_dir() -> Path:
    return get_x_dir()


def get_x_logs_dir() -> Path:
    return get_hippo_dir() / "logs" / "x"


def get_x_log_path(timestamp: str) -> Path:
    return get_x_logs_dir() / f"ingest_{timestamp}.yaml"


class _VaultDirProxy:
    def __truediv__(self, other: str) -> Path:
        return _get_vault_dir() / other

    def __rtruediv__(self, other: str) -> Path:
        return other / _get_vault_dir()

    def __fspath__(self) -> str:
        return str(_get_vault_dir())


VAULT_DIR = _VaultDirProxy()
