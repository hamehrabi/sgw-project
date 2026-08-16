"""The fitness-function gate.

A test proves the feature does what was asked. A fitness function proves the **system still
has the shape you decided on**. They are different jobs, they run as different stages, and
folding these into the test suite is how FF-002 decays while every feature test stays green
(`cicd-pipeline.md`, stage 4).

Wired here: **all seven.** FF-003 was the last one and TASK-010 wired it; nothing in this file
says `Not wired yet` any more.

**FF-004 issues a real UPDATE and a real DELETE and requires both to be refused.** Inspecting
the schema for two trigger names is not the same check: a trigger can be present and wrong.

**FF-003 removes and corrupts each source file in turn and drives every screen read against a
live application, with a recorder installed over `open`.** The recorder is shown its own canary
before its silence is believed, and the storm's files are required to be on disk before their
absence from the reads means anything — the two ways this check could pass for want of anything
to test.

    python ci/fitness.py        # exit 0 = the shape held; exit 1 = block the merge
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend"

# `summary` joined with CHG-052, in the same commit that created the directory: a package
# absent from this tuple is a package FF-001 cannot see, so a cycle through it would be
# invisible to the gate that exists to refuse cycles (CHG-010's finding, pre-empted).
MODULES = ("api", "scoring", "loader", "store", "summary")

# ADR-007's numbers. None of them may appear in the frontend: the scoring module is never
# "reimplemented, mirrored, or partially duplicated in the frontend for display purposes"
# (ADR-008). Weights, band boundaries, and the reason-strength thresholds.
SCORING_CONSTANTS = ("0.40", "0.25", "0.20", "0.15", ">= 60", ">= 30")


def imports_of(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def module_graph() -> dict[str, set[str]]:
    graph = {name: set() for name in MODULES}
    for name in MODULES:
        for path in (BACKEND / name).rglob("*.py"):
            for imported in imports_of(path):
                for other in MODULES:
                    if imported.startswith(f"app.{other}") and other != name:
                        graph[name].add(other)
    return graph


def ff_001_no_import_cycle() -> list[str]:
    """No import cycle between the scoring module, the API layer, and the data layer."""
    graph = module_graph()
    cycles = []

    def walk(node, seen):
        for nxt in sorted(graph[node]):
            if nxt in seen:
                cycles.append(" -> ".join([*seen, nxt]))
            else:
                walk(nxt, [*seen, nxt])

    for start in MODULES:
        walk(start, [start])
    return [f"FF-001 import cycle: {c}" for c in sorted(set(cycles))]


def ff_002_scoring_stays_behind_the_api() -> list[str]:
    """(a) `scoring` is imported by `api` and nothing else. (b) no scoring constant in the
    frontend. Restated by CHG-010 — the old form could not fail under ADR-008."""
    failures = []
    graph = module_graph()
    for name in ("store", "loader"):
        if "scoring" in graph[name]:
            failures.append(f"FF-002(a) `{name}` imports `scoring`; only `api` may")

    if FRONTEND.exists():
        sources = [
            p
            for suffix in ("*.ts", "*.tsx")
            for p in FRONTEND.rglob(suffix)
            if "node_modules" not in p.parts and ".next" not in p.parts
        ]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for constant in SCORING_CONSTANTS:
                if constant in text:
                    rel = path.relative_to(ROOT)
                    failures.append(f"FF-002(b) scoring constant {constant!r} in {rel}")
    return failures


def ff_006_seven_defects_caught() -> list[str]:
    """Each of the seven known defects is caught by its own check, against a fixture that
    deliberately contains all seven. Threshold: 7 of 7."""
    sys.path.insert(0, str(ROOT / "backend"))
    fixture = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
    if not fixture.is_dir():
        return ["FF-006 the seven-defect fixture is missing"]

    from app.loader.load import load_scenario

    result = load_scenario({p.name: p.read_bytes() for p in fixture.iterdir()})
    caught = {finding.defect for finding in result.findings}
    missing = sorted({1, 2, 3, 4, 5, 6, 7} - caught)
    if not missing:
        return []
    return [f"FF-006 caught {len(caught)} of 7; no check fired for defect(s) {missing}"]


def ff_007_no_reason_outruns_its_arithmetic() -> list[str]:
    """No displayed reason names a factor absent from its computed input, or asserts a
    strength the arithmetic did not produce (ADR-009 rule 3).

    **Today this guards the computed text; when a model phrases it, the same check guards the
    model.** That is the point of wiring it now rather than with the phrasing layer: the rule
    is "output is validated against its input before display", and the validation should exist
    before there is anything untrusted to validate.
    """
    sys.path.insert(0, str(ROOT / "backend"))
    fixture = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"

    from app.loader.load import load_scenario
    from app.scoring import references
    from app.scoring.rank import rank_assets

    result = load_scenario({p.name: p.read_bytes() for p in fixture.iterdir()})
    failures = []
    for item in rank_assets(result.assets):
        if item.score is None:
            if item.reasons:
                failures.append(f"FF-007 {item.external_ids} is unscored and carries reasons")
            continue
        for reason in item.reasons:
            if reason.factor not in references.WEIGHTS:
                failures.append(f"FF-007 reason names unknown factor {reason.factor!r}")
            share = reason.contribution / item.score
            expected = (
                "Strong"
                if share >= references.STRENGTH_STRONG_AT
                else "Moderate"
                if share >= references.STRENGTH_MODERATE_AT
                else "Slight"
            )
            if reason.strength != expected:
                failures.append(
                    f"FF-007 {reason.factor} contributed {share:.0%} and claims "
                    f"{reason.strength}, not {expected}"
                )
    return failures


def _loaded_and_ranked(tmp):
    """A live application with one storm loaded and its ranking delivered.

    Returns the client as well as the application: FF-003 drives the screen reads through the
    same signed-in session rather than building a second one, so what it exercises is the path
    a reader's browser takes.
    """
    import os

    os.environ.update(
        APP_ENV="test", SESSION_SIGNING_KEY="fitness-gate-key", SESSION_IDLE_TIMEOUT_MINUTES="240",
        SESSION_ABSOLUTE_MAX_HOURS="12", PASSWORD_HASH_COST="4",
        DATABASE_PATH=str(tmp / "gate.db"), SCENARIO_UPLOAD_DIR=str(tmp / "scenarios"),
        SCENARIO_MAX_FILE_BYTES="8388608", SCENARIO_MAX_TOTAL_BYTES="10485760",
        SCENARIO_PARSE_TIMEOUT_SECONDS="120", SCENARIO_STALE_AFTER_HOURS="6",
        TEMP_PASSWORD_EXPIRY_HOURS="24",
        SAMPLE_SCENARIO_DIR=str(
            ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
        ),
        # Off in the gate: nothing this script drives may reach outside the machine.
        LLM_ENABLED="false",
    )
    from app.main import create_app
    from app.store import users
    from fastapi.testclient import TestClient

    fixture = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
    app = create_app()
    users.create_user(
        app.state.db, name="Gate", email="gate@sgw.example", password="gate-password", role="admin"
    )
    client = TestClient(app)
    client.post("/api/v1/auth/session", json={"email": "gate@sgw.example",
                                              "password": "gate-password"})
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "gate", "source_note": "gate"},
        files=[("files", (p.name, p.read_bytes(), "text/csv")) for p in fixture.iterdir()],
    )
    scenario_id = created.json()["scenario_id"]
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    return app, client, scenario_id, ranking


def ff_004_decision_record_is_append_only() -> list[str]:
    """Both triggers exist, **and** an UPDATE issued against the table is refused by the
    database (ADR-004).

    Checking the schema is not enough and the register says so: a trigger can be present and
    disabled, or present and wrong. The only proof is to issue the statement and require the
    refusal.
    """
    import sqlite3
    import tempfile
    from pathlib import Path as _Path

    failures = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        app, _, _, _ = _loaded_and_ranked(_Path(tmpdir))
        connection = app.state.db
        triggers = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'trigger'"
            )
        }
        for name in ("decision_records_no_update", "decision_records_no_delete"):
            if name not in triggers:
                failures.append(f"FF-004 trigger {name} is absent")

        row = connection.execute("select * from decision_records limit 1").fetchone()
        if row is None:
            return [*failures, "FF-004 no decision_records row exists to attempt an UPDATE on"]

        for statement, params in (
            ("update decision_records set payload = '{}' where id = ?", (row["id"],)),
            ("delete from decision_records where id = ?", (row["id"],)),
        ):
            try:
                connection.execute(statement, params)
                connection.commit()
                failures.append(f"FF-004 the database ACCEPTED: {statement.split(' where')[0]}")
            except sqlite3.IntegrityError:
                pass
        connection.close()
    return failures


def ff_005_every_ranking_is_recorded() -> list[str]:
    """Every delivered ranking has a matching `decision_records` row of kind
    `recommendation`, so what was shown can be reconstructed later (REQ-F-009)."""
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        app, _, scenario_id, ranking = _loaded_and_ranked(_Path(tmpdir))
        rows = app.state.db.execute(
            "select * from decision_records where kind = 'recommendation'"
        ).fetchall()
        failures = []
        if len(rows) != 1:
            failures.append(f"FF-005 {len(rows)} recommendation rows for one delivered ranking")
        elif rows[0]["id"] != ranking.get("recommendation_id"):
            failures.append("FF-005 the delivered ranking does not name its recorded row")
        app.state.db.close()
    return failures


# --------------------------------------------------------------------------------------
# FF-003. Restated by CHG-013 before the views existed, wired by TASK-010 after they did.
#
# **Clause (a) — remove a file and open every screen — could not fail on its own**, and the
# register says so: nothing on a render path opens a file, so removing one changed nothing an
# assertion could see. What makes the removal observable is clause **(b)**, which requires the
# loss to be *named* to an admin. So the three clauses are checked as one act and each holds a
# different half of it:
#
#   (b) the loss is named — `integrity.missing_files` is exactly the file that was removed
#   (c) the loss is never read — a recorder over `open` sees no source file opened by any read
#   (a) and the picture is unaffected — every screen still answers, still states its data's
#       age, and answers the *same thing* it answered before the file was lost
#
# (a) is the weakest of the three and it is not decoration: with (b) proving the removal
# happened, (a) is what fails the day somebody makes a screen depend on a file being present —
# `if not integrity["intact"]: raise` is the tidy-looking wrong answer CHG-013 was written
# against, and it is one line away at all times.
#
# **Two ways this check could pass for want of anything to test, both closed below.** The
# storm's files must be on disk before their absence from the reads means anything, and the
# recorder must be shown its own canary before its silence is believed (`AGENT.md`: prove the
# haystack is a haystack before reporting no needle).

SOURCE_FILES = ("manifest.json", "assets.csv", "maintenance.csv", "weather.csv", "outages.csv")

# The two things that legitimately differ between two identical reads of one storm: the age
# moves with the clock, and integrity is what this check is changing.
VOLATILE = frozenset({"data_age_hours", "integrity"})

# FastAPI's own routes. They are GETs and they are not screens; the walk that finds them is
# required to find the application's endpoints too, which is the assertion that matters.
DOCUMENTATION_ROUTES = ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc")

# Node's filesystem, reached from a Next.js render path. Every view is `'use client'` today,
# but `app/page.tsx` and `app/layout.tsx` are server components: one `readFileSync` there is a
# file read per request, and `tsc`, `lint` and `build` all stay green.
FILESYSTEM_REACHES = (
    "'fs'",
    '"fs"',
    "'node:fs'",
    '"node:fs"',
    "'fs/promises'",
    '"fs/promises"',
    "readFileSync",
    "readFile(",
    "createReadStream",
    "openSync(",
)
RENDER_PATH_DIRS = ("app", "views", "lib")


class OpenProbe:
    """Records every path opened while it is installed.

    Three entry points, because one is not the same as three: `pathlib` reaches `io.open`,
    `builtins.open` is what most code calls, and `os.open` is the low-level door underneath
    both. Patching only the first would report silence over a read that happened.
    """

    def __init__(self) -> None:
        self.paths: list[str] = []
        self._saved: dict = {}

    def __enter__(self):
        import builtins
        import io
        import os

        self._saved = {"builtins": builtins.open, "io": io.open, "os": os.open}

        def recording(original):
            def wrapper(file, *args, **kwargs):
                self.paths.append(str(file))
                return original(file, *args, **kwargs)

            return wrapper

        builtins.open = recording(self._saved["builtins"])
        io.open = recording(self._saved["io"])
        os.open = recording(self._saved["os"])
        return self

    def __exit__(self, *_):
        import builtins
        import io
        import os

        builtins.open = self._saved["builtins"]
        io.open = self._saved["io"]
        os.open = self._saved["os"]
        return False

    def canary(self, path) -> int:
        """Open a real file through each patched door. Returns how many were recorded."""
        import io
        import os

        mark = len(self.paths)
        with open(path, "rb"):
            pass
        # ruff is right that this is `open` — and that is the point. `pathlib` reaches the
        # filesystem through this name, so the recorder has to be proven against this name.
        with io.open(path, "rb"):  # noqa: UP020
            pass
        os.close(os.open(path, os.O_RDONLY))
        return len(self.paths) - mark


def _inside(candidate: str, directory) -> bool:
    try:
        return pathlib.Path(candidate).resolve().is_relative_to(directory.resolve())
    except (OSError, ValueError):
        return False


def _picture(payload):
    """One response with the values that legitimately move between reads removed."""
    if isinstance(payload, dict):
        return {k: _picture(v) for k, v in payload.items() if k not in VOLATILE}
    if isinstance(payload, list):
        return [_picture(item) for item in payload]
    return payload


def _ages_stated(payload) -> list:
    """Every `data_age_hours` anywhere in a response body."""
    found = []
    if isinstance(payload, dict):
        if "data_age_hours" in payload:
            found.append(payload["data_age_hours"])
        for value in payload.values():
            found += _ages_stated(value)
    elif isinstance(payload, list):
        for item in payload:
            found += _ages_stated(item)
    return found


def _get_routes(routes) -> set[str]:
    """Every GET path under a routing table, however deeply it is wrapped.

    **This FastAPI (0.141.1) wraps each `include_router` in a `_IncludedRouter` whose own
    `path` is `None`**, so a flat walk of `application.routes` sees the four documentation
    routes and *none* of the application's seventeen endpoints. That is the exact enumeration
    `AGENT.md` records on 2026-08-16 — and it caught this function while it was being written:
    the flat version found nothing and would have reported zero file reads across zero screens.
    """
    found = set()
    for route in routes:
        path = getattr(route, "path", None)
        if path and "GET" in (getattr(route, "methods", None) or set()):
            found.add(path)
        inner = getattr(route, "original_router", None)
        nested = getattr(inner, "routes", ()) if inner is not None else getattr(route, "routes", ())
        found |= _get_routes(nested)
    return found


def _screen_reads(application, scenario_id) -> tuple[list[str], list[str]]:
    """Every GET the application serves, with its path parameters filled.

    **Discovered from the routing table rather than listed here**, so a screen added by a later
    task is covered without anyone remembering to add it — and a GET whose parameters this gate
    cannot fill is reported as uncovered rather than skipped.

    The enumeration is proven before an absence is reported over it: five named endpoints must
    be in what the walk found.
    """
    templates = _get_routes(application.routes)

    failures = [
        f"FF-003 the route walk did not find {required}; it found {sorted(templates)}"
        for required in (
            "/api/v1/scenarios",
            "/api/v1/scenarios/{scenario_id}",
            "/api/v1/scenarios/{scenario_id}/assets",
            "/api/v1/scenarios/{scenario_id}/risks",
            "/api/v1/scenarios/{scenario_id}/jobs",
        )
        if required not in templates
    ]

    urls = []
    for template in sorted(templates - set(DOCUMENTATION_ROUTES)):
        url = template.replace("{scenario_id}", scenario_id)
        if "{" in url:
            failures.append(
                f"FF-003 GET {template} has a parameter this gate cannot fill, so that render "
                "path is not covered; give it a value here rather than leaving it out"
            )
            continue
        urls.append(url)
    return urls, failures


def ff_003_a_lost_source_file_never_reaches_a_screen() -> list[str]:
    """Remove or corrupt each prepared data file in turn, then open every screen.

    (a) every screen renders and states its data's age; (b) the loss is named to an admin;
    (c) no view reads a source file at render time (CHG-013).

    A screen's content is entirely the responses behind it — every view is `'use client'` and
    reaches data only through `lib/api.ts` (ADR-008) — so *opening every screen* is driving
    every GET the application serves. The frontend half of (c) is a source scan below, for the
    one render path that runs in Node rather than in the browser.
    """
    import tempfile
    from pathlib import Path as _Path

    failures: list[str] = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        from app.store import scenarios as scenario_store

        app, client, scenario_id, _ = _loaded_and_ranked(_Path(tmpdir))
        urls, walk_failures = _screen_reads(app, scenario_id)
        if walk_failures:
            # Nothing below means anything over an enumeration that missed the screens.
            app.state.db.close()
            return walk_failures

        upload = scenario_store.find_upload_for_scenario(app.state.db, scenario_id)
        if upload is None or not upload["storage_path"]:
            app.state.db.close()
            return [*failures, "FF-003 the loaded storm has no stored upload to lose a file from"]

        directory = _Path(upload["storage_path"])
        absent = [name for name in SOURCE_FILES if not (directory / name).is_file()]
        if absent:
            # Without this the whole check is the decay it exists to catch: no source file on
            # disk means no source file can be read, and every clause below passes for free.
            app.state.db.close()
            return [
                *failures,
                f"FF-003 the storm's source files are not on disk ({absent}); with nothing "
                "there to read, no clause of this check could fail",
            ]

        scenario_url = f"/api/v1/scenarios/{scenario_id}"

        def read_every_screen(state: str) -> dict:
            """Drive every screen read once, with the recorder installed."""
            probe = OpenProbe()
            # A real source file, and one that is still there: the recorder is proven against
            # exactly the kind of read it is being trusted to report.
            canary = next(p for p in (directory / n for n in SOURCE_FILES) if p.is_file())
            with probe:
                answers = {url: client.get(url) for url in urls}
                during = list(probe.paths)
                recorded = probe.canary(canary)
            if recorded < 3:
                failures.append(
                    f"FF-003 the open recorder saw {recorded} of its own 3 canary reads, so its "
                    "silence during the screen reads proves nothing"
                )
            for path in sorted({p for p in during if _inside(p, directory)}):
                failures.append(f"FF-003(c) a screen read opened the source file {path} ({state})")
            for url, answer in answers.items():
                if answer.status_code != 200:
                    failures.append(
                        f"FF-003(a) GET {url} answered {answer.status_code} ({state})"
                    )
            return answers

        baseline = read_every_screen("every file present")
        ages = [age for answer in baseline.values() for age in _ages_stated(answer.json())]
        if len(ages) < 2:
            failures.append(
                f"FF-003(a) only {len(ages)} screen reads state the age of their data; the "
                "check for an unstated age would have nothing to read"
            )
        for url, answer in baseline.items():
            if any(age is None for age in _ages_stated(answer.json())):
                failures.append(f"FF-003(a) GET {url} renders without stating its data's age")

        # `integrity` is the one thing the picture comparison strips, so nothing below can see
        # a field added to it. Its shape is asserted here instead — the mutation that put a
        # file's byte count in this block was caught by the recorder and by nothing else.
        shape = sorted(baseline[scenario_url].json().get("integrity") or {})
        if shape != ["affects", "intact", "missing_files"]:
            failures.append(
                f"FF-003(b) the integrity notice carries {shape}; it reports presence and the "
                "consequence of a loss, and a field beyond those is invisible to every other "
                "clause of this check"
            )

        for name in SOURCE_FILES:
            path = directory / name
            kept = path.read_bytes()

            path.unlink()
            try:
                answers = read_every_screen(f"{name} removed")
                body = answers[scenario_url].json()
                integrity = body.get("integrity") or {}
                if integrity.get("missing_files") != [name]:
                    failures.append(
                        f"FF-003(b) with {name} removed, the integrity notice names "
                        f"{integrity.get('missing_files')!r} instead of exactly ['{name}']"
                    )
                if integrity.get("intact") is not False or not integrity.get("affects"):
                    failures.append(
                        f"FF-003(b) with {name} removed, the notice does not report it as a "
                        f"loss with a consequence: {integrity!r}"
                    )
                for url, answer in answers.items():
                    if answer.status_code == 200 == baseline[url].status_code and _picture(
                        answer.json()
                    ) != _picture(baseline[url].json()):
                        failures.append(
                            f"FF-003(a) with {name} removed, GET {url} answers something other "
                            "than what it answered while the file was there"
                        )
            finally:
                path.write_bytes(kept)

            # Corruption is deliberately invisible to (b), which asks whether the file is
            # there. It is (c)'s sharper probe: a render path that parsed this file would break
            # on it, including one that never touches Python's `open`.
            path.write_bytes(b"\x00\xff not a prepared file " * 64)
            try:
                answers = read_every_screen(f"{name} corrupted")
                integrity = answers[scenario_url].json().get("integrity") or {}
                if integrity.get("intact") is not True:
                    failures.append(
                        f"FF-003 with {name} corrupted the integrity notice reports a loss "
                        f"({integrity!r}); it reports presence, and content is nobody's on a "
                        "render path (CHG-013)"
                    )
                for url, answer in answers.items():
                    if answer.status_code == 200 == baseline[url].status_code and _picture(
                        answer.json()
                    ) != _picture(baseline[url].json()):
                        failures.append(
                            f"FF-003(a) with {name} corrupted, GET {url} answers something "
                            "other than what it answered while the file was sound"
                        )
            finally:
                path.write_bytes(kept)

        app.state.db.close()

    return failures + ff_003_no_view_reaches_for_a_file()


def ff_003_no_view_reaches_for_a_file() -> list[str]:
    """(c), the half that runs in Node: no render-path module reaches for the filesystem.

    A static scan, and FF-002(b)'s shape for FF-002(b)'s reason — the process line makes the
    *browser* half of this structurally impossible, and moves what is left to the one render
    path that is not in a browser. `frontend/e2e/` is out of scope on purpose: a Playwright
    spec reads a fixture off disk to upload it, which is a test harness rather than a screen.
    """
    sources = [
        path
        for directory in RENDER_PATH_DIRS
        for suffix in ("*.ts", "*.tsx")
        for path in (FRONTEND / directory).rglob(suffix)
        if "node_modules" not in path.parts and ".next" not in path.parts
    ]
    named = FRONTEND / "views" / "ScenarioView.tsx"
    if named not in sources:
        # The haystack, before the needle is reported absent.
        return [
            f"FF-003(c) the frontend scan did not find {named.name}; it found "
            f"{sorted(p.name for p in sources)}"
        ]

    failures = []
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for reach in FILESYSTEM_REACHES:
            if reach in text:
                failures.append(
                    f"FF-003(c) {path.relative_to(ROOT)} reaches for the filesystem ({reach!r}); "
                    "every read is served from stored rows (technical-spec.md, section 6)"
                )
    return failures


def main() -> int:
    failures = ff_001_no_import_cycle() + ff_002_scoring_stays_behind_the_api()
    failures += ff_006_seven_defects_caught() + ff_007_no_reason_outruns_its_arithmetic()
    failures += ff_004_decision_record_is_append_only() + ff_005_every_ranking_is_recorded()
    failures += ff_003_a_lost_source_file_never_reaches_a_screen()

    if failures:
        print("\nFITNESS GATE FAILED")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\n  FF-001  ok - no import cycle")
    print("  FF-002  ok - scoring stays behind the API; no scoring constant in the frontend")
    print("  FF-003  ok - 5 files lost and 5 corrupted; each named, none read, no screen moved")
    print("  FF-004  ok - both triggers present, and the database refused a real UPDATE")
    print("  FF-005  ok - the delivered ranking names its recorded recommendation")
    print("  FF-006  ok - 7 of 7 defects caught by their own check")
    print("  FF-007  ok - every reason names a real factor and claims the strength it earned")
    print("\nFITNESS GATE PASSED (7 of 7 wired)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
