"""STEST-006 — SEC-Z-002. Defined in `03-tests/03-non-functional/security-tests.md`.

Upload a file whose extension is on the allow-list but whose content is not. Then one over
the size limit. Expect 415 and 413 respectively, both refused **before parsing**, both
naming the file.

"Type on the allow-list, verified by **content inspection** rather than by extension"
(`security-specification.md` §3). An extension is a claim made by whoever uploaded the file,
which in any realistic threat model is the attacker.
"""

from conftest import fixture_files, sign_in


def upload(client, files):
    return client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (name, content, "text/csv")) for name, content in files.items()],
    )


def as_admin(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])


def test_a_binary_file_wearing_a_csv_extension_is_refused(client, accounts):
    as_admin(client, accounts)
    files = fixture_files()
    # A PNG header. The name says .csv; the bytes say otherwise.
    files["assets.csv"] = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 64

    response = upload(client, files)

    assert response.status_code == 415


def test_the_type_refusal_names_the_file(client, accounts):
    as_admin(client, accounts)
    files = fixture_files()
    files["assets.csv"] = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 64

    response = upload(client, files)

    # The status is asserted here as well as in the test above, and not by duplication: a
    # loader that read the PNG and gave up would answer 422 and *also* name the file, so
    # without the status this passes while the content check is gone. Found by mutation.
    assert response.status_code == 415
    assert "assets.csv" in response.json()["message"]


def test_an_oversize_file_is_refused(client, accounts):
    """SCENARIO_MAX_FILE_BYTES is 4096 in the suite and 8 MB in `.env.example`."""
    as_admin(client, accounts)
    files = fixture_files()
    files["weather.csv"] = b"grid_cell_id,asset_id,valid_time,wind_gust_mph,rainfall_in\n" + (
        b"GC-01,,2026-08-15T00:00:00Z,96,0.8\n" * 400
    )

    response = upload(client, files)

    assert response.status_code == 413
    assert "weather.csv" in response.json()["message"]


def test_a_scenario_over_the_total_limit_is_refused(client, accounts):
    as_admin(client, accounts)
    files = fixture_files()
    for index in range(8):
        files[f"filler-{index}.csv"] = b"a,b\n" + b"1,2\n" * 500

    assert upload(client, files).status_code == 413


def test_a_refused_upload_writes_nothing(client, application, accounts, env):
    """Refused **before parsing**, so nothing reaches the disk or the database."""
    import pathlib

    as_admin(client, accounts)
    files = fixture_files()
    files["assets.csv"] = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 64

    upload(client, files)

    upload_dir = pathlib.Path(env["SCENARIO_UPLOAD_DIR"])
    stored = [p for p in upload_dir.rglob("*") if p.is_file()] if upload_dir.exists() else []
    assert stored == []
    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == 0


def test_the_stored_name_contains_no_part_of_the_supplied_filename(client, accounts, env):
    """`security-specification.md` §7, acceptance criterion 5 of the upload block."""
    import pathlib

    as_admin(client, accounts)
    files = fixture_files()

    upload(client, files)

    upload_dir = pathlib.Path(env["SCENARIO_UPLOAD_DIR"])
    directories = [p.name for p in upload_dir.iterdir()] if upload_dir.exists() else []
    assert directories, "an accepted upload is stored"
    assert all("helene" not in name.lower() for name in directories)
