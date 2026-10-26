import zipfile
from http.client import IncompleteRead
from unittest.mock import MagicMock, patch
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from harness.spot_data import _fetch, iter_bars, parse_timestamp


def test_fetch_retries_truncated_archive():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b"complete"
    with patch("harness.spot_data.urllib.request.urlopen", side_effect=[IncompleteRead(b"partial", 1), response]), patch("harness.spot_data.time.sleep"):
        assert _fetch("https://example.invalid/archive.zip", 1) == b"complete"


def _archive(path, rows):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("BTCUSDT-1m-2025-01.csv", "\n".join(rows))


def test_spot_timestamps_milliseconds_and_microseconds():
    expected = datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert parse_timestamp("1735689600000") == expected
    assert parse_timestamp("1735689600000000") == expected


def test_spot_archive_streams_ordered_bars():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "bars.zip"
        _archive(path, [
            "1735689600000000,10,11,9,10.5,3,0,0,0,0,0,0",
            "1735689660000000,10.5,12,10,11,2,0,0,0,0,0,0",
        ])
        bars = list(iter_bars(path))
        assert len(bars) == 2
        assert bars[0].open_time == datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert bars[1].close == 11


def test_spot_archive_rejects_duplicate_time():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "bars.zip"
        row = "1735689600000000,10,11,9,10.5,3,0,0,0,0,0,0"
        _archive(path, [row, row])
        try:
            list(iter_bars(path))
        except ValueError as exc:
            assert "duplicadas" in str(exc)
        else:
            raise AssertionError("duplicate candle accepted")


if __name__ == "__main__":
    test_spot_timestamps_milliseconds_and_microseconds()
    test_spot_archive_streams_ordered_bars()
    test_spot_archive_rejects_duplicate_time()
    print("spot data tests ok")
