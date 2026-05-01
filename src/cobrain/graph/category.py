from cobrain.models import Category
from cobrain.yaml_utils import read_yaml, write_yaml

# Red - https://coolors.co/palette/9c191b-ac1c1e-bd1f21-d02224-dd2c2f-e35053-e66063-ec8385-f1a7a9-f6cacc
RED = ["#9C191B", "#D02224", "#E35053", "#EC8385"]

# Orange - https://coolors.co/palette/ff7b00-ff8800-ff9500-ffa200-ffaa00-ffb700-ffc300-ffd000-ffdd00-ffea00
ORANGE = ["#E06C00", "#FF8800", "#FFA900", "#FFCA00"]

# Green - https://coolors.co/palette/10451d-155d27-1a7431-208b3a-25a244-2dc653-4ad66d-6ede8a-92e6a7-b7efc5
GREEN = ["#1A7431", "#25A244", "#4AD66D", "#92E6A7"]

# Blue - https://coolors.co/palette/012a4a-013a63-01497c-014f86-2a6f97-2c7da0-468faf-61a5c2-89c2d9-a9d6e5
BLUE = ["#014F86", "#2C7DA0", "#61A5C2", "#A9D6E5"]

# Violet - https://coolors.co/palette/ebe0ff-dac7ff-c7adff-ac8bee-916dd5-7151a9-573d7f-46325d-3f3649
VIOLET = ["#7151A9", "#916DD5", "#AC8BEE", "#C7ADFF"]

GROUPS = [RED, ORANGE, GREEN, BLUE, VIOLET]

# Interleave: i % len(GROUPS) picks group, i // len(GROUPS) picks color within group
PALETTE = [
    GROUPS[i % len(GROUPS)][i // len(GROUPS)] for i in range(len(GROUPS) * len(RED))
]


def save_categories(categories: list[Category]) -> None:
    from cobrain.directories import get_categories_path

    path = get_categories_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"categories": [c.to_dict() for c in categories]}
    write_yaml(path, data)


def load_categories() -> list[Category]:
    from cobrain.directories import get_categories_path

    path = get_categories_path()
    if not path.exists():
        return []
    data = read_yaml(path)
    if not data:
        return []
    return [Category.from_dict(c) for c in data.get("categories", [])]


def merge_categories(inferred: list[Category]) -> list[Category]:
    existing = {c.id: c for c in load_categories()}
    result: list[Category] = []
    for category in inferred:
        if category.id in existing:
            result.append(existing[category.id])
        else:
            result.append(category)
    return result


def infer_categories(topics: list[dict]) -> list[Category]:
    unique_categories: set[str] = set()
    for topic in topics:
        category_id = topic.get("category", "")
        if category_id:
            unique_categories.add(category_id)

    categories = []
    for i, category_id in enumerate(sorted(unique_categories)):
        color = PALETTE[i % len(PALETTE)]
        words = category_id.replace("-", " ").replace("_", " ").split()
        title = " ".join(word.capitalize() for word in words)
        categories.append(Category(id=category_id, title=title, color=color))

    return categories
