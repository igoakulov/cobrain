from pathlib import Path
from typing import Any

import yaml


def read_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            result = yaml.safe_load(f)
            if isinstance(result, dict):
                return result
            return None
    except yaml.YAMLError:
        return None


def read_yaml_list(path: Path) -> list | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            result = yaml.safe_load(f)
            if isinstance(result, list):
                return result
            return None
    except yaml.YAMLError:
        return None


def write_yaml(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    if isinstance(data, dict) and "conversation_xurl" in data:
        with open(path) as f:
            content = f.read()
        lines = content.split("\n")
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if line.startswith("conversation_updated_at:"):
                new_lines.append("")
        with open(path, "w") as f:
            f.write("\n".join(new_lines))
