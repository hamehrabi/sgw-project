"""Reading a `.env` file into the environment, at the edges only.

`config.py` reads `os.environ` and nothing else, and that stays true: the specification says
configuration is environment variables, and a library that quietly reads a file behind its
caller's back is a different thing wearing the same name.

**So this is called by entry points and never by library code.** `app.cli` calls it, and
`ci/serve.py` calls it. `load_config()` and `create_app()` do not — which is what keeps the
test suite honest: `test_TASK-001-AC7_startup_fails_on_missing_config` deletes a variable and
requires startup to fail, and it would pass for the wrong reason forever if importing the
config module silently restored the value from a file on disk.

**Never overrides a variable that is already set.** A real environment variable beats the
file, so a deployment that sets `DATABASE_PATH` properly is not undone by a stale `.env` left
in the working directory.
"""

import os
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> list[str]:
    """Set any variable the file names that is not already in the environment.

    Returns the names it set, so a caller can say what it did rather than acting invisibly.
    """
    file = Path(path)
    if not file.is_file():
        return []

    applied = []
    for raw in file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip()
        # Quotes are how a value with spaces survives a shell; they are not part of the value.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value
            applied.append(name)
    return applied
