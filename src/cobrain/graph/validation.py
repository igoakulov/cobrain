from dataclasses import dataclass

from cobrain.models import Topic, Category


@dataclass
class ValidationError:
    topic_id: str
    filename: str
    message: str


@dataclass
class CleanIssue:
    topic_id: str
    filename: str
    issue_type: str
    message: str


@dataclass
class BuildResult:
    topics: list[Topic]
    categories: list[Category]
    validation_errors: list[ValidationError]
    clean_issues: list[CleanIssue]
