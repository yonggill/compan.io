---
name: google-workspace
description: Google Workspace integration via gws CLI — Gmail, Drive, Calendar, Sheets, Docs, Chat, Admin, and more.
---

# Google Workspace (gws CLI)

Interact with Google Workspace services using the `gws` command-line tool.
`gws` dynamically reads Google's Discovery Service at runtime, so it always reflects the latest API without updates.

## Prerequisites

1. Install: `npm install -g @googleworkspace/cli`
2. First-time setup (creates GCP project, enables APIs, logs in): `gws auth setup`
3. Subsequent logins: `gws auth login`
4. To limit scopes: `gws auth login --scopes drive,gmail,calendar`

Credentials are encrypted at rest (AES-256-GCM) in OS keyring.

## Command Structure

**Pattern:** `gws <SERVICE> <RESOURCE> <METHOD> [FLAGS]`

**Do NOT memorize commands.** Use `--help` and `gws schema` to explore:

```
gws --help                              → list all services
gws drive --help                        → list drive resources
gws drive files --help                  → list file actions
gws drive files list --help             → list parameters
gws schema drive.files.list             → view request/response schema
```

**Always explore before executing.** The API surface changes — rely on `--help`, not memory.

## Common Flags

| Flag | Purpose |
|------|---------|
| `--help` | Show available subcommands or parameters |
| `--dry-run` | Preview the API request without sending |
| `--params '{...}'` | Query/path parameters (JSON) |
| `--json '{...}'` | Request body (JSON) |
| `--upload <FILE>` | Multipart file upload |
| `--page-all` | Auto-paginate all results (outputs NDJSON) |
| `--page-limit <N>` | Max pages to fetch (default: 10) |
| `--page-delay <MS>` | Delay between pages (default: 100ms) |

## Explore-First Pattern

```
1. Find the service
   gws calendar --help

2. Find the resource
   gws calendar events --help

3. Check parameters
   gws calendar events list --help

4. Inspect schema if needed
   gws schema calendar.events.list

5. Preview without executing
   gws calendar events list --params '{"calendarId":"primary"}' --dry-run

6. Execute
   gws calendar events list --params '{"calendarId":"primary"}'
```

## Workflow Examples

High-level patterns. Always verify parameters with `--help`.

### Drive — Files

```
gws drive files list --params '{"pageSize":5}'
gws drive files create --json '{"name":"report.pdf"}' --upload ./report.pdf
gws drive files list --params '{"pageSize":100}' --page-all
```

### Gmail — Messages

```
gws gmail users messages list --params '{"userId":"me","maxResults":10}'
gws gmail users messages get --params '{"userId":"me","id":"MESSAGE_ID"}'
```

### Calendar — Events

```
gws calendar events list --params '{"calendarId":"primary","timeMin":"2026-03-09T00:00:00Z","maxResults":10,"orderBy":"startTime","singleEvents":true}'
gws calendar events insert --params '{"calendarId":"primary"}' --json '{"summary":"Meeting","start":{"dateTime":"..."},"end":{"dateTime":"..."}}'
```

### Sheets — Read and write

```
gws sheets spreadsheets values get --params '{"spreadsheetId":"ID","range":"Sheet1!A1:C10"}'
gws sheets spreadsheets values append --params '{"spreadsheetId":"ID","range":"Sheet1!A1","valueInputOption":"USER_ENTERED"}' --json '{"values":[["Name","Score"],["Alice",95]]}'
```

### Chat — Messages

```
gws chat spaces messages create --params '{"parent":"spaces/xyz"}' --json '{"text":"Hello"}' --dry-run
```

## Tips

- **Use `--dry-run` before destructive actions** (delete, send, update)
- **Use `--help` and `gws schema` liberally** — faster than guessing
- **`--page-all`** streams all pages as NDJSON, pipe to `jq` for filtering
- **User ID** — Gmail and Calendar use `"me"` for the authenticated user
- **JSON output** — all responses are structured JSON
- **Scope errors** — re-run `gws auth login --scopes <needed>` to add permissions
- **`accessNotConfigured` (403)** — enable the required API in GCP project (error message includes a link)
