#!/usr/bin/env bash
#
# The gate, as one script — `07-ops/01-deployment/cicd-pipeline.md`, *Local-only alternative*.
#
# CON-006 rules out a hosted platform, and the document says a script that fails fast delivers
# every benefit that matters: the same stages, in the same order, blocking the same merges.
# This is that script. It existed as a shape in the document and as five commands in CLAUDE.md,
# and as nothing anyone could run, so "the gate is green" was a claim assembled by hand each
# time and no two runs had to agree about what it included.
#
# `set -e` is the gate. Without it the script prints ALL GATES PASSED with a stage red behind
# it, which is the failure `fitness-functions.md` exists to prevent, committed by the thing
# meant to enforce it.
#
# TWO STAGES ARE HERE THAT A BLUEPRINT PIPELINE WOULD NOT HAVE, and both are here because
# something in this system can be silently undone:
#
#   Stage FITNESS  — FF-001..FF-007 as their own stage, never folded into the suite. Folding
#                    them in is exactly how FF-002 decays while every feature test stays green.
#   Stage TRIGGERS — after migrate, before deploy. BR-004's only enforcement is two triggers
#                    (ADR-004); a migration can drop one; nothing else notices. Not a schema
#                    inspection: `ci/triggers.py` issues a real UPDATE and requires the refusal.
#
# `ci/evals.py` is here as its own stage too, for the reason `03-tests/01-plan/test-plan.md`
# gives for keeping it out of the test folders: an eval scores a distribution against a floor,
# and forcing it through the test runner produces either a flaky suite or one that asserts
# nothing. It is a gate; it is not a test.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"

if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON="$ROOT/.venv/Scripts/python.exe"
elif [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    echo "no virtualenv at .venv — see CLAUDE.md, Commands" >&2
    exit 1
fi

stage() { printf '\n== %s ==\n' "$1"; }

stage "test        (the suite — NOT the gate on its own)"
"$PYTHON" -m pytest -q

stage "lint        (backend)"
"$PYTHON" -m ruff check backend spec/03-tests/05-executable ci

stage "fitness     (FF-001..FF-007, a separate stage — cicd-pipeline.md stage 4)"
"$PYTHON" ci/fitness.py

stage "evals       (the quality floor — ai-evals.md)"
"$PYTHON" ci/evals.py

stage "triggers    (after migrate, before deploy — cicd-pipeline.md stage 7)"
"$PYTHON" ci/triggers.py

stage "types       (frontend)"
(cd frontend && npx tsc --noEmit)

stage "lint        (frontend)"
(cd frontend && npm run lint)

stage "build       (frontend)"
(cd frontend && npm run build)

stage "browser     (Playwright — real Chromium against both processes, no mocks)"
(cd frontend && npx playwright test)

printf '\nALL GATES PASSED\n'
