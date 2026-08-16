"""Start the backend for local use, reading `.env` first.

    python ci/serve.py            # http://127.0.0.1:8000
    python ci/serve.py --port 9000

`uvicorn app.main:create_app --factory` works just as well once the environment is already
set. This exists so that starting the application does not require remembering to export
eleven variables first — the startup failure for a missing one is deliberate (ADR-006), and
it should fire because a value is genuinely absent, not because a shell forgot to load it.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.envfile import load_env_file  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    arguments = parser.parse_args(argv)

    applied = load_env_file(arguments.env_file)
    print(f"Loaded {len(applied)} setting(s) from {arguments.env_file}")

    import uvicorn
    from app.config import ConfigError

    try:
        uvicorn.run(
            "app.main:create_app",
            factory=True,
            host=arguments.host,
            port=arguments.port,
            log_level="info",
        )
    except ConfigError as error:
        # The named startup failure, said plainly rather than as a traceback.
        print(f"\nCannot start: {error}", file=sys.stderr)
        print(f"Add it to {arguments.env_file} and try again.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
