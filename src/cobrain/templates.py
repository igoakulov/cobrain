AGENTS_TOPIC_CONTENT = """---
id: AGENTS
title: CoBrain Agent Skill
aliases: cobrain,claude
created_at: 2026-03-19
updated_at: 2026-03-19
category:
parent:
related: []
sources:
---
# CoBrain Agent Skill

See [skill.md](docs/skill.md) for full instructions.

## Topic Format

Topics are markdown files with YAML frontmatter:

\\`\\`\\`yaml
---
id: topic-id
title: Topic Title
aliases: alias1,alias2
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
category: category-id
parent: parent-topic-id
related: [related1, related2]
sources:
  - https://example.com/source
  - ~/documents/file.pdf
---
# Topic Title

Your notes here...
\\`\\`\\`

## Quick Commands

- List topics: `ls topics/`
- Get metadata: `cobrain vault --ids <id>`
- Set metadata: `cobrain vault --ids <id> --set field=value`
- Search: `grep "keyword" topics/*.md`
- Graph: `cobrain vault --from <id> --depth N`
"""
