import os
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from harness.config_snapshot import snapshot


def test_snapshot_excludes_credentials_and_is_stable():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "bot.db"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE settings(user_id INTEGER,key TEXT,value TEXT)")
        connection.execute("CREATE TABLE state(user_id INTEGER,key TEXT,value TEXT)")
        connection.executemany("INSERT INTO settings VALUES(1,?,?)", [
            ("active_strategy", "smart_scalping"),
            ("timeframe", "1m"),
            ("api_secret", "PRIVATE"),
        ])
        connection.execute("INSERT INTO state VALUES(1,'enable_buying','True')")
        connection.commit()
        connection.close()
        result = snapshot(path, 1)
        assert result["settings"]["timeframe"] == "1m"
        assert "api_secret" not in result["settings"]
        assert result["state"]["enable_buying"] == "True"
        assert snapshot(path, 1)["sha256"] == result["sha256"]


if __name__ == "__main__":
    test_snapshot_excludes_credentials_and_is_stable()
    print("config snapshot tests ok")
