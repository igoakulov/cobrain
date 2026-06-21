import os
from pathlib import Path

from cobrain.AGENTS import AGENTS_CONTENT


def _find_vault_dir(start: Path | None = None) -> Path | None:
    if start is None:
        start = Path.cwd().resolve()
    home = Path.home()
    for path in [start] + list(start.parents):
        if path == home:
            break
        config_path = path / ".cobrain" / "config"
        if config_path.exists():
            return path
    return None


def _get_vault_dir() -> Path:
    vault = _find_vault_dir()
    if vault is None:
        raise RuntimeError(
            "No vault found. Run `brn init` in your vault directory first.",
        )
    return vault


def _config_path() -> Path:
    vault = _get_vault_dir()
    return vault / ".cobrain" / "config"


def ensure_config_dir() -> None:
    vault = _get_vault_dir()
    cobrain_dir = vault / ".cobrain"
    cobrain_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, str]:
    path = _config_path()
    if not path.exists():
        return {}
    config = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            config[key] = value
    return config


def save_config(config: dict[str, str]) -> None:
    ensure_config_dir()
    path = _config_path()
    lines = [f"{k}={v}" for k, v in config.items()]
    path.write_text("\n".join(lines) + "\n")


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


def get_warnings_ignored_sources() -> list[str]:
    config = load_config()
    value = config.get("warnings_ignored_sources", "")
    return [entry.strip() for entry in value.split(",") if entry.strip()]


def get_x_config() -> dict[str, str]:
    _ensure_config_key("x_oauth2_client_id", "")
    _ensure_config_key("x_oauth2_client_secret", "")
    config = load_config()
    return {
        "x_oauth2_client_id": resolve_env_value(config.get("x_oauth2_client_id", "")),
        "x_oauth2_client_secret": resolve_env_value(
            config.get("x_oauth2_client_secret", ""),
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

    # Check if inside an existing vault (nested case)
    existing = _find_vault_dir(vault_path)
    if existing and existing != vault_path:
        raise ValueError(f"Already inside vault at {existing}.")

    # Re-init case - config exists, just ensure directories
    if (vault_path / ".cobrain" / "config").exists():
        (vault_path / ".cobrain").mkdir(parents=True, exist_ok=True)
        (vault_path / "topics").mkdir(parents=True, exist_ok=True)
        (vault_path / "sources/chats").mkdir(parents=True, exist_ok=True)
        (vault_path / "sources/x").mkdir(parents=True, exist_ok=True)
        agents_path = vault_path / "AGENTS.md"
        if not agents_path.exists():
            agents_path.write_text(AGENTS_CONTENT)
        return

    # Fresh init
    (vault_path / ".cobrain").mkdir(parents=True, exist_ok=True)
    (vault_path / "topics").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources/chats").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources/x").mkdir(parents=True, exist_ok=True)

    config_path = vault_path / ".cobrain" / "config"
    config_path.write_text(
        "x_oauth2_client_id=\nx_oauth2_client_secret=\nwarnings_ignored_sources=/junk/\n",
    )

    agents_path = vault_path / "AGENTS.md"
    if not agents_path.exists():
        agents_path.write_text(AGENTS_CONTENT)
