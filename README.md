# SGW Resilience Platform

A storm-response dashboard for a utility company. It loads a prepared storm dataset,
ranks 220 infrastructure assets by risk — with a plain-English reason beside every
rank — and gives dispatchers a worklist where every action lands in a tamper-proof
audit trail.

**It recommends; people decide.** The system never moves a crew, never closes a valve,
and never sends a command anywhere. There is deliberately no code path that could.

> Built as the technical prototype (Deliverable 3) for the **AECOM AI Solution
> Engineer case study**: take an ambiguous business problem, make the assumptions
> explicit, and turn it into a working AI-enabled solution — with the governance to
> match. The full written specification the code was built from lives in [`spec/`](spec/),
> including every assumption, requirement, and change decision.

## Quick start

All you need is Docker:

```bash
docker compose up --build
```

Open **http://localhost:3000**, sign in as `admin@sgw.local` / `change-me-first-run`,
press **Use sample storm data**, then **Finish and continue**. You're looking at a
ranked storm two minutes after cloning. (Details and overrides: [DOCKER.md](DOCKER.md).)

Prefer running it bare? You'll need Python 3.12 and Node 22 — the commands are in
[CLAUDE.md](CLAUDE.md) under *Commands*.

## What it does

Three screens behind a sidebar:

1. **Load storm data** — drop the five prepared files (or use the bundled sample).
   The parser catches seven kinds of real-world data defects — duplicate identities,
   impossible outage counts, stale forecasts — and asks a human to decide the ones
   that need judgment instead of guessing.
2. **Storm Planning** — every asset ranked by risk with the *why* in plain words
   (wind vs. design limit, flood zone, age, condition), top risks up front, a live
   map, and per-asset triage: Accept / Adjust / Dismiss, each one written to the
   decision record.
3. **Dispatch Board** — a repair queue built from the dataset's own outage records,
   worst first. Assign crews, mark restored, dismiss false alarms — every action is
   appended to an audit log the database itself refuses to let anyone edit.

## Where the AI is (and where it isn't)

The **ranking is deterministic** — four weighted factors a human can check by hand.
No black box decides anything.

The AI (an OpenAI model) does exactly one job: it **phrases summaries of numbers the
platform already computed** — a situation brief for leadership, a per-asset
explanation on demand. And every output passes through a **code-level verifier**
before display: any number, place, or claim not present in the platform's own data
blocks the text. If the model is down, slow, or over budget, templated text ships
instead and nothing breaks. `LLM_ENABLED=false` runs the whole product; that's a
design rule, not a degraded mode.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 (React 19), Tailwind CSS v4, shadcn/ui, Leaflet + OpenStreetMap |
| Backend | Python 3.12, FastAPI, raw-SQL migrations |
| Database | SQLite — one file, single writer, constraints live in the schema |
| AI | OpenAI (optional at runtime), guarded by call caps and a monthly cost ceiling |
| Testing | 759 pytest cases, 7 architecture fitness functions, 40 Playwright browser tests — one gate script runs it all (`bash ci/gate.sh`) |

## The dataset

A prepared storm scenario is five files: `manifest.json` plus `assets`, `maintenance`,
`weather`, and `outages` CSVs. The repo bundles a 220-asset demo pack, and the loader
speaks two dialects — the platform's own format and the client-style field names
(`customers_served`, condition words like *good/fair/poor*, per-type design limits) —
so a real utility export loads without translation. Any file it can't read is refused
with the file and reason named, never a blank error.

## Problems this solves (the short list)

- **"Which assets do we protect first?"** — a ranked, explained, auditable list
  instead of tribal knowledge, re-rankable as each forecast update lands.
- **"Who decided that, and when?"** — an append-only decision record enforced by
  database triggers. A correction is a new row; history can't be rewritten.
- **"Can we trust AI-written text in an emergency?"** — only with a verifier in
  code. Politely asking a model not to invent numbers doesn't work; checking every
  claim against the source data does.
- **"What does the data quality actually look like?"** — defects are surfaced and
  resolved by people, on screen, before anyone plans against bad rows.
- **An empty screen never reads as safety** — an asset that can't be scored is shown
  and flagged, never silently dropped to the bottom or off the list.

## Repository map

```
backend/    FastAPI app — api / scoring / loader / store / summary modules
frontend/   Next.js app — views, components, browser tests
spec/       The full specification: requirements, ADRs, tests, change log
scenarios/  The bundled demo dataset
ci/         The gate: tests + fitness functions + trigger check, one script
docker/     Container build files (see DOCKER.md)
```
