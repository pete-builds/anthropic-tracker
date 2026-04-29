# Anthropic Hiring Tracker

Daily snapshots of Anthropic's open job listings via the Greenhouse public API. Tracks adds, removals, salary ranges, and department-level shifts. Ships with a CLI, a Rich terminal dashboard, and a web dashboard (FastAPI + htmx + Chart.js).

Built to monitor public hiring signals: which teams are growing, which roles disappeared, what compensation bands look like over time. No auth, no scraping, no PII. Pure public-API tracking.

## What it does

- **Daily fetch** of the full job list and per-job HTML, run from a host cron
- **Delta computation** against the prior snapshot (added / removed / unchanged)
- **Salary parsing** from each job's pay-transparency markup (USD, GBP, EUR; OTE vs base)
- **Alerts** on hiring freeze (>20% week-over-week drop), department surge (>50%), mass removal, new departments
- **SQLite storage** with WAL, foreign keys, and a schema-version table
- **Web dashboard** at `:3710` with auto-refreshing partials (htmx every 60s) and Chart.js trend lines

## Architecture

```
              Greenhouse API
                    │
                    ▼
            ┌───────────────┐
            │  fetcher.py   │ (httpx, retries, throttle)
            └───────┬───────┘
                    │
            ┌───────▼───────┐
            │  parser.py    │ (locations, salary regex + structured)
            └───────┬───────┘
                    │
            ┌───────▼───────┐
            │  delta.py     │ (snapshot diff, upsert, write daily row)
            └───────┬───────┘
                    │
            ┌───────▼───────┐
            │  alerts.py    │ (threshold checks, persist alerts)
            └───────┬───────┘
                    │
                    ▼
              SQLite (WAL)
              ┌───┴───┐
        ┌─────┴─┐   ┌─┴─────────┐
        │  CLI  │   │  Web (FastAPI │
        │       │   │    + htmx)    │
        └───────┘   └───────────────┘
```

Modules are independently testable: `fetcher` hits the network, `parser` is pure, `delta` takes a connection + a list of jobs, `db` owns schema.

## Running it

### Local (dev)

```bash
pip install -e ".[dev]"
tracker --help
tracker fetch --with-salary    # populates ~/.anthropic-tracker/tracker.db
tracker dashboard              # terminal dashboard
tracker summary                # latest snapshot
tracker trends --days 30
tracker alerts
uvicorn anthropic_tracker.web:app --reload   # web dashboard at localhost:8000
```

### Docker (production)

```bash
docker compose up -d web                       # start dashboard on :3710
docker compose run --rm tracker --help         # any CLI command
docker compose run --rm tracker-fetch          # one-off daily fetch
```

Host cron (already wired on nix1):

```cron
# Anthropic hiring tracker - daily fetch at 6am ET (10:00 UTC)
0 10 * * * cd /home/pete/anthropic-tracker && docker compose run --rm tracker fetch --with-salary >> /home/pete/logs/anthropic-tracker.log 2>&1
```

### Tests

```bash
pip install -e ".[dev]"
pytest                          # 56 tests
pytest --cov=anthropic_tracker  # coverage report
ruff check .                    # lint
```

## Schema (12 tables)

| Table | Purpose |
|---|---|
| `jobs` | One row per job (active or historical), with first_seen / removed_date lifecycle |
| `departments`, `offices` | Reference tables, upsert on every fetch |
| `job_locations` | M:N — parsed individual locations from semicolon/pipe-separated raw strings |
| `job_offices`, `job_departments` | M:N joins |
| `compensation` | Salary range per job in cents, currency, comp_type (annual/ote), raw text |
| `daily_snapshots` | One row per fetch day: total, added, removed, departments_json, locations_json, response hash |
| `weekly_metrics` | Rollup (not yet populated) |
| `alerts` | Triggered alerts with severity, message, acknowledged flag |
| `schema_version` | For future migrations |

## Web API

| Endpoint | Returns |
|---|---|
| `GET /` | Full HTML dashboard |
| `GET /healthz` | `{"status": "ok"}` |
| `GET /api/summary` | Latest day totals |
| `GET /api/departments` | Active roles by department |
| `GET /api/locations` | Active roles by location |
| `GET /api/trends?days=30` | Daily totals over N days |
| `GET /api/alerts` | Unacknowledged alerts |
| `GET /api/search?q=engineer` | Title search (comma-separated terms = OR) |
| `GET /api/recent-changes` | Last 10 added + last 10 removed |
| `GET /api/compensation` | Salary ranges by department |
| `GET /partials/{name}` | htmx HTML partials for the dashboard |

## Configuration

Environment:

| Var | Default | Purpose |
|---|---|---|
| `TRACKER_DB` | `~/.anthropic-tracker/tracker.db` | SQLite path |

Config constants in `src/anthropic_tracker/config.py`: API URLs, timeouts, retry policy, alert thresholds.

## Security note

The web dashboard has no auth. It exposes only public data (already on Anthropic's careers page) but should be reachable only over a trusted network (Tailscale, VPN, or behind a reverse proxy with auth). Don't expose port 3710 directly to the public internet.

## License

MIT — see [LICENSE](LICENSE).
