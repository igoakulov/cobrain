---
name: cobrain-vault
description: Manage a local knowledge vault as AI agent. Ingest sources (ChatGPT, X, other), create/update topics from synthesized sources, organize coherent graph, find knowledge on demand, run health checks. CLI provides deterministic vault operations and token-efficient graph traversal. Use for backing up knowledge, building persistent context between owner/user/agent, or tracking learning progress.
---

## Overview

Cobrain CLI helps AI agents gather, organize and visualize owner's knowledge in a local vault: files (topics, sources) + graph (structured metadata).

- Vault locally stores and organizes knowledge, tracks learning, and creates persistent shared context between owner/user/agent for collaboration and decisions
- Agent manages vault autonomously
- Cobrain CLI performs deterministic tasks and helps AI agent perform vault-related tasks reliably and token-efficiently

---

## Installation & Setup

```bash
pip install cobrain
cd <vault-path>
brn init  #  creates vault structure below
```

Multiple vaults (per project, personal/work) supported with distinct vault-local config.

---

## Vault

```
vault/
├── vault.html            # standalone shareable page with search/filters for human user
├── topics/               # topic files (.md), source of truth for CLI
├── sources/
│   ├── chats/            # ChatGPT conversations (.md)
│   ├── x/                # X conversations (.yaml)
│   └── ...               # add more for other sources
└── .cobrain/             # app internals, read but never edit directly
    ├── config            # used to detect vault
    ├── vault.yaml        # derived graph of topics, with metadata
    ├── categories.yaml   # customizable topic category colors / titles
    ├── backups/          # rolling backups
    ├── diffs/            # diffs from backups
    └── logs/             # ingest logs
        ├── chatgpt/
        └── x/
```

`vault/` is self-contained and portable.
`vault/sources/`: raw content ingested from external systems (ChatGPT, X, user-provided documents, your own chat with user), users never read this.
`vault/topics/`: curated summaries users read, source of truth for everything.

---

## Agent Responsibilities

1. Ingest sources on demand: Add ChatGPT / X conversations (X charges per post, use responsibly!) and other
2. Create good topics: Synthesize sources into few high-signal, actionable, grep-friendly topics
3. Organize clean graph: Maintain coherent hierarchy, no spam/duplicates/orphans, proper links
4. Find knowledge on demand: Explore graph, search topics, retrieve information for user or task
5. Manage vault autonomously: Health checks, graph and topic quality assessment, custom instructions

Metrics:
- Far fewer topics than sources in mature graph - synthesize, don't spam new
- Clear graph - no ambiguity, duplicates, orphans
- Topics easy to find by id/aliases/title/keywords in body
- 0 warnings in sync and sources
- Backups before meaningful graph changes
- Custom vault management instructions (learnings, user preferences) are actively updated and followed each session in `topics/AGENTS.md` or equivalent

---

## Tasks

Typical session order:
1. Read this skill + custom instructions in `topics/AGENTS.md` or equivalent
2. Ensure good current state:
   - Sync `brn sync --warnings` + fix warnings
   - Inspect graph `brn vault ...`
3. Ingest + read new sources: `brn sources --ingest ...`
4. Update topics:
   - Review graph to decide which topics to update vs. create
   - Backup graph if big changes
   - Update/create topics, bulk-manage frontmatter `brn vault --ids ... [--set ...]`
5. Sync again + fix warnings
6. Show state to user: `brn show`
7. Update custom instructions in `topics/AGENTS.md` if needed

### Ingest Sources

#### ChatGPT
```bash
brn sources --ingest chatgpt --paths path/to/conversations.json  # first big ingest
brn sources --ingest chatgpt --paths f1.json f2.json --since 2026-01-01  # incremental
brn sources --ingest chatgpt --paths f.json --titles "ML,Python"  # specific conversations
```

#### X
```bash
# Authorization (first time)
brn sources --ingest x --own
brn sources --ingest x --own --authorization-code CODE
# First ingest, ask user how far back to go (id or count)
brn sources --ingest x --own --since-id <id>  # oldest post (exclusive)
brn sources --ingest x --bookmarks --count 100
brn sources --ingest x --likes --count 500
# Regular catch-up fetch of all new posts since last fetch
brn sources --ingest x --bookmarks --new
# When user wants to fetch specific range
brn sources --ingest x --own --since-id <id> --until-id <id>  # oldest post (exclusive)
# When user shares one-off posts via url
brn sources --ingest x --ids <post-id>,<url>,<xurl>  # skips posts that are already in storage
```

