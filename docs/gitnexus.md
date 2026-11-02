# GitNexus — code intelligence

GitNexus indexes this repository into a **local knowledge graph** (symbols, call
relationships, execution flows) so an agent can answer "what calls this?", "what
breaks if I change it?" and "which flow goes through here?" without reading the
whole codebase.

It is a **development tool**. Nothing in the runtime, the API, the containers or
CI depends on it.

## Why we use it

`grep` finds text; it does not know that `search_places` is called by two use
cases and one route. On a DDD layout (`api → application → domain ←
infrastructure`) that difference matters: renaming or changing a domain port
silently leaves callers behind.

Concretely, the rules in `AGENTS.md` are:
- **impact before editing** a symbol — callers, execution flows, risk verdict;
- **`detect_changes` before committing** — maps the diff hunks to the symbols and
  flows it touches;
- `context` / `query` for read-only "how does X work?" questions.

Cost: one index per clone, no network, no third-party service, no account.

## How it works

- `analyze` parses the tree (Python backend, TypeScript web) and writes a graph
  into `.gitnexus/` — the graph store (`lbug`, ~55 MB here), `meta.json`, and
  parse caches.
- `.gitnexus/` is **not committed**: it is listed in `.git/info/exclude`, so it is
  per-clone and must be rebuilt on a fresh checkout. A missing index is not an
  error, it just means "no graph yet".
- The graph is a **snapshot**. It goes stale as code changes; `status` shows the
  indexed commit, `analyze --index-only` refreshes it without reinstalling.
- Sizes and counts (symbols, relationships, flows) are informational — they move
  with every analysis.

```bash
# first time in a fresh clone
bunx gitnexus@latest analyze          # bootstraps .gitnexus/ and builds the graph
# afterwards
node .gitnexus/run.cjs analyze --index-only
node .gitnexus/run.cjs status
```

## Everyday CLI

| Question | Command |
| --- | --- |
| What breaks if I change `X`? | `node .gitnexus/run.cjs impact "X" --direction upstream --repo .` |
| Who calls `X` / what is it? | `node .gitnexus/run.cjs context "X"` |
| Which flow handles concept `Y`? | `node .gitnexus/run.cjs query "Y"` |
| What does my diff touch? | `node .gitnexus/run.cjs detect-changes --scope all --repo .` |
| Structural sanity (cycles, orphans) | `node .gitnexus/run.cjs check --repo .` |
| Drop the index | `node .gitnexus/run.cjs clean` |

`risk: UNKNOWN` is **not** a clearance: it means the graph could not resolve the
callers (dynamic dispatch, property access). Confirm with a text search before
deleting or renaming anything.

## Running the MCP server

The MCP server is what exposes `impact`, `context`, `query`, `detect_changes`,
`explain` and the `gitnexus://repo/letmegetin/…` resources to the agent.

```bash
# wire it into the editors GitNexus detects (OpenCode, Claude Code, Cursor, …)
node .gitnexus/run.cjs setup

# or only OpenCode
node .gitnexus/run.cjs setup --coding-agent opencode

# run it by hand
node .gitnexus/run.cjs mcp          # stdio
node .gitnexus/run.cjs mcp --http   # Streamable HTTP at POST /mcp
```

Manual entry, if you prefer editing the config yourself
(`~/.config/opencode/opencode.jsonc`) — point it at the installed binary, not the
per-repo `.gitnexus/run.cjs`, so it works in every checkout:

```jsonc
{
  "mcp": {
    "gitnexus": {
      "type": "local",
      "command": ["/path/to/gitnexus", "mcp"]
    }
  }
}
```

Restart the agent afterwards; the tools appear under the `gitnexus` namespace.
`node .gitnexus/run.cjs doctor` reports the runtime and embedding configuration if
something does not start.

## When to ignore it

Literals, string and config searches, YAML/Markdown edits: use text search. The
graph is for **symbols and flows**. If `impact` returns `UNKNOWN` or the index is
stale, grep is the honest fallback — say so instead of pretending the graph
answered.
