# Deployment

## Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --port 8000
```

## Docker

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/api/health
```

The container runs as a non-root user with a read-only root filesystem; SQLite files live in the `lifecanvas-data` volume.

## Production checklist

- Terminate TLS in front of the app and set `LIFECANVAS_SECURE_COOKIES=1`.
- Set `LIFECANVAS_ALLOWED_HOSTS` to your hostname.
- Run a single worker: checkpoints, rate limits and run tasks are per process.
- Back up the data volume (`lifecanvas.sqlite3`, `checkpoints.sqlite3`).
- Add provider keys in `.env`, then use App connections → Verify all.
- Disable response buffering for `/api/runs/*/stream` on your proxy.

## Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `LIFECANVAS_DB` | `data/lifecanvas.sqlite3` | Application database |
| `LIFECANVAS_CHECKPOINTS` | `data/checkpoints.sqlite3` | LangGraph checkpoints |
| `LIFECANVAS_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hostnames the app answers to |
| `LIFECANVAS_ALLOWED_ORIGINS` | empty | Extra origins allowed to make state-changing requests |
| `LIFECANVAS_SECURE_COOKIES` | `0` | Set to `1` behind HTTPS |
| `LIFECANVAS_SESSION_TTL` | 14 days (seconds) | Session lifetime |
| `LIFECANVAS_APPROVAL_TTL` | `900` | Seconds an approval stays valid |
| `LIFECANVAS_RATE_LIMIT` | `240` | Requests per client per minute |
| `LIFECANVAS_ROUTING` | `balanced` | Model routing: `balanced`, `quality`, `cost`, `latency` |
| `LIFECANVAS_MAX_REVISIONS` | `1` | Critic-driven revision rounds per run |
| `LIFECANVAS_TOOL_DEADLINE` | `14` | Seconds allowed per tool call |
| `AMADEUS_ENV` | test | Set to `production` to book real flights |

Provider and model keys are listed in [.env.example](../.env.example) and explained in [Integrations](INTEGRATIONS.md). The app starts with none of them; each provider then reports "configuration required".

## Reverse proxy

Example for nginx. The stream route must not be buffered.

```nginx
server {
    listen 443 ssl;
    server_name life.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
    location ~ ^/api/runs/.+/stream$ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_read_timeout 1h;
    }
}
```

Set `LIFECANVAS_ALLOWED_HOSTS=life.example.com` and `LIFECANVAS_SECURE_COOKIES=1`.

## Backup and restore

Both SQLite files live in the data directory (the `lifecanvas-data` volume in Docker).

```bash
sqlite3 data/lifecanvas.sqlite3 ".backup 'backup/lifecanvas.sqlite3'"
sqlite3 data/checkpoints.sqlite3 ".backup 'backup/checkpoints.sqlite3'"
```

To restore, stop the app, put both files back and start it. On start, any action that was mid-send is marked `unknown` and interrupted runs can be resumed from their last checkpoint.

## Upgrades

Tables are created if missing at start. There is no migration tool yet, so back up before upgrading and check the release notes for schema changes.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| 400 on every request, "Invalid host header" | Add your hostname to `LIFECANVAS_ALLOWED_HOSTS` |
| Sign-in works but the next request is 401 | Cookies are marked secure on plain HTTP; serve over HTTPS or unset `LIFECANVAS_SECURE_COOKIES` locally |
| 403 on every POST | The `X-Requested-With: lifecanvas` header or a same-origin `Origin` is missing |
| The run view stalls then jumps | The proxy is buffering the stream; see above |
| A provider shows "configuration required" | Its key is not set; add it and use App connections → Verify |
| A provider shows "configured, unverified" | The key is present but no probe has succeeded yet; press Verify |
| Answers are templated rather than written | No language-model key is set; the deterministic fallback is in use |
| Runs disappear after scaling out | More than one worker is not supported; use a single process |