Notes:
- X posts stored in `sources/x/` as coherent conversation trees with rich context. Filename format: `<original_post_author>_<original_post_id>.yaml`. Do NOT modify conversation structure.
- X API Billing (at the time of writing):
  - Charges per (uncached) post/bookmark retrieved.
  - Use owner's credits responsibly. When scope of ingest is not clear, ask user and add appropriate filters.
  - X caches retrieved posts for 24h, doesn't charge twice. If needed, retry immediately.
  - When building conversation trees, CLI prefers posts in local storage to save credits.
- Flags `--since-id` and `--until-id` exclude boundary posts.

X Prerequisites (at the time of writing):
1. Create X Developer App at https://console.x.com
   - Permissions: Read
   - Type: Web App, Automated App, or Bot
   - Callback URI: http://127.0.0.1
2. Ensure sufficient X API credits
3. Save OAuth 2 credentials in `vault/.cobrain/config`:
   ```
   x_oauth2_client_id=$X_OAUTH2_CLIENT_ID
   x_oauth2_client_secret=$X_OAUTH2_CLIENT_SECRET
   ```
   Set directly or via env variables.
4. OAuth flow on first ingest: agent gives output URL to user -> user opens/authorizes and provides new URL/code to agent (expires in 30s!) -> agent immediately re-runs ingest with `--authorization-code CODE` -> done, tokens auto-refresh.

Guide user through setup on first X ingest.

#### Other sources

Read non-integrated sources (webpage, file, chat) directly and choose:
1. Generate markdown recap in `vault/sources/` - to preserve full details for info-dense sources
2. Copy file/shortcut for easy access
3. Skip `vault/sources`, update/create topic directly + set as `source` in frontmatter - when extra effort is not worth it

#### Managing sources

Organize each source with subfolders to help your workflow. Examples:
- Move X conversations with no value to topics to `sources/x/junk/` to avoid reading (wastes tokens, pollutes context) in next agent session
- Move ingested but unprocessed ChatGPT chats to `souces/chats/pending/` or similar, so that unfinished state isn't lost in translation between agent sessions
- Find and update any old source filepath in topics frontmatter after you move the file.
- Note unfinished work for the next agent/session in `topics/AGENTS.md` or equivalent. Example: "Process `sources/x/pending/` into topics."


---

### Discover Graph

Before adding new content, understand current graph with token-efficient `brn vault` traversal:

```bash
brn vault  # all topics, minimal fields
brn vault --ids a,b --full+  # specific topics, all fields
brn vault --from <topic> --depth 2  # discover subtree under topic
brn vault --from <a> --to <b>  # path between topics via parents
brn vault --block  # human-friendly output for user to view directly
```

Use `ls topics/` and `grep` to search by content when CLI insufficient. Use `head` (not CLI) for quick single-topic metadata - first 10 lines of frontmatter include everything except sources.

---

### Create/Update Topics

Topic Template (markdown with YAML frontmatter):

```yaml
---
id: <unique-id>  # immutable after creation
title: <Topic Title>  # proper full title
aliases: <alternative-names>  # for search
created_at: <YYYY-MM-DD>  # ISO date
updated_at: <YYYY-MM-DD>
category: <category>  # for classification, search, color-coding
parent: <parent-topic-id>  # required unless root
related: [<related-topic-ids>]
sources:  # source URLs/paths
  - <source-url-or-path>
---
# <Topic Title>
## Overview
Content here...
```

Guidelines:
- Grep-friendly: use canonical keywords
- Inspectable: starts with short overview of its full contents
- Actionable: information with high probability of future use
- Educational: captures new knowledge on the topic
- Concrete: data points and figures, formulas, specific cases
- Noise-free: has high value density, no noise from original sources
- Multiple sources per topic, not 1:1 (spammy)

Before creating: search (`brn vault`, grep) -> check aliases/category/keywords for overlaps -> assess graph structure fit -> decide create vs update (update if same domain/parent, create if too large/distinct concept/needs different parent)

Creating:
1. Write file to `vault/topics/<id>.md` using `cat > topics/<id>.md`.
2. Topic ID is immutable after creation - never change it.

Updating:
1. Read existing topic metadata with `head topics/<id>.md`
2. Read full content via `cat topics/<id>.md`
3. Edit file directly
4. Use token-efficient `brn vault --ids <id> --set parent=<parent> category=<cat>` to set metadata for multiple topics in bulk, and/or skipping file reads.
5. Update `updated_at` in frontmatter
6. Run `brn sync` to reflect changes in graph

After creating/updating:
1. Update related topics: add new topic to their related lists
2. Run `brn sync --warnings` to update `vault.yaml` graph, troubleshoot flagged issues.

