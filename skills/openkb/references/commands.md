# OpenKB CLI reference

Read commands the skill calls on. Write commands are listed at the
bottom — the agent MUST NOT run them autonomously.

## `openkb status`

KB overview. First line carries the absolute path of the active KB
— parse it before any file read:

```
$ openkb status
Knowledge base: /path/to/kb
Knowledge Base Status:
  ...directory counts and timestamps...
```

Resolution: walks up from cwd, then falls back to `openkb use`'s
global default. Empty case prints "No knowledge base found. Run
`openkb init` first." — stop and tell the user; don't try to read.

## `openkb list` (deprecated)

Documents + concepts/summaries/entities/reports lists, no briefs or
`--json`. Prefer `list-taxonomy`/`list-documents` below — kept for
existing scripts. `Type` is mapped via `_TYPE_DISPLAY_MAP`: long PDFs
show as `pageindex`, everything else as `short` (the raw file
extension is internal and not exposed). `Pages` only populated for
long PDFs.

```
$ openkb list
Documents (N):
  Name              Type        Pages
  paper.pdf         pageindex   42
  notes.md          short
Summaries (N):
  - paper
Concepts (N):
  - attention
```

## `openkb list-taxonomy [--kind concept|entity] [--json]`

Persisted concept/entity pages with one-line briefs — semantic
browsing, not keyword search. Never includes not-yet-paged pending
candidates. `--json` gives `[{kind, slug, path, brief, type}, ...]`.

## `openkb list-documents [--kind summary|exploration] [--json]`

Same shape as `list-taxonomy`, for summaries (one per ingested
document) and explorations (saved `query --save` answers — `brief` is
the originally-asked question). `--json` gives `[{kind, slug, path,
brief}, ...]`.

## `openkb search "<term>" [--scope briefs,summaries,sources,explorations] [--json]`

Tiered BM25 keyword search — never covers concepts/entities (use
`list-taxonomy` for those). Each tier is scored independently; a
`sources` hit may carry a `[line N]`/`[page N]` locator naming the
exact spot to read next. `--json` gives `{tier: [{path, title, score,
snippet, locator}, ...], ...}`.

## `openkb query "<question>"`

Full RAG pipeline — costs an LLM call inside openkb. Use only when
no obvious slug matches and direct reads can't answer. Returns
free-form answer text plus cited `[[concepts/...]]` / `[[summaries/...]]`
paths. Add `--save` to persist to `wiki/explorations/<slug>.md` —
only when the user asks for it.

## Read-only commands the skill should NOT call

- `openkb chat` — interactive REPL
- `openkb watch` — daemon
- `openkb lint` — health-check report (run only if the user
  explicitly asks about wiki health)

## Write commands — MUST NOT run autonomously

These mutate the user's knowledge base. Suggest with a one-line
description of what they do; let the user run them:

- `openkb add <path>` — ingest a document (LLM cost, modifies wiki)
- `openkb remove <doc>` — destructive removal
- `openkb lint --fix` — auto-edits wiki pages
- `openkb init` — one-time KB setup
- `openkb use <path>` — set the default KB

Also: never directly `Edit`/`Write` any file under `<kb>/wiki/` or
`<kb>/.openkb/`. That's the user's curated content (and openkb's
internal state) — the agent must not patch it directly.
