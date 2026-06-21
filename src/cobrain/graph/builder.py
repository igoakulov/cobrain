import re
from datetime import datetime
from pathlib import Path

from cobrain.directories import VAULT_DIR, get_vault_graph_path
from cobrain.graph.validation import BuildResult, CleanIssue, ValidationError
from cobrain.topics.topic import (
    Topic,
    body_has_content,
    frontmatter_position,
    parse_frontmatter,
    topic_from_markdown,
)
from cobrain.yaml_utils import read_yaml, write_yaml


def _count_words(body: str) -> int:
    return len(body.split())


def _file_dates(path: Path) -> tuple[str, str]:
    stat = path.stat()
    updated_ts = stat.st_mtime
    created_ts = getattr(stat, "st_birthtime", None) or stat.st_ctime
    created_at = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%dT%H:%M")
    updated_at = datetime.fromtimestamp(updated_ts).strftime("%Y-%m-%dT%H:%M")
    return created_at, updated_at


def scan_topics_dir() -> list[Path]:
    topics_dir = VAULT_DIR / "topics"
    if not topics_dir.exists():
        return []
    return sorted(topics_dir.glob("*.md"))


def build_graph() -> BuildResult:
    validation_errors: list[ValidationError] = []
    clean_issues: list[CleanIssue] = []
    topics_dict: dict[str, Topic] = {}
    seen_ids: set[str] = set()
    filename_map: dict[str, str] = {}

    topic_files = scan_topics_dir()
    if not topic_files:
        return BuildResult([], [], [], [])

    for path in topic_files:
        topic_id = path.stem
        filename = path.name

        try:
            content = path.read_text()
            data, body = parse_frontmatter(content)

            has_fm = bool(re.search(r"^---\s*\n", content, re.MULTILINE))

            if has_fm and not data:
                validation_errors.append(
                    ValidationError(
                        topic_id=topic_id,
                        filename=filename,
                        message="Metadata frontmatter cannot be parsed",
                    ),
                )

            if "id" not in data:
                validation_errors.append(
                    ValidationError(
                        topic_id=topic_id,
                        filename=filename,
                        message="Missing topic id",
                    ),
                )

            topic = topic_from_markdown(topic_id, content)
            topic.word_count = _count_words(body)
            topic.created_at, topic.updated_at = _file_dates(path)

            filename_map[topic.id] = filename

            if topic.id in seen_ids:
                validation_errors.append(
                    ValidationError(
                        topic_id=topic.id,
                        filename=filename,
                        message=f"Duplicate topic id: {topic.id}",
                    ),
                )
            seen_ids.add(topic.id)

            topics_dict[topic.id] = topic

            if frontmatter_position(content) != 0:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="frontmatter_position",
                        message="Frontmatter not at top",
                    ),
                )

            if not body_has_content(body):
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="empty_body",
                        message="Empty body",
                    ),
                )

            if not topic.sources:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="no_sources",
                        message="No sources",
                    ),
                )

            if not topic.parent:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="no_parent",
                        message="No parent",
                    ),
                )

        except Exception:
            validation_errors.append(
                ValidationError(
                    topic_id=topic_id,
                    filename=filename,
                    message="Metadata frontmatter cannot be parsed",
                ),
            )
            clean_issues.append(
                CleanIssue(
                    topic_id=topic_id,
                    filename=filename,
                    issue_type="invalid_yaml",
                    message="Frontmatter parsed with issues",
                ),
            )

    for topic in topics_dict.values():
        if topic.parent and topic.parent not in topics_dict:
            clean_issues.append(
                CleanIssue(
                    topic_id=topic.id,
                    filename=filename_map.get(topic.id, f"{topic.id}.md"),
                    issue_type="orphan_parent",
                    message=f"Parent not found: {topic.parent}",
                ),
            )

    topic_list = list(topics_dict.values())

    return BuildResult(
        topics=topic_list,
        categories=[],
        validation_errors=validation_errors,
        clean_issues=clean_issues,
    )


def save_graph(result: BuildResult) -> dict:
    vault_graph_path = get_vault_graph_path()
    vault_graph_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"topics": [t.to_dict() for t in result.topics]}

    write_yaml(vault_graph_path, data)

    word_counts = {}
    for topic in result.topics:
        word_counts[topic.id] = topic.word_count

    return word_counts


def sync() -> BuildResult:
    result = build_graph()
    if not result.validation_errors:
        save_graph(result)
    return result


def read_graph() -> BuildResult:
    """Read vault.yaml, sync if missing."""
    vault_graph_path = get_vault_graph_path()
    if not vault_graph_path.exists():
        return sync()

    data = read_yaml(vault_graph_path)
    if not data:
        return sync()

    topics = [Topic.from_dict(t) for t in data.get("topics", [])]
    return BuildResult(
        topics=topics,
        categories=[],
        validation_errors=[],
        clean_issues=[],
    )