Deleting: Use `rm topics/<id>.md` then run `brn sync` to update graph.

---

### Show State/Progress to User

Visualization:
```bash
brn show  # Build vault.html and open in browser
```

Builds vault.html with D3js graph. Users search, filter by date, open topics (in browser), multi-select to copy IDs (to refer agent). Infer progress over time via `.cobrain/backup/` + `.cobrain/diffs/`. Summarize new topics, growth direction, category distribution etc.

---

### Find Information

1. Explore graph: `brn vault --from <topic> --depth N` (token-efficient for traversal)
2. Search files: `grep "keyword" topics/*.md` (use for content search)
3. List topics: `ls topics/` (flat list, e.g. to sort)
4. View topic:
   - `head topics/<id>.md` for metadata only (returns ~10 lines, no sources)
   - `head -n 30 topics/<id>.md` for metadata + sources
   - `cat topics/<id>.md` for full content (CLI doesn't return body)

When to use shell vs CLI:
- Metadata only: use `head` (simpler, frontmatter designed for this)
- Need sources in metadata: use `head -n 30` or `brn vault --ids <id> --full+`
- Multiple topics: use `brn vault --ids a,b` (token-efficient vs multiple head calls)
- Graph traversal: use `brn vault --from <id> --depth N` (token-efficient vs vault.yaml)
- Full body content: use `cat` (CLI doesn't return body)

---

### f. Maintenance

```bash
brn sync --warnings  # missing/duplicate id, no parent, frontmatter not at top, empty body
brn sources --warnings  # orphan sources
```

Run `--warnings` when notice warnings >0. Also manually check:
- Active vs stale topics
- Distribution of sources per topic (find missed updates or bad structure)
- Category balance

Run `brn backup` to:
- Save graph snapshots before large changes
- Generate diffs for progress tracking
- Back up and restore customized category colors: copy backup to `.cobrain/categories.yaml`.
- IMPORTANT: topic/source content not covered, use Git for proper versioning!


---

## CLI Reference

```bash
brn version                        # show version
brn init                           # initialize vault in current directory
brn sync [--warnings]              # build graph from files + show warnings
brn show                           # build and open vault.html in browser
brn vault [--ids <ids>] [--minimal | --full | --full+] [--flow | --block]  # get graph as YAML (select ids, topic metadata fields, YAML format)
brn vault --ids <ids> --set field=value...  # update topic frontmatter + sync
brn vault --from <id> [--depth N]  # subtree
brn vault --from <id> --to <id2>   # shortest path (parent links only)
brn sources [--warnings]           # view source stats + warnings
brn sources --ingest chatgpt --paths <path...> [--since <dt>] [--until <dt>] [--titles <titles]>  # ingest ChatGPT conversations.json
brn sources --ingest x --ids <post_ids>  # ingest X posts by ID/URL/xurl
brn sources --ingest x --own [--count <N> | --new | --since-id <id> --until-id <id>]  # fetch own posts (default 10, count, all new until hit existing, or target range)
brn sources --ingest x --own --authorization-code <code>  # first-time X auth
brn sources --ingest x --likes [--count <N> | --new]  # ingest liked posts
brn sources --ingest x --bookmarks [--count <N> | --new]  # ingest bookmarked posts
brn backup                         # copy vault.yaml + categories.yaml (up to 20)
```

---

## Troubleshooting

### Vault Stale

Direct file edits not reflected in vault.yaml. Run `brn sync` before reads.

### Issues in `sync --warnings`

Solve `brn sync --warnings` by fixing frontmatter (`brn vault --ids <ids> --set` or file edits) or body. Use `brn vault` commands to decide on appropriate frontmatter.

### Catch-up X ingest stops too early

If user removes like/bookmark and later re-likes/re-bookmarks the same post, `--new` will find this post in storage and stop catch-up fetch too early (false-positive).

If only a few are skipped: find missing IDs, ingest individually with `brn sources --ingest x --ids <id>`
If too many are skipped:
1. Check logs in .cobrain/logs/x/ for last good ingest
2. Collect target_ids after that point
3. Delete files in sources/x/ containing those IDs
Get all X post IDs:
```bash
grep -roh '/status/[0-9]*' sources/x/ | sed 's|/status/||' | sort -u
```
4. Re-ingest with `--new`

### Debugging

Check .cobrain/ directory:
- vault.yaml: current graph state
- backups/: snapshots of past states
- diffs/: change history based on backups
- logs/: ingest logs

To review code or customize behavior, find repo at https://github.com/igoakulov/cobrain
