# Hippo

Hippo helps AI agents gather, organize and visualize owner's knowledge locally on device. Use it to back up and organize your knowledge, help AI agents read your mind, or map and track your learning progress.

## Quick Start

TBD

## Commands

```bash
hippo init --vault <path>          # Create new vault
hippo version                       # Show version
hippo sync                         # Rebuild graph from files
hippo topics                       # List topics with progress counts
hippo topics --ids <ids>          # Get metadata (single or comma-separated)
hippo topics --ids <ids> --set field=value...   # Update metadata
hippo topics --ids <ids> --set ... --sync       # Update then sync
hippo topics --sync --warnings               # Sync and show warnings
hippo graph                         # View full graph
hippo graph --minimal               # id, aliases, cluster, parent, related
hippo graph --full                  # minimal + title, progress, created_at, updated_at
hippo graph --full+                 # full + sources, word_count
hippo graph --flow                 # Flow style YAML (compact, default)
hippo graph --block                # Block style YAML (multiline)
hippo graph --from <id>           # View neighborhood
hippo graph --from <id> --depth N # Traverse N levels
hippo graph --from <id> --to <id2> # Find path
hippo graph --sync                  # Sync before viewing
hippo graph --sync --warnings       # Sync and show warnings
hippo sources                       # View source stats
hippo sources --ingest chatgpt --paths <path...>  # Ingest ChatGPT exports
hippo sources --ingest chatgpt --paths <path...> --since <dt> --until <dt> --titles <titles>  # Ingest with filters
hippo sources --ingest x --ids <post_ids>          # Ingest X posts by ID/URL/xurl (batch)
hippo sources --ingest x --own                     # Ingest own posts (1 page, 10 posts)
hippo sources --ingest x --own --count <N>         # Paginate (derived), fetch up to N posts
hippo sources --ingest x --own --since-id <id> --until-id <id>  # Targeted range
hippo sources --ingest x --own --new               # Catch-up: paginate (10/page), stop on cached
hippo sources --ingest x --likes                   # Ingest liked posts (1 page, 10 posts)
hippo sources --ingest x --likes --count <N>       # Paginate (derived), fetch up to N posts
hippo sources --ingest x --likes --new             # Catch-up: paginate (10/page), stop on cached
hippo sources --ingest x --bookmarks               # Ingest bookmarked posts (1 page, 10 posts)
hippo sources --ingest x --bookmarks --count <N>   # Paginate (derived), fetch up to N posts
hippo sources --ingest x --bookmarks --new         # Catch-up: paginate (10/page), stop on cached
hippo backup                        # Create backup with diff from previous
```

All `--ingest x` commands pull full conversation above the target post, and minimize API credits spent by always checking locally stored posts first.

## Warnings

Add `--warnings` to show and troubleshoot issues:
- `hippo sync --warnings`
- `hippo sources --warnings`
- `hippo topics --sync --warnings`
- `hippo graph --sync --warnings`

Backup shows warning counts in summary.

## Topic Format

Topics are markdown files with YAML frontmatter:

```yaml
---
id: flashattention
title: FlashAttention
aliases: flash-attention
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: transformers
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
vault/
├── topics/                   # Topics (.md), source of truth for CLI
├── sources/                  # Cached sources
│   ├── chats/                # ChatGPT (or other) conversations (.md)
│   └── x/                    # X posts arranged in conversations (.yaml)
└── .hippo/                   # App internals
    ├── graph.yaml            # Derived graph (from topics)
    ├── graph.html            # Visualization
    ├── clusters.yaml         # Cluster colors and titles
    ├── backups/              # Rolling backups
    ├── diffs/                # Change logs
    └── logs/                 # Ingest logs
        ├── chatgpt/          # ChatGPT ingest logs
        └── x/                # X ingest logs
```
