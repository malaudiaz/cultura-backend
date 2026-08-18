import os
import subprocess
import sys


def test_database_url_is_required():
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)

    result = subprocess.run(
        [sys.executable, "-c", "import app.database"],
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode != 0
    assert "DATABASE_URL must be configured" in result.stderr
