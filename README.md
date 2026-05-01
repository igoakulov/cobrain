# Cobrain

Cobrain CLI helps AI agents gather, organize and visualize owner's knowledge locally on device. Use it to back up and organize your knowledge, help AI agents read your mind, or map and track your learning progress.

## Quick Start

Install agent skill (to be published soon)

Alternative (to be published soon):
```bash
pip install cobrain
```

## Commands

```bash
brn version                        # Show version
brn vault --dir <path>             # Initialize/connect vault and create config
brn sync [--warnings]              # Rebuild vault graph from files + show warnings
brn show                           # Build and open vault.html in browser (+ generate categories.yaml for color customization)
brn vault [--ids <ids>] [--minimal | --full | --full+] [--flow | --block]  # Get vault graph as YAML (select ids, topic metadata fields, YAML format)
brn vault --ids <ids> --set field=value...  # Update metadata in topic file frontmatter + sync to graph
brn vault --from <id> [--depth N]  # Neighborhood at N depth
brn vault --from <id> --to <id2>   # Shortest path (parent links only)
brn sources [--warnings]           # View source stats + warnings
brn sources --ingest chatgpt --paths <path...> [--since <dt>] [--until <dt>] [--titles <titles]>  # Ingest ChatGPT conversations.json exports
brn sources --ingest x --ids <post_ids>  # Ingest X posts by ID/URL/xurl
brn sources --ingest x --own [--count <N> | --new | --since-id <id> --until-id <id>]  # Fetch own posts (default 10, count, all new until hit existing, or target range)
brn sources --ingest x --own --authorization-code <code>  # First-time X auth
brn sources --ingest x --likes [--count <N> | --new]  # Ingest liked posts
brn sources --ingest x --bookmarks [--count <N> | --new]  # Ingest bookmarked posts
brn backup                         # Copy vault.yaml + categories.yaml (up to 20)
```

All `--ingest x` commands pull full conversation above the target post, and minimize API credits spent by always checking locally stored posts first.

## Topic Format

Topics are markdown files with YAML frontmatter:

```yaml
---
id: flashattention
title: FlashAttention
aliases: flash-attention
created_at: 2026-03-19
updated_at: 2026-03-19
category: transformers
parent: attention
related: [ringattention]
sources:
  - https://arxiv.org/abs/2205.14148
---
# FlashAttention

Your notes here...
```

## Vault Structure

```
vault/                    # User's vault directory
├── vault.html            # Visualization for user
├── topics/               # Topic files (.md), source of truth for CLI
├── sources/              # Cached sources
│   ├── chats/            # ChatGPT (or other) conversations (.md)
│   └── x/                # X posts arranged in conversation trees (.yaml)
└── .cobrain/             # App internals
    ├── vault.yaml        # Derived vault graph (from topics)
    ├── categories.yaml   # Category colors and titles
    ├── backups/          # Rolling backups
    ├── diffs/            # Change logs
    └── logs/             # Ingest logs
        ├── chatgpt/      # ChatGPT ingest logs
        └── x/            # X ingest logs
```
