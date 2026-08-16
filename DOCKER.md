# Running the SGW Resilience Platform with Docker

One command runs everything — backend, frontend, database, and the optional AI
phrasing. Nothing needs to be installed on the host except Docker.

```bash
docker compose up --build
```

Then open **http://localhost:3000**.

## Signing in

- **First run:** an admin account is created automatically —
  `admin@sgw.local` / `change-me-first-run` (override with `BOOTSTRAP_ADMIN_EMAIL`
  and `BOOTSTRAP_ADMIN_PASSWORD`; 12-character minimum). The bootstrap applies only
  while no account exists, then the variables are ignored forever.
- Anyone else can press **Create one** on the sign-in screen — self-service sign-up
  creates **operator** accounts (read rankings, record decisions; loading a storm
  needs an admin).
- Further admins: `docker compose exec backend python -m app.cli create-user
  --name "Ops Manager" --email ops@example.com --role admin` (prompts for a password).

## First storm

Sign in as an admin, press **Use sample storm data** on the Load screen — the bundled
220-asset demo dataset loads through the same parse path as a real upload — then
**Finish and continue**. Or drop your own five prepared files
(`manifest.json` + `assets/maintenance/weather/outages.csv`) on the same screen.

## The AI phrasing (optional by design)

The ranking, the reasons and every screen work with the model off — that is ADR-009's
rule, not a degraded mode. To turn phrasing on, put this in a `.env` next to
`docker-compose.yml` and restart:

```
LLM_ENABLED=true
OPENAI_API_KEY=sk-...
```

Every model output is verified in code against the platform's own figures before it
is shown; the key never leaves the backend container.

## Data

The database is one SQLite file on the named volume `sgw-data` — storms, rankings and
the append-only decision record survive restarts. `docker compose down -v` erases
everything and the next start bootstraps fresh.

## Ports

Only the frontend is published (`3000`, override with `SGW_PORT=…`). The browser
reaches the API through the frontend's same-origin proxy, exactly as in development —
the backend is not exposed to the host network.

`APP_ENV=development` keeps the session cookie usable over plain http. If you put
this behind TLS for real users, set `APP_ENV=production` so the cookie requires it.
