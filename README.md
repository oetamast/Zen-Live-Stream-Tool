# ZenStream Tool (Live Stream Tool)

Self-hosted toolkit for scheduling and running live streams to YouTube RTMP/RTMPS targets. The initial release focuses on the runner/data model described in the project brief with a minimal HTTP dashboard bootstrap.

## One-line install & uninstall

After cloning the repo:

- Install + start everything: `./scripts/install.sh`
- Uninstall + wipe data/volumes: `./scripts/uninstall.sh`

The stack uses Docker Compose (PostgreSQL + FastAPI API + runner) and persists content under the `data` directory/volume.

## What ships in v0

- **Core objects** that mirror the brief: assets, destinations, presets, jobs, schedules, sessions, events/FFmpeg log records, and license state persisted in Postgres via SQLModel.
- **Minimal HTTP wizard** served at `/wizard` to remind operators how to activate and change the default password (HTTP only by design).
- **Admin auth** via HTTP Basic using credentials in environment variables. First login requires a password change via `/auth/change-password`.
- **Scheduling guardrails**: loop/crossfade checks, Premium/Ultimate validation on jobs, and open-ended schedule validation.
- **Runner service** that enforces a single-runner lock, ticks on the configured heartbeat, and materializes queued sessions from eligible schedules without deduping.
- **Data folders** provisioned under `/data` for assets/logs (`/data/assets/videos|audios|sfx`).

## Project layout

```
backend/               FastAPI app + SQLModel data layer
backend/app/routers    Feature routers (assets, destinations, presets, jobs, schedules, sessions, license)
runner/                Lightweight runner loop that enforces schedule eligibility and single-runner locking
scripts/               install/uninstall helpers
```

## Environment

Key environment variables are read by the API and runner:

- `DATABASE_URL` (default set by `docker-compose.yml`)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`
- `DATA_DIR` (defaults to `/data` in containers)

## Usage highlights

1. Hit `http://localhost:7575/wizard` to see the bootstrap steps and bootstrap the admin login.
2. Change the admin password via `POST /auth/change-password` (Basic Auth).
3. Issue member licenses in-dashboard with `POST /license/issue`, then activate with `POST /license/activate` using the bound install id/secret; renewals are hourly with outage grace tracked automatically.
4. Monitor member counts across Basic/Premium/Ultimate with `GET /license/metrics` and audit history via `GET /license/activity`.
5. Create assets, destinations, presets, and jobs via the corresponding REST endpoints. Crossfade requires loop, audio replacement needs Premium+, and scenes need Ultimate. License downgrades auto-create job backups you can restore from `POST /jobs/{id}/restore`.
6. Create schedules; open-ended schedules require loop-enabled jobs. The runner converts eligible schedules into queued sessions on every heartbeat.
7. Inspect sessions/events via `GET /sessions`. Export/import non-license configuration via `GET /config/export` and `POST /config/import` (license identity is excluded).

## Updating

Because the stack is containerized, you can refresh to the latest code by pulling the repo and rerunning `./scripts/install.sh` (safe update while streams are stopped; full update requires a restart of containers which may interrupt running streams).

## Uninstall / cleanup

`./scripts/uninstall.sh` stops the stack, removes containers/volumes, and deletes the local `data` folder for a clean slate.
