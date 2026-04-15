AGENTS_TOPIC_CONTENT = """---
id: AGENTS
title: Hippo Agent Skill
aliases: hippo,claude
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster:
parent:
related: []
sources:
---
# Hippo Agent Skill

See [skill.md](docs/skill.md) for full instructions.

## Topic Format

Topics are markdown files with YAML frontmatter:

\\`\\`\\`yaml
---
id: topic-id
title: Topic Title
aliases: alias1,alias2
progress: new|started|completed
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
cluster: cluster-id
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
- Get metadata: `hippo topics --ids <id>`
- Set metadata: `hippo topics --ids <id> --meta field=value`
- Search: `grep "keyword" topics/*.md`
- Graph: `hippo graph --from <id> --depth N`
"""
