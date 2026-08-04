# CLAUDE.md

Guidance for AI assistants (Claude Code and similar) working in this repository.

## What this repository is

A small automation repository. Its only running code is a scheduled reminder bot
that reads tasks from a Notion database and posts the ones with an approaching
deadline to Slack. Everything runs on GitHub Actions — there is no server, no
build step, and no application to start locally.

The repository also stores a marketing seminar deck
(`GROWTHCAMP_第1回_マーケティングとは.pptx`). It is unrelated to the code; treat
it as a binary document, not a source file.

## Layout

```
.
├── .github/workflows/reminder.yml   # Daily schedule + manual trigger for the bot
├── notion_reminder.py               # The entire bot: Notion query → Slack post
├── README.md                        # Placeholder, effectively empty
└── GROWTHCAMP_第1回_マーケティングとは.pptx   # Unrelated seminar deck (binary)
```

## How the bot works

`notion_reminder.py` runs top to bottom under `if __name__ == "__main__":` and
has two functions:

- `get_upcoming_tasks(days=3)` — POSTs to the Notion
  `/v1/databases/{id}/query` endpoint filtering on `期限日` (due date)
  `on_or_before` today + `days`, then reads `名前` (title) and `期限日` from each
  result. Returns a list of preformatted Japanese strings.
- `notify_slack(tasks)` — returns early when the list is empty (no "nothing due"
  message is ever sent), otherwise POSTs a bullet list to the Slack incoming
  webhook.

Both calls use `raise_for_status()`, so an API error fails the workflow run
loudly rather than passing silently. Keep that behavior when editing.

### Notion schema coupling

The property names `期限日` and `名前` are hard-coded, as is the shape of the
Notion response (`properties["名前"]["title"][0]["plain_text"]`). Renaming a
property in Notion, or a row with an empty title or no due date, raises a
`KeyError`/`IndexError`. If you change the database schema assumptions, change
them in both the filter and the extraction loop.

The Notion API version is pinned to `2022-06-28` in the request headers. Do not
bump it casually — property payload shapes differ between versions.

## Configuration

All configuration is via environment variables, supplied in CI from repository
secrets. There is no `.env` file and no config module.

| Variable | Purpose |
| --- | --- |
| `NOTION_TOKEN` | Notion integration token (sent as `Bearer`) |
| `NOTION_DATABASE_ID` | ID of the task database to query |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook to post to |

Never hard-code these values, log them, echo them in a workflow step, or commit
them. Read new configuration with `os.getenv` and wire it through
`.github/workflows/reminder.yml`'s `env:` block, adding the matching repository
secret.

## Running and testing

There is no test suite, linter, or CI check beyond the scheduled job itself.

Locally:

```bash
pip install requests
NOTION_TOKEN=... NOTION_DATABASE_ID=... SLACK_WEBHOOK_URL=... python notion_reminder.py
```

Running it for real posts to Slack. When verifying a change without wanting to
notify anyone, call `get_upcoming_tasks()` on its own from a REPL or a scratch
script rather than running the module.

In CI, use the workflow's `workflow_dispatch` trigger to run on demand from the
Actions tab instead of waiting for the schedule.

## Dependencies

`requests` only, and it is not declared anywhere — the workflow installs it with
a bare `pip install requests`. If you add a dependency, add it to that step (or
introduce a `requirements.txt` and switch the step to `pip install -r`), because
nothing else will install it.

## Schedule

`cron: '0 0 * * *'` in UTC, i.e. 09:00 JST daily. The inline comment on that line
is confused leftover text; the schedule itself is correct for a 9 AM JST
reminder. Adjust the cron in UTC when changing the time.

## Conventions

- Comments, Slack output, and Notion property names are Japanese; code
  identifiers are English. Match that split.
- The script is deliberately flat — plain module-level constants, no classes, no
  argument parsing, no logging framework. Prefer keeping it that way over
  introducing structure a single scheduled script does not need.
- Standard library plus `requests`; avoid pulling in an SDK for what is two HTTP
  calls.

## Known rough edges

Worth knowing before you touch the file; fix them if a task calls for it, but
they are not urgent on their own.

- `datetime.utcnow()` is deprecated from Python 3.12. The workflow pins
  `python-version: '3.x'`, so a future runner default could start emitting a
  `DeprecationWarning`. `datetime.now(timezone.utc)` is the replacement.
- Dates are computed in UTC while the audience is on JST, so "3 days out" is off
  by the timezone offset near midnight.
- The Notion query has no pagination (`has_more` is ignored) and no filter on
  completion status, so long-overdue and finished tasks are included and results
  cap at Notion's default page size of 100.
- `README.md` does not describe the project.

## Git workflow

Default branch is `main`. Work on a feature branch and push with
`git push -u origin <branch>`. Do not open a pull request unless asked.
Never commit the Notion token, database ID, or Slack webhook URL.
