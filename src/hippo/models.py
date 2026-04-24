from dataclasses import dataclass, field

from hippo.topics.topic import Topic


@dataclass
class Category:
    id: str
    title: str
    color: str = "#888888"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "color": self.color,
        }

    @staticmethod
    def from_dict(data: dict) -> "Category":
        return Category(
            id=data["id"],
            title=data["title"],
            color=data.get("color", "#888888"),
        )


@dataclass
class Graph:
    topics: list[Topic] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "categories": [c.to_dict() for c in self.categories],
            "topics": [n.to_dict() for n in self.topics],
        }

    @staticmethod
    def from_dict(data: dict) -> "Graph":
        return Graph(
            categories=[Category.from_dict(c) for c in data.get("categories", [])],
            topics=[Topic.from_dict(n) for n in data.get("topics", [])],
        )
