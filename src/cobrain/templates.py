AGENTS_CONTENT = """# Cobrain Guide For Agents

Cobrain CLI helps AI agents gather, organize and visualize owner's knowledge in a local vault: files (topics, sources) + graph (structured metadata).

- Vault locally stores and organizes knowledge, tracks learning, and creates persistent shared context between owner/user/agent for collaboration and decisions
- Agent manages vault autonomously
- Cobrain CLI performs deterministic tasks and helps AI agent perform vault-related tasks reliably and token-efficiently

Repo: https://github.com/igoakulov/cobrain/
Agent skill: https://github.com/igoakulov/cobrain/blob/main/skills/cobrain-vault/SKILL.md

## Agent Responsibilities

1. Ingest sources on demand: Add ChatGPT / X conversations (X charges per post, use responsibly!) and other
2. Create good topics: Synthesize sources into few high-signal, actionable, grep-friendly topics
3. Organize clean graph: Maintain coherent hierarchy, no orphans, no duplicates, proper parent-child and related links
4. Find knowledge on demand: Explore graph, search topics, retrieve information for user or for context in other tasks
5. Manage vault autonomously: Health checks, graph and topic quality assessment, custom instructions

## Indicators of Good Performance

- Far fewer topics than sources (in a mature graph) - sources are synthesized and organized into as few topics as reasonable
- Clear unambiguous graph with sufficient links and no repetition
- Topics are easy to locate by id/aliases, title or obvious keywords in body
- 0 --warnings in sync and sources
- Backups before meaningful graph changes

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

## User Preferences

Add user-specific preferences like naming convention, vocabulary and more here.
Example: Unrelated themes should exist as independent (disconnected) topic subtrees with distinct roots.

## Agent Learnings

Document custom rules learned over time that affect vault management here.
Example: "From X, only ingest --bookmarks and --ids. Owner never intends likes or own posts as sources for the vault."

## Unfinished work
Note unfinished work for the next agent/session.
Example: "Process `sources/x/pending/` into topics."
"""
