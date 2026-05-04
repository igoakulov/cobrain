# Cobrain

Cobrain CLI helps AI agents gather, organize and visualize owner's knowledge in a local vault: files (topics, sources) + graph (structured metadata).

- Vault locally stores and organizes knowledge, tracks learning, and creates persistent shared context between owner/user/agent for collaboration and decisions
- Agent manages vault autonomously
- Cobrain CLI performs deterministic tasks and helps AI agent perform vault-related tasks reliably and token-efficiently

![Cobrain screenshot](cobrain.png)

## Installation & Setup

Install agent skill in your harness: [skills/cobrain-vault](skills/cobrain-vault). Agent does the rest.

Alternative:
```bash
pip install cobrain
```

## Vault

```
vault/
├── vault.html            # Visual graph with search/filters for human user
├── topics/               # Topic files (.md), source of truth for CLI
├── sources/
│   ├── chats/            # ChatGPT conversations (.md)
│   ├── x/                # X conversations (.yaml)
│   └── ...               # Add more for other sources
└── .cobrain/             # App internals, read but never edit directly
    ├── vault.yaml        # Derived graph of topics, with metadata
    ├── categories.yaml   # Customizable topic category colors / titles
    ├── backups/          # Rolling backups
    ├── diffs/            # Diffs from backups
    └── logs/             # Ingest logs
        ├── chatgpt/
        └── x/
```

`vault/sources/`: raw content ingested from external systems (ChatGPT, X, user-provided documents, your own chat with user), users never read this.
`vault/topics/`: curated summaries users read, source of truth for everything.

## CLI reference

```bash
brn version                        # show version
brn vault --dir <path>             # initialize new/existing vault, write config
brn sync [--warnings]              # build graph from files + show warnings
brn show                           # build and open vault.html in browser
brn vault [--ids <ids>] [--minimal | --full | --full+] [--flow | --block]  # get graph as YAML (select ids, topic metadata fields, YAML format)
brn vault --ids <ids> --set field=value...   # update topic frontmatter + sync
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

All `--ingest x` commands pull full conversation above the target post, and minimize API credits spent by always checking locally stored posts first.

## Topics

Agent creates `vault/topics/topic.md` with YAML frontmatter, based on sources. Topics are source of truth for everything.

## Sources

X and ChatGPT: integrated, agent ingests with CLI command.
Other sources (webpage, file, chat): agent reads directly.

### X

- Built with XDK (official X SDK), with their affordable [pay-per-use pricing](https://docs.x.com/x-api/getting-started/pricing) and 24h retrieved post caching to save your credits.
- Uses your own app's OAuth2.0 credentials.
- Ingest your bookmarks, likes, posts and replies, or any post by id/url. Official endpoint filters supported as flags.
- CLI automatically builds coherent conversations (one per file) from target post up to original (root) post. Locally stored posts are re-used whenever possible to save your credits. New posts from an existing conversation merge into the same file seamlessly.
- Output: `vault/x/<conversation_author>_<conversation_id>.yaml`.

### ChatGPT

- Request data export from your ChatGPT app and run ingest command on `conversations.json`.
- Filter by dates and title supported as flags.
- Output: `vault/chats/<title>.md`.

## License

MIT
