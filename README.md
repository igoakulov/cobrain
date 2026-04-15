# Hippo

Hippo is a tool for your AI agent to visualize, update and expand your personal knowledge locally on your device.

## Quick Start

TBD

## Commands

```bash
hippo init --vault <path>          # Create new vault
hippo version                       # Show version
hippo sync                         # Rebuild graph from files
hippo topics                       # List topics with progress counts
hippo topics --ids <ids>          # Get metadata (single or comma-separated)
hippo topics --ids <ids> --meta field=value...   # Update metadata
hippo topics --ids <ids> --meta ... --sync       # Update then sync
hippo graph                         # View full graph
hippo graph --minimal               # id, cluster, parent, related
hippo graph --full                  # All standard fields
hippo graph --full+                 # Full + sources, word_count
hippo graph --pretty                # Pretty-print JSON
hippo graph --from <id>           # View neighborhood
hippo graph --from <id> --depth N # Traverse N levels
hippo graph --from <id> --to <id2> # Find path
hippo graph --sync                  # Sync before viewing
hippo graph --warnings              # Show warnings
hippo sources                       # View source stats
hippo sources --ingest chatgpt --paths <path...>  # Ingest ChatGPT exports
hippo sources --ingest chatgpt --paths <path...> --from <dt> --till <dt> --titles <titles>  # Ingest with filters
hippo sources --ingest x --ids <post_ids>         # Ingest X posts by ID
hippo sources --ingest x --own                     # Ingest own posts (1 page)
hippo sources --ingest x --likes                   # Ingest liked posts (1 page)
hippo sources --ingest x --bookmarks                # Ingest bookmarked posts (1 page)
hippo sources --ingest x --own --new               # Catch-up: loop until existing
hippo sources --ingest x --likes --new             # Catch-up: loop until existing
hippo sources --ingest x --bookmarks --new         # Catch-up: loop until existing
hippo sources --ingest x --own --count <N>         # Initial ingest: up to N posts
hippo sources --ingest x --own --since-id <id> --until-id <id>  # Targeted range
hippo backup                        # Create backup
hippo restore                       # Restore (most recent)
hippo restore --version <timestamp> # Restore specific backup
```

## Warnings

Add `--warnings` to any command to show and troubleshoot issues:
- `hippo sync --warnings`
- `hippo topics --warnings`
- `hippo sources --warnings`
- `hippo graph --warnings`

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
├── topics/            # Topic markdown files (source of truth)
├── sources/           # Cached sources
│   ├── chats/        # Chat exports
│   └── x/            # X posts (YAML trees)
└── .hippo/           # App internals
    ├── graph.yaml     # Derived graph
    ├── graph.html   # Visualization
    ├── clusters.yaml # Cluster colors and titles
    ├── sources_archive.yaml # Source references
    ├── backups/     # Rolling backups
    ├── diffs/       # Change logs
    └── logs/        # Ingest logs
        ├── chatgpt/ # ChatGPT ingest logs
        └── x/       # X ingest logs
```
