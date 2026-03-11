# Tool Usage Notes

companio delegates all tool execution to Claude CLI (`claude -p`). Claude CLI's built-in tools (Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, etc.) are available automatically — no configuration required.

## companio-Specific Tools

Two additional tools are injected by companio:

### `message`
- Sends a message to a specific chat channel (e.g., Telegram)
- Use this to proactively notify the user, such as from cron tasks
- Requires a channel name and chat ID

### `cron`
- Schedules reminders and recurring tasks, managed by companio's CronService
- Three modes: reminder (direct message), task (agent executes), one-time (auto-deletes after firing)
- Scheduling options: `every_seconds`, `cron_expr` (with optional `tz`), `at` (ISO datetime)
- Refer to the cron skill for detailed usage

## Workspace Files

The following files in the workspace directory are managed by companio:
- `MEMORY.md` — persistent notes across sessions
- `HISTORY.md` — conversation history log
- `skills/` — skill definitions loaded into the system prompt

## Security

- **Secret filtering**: companio strips sensitive environment variables (API keys, tokens, passwords) before spawning Claude CLI, and also filters secrets from Claude CLI's output
- companio does not enforce workspace path restrictions — Claude CLI manages its own tool permissions
