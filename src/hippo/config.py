import os
from pathlib import Path

from hippo.templates import AGENTS_TOPIC_CONTENT

CONFIG_DIR = Path.home() / ".config" / "hippo"
CONFIG_FILE = CONFIG_DIR / "config"
DEFAULT_VAULT_DIR = Path.cwd()


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, str]:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        return {}
    config = {}
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            config[key] = value
    return config


def save_config(config: dict[str, str]) -> None:
    ensure_config_dir()
    lines = [f"{k}={v}" for k, v in config.items()]
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def get_vault_dir() -> Path | None:
    _ensure_config_key("vault_dir", "")
    config = load_config()
    if not config.get("vault_dir"):
        return None
    return Path(config["vault_dir"])


def set_vault_dir(vault_dir: Path) -> None:
    config = load_config()
    config["vault_dir"] = str(vault_dir)
    save_config(config)


def _ensure_config_key(key: str, default: str) -> str:
    config = load_config()
    if key not in config:
        config[key] = default
        save_config(config)
    return config.get(key, default)


def resolve_env_value(value: str) -> str:
    if value.startswith("$"):
        return os.environ.get(value[1:], "")
    return value


def get_x_config() -> dict[str, str]:
    _ensure_config_key("x_oauth2_client_id", "")
    _ensure_config_key("x_oauth2_client_secret", "")
    config = load_config()
    return {
        "x_oauth2_client_id": resolve_env_value(config.get("x_oauth2_client_id", "")),
        "x_oauth2_client_secret": resolve_env_value(
            config.get("x_oauth2_client_secret", "")
        ),
        "x_oauth2_access_token": config.get("x_oauth2_access_token") or "",
        "x_oauth2_refresh_token": config.get("x_oauth2_refresh_token") or "",
        "x_oauth2_pkce_verifier": config.get("x_oauth2_pkce_verifier") or "",
    }


def set_x_config(
    oauth2_client_id: str = "",
    oauth2_client_secret: str = "",
    oauth2_access_token: str = "",
    oauth2_refresh_token: str = "",
    oauth2_pkce_verifier: str = "",
) -> None:
    config = load_config()
    if oauth2_client_id:
        config["x_oauth2_client_id"] = oauth2_client_id
    if oauth2_client_secret:
        config["x_oauth2_client_secret"] = oauth2_client_secret
    if oauth2_access_token:
        config["x_oauth2_access_token"] = oauth2_access_token
    if oauth2_refresh_token:
        config["x_oauth2_refresh_token"] = oauth2_refresh_token
    if oauth2_pkce_verifier is not None:
        if oauth2_pkce_verifier:
            config["x_oauth2_pkce_verifier"] = oauth2_pkce_verifier
        elif "x_oauth2_pkce_verifier" in config:
            del config["x_oauth2_pkce_verifier"]
    save_config(config)


def init_vault(vault_path: Path) -> None:
    vault_path = vault_path.resolve()
    if vault_path.exists() and any(vault_path.iterdir()):
        raise ValueError(f"Directory {vault_path} is not empty")

    vault_path.mkdir(parents=True, exist_ok=True)
    (vault_path / "topics").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources/chats").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources/x").mkdir(parents=True, exist_ok=True)

    _ensure_config_key("vault_dir", str(vault_path))
    _ensure_config_key("x_oauth2_client_id", "")
    _ensure_config_key("x_oauth2_client_secret", "")

    (vault_path / "topics/AGENTS.md").write_text(AGENTS_TOPIC_CONTENT)
    set_vault_dir(vault_path)
