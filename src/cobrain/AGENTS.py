AGENTS_CONTENT = """# Cobrain Guide For Agents

Cobrain CLI helps AI agents gather, organize and visualize owner's knowledge in a local vault: files (topics, sources) + graph (structured metadata).

- Vault locally stores and organizes knowledge, tracks learning, and creates persistent shared context between owner/user/agent for collaboration and decisions
- Agent manages vault autonomously
- Cobrain CLI performs deterministic tasks and helps AI agent perform vault-related tasks reliably and token-efficiently

Repo: https://github.com/igoakulov/cobrain/
Agent skill: https://github.com/igoakulov/cobrain/blob/main/skills/cobrain-vault/SKILL.md

## Agent Responsibilities

Manager:
1. Ingest sources on demand: Add ChatGPT / X conversations (X charges per post, use responsibly!) and other
2. Organize clean graph: decide structure (create vs update, placement, hierarchy), no spam/duplicates/orphans, proper links
3. Find knowledge on demand: Explore graph, search topics, retrieve information for user or task
4. Manage vault autonomously: Health checks, graph and topic quality assessment, custom instructions
5. Manage sub-agents: brief, delegate, verify decisions against actual source content
6. Accountable for quality of final result

Sub-agent (Writer):
1. Read assigned sources
2. Identify signal vs junk
3. Synthesize content into topics: high-signal, actionable, grep-friendly
4. Propose new topics (id, title, hub, rationale)
5. Report updates + junk recs + quality issues
Constraints: no editing/moving/deleting source files (read only), no creating topics (propose only), no writing to AGENTS.md (report back only)

## Metrics

- Far fewer topics than sources in mature graph - synthesize, don't spam new
- Clear graph - no ambiguity, duplicates, orphans
- Topics easy to find by id/aliases/title/keywords in body
- 0 warnings in sync and sources
- Backups before meaningful graph changes
- Custom instructions (learnings, user preferences) are actively updated and followed each session in `vault/AGENTS.md` or equivalent

## Files as Source of Truth

Topic markdown files determine vault.yaml graph state.
vault.yaml (in .cobrain/) is a derived snapshot for most CLI operations.

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

## Custom instructions

Contains custom instructions, workflow, user preferences, and agent learnings that affect how vault is managed.

- Files in `junk/` ignored from `brn sources --warnings` by default (`warnings_ignored_sources=/junk/` in `.cobrain/config`)
- Hubs optional — for grouping related topics. If used, no content duplication between hub and children
- IDs short, searchable (displayed on graph, not titles)
- No `related:` between siblings — shared parent implies relationship. Cross-link non-siblings only
- Sources split across topics if mixed content

Working at scale (manager + sub-agents):
- Delegate to sub-agents, distinct sets, no overlap
- Sub-agent: reads sources, identifies signal vs junk, synthesizes, proposes new topics
- Manager: reviews proposals vs full graph, creates empty shells (prevents dups), assigns back, moves junk sources
- Sub-agent: fills assigned topics, reports updates + junk recs
- Manager: verifies, asks fixes if needed
- One topic per batch (no merge conflicts)
- Sub-agent constraints: no editing/moving/deleting source files (read only), no creating topics (propose only), no writing to AGENTS.md (report back only)
- Before delegating: `brn sources --warnings` — check used sources
- Resume sub-agents (if harness supports) to preserve context

Add user-specific preferences and learnings here.
Example: "From X, only ingest --bookmarks and --ids. Owner never intends likes or own posts as sources for the vault."

## Unfinished work

Handoff only — items next agent needs to solve/prevent a specific problem:
- In-progress, unresolved, next steps
- No completion reports, no session summaries (work lives in topics)
Update Custom instructions above if learned something new.
Example: "Process `sources/x/pending/` into topics."
"""
